"""Proyecto nuevo: de la plantilla al libro de salida, en una sola pasada.

Es el punto de entrada del generador. Lee `Plantilla_Proyecto_Nuevo.xlsx`,
deriva el calendario de sus fechas, arma la cadena de construccion, dimensiona
la deuda, cierra el PPDI, cierra la tarifa variable del PPDMO con el modelo
sombra estructural y escribe un libro de Excel con formulas vivas: el resumen y
la malla completa, la misma informacion que dan los modelos aprobados.

Del libro de Cajamarca ya no queda ninguna serie salvo dos primitivas que van en
cero para un proyecto nuevo y estan declaradas como tales: el efecto ITAN, que
necesita el balance, y el tramo complementario de deuda de `M.Sombra!192:195`.
Al Ke del modelo valen -376 y +305 S/ miles de valor presente.

Eso esta comprobado, no supuesto: `proyecto_ficticio.py` corre una PTAR
inventada con otras fechas y otros costos, y envenenando las series del JSON de
Cajamarca el resultado no se mueve ni en la ultima cifra.
"""
import calendario_caj as C
import deuda_cajamarca as DE
import escribir_excel as EX
import flujo_cajamarca as FL
import intangible_caj as IN
import leer_plantilla as LP
import motor_cajamarca as M
import sombra_cajamarca as S
import tributos_cajamarca as TR

COSTOS_OP = ("seguros", "fianzas", "promocion", "fideicomiso")


def _tributos(p):
    """Las tasas de la plantilla, a los tres modulos que las usan.

    Sin esto el usuario puede escribir otro IR o otro IGV y el cierre no se
    entera: los motores nacieron con las tasas del libro de Cajamarca dentro.
    """
    igv, ir = p["IGV"], p["Impuesto a la Renta"]
    part, sup = p["Participacion de trabajadores"], p["Supervision del regulador"]
    M.usar_tributos(igv, ir)
    TR.usar_tributos(part, ir)
    S.usar_tributos(part, ir, sup)


def _a_trim(mensual, cal):
    out = [0.0] * cal["nq"]
    for m in range(cal["nm"]):
        out[cal["trim_m"][m] - 1] += mensual[m]
    return out


