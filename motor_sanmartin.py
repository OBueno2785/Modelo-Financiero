"""Cierre del PPDI del modelo de Hitos Funcionales (PTAR San Martin).

Resuelve el punto fijo de las necesidades de financiamiento (los intereses y
comisiones de construccion se capitalizan y vuelven a financiarse) y de ahi el
PPDI anual que iguala VAN(PPDI ; WACC) = VAN(necesidades sin CRSD ; WACC).
"""
import json

D = json.load(open("sanmartin_primitivos.json"))
S, K = D["series"], D["escalares"]
N, OFF = K["n"], K["col_P"] - K["col_F"]

base = [S["nec_capex"][t] + S["nec_otros"][t] + S["nec_igv"][t]
        + S["nec_crsd"][t] + S["nec_ktrabajo"][t] for t in range(N)]
crsd = S["nec_crsd"]
flag = S["flag_dcpm"]
mes  = S["nro_mes"]
APAL, UPF, COMM, MES_CF = K["apalancamiento"], K["upfront"], K["commitment"], K["mes_cf"]
AP_PCT, AP_MES = K["ap_pct"], K["ap_mes"]


# Reembolsos a BID y Proinversion: US$ 1,118,899.80 pagados una sola vez en el
# mes 10 de la malla (Capex!174), convertidos al tipo de cambio de Hip_Mensual!C58.
REEMB_USD, FX_LIBRO, MES_REEMB = 709987.71 + 408912.09, 3.80, 10


def usar_entrada(cal, capex, otros, igv, ktrabajo, reserva):
    """Reemplaza las primitivas del libro por las que salen de la plantilla.

    `cal` es la salida de `calendario_sm.calendario`. `capex` y `otros` son
    mallas mensuales; `igv` es la necesidad de IGV mes a mes; `ktrabajo` y
    `reserva` son los dos importes que el libro carga de una vez al cierre de la
    construccion (capital de trabajo y cuenta de reserva del servicio).
    """
    global base, crsd, flag, mes, N, OFF
    N = cal["n"]
    flag, mes = cal["flag_dcpm"], cal["nro_mes"]
    OFF = cal["i_dcpm"][0]
    fin = cal["i_dcpm"][1]
    crsd = [reserva if t == fin else 0.0 for t in range(N)]
    kt = [ktrabajo if t == fin else 0.0 for t in range(N)]
    base = [capex[t] + otros[t] + igv[t] + crsd[t] + kt[t] for t in range(N)]
    S["ppdi_trim"] = cal["flag_pago"]


def necesidades(kd_anual, fx=FX_LIBRO, iteraciones=120):
    kd_m = (1 + kd_anual) ** (1 / 12) - 1
    ajuste = (fx - FX_LIBRO) * REEMB_USD
    inter = [0.0] * N
    comis = [0.0] * N
    for _ in range(iteraciones):
        total = [base[t] + inter[t] + comis[t] + (ajuste if t == MES_REEMB else 0.0)
                 for t in range(N)]
        capital = sum(total) * (1 - APAL)
        prog = [capital * sum(p for p, m in zip(AP_PCT, AP_MES) if m == mes[t]) for t in range(N)]

        desemb = [0.0] * N
        aportes = [0.0] * N
        saldo_prev, cum_prog, cum_real = 0.0, 0.0, 0.0
        for t in range(N):
            ini = saldo_prev * flag[t]
            cum_prog += prog[t]
            neto = ini + total[t]
            if neto > 0 and mes[t] <= AP_MES[-1]:
                aporte = -max(neto, cum_prog + cum_real)
            else:
                aporte = -prog[t]
            cum_real += aporte
            aportes[t] = aporte
            saldo_prev = min(0.0, neto + aporte)
            desemb[t] = max(0.0, neto + aporte)

        tot_des = sum(desemb)
        saldo_d, acum_d = 0.0, 0.0
        n_i, n_c = [0.0] * N, [0.0] * N
        for t in range(N):
            saldo_d = saldo_d * flag[t] + desemb[t]   # el saldo solo vive en [D+C+PM]
            acum_d += desemb[t]
            n_i[t] = saldo_d * kd_m
            up = UPF * tot_des if mes[t] == MES_CF else 0.0
            cm = COMM * (tot_des - acum_d) / 12 * flag[t] if mes[t] > MES_CF else 0.0
            n_c[t] = up + cm
        if max(abs(a - b) for a, b in zip(inter + comis, n_i + n_c)) < 1e-7:
            inter, comis = n_i, n_c
            break
        inter, comis = n_i, n_c

    total = [base[t] + inter[t] + comis[t] + (ajuste if t == MES_REEMB else 0.0)
             for t in range(N)]
    sin_crsd = [total[t] - crsd[t] for t in range(N)]
    return dict(total=total, sin_crsd=sin_crsd, inter=inter, comis=comis,
                desemb=desemb, aporte=aportes,
                desembolso=sum(desemb), capital=sum(total) * (1 - APAL))


def npv(serie, r):
    return sum(serie[j] / (1 + r) ** (j - OFF + 1) for j in range(OFF, N))


def ppdi_anual(wacc_anual, kd_anual, fx=FX_LIBRO):
    wm = (1 + wacc_anual) ** (1 / 12) - 1
    nec = necesidades(kd_anual, fx)
    van = npv(nec["sin_crsd"], wm)
    pagos = [j for j in range(N) if S["ppdi_trim"][j] > 0]
    sdf = sum(1 / (1 + wm) ** (j - OFF + 1) for j in pagos)
    return 4 * van / sdf, van, nec


if __name__ == "__main__":
    P, van, nec = ppdi_anual(K["wacc_anual"], K["kd"])
    print("VALIDACION contra el libro aprobado")
    for nom, calc, ref in [
        ("Necesidades totales",  sum(nec["total"]),  K["nec_total_libro"]),
        ("Intereses en constr.", sum(nec["inter"]),  K["nec_int_libro"]),
        ("Comisiones",           sum(nec["comis"]),  K["nec_com_libro"]),
        ("Deuda",                nec["desembolso"],  K["deuda_libro"]),
        ("Capital",              nec["capital"],     K["capital_libro"]),
        ("VAN necesidades",      van,                K["van_nec"]),
        ("PPDI anual",           P,                  K["ppdi_anual"]),
    ]:
        print(f"  {nom:<22} {calc:20,.4f}  vs {ref:20,.4f}   dif {calc-ref:+12,.4f}")
