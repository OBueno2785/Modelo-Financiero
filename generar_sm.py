"""Proyecto nuevo con pago por hitos funcionales: de la plantilla al cierre.

Lee la plantilla (hojas `Hitos` y `OPEX hitos` para el esquema por hitos, y
`CAPEX` y `Otros` para la malla de construccion), deriva el calendario, cierra
el PPDI con `motor_sanmartin` y cierra todo el PPDMO con `flujo_sm`, que arma el
flujo anual linea por linea.

La plantilla viene precargada con Cajamarca en `CAPEX` y `Otros`, que es el otro
esquema; para un proyecto por hitos esas dos hojas hay que reemplazarlas por la
malla del proyecto. `correr` acepta las series por parametro para poder
contrastar la cadena contra el libro de San Martin.
"""
import calendario_sm as C
import flujo_sm as F
import ingresos_sm as I
import leer_plantilla as LP
import motor_ppdmo_sm as Q
import motor_sanmartin as M
import opex_sm as O


# Reparto que deja toda la referencia en la pata variable: en autofinanciada no
# hay patas fijas por hito, solo la tarifa al usuario. `referencias()` lo lee
# igual que el reparto real, asi que no hace falta otra ruta de calculo.
REP_AUTO = {"e": [0.0, 0.0, 0.0], "d83": 1.0, "d84": 0.0, "d87": 1.0, "d88": 0.0}


def _opcional(d, nombre, defecto):
    """Como `_param`, pero para parametros que las plantillas viejas no traen."""
    for hoja in ("proyecto", "hitos"):
        v = d.get(hoja, {}).get(nombre)
        if v is not None:
            return v
    return defecto


def _param(d, nombre):
    """Busca un parametro primero en `Proyecto` y despues en `Hitos`."""
    for hoja in ("proyecto", "hitos"):
        v = d.get(hoja, {}).get(nombre)
        if v is not None:
            return v
    raise KeyError(f"la plantilla no trae '{nombre}' ni en Proyecto ni en Hitos")


def _ap(h):
    pct, mes = [], []
    for i in (1, 2, 3):
        p = h.get(f"Aporte {i}, porcentaje")
        if p:
            pct.append(p)
            mes.append(int(h[f"Aporte {i}, mes del contrato"]))
    return pct, mes


