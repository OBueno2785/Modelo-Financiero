"""Series anuales de San Martin con el motor estructural, para el tablero.

Reemplaza a `exportar_sm.py`, que salia del motor de reescalado. Corre los cinco
escenarios de `correr_final.ESC` por la cadena de la plantilla y escribe un JSON
con las series anuales de 28 anos.

    python3 exportar_sm_estructural.py        ->  sanmartin_series_estructural.json

Dos cosas que hay que pasarle bien al motor, y que no son intuitivas:

  * El reparto del PPDMO entre fijo y variable, y el descuento del ultimo pago,
    usan la tasa de `Ingresos!D80`, que es el **WACC**, no el Ke del accionista.
    La TIR objetivo del cierre si es el Ke, redondeado a 4 decimales.
  * `FC!36`, la variacion del IGV de construccion, suma casi cero pero se mueve
    millones ano a ano; va como serie, no como cero.
"""
import json

import correr_final as CF
import generar_sm as GS
import motor_sanmartin as M

SERIES = ("ppdi", "pfij", "pvar", "ir", "pt", "amort", "int_op", "fcf")
IPM_LIBRO = 0.0119
RUTA = "/mnt/project-files/generador/sanmartin_series_estructural.json"


def entrada():
    P = json.load(open("/mnt/project-files/generador/sanmartin_primitivos.json"))
    A = json.load(open("/mnt/project-files/generador/sanmartin_anual.json"))
    G = json.load(open("/mnt/project-files/generador/sanmartin_ingresos.json"))
    return P["series"], A, [1.0 if x else 0.0 for x in G["ing"]["8"]]


def escenario(params, fx, ipm, S, A, fop):
    cc = CF.corre(params, fx, ipm)["cc"]
    capex = list(S["nec_capex"])
    capex[M.MES_REEMB] += (fx - M.FX_LIBRO) * M.REEMB_USD
    con = {"capex": capex, "otros": S["nec_otros"], "igv": S["nec_igv"],
           "igv_flujo": A["fc"]["36"]}
    g = GS.correr(con, kd=cc["kd"], tasa_reparto=cc["wacc"], wacc=cc["wacc"],
                  tir=round(cc["ke"], 4), ipm=IPM_LIBRO if ipm is None else ipm,
                  reserva=sum(S["nec_crsd"]), flag_op=fop)
    r, ent = g["r"], g["ent"]
    out = {k: r[k] for k in SERIES}
    out["desem"] = ent["desem"]
    out["anio"] = [ent["anio0"] + i for i in range(ent["ny"])]
    out.update(ppdi_anual=g["ppdi"], ref=g["ref"], precio=r["precio"],
               ke=cc["ke"], kd=cc["kd"], wacc=cc["wacc"], van=r["van"])
    return out


def exportar(ruta=RUTA):
    S, A, fop = entrada()
    R = {n: escenario(p, fx, ipm, S, A, fop) for n, p, fx, ipm in CF.ESC}
    json.dump(R, open(ruta, "w"))
    return R


if __name__ == "__main__":
    R = exportar()
    print("escrito:", RUTA)
    print(f"{'':<22}" + "".join(f"{n:>20}" for n in R))
    for nom, k in (("PPDI anual", "ppdi_anual"), ("PPDMO referencia", "ref"),
                   ("Precio unitario", "precio")):
        print(f"  {nom:<20}" + "".join(f"{R[n][k]:>20,.6f}" for n in R))
    print(f"  {'VAN del cierre':<20}" + "".join(f"{R[n]['van']:>20.8f}" for n in R))
    i1 = next(i for i, v in enumerate(R['libro']['pfij']) if v)
    print(f"  {'ano 1 operacion':<20}" + "".join(f"{R[n]['anio'][i1]:>20}" for n in R))
    for nom, k in (("  PPDMO fijo", "pfij"), ("  PPDMO variable", "pvar")):
        print(f"  {nom:<20}" + "".join(f"{R[n][k][i1]:>20,.0f}" for n in R))