def correr(ruta=LP.RUTA, kd=None, ke=None, wacc=None, ipm=None,
           extras_del_libro=False):
    kd = DE.KD_LIBRO if kd is None else kd
    ke = S.KE_LIBRO if ke is None else ke
    wacc = M.WACC_M if wacc is None else wacc
    d = LP.leer(ruta)
    p, fechas = d["proyecto"], d["fechas"]
    ipm = p["IPM, reajuste de ingresos"] if ipm is None else ipm
    cuotas = int(p["Numero de cuotas del PPDI"])

    # 1. Calendario y tributos, derivados solo de la plantilla
    _tributos(p)
    cal = C.calendario(fechas, p["Inicio de operacion"], p["Fin de la concesion"])
    n_motor = fechas.index(p["Fin de la concesion"]) + 1
    M.usar_calendario(C.malla_ppdi(fechas, p["Inicio de operacion"], cuotas, n_motor))
    FL.usar_calendario(cal, cuotas, extras_del_libro)

    # 2. Construccion y deuda
    con, ser, otros = LP.construccion(d), LP.series(d), d["otros"]
    i0 = fechas.index(p["Inicio del pago de deuda"])
    i1 = fechas.index(p["Fin del pago de deuda"])
    f33 = [1 if i0 <= i <= i1 else 0 for i in range(len(fechas))]
    deu = DE.corrida(kd, p["Tamano de deuda"], con["inversion"],
                     con["flag_obra"], f33)

    enc = lambda s: (list(s) + [0.0] * M.N)[:M.N]
    mes_estr = next(i for i in range(len(fechas)) if con["flag_obra"][i])
    ext = {"obra": enc(con["costo_obra"]), "fid": enc(otros["fideicomiso"]),
           "seg": enc(otros["seguros"]), "gar": enc(otros["garantias"]),
           "reem": enc(otros["reembolso"]),
           "estr": enc([deu["costo_estructuracion"] if i == mes_estr else 0.0
                        for i in range(len(fechas))]),
           "com": enc(deu["costo_no_uso"])}

    # 3. Cierre del PPDI: VAN del flujo antes de deuda al WACC = 0.
    #    El motor descuenta con tasa mensual; `wacc` entra anual salvo que ya
    #    venga mensual, como el del propio libro.
    wacc_m = wacc if wacc < 0.02 else (1 + wacc) ** (1 / 12) - 1
    gf = enc(deu["interes"])
    ppdi = M.cerrar(rate=wacc_m, gfin_ext=gf, ext=ext) * 12

    # 4. Cierre de la tarifa variable: VAN del flujo de caja financiero al Ke = 0
    pad = lambda s: (list(s) + [0.0] * cal["nm"])[:cal["nm"]]
    costos = {k: _a_trim(pad(ser[k]), cal)
              for k in ("costo_fijo", "costo_var", "gastos_spv")}
    costos.update({k: _a_trim(pad(d["otros_op"][k]), cal) for k in COSTOS_OP})
    comun = dict(ipm=ipm, ke=ke, kd=kd, ppdi=ppdi, kg=pad(ser["kg"]),
                 fijo_base_cte=ser["fijo_base_cte"], costos=costos,
                 deuda=deu, ext=ext, gfin_ext=gf,
                 # Dato de la zona: bajo la ley de la Amazonia el PPD no lleva
                 # IGV y el soportado en O&M es costo. Cajamarca no lo esta, asi
                 # que su defecto es cero y el libro se reproduce igual.
                 exonera_igv=int(p.get(
                     "Zona con exoneracion de IGV (ley de la Amazonia)", 0)),
                 igv=p["IGV"])
    tarifa = FL.cerrar(**comun)
    r = FL.flujo(tarifa, **comun)

    # 5. El activo financiero del PPDI, con la misma corrida que cerro el PPDI.
    #    CINIIF 12 p.16: el cobro es incondicional, asi que la obra es cuenta
    #    por cobrar y no intangible; su amortizacion se expone aparte.
    af = M.corrida(ppdi / 12, gfin_ext=gf, ext=ext)
    af["flag"], af["paga"], af["n"] = M.flag[:M.N], M.paga[:M.N], M.N
    return {"d": d, "cal": cal, "con": con, "ser": ser, "deu": deu, "r": r,
            "ppdi": ppdi, "tarifa": tarifa, "ipm": ipm, "af": af,
            "kd": kd, "ke": ke, "wacc": wacc, "cuotas": cuotas}


