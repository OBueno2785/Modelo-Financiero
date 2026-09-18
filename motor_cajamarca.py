"""Reproduce el cierre del PPDI del modelo PTAR Cajamarca sin Excel ni Solver.

Primitivas (no dependen del PPDI): costo de obra, fideicomiso, seguros,
garantias, reembolso de gastos del proceso, costo de estructuracion, comision,
gastos financieros de la deuda y el calendario contractual.

Incognita: el PPDI base mensual, que en el libro vive en PPDI!H367 y se resuelve
con Buscar Objetivo hasta que PPDI!D378 = VAN(FC antes de deuda ; WACC) = 0.
Aca se resuelve por biseccion.
"""
import json

D = json.load(open("cajamarca_primitivos.json"))
S, K = D["series"], D["escalares"]
N = K["n_meses"]
IGV, TASA_IR = K["igv"], K["ir"]
WACC_M = K["wacc_mensual"]
PLAZO_PPI = 15                      # Inputs!D214, anos de pago del PPDI
MES_INICIAL = 10                    # el mes 1 del contrato es octubre

flag  = S["flag_ppdi"]              # meses en que se devenga PPDI
obra  = S["costo_obra"]
fid   = S["fideicomiso"]
seg   = S["seguros"]
gar   = S["garantias"]
reem  = S["reembolso"]
estr  = S["estructuracion"]
com   = S["comision"]
gfin  = S["gastos_fin"]             # gastos financieros de la deuda senior
ftrib = S["flag_trib"]              # mes en que se carga el IR del ano
anio  = S["anio"]

SC = [obra[t] + fid[t] + seg[t] + gar[t] + reem[t] + estr[t] + com[t] for t in range(N)]
mes_cal = [((t + MES_INICIAL - 1) % 12) + 1 for t in range(N)]
# El PPDI se devenga mensual y se paga al cierre de cada trimestre calendario.
paga = [1 if flag[t] and mes_cal[t] in (3, 6, 9, 12) else 0 for t in range(N)]


def usar_tributos(igv=None, ir=None):
    """IGV e Impuesto a la Renta de la plantilla. Sin esto el cierre del PPDI
    corre siempre con las tasas del libro de Cajamarca."""
    global IGV, TASA_IR
    IGV = IGV if igv is None else igv
    TASA_IR = TASA_IR if ir is None else ir


def usar_calendario(cal):
    """Reemplaza el calendario del libro por el que sale de las fechas de la
    plantilla (`calendario_caj.malla_ppdi`). Sin esto el motor corre siempre
    sobre el cronograma de Cajamarca."""
    global N, flag, ftrib, anio, mes_cal, paga
    N = cal["n"]
    flag, ftrib, anio, mes_cal = (cal["flag_ppdi"], cal["flag_trib"],
                                  cal["anio"], cal["mes_cal"])
    paga = [1 if flag[t] and mes_cal[t] in (3, 6, 9, 12) else 0 for t in range(N)]


def irr(flows, lo=1e-9, hi=0.20, it=300):
    def npv(r):
        return sum(f / (1 + r) ** i for i, f in enumerate(flows))
    fa = npv(lo)
    for _ in range(it):
        m = (lo + hi) / 2
        fm = npv(m)
        if fa * fm <= 0:
            hi = m
        else:
            lo, fa = m, fm
    return (lo + hi) / 2