def preparar(construccion, ruta=LP.RUTA, kd=None, tasa_reparto=None, wacc=None, tir=None,
             ipm=None, reserva=0.0, flag_op=None, ir=0.295, pt=0.05,
             rcsd=None, crsd_obj=None, arrastre=0.5, plazo_gf=10.0, pmp=1.0,
             desfase_ppdi=1, desfase_ppdmo=3, regimen=None, exonera_igv=None):
    """`construccion` trae las mallas mensuales de capex, otros e igv de las
    necesidades de financiamiento, y `igv_flujo`, la variacion anual del IGV de
    construccion que entra al flujo de caja (`FC!36`)."""
    d = LP.leer(ruta)
    h, lin = d["hitos"], d["opex_hitos"]
    anio0, n = int(h["Primer ano de la malla"]), int(h["Meses de la malla"])
    cal = C.calendario(anio0, n, h["Inicio del periodo D + C + PM"],
                       h["Fin del periodo D + C + PM"],
                       h["Primer pago del PPDI"])
    cal["flag_op"] = (flag_op if flag_op is not None
                      else _flag_op(cal, n, anio0, h.get("Fin de la operacion")))

    M.APAL, M.UPF, M.COMM = (h["Apalancamiento"],
                             h["Comision de estructuracion"],
                             h["Comision por no uso"])
    M.MES_CF = int(h["Mes del cierre financiero"])
    M.AP_PCT, M.AP_MES = _ap(h)
    M.usar_entrada(cal, construccion["capex"], construccion["otros"],
                   construccion["igv"], h["Capital de trabajo inicial"], reserva)
    reg = (regimen or d["proyecto"].get("Regimen de la APP", "cofinanciada"))
    auto = str(reg).strip().lower().startswith("auto")
    if auto:
        # Sin PPDI no hay nada que cerrar en el bloque de construccion: las
        # necesidades de financiamiento no dependen del PPDI, solo lo repagan.
        nec, ppdi = M.necesidades(kd), 0.0
    else:
        ppdi, van_nec, nec = M.ppdi_anual(wacc, kd)

    ny = len(lin["fijo_h1"])
    anio_mes = cal["anio"]
    an = lambda m: F._anual(m, anio_mes, ny, anio0)
    _om = O.series(lin, anio_mes, cal["flag_op"], ipm, anio0, ny,
                   C.ventana_reajuste(cal))
    cst = _om["anual"]
    fop = [sum(cal["flag_op"][t] for t in range(n)
               if int(anio_mes[t]) - anio0 == i) / 12 for i in range(ny)]
    fdc = [sum(cal["flag_dcpm"][t] for t in range(n)
               if int(anio_mes[t]) - anio0 == i) / 12 for i in range(ny)]

    ent = dict(
        ny=ny, cal=cal, anio0=anio0, fop=fop, fdc=fdc,
        fcon=[min(1.0, fop[i] + fdc[i]) for i in range(ny)],
        # Ojo: el reparto del PPDMO y el descuento del ultimo pago usan la
        # tasa de `Ingresos!D80`, que es el **WACC**, no el Ke del accionista.
        kd=kd, tir=tir, ke_mensual=(1 + tasa_reparto) ** (1 / 12) - 1,
        # El RCSD y la reserva viven en la hoja `Proyecto`. `Hitos` queda como
        # respaldo para las plantillas escritas antes de que subieran alli.
        ir=ir, pt=pt, rcsd=rcsd or _param(d, "Cobertura minima RCSD"),
        crsd_obj=crsd_obj or _param(d, "Cuenta de reserva CRSD"),
        base_arrastre=arrastre, plazo_gf=plazo_gf,
        # Dato de la zona, no preferencia: bajo la ley de la Amazonia el PPD no
        # lleva IGV y el soportado en O&M no tiene contra que acreditarse, asi
        # que es costo. Fuera de esas zonas se repercute y se lava. Ausente en
        # las plantillas viejas, donde `igv_op` ya venia como costo: por eso el
        # respaldo es 1 y San Martin sigue reproduciendose igual.
        exonera_igv=int(exonera_igv if exonera_igv is not None else _opcional(
            d, "Zona con exoneracion de IGV (ley de la Amazonia)", 1)),
        regimen=("autofinanciada" if auto else "cofinanciada"),
        # El reparto del PPDMO sale del O&M **del proyecto**, no del libro:
        # `Q.repartos` lee las series de `sanmartin_anual.json` y dejaba a
        # cualquier proyecto nuevo con el perfil fijo/variable de San Martin.
        rep=(REP_AUTO if auto else I.repartos(_om["mensual"], tasa_reparto)),
        ipm=ipm,
        carga_1=lin["carga_1"], carga_2=lin["carga_2"],
        corr_1=h["Sistema 1, kg DBO al ano"],
        corr_2=h["Sistema 2, kg DBO al ano"],
        pct_ppdi=1.0, desfase_ppdi=desfase_ppdi, desfase_ppdmo=desfase_ppdmo,
        costos=cst, pmp=h.get("Periodo medio de pago a proveedores", pmp),
        kt_inicial=h["Capital de trabajo inicial"],
        capex_total=sum(construccion["capex"]),
        int_dc_total=sum(nec["inter"]),
        desem=an(nec["desemb"]), aporte=an([-a for a in nec["aporte"]]),
        int_dc=an([-v for v in nec["inter"]]),
        com_dc=an([-v for v in nec["comis"]]),
        pago_obras=cst["pago_obras"],
        capex=[-x for x in an(construccion["capex"])],
        otros_dc=[-x for x in an(construccion["otros"])],
        # `FC!36`: la variacion del IGV durante la construccion. Suma casi cero
        # en toda la obra pero se mueve fuerte ano a ano, asi que omitirla
        # desplaza el flujo y con el la deuda dimensionada por cobertura.
        igv_dc=(construccion.get("igv_flujo") or [0.0] * ny),
        laguna=[-x for x in cst["cierre_laguna"]],
        repex=[-x for x in cst["repex"]],
    )
    return {"ent": ent, "ppdi": ppdi, "nec": nec, "hitos": h,
            "pct_capex": h["pct_capex"], "cal": cal}


def _flag_op(cal, n, anio0, fin_op):
    """Operacion: del mes siguiente al fin de [D+C+PM] hasta el fin del O&M."""
    ini = cal["i_dcpm"][1]
    if fin_op:
        y, m = int(str(fin_op)[:4]), int(str(fin_op)[5:7])
        ult = (y - anio0) * 12 + m - 1
    else:
        ult = n - 1
    return [1.0 if ini < t <= ult else 0.0 for t in range(n)]


