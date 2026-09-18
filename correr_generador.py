"""Arma el libro de salida del generador para Cajamarca y lo guarda en xlsx."""
import json
import deuda_cajamarca as DE
import escribir_excel as EX
import motor_cajamarca as M
import sombra_cajamarca as S

D = S.D
A = json.load(open("/mnt/project-files/generador/cajamarca_actualizado.json"))


def preparar(ipm=0.0267, kd=None, ke=None, wacc=None):
    kd = A["hoy"]["kd"] if kd is None else kd
    ke = A["hoy"]["ke"] if ke is None else ke
    wacc = A["hoy"]["wacc"] if wacc is None else wacc
    deu = DE.corrida(kd)
    pad_m = lambda s: list(s) + [0.0] * (S.NM - len(s))
    ppdi = M.cerrar(rate=(1 + wacc) ** (1 / 12) - 1,
                    gfin_ext=list(deu["interes"]) + [0.0] * (M.N - len(deu["interes"]))) * 12
    tarifa = S.cerrar(ipm, ke, kd, ppdi)
    fijo, var, fijo_base, _, fijo_acc, var_acc = S.pagos(ipm, tarifa)
    rp = ppdi / S.PPDI_LIBRO
    inte_q = S._a_trimestres(pad_m(deu["interes"]))
    srv_q = S._a_trimestres(pad_m(deu["servicio"]))
    des_q = S._a_trimestres(pad_m(deu["desemb"]))

    # impuestos: los del libro mas el delta que el motor calcula
    imp = [D["part"][i] + D["ir"][i] for i in range(S.NQ)]
    d_tax = [0.0] * S.NQ
    for i in S.VIVOS:
        d_ppdi = D["ppdi"][i] * (rp - 1)
        d_rev = ((d_ppdi + fijo[i] - D["fijo"][i] + var[i] - D["var"][i])
                 * (1 - S.SUPERV * S.FLAG_SUP[i]))
        base = d_rev - (inte_q[i] - S.INTE_LIBRO_Q[i])
        j = next((q for q in S.IR_Q if q >= i), S.IR_Q[-1])
        d_tax[j] -= S.TAU * base

    return {
        "inputs": {
            "costo_obra": sum(DE.INV), "tamano_deuda": DE.TAMANO, "kd": kd,
            "spread": 0.035, "ke": ke, "wacc": wacc, "pagos": DE.PAGOS,
            "ipm": ipm, "gatillo": 0.03, "ipc": 0.02, "ir": 0.295, "part": 0.05,
            "superv": S.SUPERV, "margen_cf": 0.15, "fijo_base": fijo_base,
            "tarifa": tarifa, "ppdi_anual": ppdi,
        },
        "meses": {
            "fecha": [f[:10] for f in D["m_fecha"]],
            "flag_obra": pad_m(DE.F32), "flag_deuda": pad_m(DE.F33),
            "inversion": pad_m(DE.INV), "flag_om": D["Pflag_om"],
            "flag_trim": D["Pflagt"], "flag_pago": D["Pflag_ppdmo"], "kg": D["Pkg"],
        },
        "mes_base": next(t for t in range(S.NM) if pad_m(DE.F33)[t] > 0.5) - 1,
        "trimestres": {
            "anio": D["anio"], "trim": D["trim"], "meses": D["meses"],
            "ppdi_perfil": [D["ppdi"][i] / S.PPDI_LIBRO for i in range(S.NQ)],
            "fijo": fijo, "var": var,
            "costo_fijo": D["costo_fijo"], "costo_var": D["costo_var"],
            "gastos_spv": D["gastos_spv"], "seguros": D["seguros"],
            "fianzas": D["fianzas"], "promocion": D["promocion"],
            "fideicomiso": D["fideicomiso"], "itan": D["itan"],
            "capex": D["capex"], "igv": D["igv"],
            "interes": [-x for x in inte_q],
            "impuestos": [imp[i] + d_tax[i] for i in range(S.NQ)],
            "desembolso": des_q, "servicio": srv_q,
            "des2": D["des2"], "srv2": D["srv2"],
            "flag_superv": D["flag_superv"],
        },
    }


if __name__ == "__main__":
    d = preparar()
    ruta = EX.escribir(d, "/mnt/project-files/generador/PTAR_Cajamarca_generado.xlsx")
    print("escrito:", ruta)
    print(f"  PPDI anual        {d['inputs']['ppdi_anual']:>14,.4f}")
    print(f"  tarifa variable   {d['inputs']['tarifa']:>14,.7f}")
    print(f"  PPDMO fijo base   {d['inputs']['fijo_base']:>14,.4f}")