def payload(g):
    """Arma lo que consume el escritor del libro de salida."""
    d, cal, r, ser = g["d"], g["cal"], g["r"], g["ser"]
    p, deu, nq = d["proyecto"], g["deu"], cal["nq"]
    pad = lambda s: (list(s) + [0.0] * cal["nm"])[:cal["nm"]]
    fijo_base = ser["fijo_base_cte"] * (1 + (1 + g["ipm"]) ** (1 / 12) - 1)
    return {
        "inputs": {
            "costo_obra": sum(g["con"]["inversion"]),
            "tamano_deuda": p["Tamano de deuda"], "kd": g["kd"],
            "spread": p["Spread sobre el soberano"], "ke": g["ke"],
            "wacc": g["wacc"], "pagos": deu["pagos"], "ipm": g["ipm"],
            "gatillo": p["Gatillo del reajuste"],
            "ipc": p["IPC, reajuste de costos"],
            "ir": p["Impuesto a la Renta"],
            "part": p["Participacion de trabajadores"],
            "superv": p["Supervision del regulador"],
            "margen_cf": p["Margen del costo fijo"], "fijo_base": fijo_base,
            "tarifa": g["tarifa"], "ppdi_anual": g["ppdi"],
        },
        "meses": {
            "fecha": d["fechas"], "flag_obra": g["con"]["flag_obra"],
            "flag_deuda": pad(deu["flag_pago"]),
            "inversion": g["con"]["inversion"], "flag_om": cal["flag_om"],
            "flag_trim": cal["flag_t"], "flag_pago": cal["flag_p"],
            "kg": pad(ser["kg"]),
        },
        "mes_base": deu["mes_base"],
        "activo": {
            "fecha": d["fechas"][:g["af"]["n"]],
            "flag": g["af"]["flag"], "paga": g["af"]["paga"],
            "sc": g["af"]["sc"], "ing_fin": g["af"]["ing_fin"],
            "cobro": g["af"]["cobro"], "saldo": g["af"]["af"],
            # amortizacion = cobro del mes menos ingreso financiero devengado,
            # SIN truncar en cero: en los meses sin cobro el activo crece.
            "amort": [g["af"]["cobro"][t] - g["af"]["ing_fin"][t]
                      for t in range(g["af"]["n"])],
            "tasa": g["af"]["r"],
        },
        "trimestres": {
            "anio": cal["anio"], "trim": cal["trim"], "meses": cal["meses"],
            "ppdi_perfil": FL.PERFIL_PPDI, "fijo": r["fijo"], "var": r["var"],
            "costo_fijo": _a_trim(pad(ser["costo_fijo"]), cal),
            "costo_var": _a_trim(pad(ser["costo_var"]), cal),
            "gastos_spv": _a_trim(pad(ser["gastos_spv"]), cal),
            "seguros": _a_trim(pad(d["otros_op"]["seguros"]), cal),
            "fianzas": _a_trim(pad(d["otros_op"]["fianzas"]), cal),
            "promocion": _a_trim(pad(d["otros_op"]["promocion"]), cal),
            "fideicomiso": _a_trim(pad(d["otros_op"]["fideicomiso"]), cal),
            # las dos primitivas que faltan por modelar, en cero y declaradas
            "itan": [0.0] * nq, "des2": [0.0] * nq, "srv2": [0.0] * nq,
            "capex": [-x for x in r["sc"]], "igv": r["igv"],
            "interes": [-x for x in r["interes"]],
            "impuestos": r["impuestos"], "desembolso": r["desembolso"],
            "servicio": r["servicio"], "flag_superv": cal["flag_superv"],
        },
    }


# =========================================================== AUTOFINANCIADA
def _primitivas(d, kd):
    """Lo que no depende del regimen: calendario, construccion, deuda, OPEX."""
    p, fechas = d["proyecto"], d["fechas"]
    _tributos(p)
    cal = C.calendario(fechas, p["Inicio de operacion"], p["Fin de la concesion"])
    con, ser, otros = LP.construccion(d), LP.series(d), d["otros"]
    i0 = fechas.index(p["Inicio del pago de deuda"])
    i1 = fechas.index(p["Fin del pago de deuda"])
    f33 = [1 if i0 <= i <= i1 else 0 for i in range(len(fechas))]
    deu = DE.corrida(kd, p["Tamano de deuda"], con["inversion"],
                     con["flag_obra"], f33)
    nm = cal["nm"]
    enc = lambda x: (list(x) + [0.0] * nm)[:nm]
    mes_estr = next(i for i in range(len(fechas)) if con["flag_obra"][i])
    ext = {"obra": enc(con["costo_obra"]), "fid": enc(otros["fideicomiso"]),
           "seg": enc(otros["seguros"]), "gar": enc(otros["garantias"]),
           "reem": enc(otros["reembolso"]),
           "estr": enc([deu["costo_estructuracion"] if i == mes_estr else 0.0
                        for i in range(len(fechas))]),
           "com": enc(deu["costo_no_uso"])}
    sc = [sum(ext[k][m] for k in ext) for m in range(nm)]
    costos = {k: _a_trim(enc(ser[k]), cal)
              for k in ("costo_fijo", "costo_var", "gastos_spv")}
    costos.update({k: _a_trim(enc(d["otros_op"][k]), cal) for k in COSTOS_OP})
    return cal, con, ser, deu, ext, sc, costos