def construccion_plantilla(d, cal, anio0):
    """Las mallas de construccion del esquema por hitos, leidas de la plantilla.

    Hasta hoy la rama por hitos recibia `capex`, `otros` e `igv` por parametro y
    quien la llamaba los sacaba del libro de San Martin, asi que un proyecto
    nuevo por hitos no se podia correr solo con la plantilla. Esto los arma de
    las hojas `CAPEX` y `Otros`, que es donde el usuario los escribe.

    **El IGV de construccion va en cero**, y no es un atajo: en el modelo
    aprobado la necesidad neta de IGV suma 183 377 soles sobre 555 millones de
    CAPEX, o sea el 0.03 %, y la variacion anual del IGV en el flujo suma
    exactamente cero. El libro asume recuperacion practicamente contemporanea,
    que es el regimen especial de recuperacion anticipada. Un proyecto con otro
    regimen tiene que traer su propia serie por `igv` e `igv_flujo`.
    """
    fechas = d["fechas"]
    p = d["proyecto"]
    idx = LP.indice_capex(fechas, p["IPC, reajuste de costos"],
                          p.get("Indice de CAPEX al cierre del contrato", 1.0))
    n = cal["n"]
    pos = {}
    for i, f in enumerate(fechas):
        t = (int(f[:4]) - anio0) * 12 + int(f[5:7]) - 1
        if 0 <= t < n:
            pos[t] = i
    capex, otros = [0.0] * n, [0.0] * n
    for t, i in pos.items():
        capex[t] = d["capex"][i] * idx[i]
        otros[t] = sum(d["otros"][c][i] for c in d["otros"]) * idx[i]
    fuera = [f for j, f in enumerate(fechas)
             if j not in pos.values() and (d["capex"][j] or
                                           any(d["otros"][c][j] for c in d["otros"]))]
    if fuera:
        raise ValueError(f"la malla de `Hitos` no cubre estos meses con gasto: "
                         f"{fuera[0]} .. {fuera[-1]} ({len(fuera)} meses)")
    return {"capex": capex, "otros": otros, "igv": [0.0] * n, "igv_flujo": None}


def correr_plantilla(ruta=LP.RUTA, kd=None, wacc=None, tir=None, ipm=None,
                     tasa_reparto=None, it=40, tol=1e-6, verificar_opex=True,
                     **kw):
    """Proyecto nuevo por hitos, de la plantilla al cierre, sin series del libro.

    La cuenta de reserva es un punto fijo aparte del de las necesidades: se
    dota con `CRSD x servicio de deuda del primer ano de operacion`, y ese
    servicio depende de la deuda, que depende de la reserva porque la reserva se
    financia. Se resuelve iterando la cadena entera; converge en pocas vueltas
    porque la reserva es un par de puntos porcentuales del total.
    """
    if verificar_opex:
        import opex_consistente as OC
        fallos = OC.validar(ruta)
        if fallos:
            peor = max(fallos, key=lambda f: abs(f[4]))
            raise ValueError(
                f"la hoja `OPEX hitos` no suma el OPEX de la hoja `OPEX`: "
                f"{len(fallos)} anos con desvio, el mayor en {peor[0]} "
                f"({peor[1]}: {peor[2]:,.2f} contra {peor[3]:,.2f}). "
                f"Corrigelo con `opex_consistente.derivar(ruta)`, o pasa "
                f"verificar_opex=False si el desvio es intencional.")
    d = LP.leer(ruta)
    h = d["hitos"]
    anio0, n = int(h["Primer ano de la malla"]), int(h["Meses de la malla"])
    cal = C.calendario(anio0, n, h["Inicio del periodo D + C + PM"],
                       h["Fin del periodo D + C + PM"],
                       h["Primer pago del PPDI"])
    con = construccion_plantilla(d, cal, anio0)
    crsd_obj = _param(d, "Cuenta de reserva CRSD")
    reserva, g = 0.0, None
    for _ in range(it):
        g = correr(con, ruta=ruta, kd=kd, wacc=wacc, tir=tir, ipm=ipm,
                   tasa_reparto=tasa_reparto, reserva=reserva, **kw)
        fop = g["ent"]["fop"]
        i0 = next((i for i in range(len(fop)) if fop[i] > 0), 0)
        serv = abs(g["r"]["amort"][i0]) + abs(g["r"]["int_op"][i0])
        nueva = crsd_obj * serv
        if abs(nueva - reserva) < tol * max(1.0, abs(nueva)):
            reserva = nueva
            break
        reserva = nueva
    g["reserva"] = reserva
    # Solo aca: la plantilla precargada mezcla unidades a proposito (Cajamarca
    # en `Proyecto`, San Martin en `Hitos`), asi que su "Moneda" solo describe
    # al libro cuando la plantilla es de un proyecto de verdad.
    g["moneda"] = d["proyecto"].get("Moneda", "S/")
    return g