def corrida(X, k_gfin=1.0, gfin_ext=None, ext=None):
    """`ext` reemplaza las primitivas del libro por las que sale de la plantilla:
    obra, fideicomiso, seguros, garantias, reembolso, estructuracion y comision."""
    gf = gfin if gfin_ext is None else gfin_ext
    e = ext or {}
    _obra = e.get("obra", obra)
    _sc = ([_obra[t] + e.get("fid", fid)[t] + e.get("seg", seg)[t]
            + e.get("gar", gar)[t] + e.get("reem", reem)[t]
            + e.get("estr", estr)[t] + e.get("com", com)[t] for t in range(N)]
           if ext else SC)
    devengo = [flag[t] * X for t in range(N)]
    cobro, acum = [0.0] * N, 0.0
    for t in range(N):
        acum += devengo[t]
        if paga[t]:
            cobro[t], acum = acum, 0.0

    # Tasa implicita: TIR de (-servicio de construccion + PPDI cobrado)
    r = irr([-_sc[t] + cobro[t] for t in range(N)])

    af, ing_fin, prev = [0.0] * N, [0.0] * N, 0.0
    for t in range(N):
        ing_fin[t] = prev * r if t else 0.0
        af[t] = prev + _sc[t] + ing_fin[t] - cobro[t]
        prev = af[t]

    # --- Bloque tributario, por ano calendario ---
    anios = sorted(set(anio))
    ag = lambda serie: {a: sum(serie[t] for t in range(N) if anio[t] == a) for a in anios}
    a_sc, a_if, a_gf, a_cobro = (ag(_sc), ag(ing_fin),
                                 ag([g * k_gfin for g in gf]), ag(cobro))

    ir_anual, perdidas, ded_acum, cuotas_adi = {}, 0.0, 0.0, 0
    for a in anios:
        uai = a_if[a] - a_gf[a]                        # utilidad bruta = 0
        deduccion = -a_if[a] if a_sc[a] > 1 else 0.0   # PPDI!481
        adicion = 0.0                                  # PPDI!482
        # El tope de cuotas va EXPLICITO: la formula del libro solo se apaga
        # cuando deja de cobrarse el PPDI, asi que con mas de 60 cuotas
        # adicionaria mas de lo que dedujo. Ver tributos_cajamarca._deducciones.
        if deduccion >= 0 and a_cobro[a] > 0 and cuotas_adi < PLAZO_PPI:
            adicion = -ded_acum / PLAZO_PPI
            cuotas_adi += 1
        ded_acum += deduccion
        base_previa = uai + deduccion + adicion        # PPDI!483
        perd_ant = perdidas
        perdidas = min(0.0, base_previa + perd_ant)    # PPDI!484
        if perd_ant + base_previa < 0 and perdidas == 0:
            base = base_previa
        elif perdidas < 0:
            base = 0.0
        else:
            base = base_previa + perd_ant
        base = max(0.0, base)                          # PPDI!485
        ir_anual[a] = base * TASA_IR

    ir = [ir_anual[anio[t]] if ftrib[t] == 1 else 0.0 for t in range(N)]

    # --- IGV con recuperacion anticipada a un mes ---
    _reem, _fid, _seg = e.get("reem", reem), e.get("fid", fid), e.get("seg", seg)
    compras = [(-_obra[t] - _reem[t] - _fid[t] - _seg[t]) * IGV for t in range(N)]
    igv_neto, credito = [0.0] * N, 0.0
    for t in range(N):
        dif = cobro[t] * IGV + compras[t] + (-compras[t - 1] if t else 0.0)
        acum_igv = dif + credito if t else dif
        credito = min(acum_igv, 0.0)
        igv_neto[t] = dif - (0.0 if credito < 0 else acum_igv)

    fc = [cobro[t] - _sc[t] - ir[t] + igv_neto[t] for t in range(N)]
    return dict(fc=fc, r=r, af=af, ing_fin=ing_fin, ir=ir, igv=igv_neto,
                cobro=cobro, sc=_sc)


def van(fc, rate=WACC_M):
    return sum(f / (1 + rate) ** (i + 1) for i, f in enumerate(fc))


def cerrar(rate=None, k_gfin=1.0, gfin_ext=None, ext=None, lo=0.0, hi=50_000.0, it=200):
    rate = WACC_M if rate is None else rate
    f = lambda m: van(corrida(m, k_gfin, gfin_ext, ext)["fc"], rate)
    # Sin cambio de signo en el intervalo el VAN nunca cruzo cero y la
    # biseccion devuelve el borde disfrazado de cierre, que es un numero
    # razonable y falso. Mejor que reviente.
    if f(lo) * f(hi) > 0:
        raise ValueError(
            f"el PPDI no cierra en [{lo:,.2f}, {hi:,.2f}]: "
            f"VAN {f(lo):,.2f} y {f(hi):,.2f}, sin cambio de signo")
    for _ in range(it):
        m = (lo + hi) / 2
        if van(corrida(m, k_gfin, gfin_ext, ext)["fc"], rate) < 0:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


if __name__ == "__main__":
    X, libro = cerrar(), K["ppdi_base_mensual"]
    R = corrida(X)
    print(f"PPDI base mensual resuelto  : {X:15,.4f} S/ miles")
    print(f"PPDI base mensual del libro : {libro:15,.4f} S/ miles")
    print(f"Diferencia                  : {X - libro:15,.6f}   ({(X/libro - 1)*100:+.6f} %)")
    print(f"PPDI anual resuelto         : {X*12:15,.4f} S/ miles   (libro {libro*12:,.4f})")
    print()
    print(f"VAN al WACC mensual         : {van(R['fc']):,.8f}")
    print(f"Tasa implicita mensual      : {R['r']:.10f}   (libro {K['tasa_implicita_mensual']:.10f})")
    print(f"Tasa implicita anual        : {(1 + R['r'])**12 - 1:.6%}")
    print(f"Saldo final activo financ.  : {R['af'][-1]:,.8f}")
    print()
    print("Contraste serie por serie contra los valores en cache del libro:")
    for nom, calc, ref in [
        ("PPDI cobrado",            R["cobro"],   [-v for v in S["ppdi"]]),
        ("Ingresos financieros",    R["ing_fin"], S["ing_fin"]),
        ("Impuesto a la Renta",     R["ir"],      S["ir"]),
        ("Efecto neto IGV",         R["igv"],     S["igv_neto"]),
        ("Saldo activo financiero",  R["af"],     S["af_saldo"]),
        ("FC antes de deuda",       R["fc"],      S["fc_antes_deuda"]),
    ]:
        dmax = max(abs(a - b) for a, b in zip(calc, ref))
        print(f"  {nom:<24} desvio max {dmax:12,.6f}   total {sum(calc):15,.2f} vs {sum(ref):15,.2f}")
