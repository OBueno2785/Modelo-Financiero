"""Las cuatro combinaciones del generador, en una corrida.

    regimen \\ esquema     al final de obra        por hitos
    cofinanciada          generar.correr          generar_sm.correr
    autofinanciada        generar.correr_auto     generar_sm.correr(regimen=...)

Sirve de control: si una de las cuatro deja de cerrar, se ve aqui.
"""
import json

import correr_final as CF
import escribir_excel as EX
import escribir_excel_sm as EXS
import exportar_sm_estructural as ES
import generar as G
import generar_sm as GS
import leer_plantilla as LP
import motor_sanmartin as M

CAJ = "/mnt/project-files/generador/Plantilla_Proyecto_Nuevo.xlsx"
CAJ_AUTO = "/mnt/project-files/generador/Plantilla_Autofinanciada.xlsx"
SAL = "/mnt/project-files/generador/"


def _sm(regimen):
    S, A, fop = ES.entrada()
    params, fx, ipm = {n: (p, f, i) for n, p, f, i in CF.ESC}["+ IPM 2.67%"]
    cc = CF.corre(params, fx, ipm)["cc"]
    capex = list(S["nec_capex"])
    capex[M.MES_REEMB] += (fx - M.FX_LIBRO) * M.REEMB_USD
    con = {"capex": capex, "otros": S["nec_otros"], "igv": S["nec_igv"],
           "igv_flujo": A["fc"]["36"]}
    # La plantilla trae Cajamarca en `Proyecto` y San Martin en `Hitos`, asi que
    # su celda de exoneracion es la de Cajamarca. Aca el proyecto es San Martin,
    # que esta bajo la ley de la Amazonia, y por eso su IGV de operacion es
    # costo no recuperable (`Opex!143` de su libro).
    g = GS.correr(con, regimen=regimen, kd=cc["kd"], tasa_reparto=cc["wacc"],
                  wacc=cc["wacc"], tir=round(cc["ke"], 4), ipm=ipm,
                  reserva=sum(S["nec_crsd"]), flag_op=fop, exonera_igv=1)
    return g, cc, fx, ipm


def correr_todo():
    A = json.load(open("cajamarca_actualizado.json"))["hoy"]
    kw = dict(kd=A["kd"], ke=A["ke"], wacc=A["wacc"])
    out = []

    g = G.correr(CAJ, **kw)
    EX.escribir(G.payload(g), SAL + "PTAR_Cajamarca_generado.xlsx")
    out.append(("cofinanciada", "al final de obra", g["r"]["van"],
                f"PPDI {g['ppdi']:,.2f} / tarifa {g['tarifa']:.7f}"))

    g = G.correr_auto(CAJ_AUTO, **kw)
    EX.escribir_auto(G.payload_auto(g), SAL + "PTAR_Cajamarca_autofinanciada.xlsx")
    out.append(("autofinanciada", "al final de obra", g["r"]["van"],
                f"tarifa {g['tarifa']:.7f} / intangible "
                f"{g['r']['intangible']['base']:,.2f}"))

    g, cc, fx, ipm = _sm("cofinanciada")
    EXS.escribir(GS.payload(g, cc["ke"], cc["kd"], cc["wacc"], ipm, fx),
                 SAL + "PTAR_San_Martin_generado.xlsx")
    out.append(("cofinanciada", "por hitos", g["r"]["van"],
                f"PPDI {g['ppdi']:,.2f} / referencia {g['ref']:,.4f}"))

    g, cc, fx, ipm = _sm("autofinanciada")
    EXS.escribir_auto(GS.payload_auto(g, cc["ke"], cc["kd"], cc["wacc"], ipm, fx,
                                      margen_om=LP.leer(CAJ)["proyecto"]
                                      ["Margen del costo fijo"]),
                      SAL + "PTAR_San_Martin_autofinanciada.xlsx")
    out.append(("autofinanciada", "por hitos", g["r"]["van"],
                f"tarifa {g['r']['precio']:.6f} / intangible "
                f"{g['r']['intangible']['base']:,.2f}"))
    return out


# Las dos columnas NO son comparables entre si y no deben leerse como tales:
# "al final de obra" corre Cajamarca y "por hitos" corre San Martin, cada uno a
# sus propios parametros, que es lo que hace de esto un control. Cajamarca esta
# en MILES de soles y San Martin en SOLES, asi que la columna de hitos sale unas
# 2,000 veces mas grande sin que haya nada roto. La primera vez cuesta un susto.
LIBRO = {"al final de obra": "Cajamarca, miles S/",
         "por hitos": "San Martin, soles"}

if __name__ == "__main__":
    print(f"{'regimen':<16}{'esquema':<18}{'libro y unidad':<22}"
          f"{'VAN del cierre':>18}   resultado")
    for reg, esq, van, txt in correr_todo():
        print(f"{reg:<16}{esq:<18}{LIBRO[esq]:<22}{van:>18.8f}   {txt}")
