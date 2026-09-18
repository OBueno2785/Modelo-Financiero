"""Recalcula el PPDI y el PPDMO de San Martin con parametros actualizados."""
import json, motor_sanmartin as M, motor_ppdmo_sm as Q, ipm_sm as I

IRR_, PT_ = 0.295, 0.05
TIMP = 1 - (1 - IRR_) * (1 - PT_)
WD, WE = 0.4, 0.6


def costo_capital(rf, erp, bu, rp, zc_sol, zc_usd, soberano, spread=0.035):
    bl = bu * (1 + (WD / WE) * (1 - TIMP))
    ke_usd = rf + bl * erp + rp
    dev = (1 + zc_sol) / (1 + zc_usd) - 1
    ke = (1 + ke_usd) * (1 + dev) - 1
    kd = soberano + spread
    wacc = WE * ke + WD * kd * (1 - TIMP)
    return dict(beta_l=bl, ke_usd=ke_usd, dev=dev, ke=ke, kd=kd, wacc=wacc)


F33_B, F35_B = I.factores(0.0119)
KR_B, KC_B = I.por_anio(F33_B), I.por_anio(F35_B)


def mult_ipm(ipm):
    if ipm is None:
        return None, None
    a, b = I.factores(ipm)
    ka, kb = I.por_anio(a), I.por_anio(b)
    return ([ka[i] / KR_B[i] if KR_B[i] else 1.0 for i in range(Q.NY)],
            [kb[i] / KC_B[i] if KC_B[i] else 1.0 for i in range(Q.NY)])


def corrida(cc, ipm=None):
    nec = M.necesidades(cc["kd"])
    ppdi, van_nec, _ = M.ppdi_anual(cc["wacc"], cc["kd"])
    rep = Q.repartos(cc["wacc"])
    tir_obj = round(cc["ke"], 4)
    kr, kc = mult_ipm(ipm)
    ref = Q.cerrar(ppdi, nec, cc["kd"], cc["wacc"], cc["ke"], tir_obj, rep, kr, kc)
    _v, det = Q.flujo(ppdi, ref, nec, cc["kd"], cc["wacc"], tir_obj, rep, kr, kc)
    fijo_anual = ref * rep["kfix"] * 12
    precio = ref * rep["kvar"] * 12 / Q.E["corr"]
    hitos_ppdi = [ppdi * p / 4 for p in M.K["pct_capex"]]
    hf = [ref * rep["e"][0] * rep["d83"] * (1 - rep["d87"]),
          ref * rep["e"][1] * rep["d83"] * (1 - rep["d87"]),
          ref * rep["e"][2] * rep["d83"] * (1 - rep["d87"]),
          ref * rep["d84"] * (1 - rep["d88"])]
    return dict(cc=cc, nec=nec, ppdi=ppdi, van_nec=van_nec, ref=ref,
                fijo_anual=fijo_anual, precio=precio, tir_obj=tir_obj,
                ppdi_trim=ppdi / 4, hitos_ppdi=hitos_ppdi, ppdmo_hito=hf,
                deuda=nec["desembolso"], capital=nec["capital"],
                inter=sum(nec["inter"]), comis=sum(nec["comis"]),
                ing_tot=sum(det["ppdi"]) + sum(det["pfij"]) + sum(det["pvar"]))


ESC = {
  "libro": dict(rf=0.04791710945175432, erp=0.07002434886018517, bu=0.407,
                rp=0.017810376734507548, zc_sol=0.0726912, zc_usd=0.061171,
                soberano=0.070006),
  "hoy": dict(rf=0.04822361658701883, erp=0.07032289401128841,
              bu=0.44533853048776256, rp=0.016728584245321004,
              zc_sol=0.0669974, zc_usd=0.0558827, soberano=0.061895),
  "hoy_zc_proxy": dict(rf=0.04822361658701883, erp=0.07032289401128841,
              bu=0.44533853048776256, rp=0.016728584245321004,
              zc_sol=0.061895, zc_usd=0.055751, soberano=0.061895),
  "hoy_con_ipm": dict(rf=0.04822361658701883, erp=0.07032289401128841,
              bu=0.44533853048776256, rp=0.016728584245321004,
              zc_sol=0.0669974, zc_usd=0.0558827, soberano=0.061895),
}
IPM_ESC = {"libro": None, "hoy": None, "hoy_zc_proxy": None,
           "hoy_con_ipm": 0.0267}

if __name__ == "__main__":
    res = {}
    for k, p in ESC.items():
        cc = costo_capital(**p)
        res[k] = corrida(cc, IPM_ESC[k])
    json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("nec",)}
               for k, v in res.items()}, open("resultado_sm.json", "w"), default=str)

    def fila(nom, f, fmt="{:>18,.4f}"):
        print(f"  {nom:<34}" + "".join(fmt.format(f(res[k])) for k in ESC))

    print("ESCENARIOS".ljust(36) + "".join(f"{k:>18}" for k in ESC))
    print("\n-- Costo de capital --")
    for nom, key in [("Beta apalancado","beta_l"),("Ke USD","ke_usd"),
                     ("Prima devaluacion","dev"),("Ke soles","ke"),
                     ("Kd soles","kd"),("WACC soles","wacc")]:
        fila(nom, lambda r, k=key: r["cc"][k], "{:>17.4%} ")
    print("\n-- Financiamiento --")
    for nom, key in [("Intereses construccion","inter"),("Comisiones","comis"),
                     ("Deuda","deuda"),("Capital","capital"),
                     ("VAN necesidades","van_nec")]:
        fila(nom, lambda r, k=key: r[k])
    print("\n-- PPDI --")
    fila("PPDI anual", lambda r: r["ppdi"])
    fila("PPDI trimestral", lambda r: r["ppdi_trim"])
    for i in range(4):
        fila(f"  cuota trim. hito {i+1}", lambda r, i=i: r["hitos_ppdi"][i])
    print("\n-- PPDMO --")
    fila("Referencia mensual", lambda r: r["ref"])
    fila("PPDMO fijo anual", lambda r: r["fijo_anual"])
    for i in range(4):
        fila(f"  PPDMO fijo mensual hito {i+1}", lambda r, i=i: r["ppdmo_hito"][i])
    fila("Precio unitario S//kg DBO", lambda r: r["precio"], "{:>18,.6f}")
    fila("TIR objetivo", lambda r: r["tir_obj"], "{:>17.2%} ")