def correr(construccion, **kw):
    g = preparar(construccion, **kw)
    ref = F.cerrar(g["ppdi"], g["ent"])
    g["ref"] = ref
    g["r"] = F.flujo(ref, g["ppdi"], g["ent"])
    return g


def payload(g, ke, kd, wacc, ipm, fx=0.0, cuotas=60):
    """`ke` es el del accionista, solo para mostrarlo en el libro de salida."""
    """Lo que consume `escribir_excel_sm` para pintar el libro de salida."""
    ent, r, h = g["ent"], g["r"], g["hitos"]
    ny, ref, ppdi = ent["ny"], g["ref"], g["ppdi"]
    pg = I_pagos(g)
    det = {"ppdi": r["ppdi"], "pfij": r["pfij"], "pvar": r["pvar"],
           "pago_obras": ent["pago_obras"], "capex": ent["capex"],
           "otros_dc": ent["otros_dc"], "igv_dc": ent["igv_dc"],
           "laguna": ent["laguna"], "costo_om": r["costo_om"],
           "repex": ent["repex"], "varkt": r["varkt"], "otros_op": r["r119"],
           "pt": r["pt"], "ir": r["ir"], "desem": ent["desem"],
           "int_dc": ent["int_dc"], "com_dc": ent["com_dc"],
           "int_op": r["int_op"], "amort": r["amort"], "crsd": r["crsd"],
           "per": r["per"], "anio": [ent["anio0"] + i for i in range(ny)]}
    return {"inputs": {"moneda": g.get("moneda", "S/"),
                       "ke": ke, "kd": kd, "wacc": wacc, "tir": ent["tir"],
                       "rcsd": ent["rcsd"], "crsd": ent["crsd_obj"],
                       "ir": ent["ir"], "pt": ent["pt"],
                       "arr": ent["base_arrastre"], "ipm": ipm, "fx": fx,
                       "cuotas": cuotas, "ppdi": ppdi, "ref": ref},
            "anio": det["anio"], "det": det,
            "perfil_ppdi": [v / ppdi if ppdi else 0.0 for v in r["ppdi"]],
            "perfil": {c: [v / ref if ref else 0.0 for v in r[c]]
                       for c in ("pfij", "pvar")},
            "pct_capex": g["pct_capex"], "ppdmo_hito": pg,
            "precio": r["precio"]}


def payload_auto(g, ke, kd, wacc, ipm, fx=0.0, margen_om=0.15):
    """Igual que `payload`, mas lo que necesita la hoja del intangible.

    `margen_om` es el margen del operador sobre el costo de O&M, el mismo
    `Margen del costo fijo` de la plantilla. Aca se aplica a TODO el costo,
    porque en la rama autofinanciada no hay pata fija y pata variable que
    separar: el operador opera el servicio entero.
    """
    d = payload(g, ke, kd, wacc, ipm, fx)
    d["inputs"]["margen_om"] = margen_om
    ent, r = g["ent"], g["r"]
    ny, anio0, cal = ent["ny"], ent["anio0"], ent["cal"]
    d["inputs"]["precio"] = r["precio"]
    d["intangible"] = r["intangible"]
    # meses de operacion de cada ano, para amortizar el intangible sin suponer
    # que todos los anos tienen doce
    d["meses_op"] = [sum(1 for t in range(cal["n"])
                         if int(cal["anio"][t]) - anio0 == i and cal["flag_op"][t])
                     for i in range(ny)]
    d["ingreso_1"] = next((v for v in r["ingreso"] if v), 0.0)
    return d


def I_pagos(g):
    """Las cuatro referencias mensuales del PPDMO fijo, una por hito."""
    import ingresos_sm as I
    fijo, _precio = I.referencias(g["ref"], g["ent"]["rep"],
                                  g["ent"]["corr_1"], g["ent"]["corr_2"])
    return fijo
