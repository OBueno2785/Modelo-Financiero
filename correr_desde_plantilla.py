"""Corre el modelo entero desde `Plantilla_Proyecto_Nuevo.xlsx`.

Es el viaje completo del generador: se lee la plantilla, se arma la cadena de
construccion, se dimensiona la deuda, se cierra el PPDI y se cierra la tarifa
variable del PPDMO, sin tocar ninguna primitiva del libro salvo las que todavia
no estan modeladas, que estan listadas abajo.
"""
import json
import deuda_cajamarca as DE
import leer_plantilla as LP
import motor_cajamarca as M
import sombra_cajamarca as S

# Lo que todavia se toma del libro y falta modelar: el bloque tributario del
# modelo sombra (IR y participacion con arrastre de perdidas), el flujo neto de
# IGV, el efecto ITAN y el tramo complementario de deuda de `M.Sombra!192:195`.


def corrida(ruta=LP.RUTA, kd=None, ke=None, wacc=None, ipm=None):
    d = LP.leer(ruta)
    p = d["proyecto"]
    con = LP.construccion(d)
    ser = LP.series(d)
    fechas = d["fechas"]
    ipm = p["IPM, reajuste de ingresos"] if ipm is None else ipm

    i0 = fechas.index(p["Inicio del pago de deuda"])
    i1 = fechas.index(p["Fin del pago de deuda"])
    f33 = [1 if i0 <= i <= i1 else 0 for i in range(len(fechas))]
    deu = DE.corrida(kd, p["Tamano de deuda"], con["inversion"],
                     con["flag_obra"], f33)

    enc = lambda s: (list(s) + [0.0] * M.N)[:M.N]
    otros = d["otros"]
    ext = {"obra": enc(con["costo_obra"]), "fid": enc(otros["fideicomiso"]),
           "seg": enc(otros["seguros"]), "gar": enc(otros["garantias"]),
           "reem": enc(otros["reembolso"]),
           "estr": enc([deu["costo_estructuracion"] if i == 21 else 0.0
                        for i in range(len(fechas))]),
           "com": enc(deu["costo_no_uso"])}
    ppdi = M.cerrar(rate=(1 + wacc) ** (1 / 12) - 1, gfin_ext=enc(deu["interes"]),
                    ext=ext) * 12

    padm = lambda s: (list(s) + [0.0] * S.NM)[:S.NM]
    tarifa = S.cerrar(ipm, ke, kd, ppdi)
    fijo, var, _, _, fijo_acc, var_acc = S.pagos(ipm, tarifa, kg=padm(ser["kg"]),
                              fijo_base_cte=ser["fijo_base_cte"])
    return {"ppdi_anual": ppdi, "tarifa": tarifa, "cuota_deuda": deu["cuota"],
            "interes_total": deu["total_interes"], "fijo": fijo, "var": var,
            "fijo_base": ser["fijo_base_cte"] * (1 + (1 + ipm) ** (1 / 12) - 1)}


if __name__ == "__main__":
    A = json.load(open("/mnt/project-files/generador/cajamarca_actualizado.json"))
    r = corrida(kd=A["libro"]["kd"], ke=A["libro"]["ke"],
                wacc=A["libro"]["wacc"], ipm=S.IPM_LIBRO)
    D = S.D
    print("=== la plantilla contra el libro aprobado ===")
    filas = [("PPDI anual", r["ppdi_anual"], 46472.546554744986),
             ("tarifa variable", r["tarifa"], 4.317668971541212),
             ("cuota de deuda mensual", r["cuota_deuda"], 2692.2758856404166),
             ("interes total de la deuda", r["interes_total"], 178771.87820306382),
             ("PPDMO fijo base mensual", r["fijo_base"], 555.9856812752989)]
    print(f"{'':<30}{'plantilla':>18}{'libro':>18}{'desvio':>14}")
    for nom, mio, lib in filas:
        print(f"  {nom:<28}{mio:>18,.6f}{lib:>18,.6f}{mio - lib:>14.8f}")
    print(f"  {'PPDMO fijo trimestral':<28}{'':>18}{'':>18}"
          f"{max(abs(r['fijo'][i] - D['fijo'][i]) for i in range(S.NQ)):>14.8f}")
    print(f"  {'PPDMO variable trimestral':<28}{'':>18}{'':>18}"
          f"{max(abs(r['var'][i] - D['var'][i]) for i in range(S.NQ)):>14.8f}")