def correr_auto(ruta=LP.RUTA, kd=None, ke=None, wacc=None, ipm=None):
    """Rama autofinanciada: no hay PPDI ni PPDMO, cierra la tarifa al usuario."""
    kd = DE.KD_LIBRO if kd is None else kd
    ke = S.KE_LIBRO if ke is None else ke
    wacc = M.WACC_M if wacc is None else wacc
    d = LP.leer(ruta)
    p = d["proyecto"]
    ipm = p["IPM, reajuste de ingresos"] if ipm is None else ipm
    cal, con, ser, deu, ext, sc, costos = _primitivas(d, kd)
    nm = cal["nm"]
    comun = dict(ke=ke, kd=kd, kg=(list(ser["kg"]) + [0.0] * nm)[:nm],
                 costos=costos, deuda=deu, sc=sc, cal=cal, ext=ext,
                 igv_tasa=p["IGV"], superv=p["Supervision del regulador"],
                 exonera_igv=int(p.get(
                     "Zona con exoneracion de IGV (ley de la Amazonia)", 0)))
    tarifa = IN.cerrar(ipm, **comun)
    r = IN.flujo(tarifa, ipm, **comun)
    return {"d": d, "cal": cal, "con": con, "ser": ser, "deu": deu, "r": r,
            "tarifa": tarifa, "ipm": ipm, "kd": kd, "ke": ke, "wacc": wacc,
            "ext": ext, "sc": sc, "_ruta": ruta}


# NO sacar el margen del operador del gemelo cofinanciado, aunque sea tentador
# porque ahi el pago al operador existe y tiene nombre. Se probo y esta mal de
# raiz: el PPDMO de Cajamarca **no** se descompone en costo mas margen. Medido en
# VAN al Ke, la pata FIJA vale 36,736.45 contra 47,804.52 de costo fijo, o sea
# **0.7685 veces su costo**, y la VARIABLE 157,597.06 contra 98,108.38, **1.6064
# veces**. El 60.6 % que lleva encima la variable es el **cierre**, no el margen:
# esa pata absorbe lo que el PPDI no recupera. Tomar `VAN(PPDMO)/VAN(costo) - 1`
# = 17.00 % mete el cierre de un regimen dentro de la respuesta del otro y llama
# "operacion" a parte de la recuperacion de la inversion cofinanciada. El margen
# del operador es un dato del OPERADOR, no de como se financio la obra, y por eso
# sale de la plantilla.


