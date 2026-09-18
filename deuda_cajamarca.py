"""Modulo de deuda de Cajamarca, replicado de la hoja `Deuda` del libro.

A diferencia de San Martin, Cajamarca NO dimensiona la deuda por cobertura:
la linea es un porcentaje fijo del costo de obra y el servicio es una
**anualidad de cuota constante**. La amortizacion es el residuo.

    Linea       = costo de obra x Tamano_deuda          (Deuda!D15)
    Desembolso  = flag obra x inversion a financiarse x Tamano_deuda
    Interes_t   = saldo_{t-1} x tasa mensual            (Deuda!38)
    Servicio_t  = flag deuda x cuota                    (Deuda!39)
    Amortiz_t   = Servicio_t - Interes_t                (Deuda!37)
    cuota       = -PMT(tasa mensual, n pagos, saldo al mes base)   (Deuda!D25)

Durante la obra el servicio es cero, asi que la amortizacion sale negativa y
el interes se capitaliza. Los dos flags son disjuntos (la obra cierra el
2030-09-30 y la deuda arranca el 2030-10-31), de modo que la cuota no es
circular: se calcula sobre el saldo ya capitalizado.
"""
import json

D = json.load(open("/mnt/project-files/generador/deuda_caj.json"))
INV, F32, F33 = D["inv"], D["f32"], D["f33"]
N = len(INV)

TAMANO = 0.8          # Deuda!D14 = Inputs!D225 x (1 + Var_deuda)
ESTRUCT = 0.02        # Deuda!D18 = Inputs!D234
COMISION = 0.01       # Deuda!D20 = Inputs!D235
KD_LIBRO = 0.09288787939497108      # Deuda!D16 = Inputs!D236
PAGOS = int(round(sum(F33)))        # Deuda!F34 = 144


def pmt(i, n, pv):
    return pv * i / (1 - (1 + i) ** -n)


def corrida(kd_anual=KD_LIBRO, tamano=TAMANO, inv=None, f32=None, f33=None):
    """`inv`, `f32` y `f33` vienen de la plantilla cuando hay proyecto nuevo:
    la inversion a financiarse y los dos flags, el de obra y el de pago."""
    inv = INV if inv is None else inv
    f32 = F32 if f32 is None else f32
    f33 = F33 if f33 is None else f33
    n = len(inv)
    pagos = int(round(sum(f33)))
    im = (1 + kd_anual) ** (1 / 12) - 1
    ic = (1 + COMISION) ** (1 / 12) - 1
    desemb = [f32[t] * inv[t] * tamano for t in range(n)]

    # fase de obra: el servicio es cero y el interes se capitaliza
    saldo, sal_obra = 0.0, [0.0] * n
    for t in range(n):
        saldo += saldo * im + desemb[t]
        sal_obra[t] = saldo
    base = next(t for t in range(n) if f33[t] > 0.5) - 1
    cuota = pmt(im, pagos, sal_obra[base])

    # pasada completa con la cuota ya fijada
    saldo = 0.0
    inte, amo, srv, sal = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
    for t in range(n):
        inte[t] = saldo * im
        srv[t] = f33[t] * cuota
        amo[t] = srv[t] - inte[t]
        saldo += desemb[t] - amo[t]
        sal[t] = saldo

    # Comision por no uso: la linea se abre el primer mes de obra
    # (`Deuda!35`), no al arranque de la malla, asi que antes no hay saldo no
    # utilizado sobre el que cobrar.
    linea = sum(inv) * tamano
    apertura = next(t for t in range(n) if f32[t] > 0.5)
    nouso, no_util = [0.0] * n, 0.0
    for t in range(n):
        if t == apertura:
            no_util = linea
        no_util -= desemb[t]
        nouso[t] = no_util * ic * f32[t]

    return {
        "cuota": cuota, "linea": linea, "saldo_base": sal_obra[base],
        "desemb": desemb, "interes": inte, "amortizacion": amo,
        "servicio": srv, "saldo": sal, "costo_no_uso": nouso,
        "costo_estructuracion": linea * ESTRUCT,
        "total_interes": sum(inte), "total_servicio": sum(srv),
        "saldo_final": sal[-1], "pagos": pagos, "mes_base": base,
        "flag_pago": list(f33),
    }


if __name__ == "__main__":
    r = corrida()
    print(f"{'':<34}{'motor':>18}{'libro':>18}{'desvio':>12}")
    for nom, mio, libro in [
        ("linea aprobada", r["linea"], 208915.84932915613),
        ("desembolsos", sum(r["desemb"]), sum(D["des"])),
        ("interes total", r["total_interes"], sum(D["int"])),
        ("servicio total", r["total_servicio"], sum(D["srv"])),
        ("cuota mensual", r["cuota"], 2692.2758856404166),
        ("saldo al mes base", r["saldo_base"], 237567.72456850973),
        ("saldo final", r["saldo_final"], 0.0),
    ]:
        print(f"  {nom:<32}{mio:>18,.6f}{libro:>18,.6f}{mio - libro:>12.6f}")
    peor = max(abs(r["interes"][t] - D["int"][t]) for t in range(N))
    print(f"\n  desvio maximo del interes mes a mes: {peor:.9f}")
