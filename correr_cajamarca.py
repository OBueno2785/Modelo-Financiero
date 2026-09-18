"""Cajamarca con parametros actualizados al 14-set-2026.

El soberano base del Kd sale de la curva soberana interpolada a la vida media de
la deuda (Inputs!D240 = 9.2545 anios), igual que hace el libro.
"""
import json, motor_cajamarca as M, curva_sbs as C

IR_, PT_ = 0.295, 0.05
T = 1 - (1 - IR_) * (1 - PT_)
DE = 0.9736452003104606          # Tasa!E8, promedio D/E del propio modelo
WD = DE / (1 + DE)
WE = 1 - WD
VIDA_MEDIA = 9.254513642313936   # Inputs!D240
SPREAD = 0.035                   # Inputs!D238, sondeo de mercado


def capital(rf, erp, bu, rp, zc_sol, zc_usd, soberano):
    bl = bu * (1 + DE * (1 - T))
    ke_usd = rf + bl * erp + rp
    prima = (1 + zc_sol) / (1 + zc_usd) - 1
    ke = (1 + ke_usd) * (1 + prima) - 1
    kd = soberano + SPREAD
    return dict(beta_l=bl, ke_usd=ke_usd, prima=prima, ke=ke, kd=kd,
                soberano=soberano, wacc=ke * WE + kd * WD * (1 - T))


LIBRO = dict(rf=0.04822361658701883, erp=0.07032289401128841,
             bu=0.44533853048776256, rp=0.01724572989190804,
             zc_sol=0.0669974, zc_usd=0.0558827,
             soberano=0.05788787939497107)
HOY = dict(LIBRO, rp=0.016728584245321004,
           zc_sol=C.punto(C.SOL, 15.0), zc_usd=C.punto(C.USD, 15.0),
           soberano=C.punto(C.SOL, VIDA_MEDIA))


def corre(p, k_gfin=1.0):
    cc = capital(**p)
    wm = (1 + cc["wacc"]) ** (1 / 12) - 1
    x = M.cerrar(wm, k_gfin)
    return cc, x, x * 12


if __name__ == "__main__":
    cc0, x0, a0 = corre(LIBRO)
    print("Control: el WACC del libro es 9.603614%, calculado", f"{cc0['wacc']:.6%}")
    print("         PPDI anual del libro 46,472.5466, calculado", f"{a0:,.4f}")
    print()
    cc1, x1, a1 = corre(HOY)
    k = cc1["kd"] / cc0["kd"]
    cc2, x2, a2 = corre(HOY, k)
    print(f"{'':<34}{'libro':>18}{'hoy':>18}{'hoy, gfin escalado':>22}")
    for nom, key in [("Beta apalancado","beta_l"),("Ke USD","ke_usd"),
                     ("Prima devaluacion","prima"),("Ke soles","ke"),
                     ("Soberano a vida media","soberano"),("Kd soles","kd"),
                     ("WACC soles","wacc")]:
        f = "{:>17.4%} " if key != "beta_l" else "{:>17.5f} "
        print(f"  {nom:<32}" + "".join(f.format(c[key]) for c in (cc0, cc1, cc2)))
    print()
    print(f"  {'PPDI base mensual S/ miles':<32}" + "".join(f"{v:>17,.4f} " for v in (x0, x1, x2)))
    print(f"  {'PPDI anual S/ miles':<32}" + "".join(f"{v:>17,.4f} " for v in (a0, a1, a2)))
    print(f"  {'PPDI trimestral S/ miles':<32}" + "".join(f"{v/4:>17,.4f} " for v in (a0, a1, a2)))

    json.dump(dict(
        fecha="2026-09-14",
        curva_sbs=C.FECHA,
        nota=("PPDI cerrado con el motor validado. El PPDMO de Cajamarca NO esta "
              "construido: su cierre es solo sobre la pata variable "
              "(Resumen!J6 = Tarifa_Media_Vta contra M.Sombra!D74 = 0) y hace falta "
              "el modelo sombra. La pata fija no depende de las tasas."),
        unidad="S/ miles sin IGV, anio 1 de operacion (2031)",
        libro=dict(wacc=cc0["wacc"], kd=cc0["kd"], ke=cc0["ke"],
                   soberano=cc0["soberano"], prima_devaluacion=cc0["prima"],
                   ppdi_anual=a0, ppdi_trimestral=a0 / 4, ppdi_base_mensual=x0,
                   ppdmo_fijo_anual=6671.828175303587,
                   ppdmo_variable_anual=28935.325022853205,
                   ppdmo_total_anual=35607.15319815679),
        hoy=dict(wacc=cc1["wacc"], kd=cc1["kd"], ke=cc1["ke"],
                 soberano=cc1["soberano"], prima_devaluacion=cc1["prima"],
                 ppdi_anual=a1, ppdi_trimestral=a1 / 4, ppdi_base_mensual=x1,
                 ppdmo_fijo_anual=6671.828175303587,
                 ppdmo_fijo_nota=("sin cambio: PPDMO!D21 sale de costos fijos por "
                                  "(1 + Margen_CF 15%), no pasa por el cierre"),
                 ppdmo_variable_anual=None,
                 ppdmo_variable_nota="no disponible: falta el modelo sombra M.Sombra"),
        hoy_gfin_escalado=dict(wacc=cc2["wacc"], ppdi_anual=a2,
                               nota=("mismo escenario pero escalando los gastos "
                                     "financieros por Kd_nuevo/Kd_libro; acota el "
                                     "efecto de no tener el modulo de deuda")),
        parametros_actualizados=dict(
            riesgo_pais=dict(valor=HOY["rp"], fuente="BCRP PN01129XM, 60 meses set-2021 a ago-2026"),
            zc_soles_15a=dict(valor=HOY["zc_sol"], fuente=f"SBS, curva cupon cero soberana, {C.FECHA}"),
            zc_dolares_15a=dict(valor=HOY["zc_usd"], fuente=f"SBS, curva cupon cero soberana, {C.FECHA}"),
            soberano_vida_media=dict(valor=HOY["soberano"], plazo_anios=VIDA_MEDIA,
                                     fuente=f"SBS, curva soles interpolada a la vida media, {C.FECHA}"),
        ),
        sin_actualizar=dict(
            spread_deuda=dict(valor=SPREAD, motivo="sondeo de mercado, sin fuente publica"),
            d_sobre_e=dict(valor=DE, motivo="lo calcula el propio modelo en EEFF Anuales!D254"),
            gastos_financieros=dict(motivo=("entran como primitiva del libro: falta el "
                                            "dimensionamiento de deuda por cobertura en Cajamarca")),
        ),
    ), open("cajamarca_actualizado.json", "w"), indent=2, ensure_ascii=False)
    print("\n-> cajamarca_actualizado.json")