def payload_auto(g, margen_om=None):
    d, cal, r, ser = g["d"], g["cal"], g["r"], g["ser"]
    p, deu, nm = d["proyecto"], g["deu"], cal["nm"]
    enc = lambda x: (list(x) + [0.0] * nm)[:nm]
    interes = enc(deu["interes"])
    return {
        "inputs": {
            "costo_obra": sum(g["con"]["inversion"]),
            "tamano_deuda": p["Tamano de deuda"], "kd": g["kd"],
            "spread": p["Spread sobre el soberano"], "ke": g["ke"],
            "wacc": g["wacc"], "pagos": deu["pagos"], "ipm": g["ipm"],
            "gatillo": p["Gatillo del reajuste"],
            "ipc": p["IPC, reajuste de costos"],
            "ir": p["Impuesto a la Renta"],
            "part": p["Participacion de trabajadores"],
            "superv": p["Supervision del regulador"], "igv": p["IGV"],
            "tarifa_usuario": g["tarifa"],
            # El margen del operador, de la plantilla, aplicado a TODO el
            # costo de O&M: en autofinanciada no hay pata fija y variable que
            # separar, el operador opera el servicio entero. Ver el comentario
            # de arriba sobre por que NO se saca del gemelo cofinanciado.
            "margen_om": (p["Margen del costo fijo"] if margen_om is None
                          else margen_om),
        },
        "meses": {
            "fecha": d["fechas"][:nm], "flag_obra": g["con"]["flag_obra"][:nm],
            "flag_deuda": enc(deu["flag_pago"]),
            "inversion": g["con"]["inversion"][:nm], "flag_om": cal["flag_om"],
            "trim_m": cal["trim_m"], "kg": enc(ser["kg"]),
        },
        "mes_base": deu["mes_base"],
        # 1 en los meses anteriores a la operacion. No es `1 - flag_om`: la
        # malla dura mas que la concesion y ahi `flag_om` tambien es 0.
        "intangible": {"flag_obra": [1 if m < r["intangible"]["mes_inicio_op"]
                                     else 0 for m in range(nm)],
                       "sc": g["sc"], "interes": interes,
                       "amort": r["amort_m"], "saldo": r["saldo_m"],
                       "base": r["intangible"]["base"],
                       "n_op": r["intangible"]["meses_operacion"]},
        "trimestres": {
            "anio": cal["anio"], "trim": cal["trim"], "meses": cal["meses"],
            "costo_fijo": _a_trim(enc(ser["costo_fijo"]), cal),
            "costo_var": _a_trim(enc(ser["costo_var"]), cal),
            "gastos_spv": _a_trim(enc(ser["gastos_spv"]), cal),
            "seguros": _a_trim(enc(d["otros_op"]["seguros"]), cal),
            "fianzas": _a_trim(enc(d["otros_op"]["fianzas"]), cal),
            "promocion": _a_trim(enc(d["otros_op"]["promocion"]), cal),
            "fideicomiso": _a_trim(enc(d["otros_op"]["fideicomiso"]), cal),
            "capex_caja": r["sc"], "igv": r["igv"],
            "interes_op": r["interes_op"], "impuestos": r["impuestos"],
            "desembolso": r["desembolso"], "servicio": r["servicio"],
        },
    }


if __name__ == "__main__":
    import json
    A = json.load(open("/mnt/project-files/generador/cajamarca_actualizado.json"))
    t = json.loads(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else {}
    ruta_pl = t.get("plantilla", LP.RUTA)
    regimen = LP.leer(ruta_pl)["proyecto"]["Regimen de la APP"].strip().lower()
    kw = dict(kd=A["hoy"]["kd"], ke=A["hoy"]["ke"], wacc=A["hoy"]["wacc"])
    if regimen.startswith("autofinanciada"):
        g = correr_auto(ruta_pl, **kw)
        nombre = g["d"]["proyecto"]["Nombre del proyecto"].replace(" ", "_")
        ruta = EX.escribir_auto(
            payload_auto(g),
            f"/mnt/project-files/generador/{nombre}_autofinanciada.xlsx")
        ai = g["r"]["intangible"]
        print("escrito:", ruta, " regimen: autofinanciada (activo intangible)")
        print(f"  tarifa al usuario  {g['tarifa']:>14,.7f} S/ por kg DBO5")
        print(f"  intangible al termino de obra {ai['base']:>14,.2f} S/ miles")
        print(f"    inversion        {ai['inversion']:>14,.2f}")
        print(f"    interes capitalizado {ai['interes_capitalizado']:>10,.2f}")
        print(f"  amortizacion mensual {ai['base']/ai['meses_operacion']:>12,.2f}"
              f"   ({ai['meses_operacion']} meses)")
        print(f"  VAN financiero     {g['r']['van']:>14,.8f}")
    else:
        g = correr(ruta_pl, **kw)
        nombre = g["d"]["proyecto"]["Nombre del proyecto"].replace(" ", "_")
        ruta = EX.escribir(payload(g),
                           f"/mnt/project-files/generador/{nombre}_generado.xlsx")
        print("escrito:", ruta, " regimen: cofinanciada (activo financiero)")
        print(f"  PPDI anual        {g['ppdi']:>14,.4f} S/ miles")
        print(f"  tarifa variable   {g['tarifa']:>14,.7f} S/ por kg DBO5")
        print(f"  VAN del sombra    {g['r']['van']:>14,.8f}")
