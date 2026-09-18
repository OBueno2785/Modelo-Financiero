"""Corrida final de San Martin con todas las fuentes primarias actualizadas."""
import motor_sanmartin as M, motor_ppdmo_sm as Q, correr_sanmartin as C, curva_sbs as SBS

# Curva soberana de la SBS al 11-set-2026. El libro toma el punto de 15 anios
# para la prima por devaluacion y el punto a la VIDA MEDIA de la deuda (8.84
# anios, 'Tasa de Interes'!C6) como base del Kd, interpolado linealmente.
VIDA_MEDIA = 8.84
ZC_SOL, ZC_USD = SBS.punto(SBS.SOL, 15.0), SBS.punto(SBS.USD, 15.0)
SOBERANO = SBS.punto(SBS.SOL, VIDA_MEDIA)
FX_MMM = 3.3805                             # MMM 2027-2030, promedio 2027-2030
HOY = dict(C.ESC["hoy"], zc_sol=ZC_SOL, zc_usd=ZC_USD, soberano=SOBERANO)


def corre(params, fx=M.FX_LIBRO, ipm=None):
    cc = C.costo_capital(**params)
    nec = M.necesidades(cc["kd"], fx)
    ppdi, van, _ = M.ppdi_anual(cc["wacc"], cc["kd"], fx)
    rep = Q.repartos(cc["wacc"])
    kr, kc = C.mult_ipm(ipm)
    fx_aj = (fx - M.FX_LIBRO) * M.REEMB_USD
    tir = round(cc["ke"], 4)
    ref = Q.cerrar(ppdi, nec, cc["kd"], cc["wacc"], cc["ke"], tir, rep, kr, kc, fx_aj)
    _v, det = Q.flujo(ppdi, ref, nec, cc["kd"], cc["wacc"], tir, rep, kr, kc, fx_aj)
    return dict(cc=cc, ppdi=ppdi, van=van, ref=ref, nec=nec,
                fijo=ref * rep["kfix"] * 12,
                precio=ref * rep["kvar"] * 12 / Q.E["corr"],
                hitos=[ppdi * p / 4 for p in M.K["pct_capex"]],
                phito=[ref * rep["e"][0] * rep["d83"] * (1 - rep["d87"]),
                       ref * rep["e"][1] * rep["d83"] * (1 - rep["d87"]),
                       ref * rep["e"][2] * rep["d83"] * (1 - rep["d87"]),
                       ref * rep["d84"] * (1 - rep["d88"])],
                nominal=sum(det["pfij"]) + sum(det["pvar"]))


ESC = [
    ("libro",        C.ESC["libro"], M.FX_LIBRO, None),
    ("tasas hoy",    HOY,            M.FX_LIBRO, None),
    ("+ TC del MMM", HOY,            FX_MMM,     None),
    ("+ IPM 2.67%",  HOY,            FX_MMM,     0.0267),
    ("+ IPC MMM 2.26%", HOY,         FX_MMM,     0.0226),
]


if __name__ == "__main__":
    R = {n: corre(p, fx, ipm) for n, p, fx, ipm in ESC}
    cols = [n for n, *_ in ESC]

    print(f"{'':<30}" + "".join(f"{c:>19}" for c in cols))
    def fila(nom, fn, fmt="{:>18,.4f} "):
        print(f"  {nom:<28}" + "".join(fmt.format(fn(R[c])) for c in cols))

    for nom, k in [("Prima devaluacion","dev"),("Ke soles","ke"),("Kd soles","kd"),("WACC soles","wacc")]:
        fila(nom, lambda r, k=k: r["cc"][k], "{:>18.4%} ")
    print()
    fila("Intereses construccion", lambda r: sum(r["nec"]["inter"]))
    fila("Deuda", lambda r: r["nec"]["desembolso"])
    fila("VAN necesidades", lambda r: r["van"])
    print()
    fila("PPDI anual", lambda r: r["ppdi"])
    fila("PPDI trimestral", lambda r: r["ppdi"] / 4)
    for i in range(4):
        fila(f"  cuota trim. hito {i+1}", lambda r, i=i: r["hitos"][i])
    print()
    fila("PPDMO referencia mensual", lambda r: r["ref"])
    fila("PPDMO fijo anual", lambda r: r["fijo"])
    for i in range(4):
        fila(f"  PPDMO fijo mes hito {i+1}", lambda r, i=i: r["phito"][i])
    fila("Precio unit. S//kg DBO", lambda r: r["precio"], "{:>18,.6f} ")
    fila("PPDMO nominal del contrato", lambda r: r["nominal"], "{:>18,.0f} ")
