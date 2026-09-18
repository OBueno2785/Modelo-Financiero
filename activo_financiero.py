"""El activo financiero de la CINIIF 12: de donde sale el ingreso del P&G.

Leido de `Act_Financ TRIM!22:27` del libro de San Martin el 2026-09-17. La regla
son cinco renglones y **corre por TRIMESTRE**; la hoja anual `Act_Financ` es solo
un `SUMIF` de esta:

    22 saldo inicial  = saldo final del trimestre anterior
    23 + Capex
    24 + Otras inversiones del periodo D+C+PM
    25 - PPD Inversiones cobrado
    26 + Ingreso financiero  = saldo INICIAL x tasa trimestral   (`=+AN22*$D$19`)
    27 = saldo final

En San Martin la tasa es `D19` = **2.942246259480763 % trimestral**, equivalente
a **12.298657 % anual**, y el activo se extingue en **2044**, no al final de la
concesion.

## Las tres trampas, todas costaron una corrida

**El ingreso devenga sobre el saldo de APERTURA**, no sobre apertura mas la
inversion del periodo. Devengar sobre la base ampliada mete ingreso de mas desde
el primer trimestre de obra y ningun total lo delata hasta el final.

**Corre por trimestre.** La tasa anual implicita del cuadro ANUAL no es
constante: baja de 11.656 % en 2030 a 7.462 % en 2044, porque dentro del ano el
saldo ya amortizo. Quien lea esa serie como una tasa y la use, se equivoca en
todos los anos menos uno.

**La amortizacion NO se trunca en cero**: mientras el cobro del periodo sea menor
que el ingreso devengado, el activo CRECE. Truncar infla el total amortizado y
deja el saldo final distinto de cero.

Y la de arriba de todas: **el ingreso financiero no es el PPDI**. En TOTAL el
PPDI cobrado es recuperacion de capital mas ingreso financiero, asi que usar el
PPDI como ingreso del P&G da el EBITDA correcto EN TOTAL y equivocado en cada
ano: en San Martin, hasta 308 MM en un solo ano. Ver [[total-correcto-reparto-roto]].

Control: reconstruido asi, el ingreso da 891,466,417.94 contra `Act_Financ!19`,
peor trimestre 9e-6 y peor ano 0.000000.
"""

TASA_TRIM_LIBRO = 0.02942246259480763   # `Act_Financ TRIM!D19`, San Martin


def _saldo_final(inversion, cobros, r):
    s = 0.0
    for i in range(len(inversion)):
        s = s + inversion[i] - cobros[i] + s * r
    return s


def tasa(inversion, cobros, lo=0.0, hi=0.25, it=300, tol=1e-15):
    """La tasa por periodo que deja el saldo final del activo en cero.

    `inversion` y `cobros` son series POSITIVAS por periodo, en la periodicidad
    en que corre el cuadro (trimestral en los dos libros).

    Biseccion con guarda de cambio de signo: sin ella devuelve el borde del
    intervalo disfrazado de solucion.
    """
    a, b = _saldo_final(inversion, cobros, lo), _saldo_final(inversion, cobros, hi)
    if a * b > 0:
        raise ValueError(f"no hay cambio de signo entre {lo} y {hi}: saldo final "
                         f"{a:,.2f} y {b:,.2f}; el activo no se extingue")
    for _ in range(it):
        m = (lo + hi) / 2.0
        if a * _saldo_final(inversion, cobros, m) <= 0:
            hi = m
        else:
            lo, a = m, _saldo_final(inversion, cobros, m)
        if hi - lo < tol:
            break
    return (lo + hi) / 2.0


def cuadro(inversion, cobros, r=None):
    """El cuadro del activo por periodo. `ingreso` es el renglon que va al P&G."""
    n = len(inversion)
    if r is None:
        r = tasa(inversion, cobros)
    ini, ing, amo, fin = [], [], [], []
    s = 0.0
    for i in range(n):
        ini.append(s)
        g = s * r                      # sobre el saldo de APERTURA
        ing.append(g)
        amo.append(cobros[i] - g)      # puede ser negativa: el activo crece
        s = s + inversion[i] + g - cobros[i]
        fin.append(s)
    return dict(tasa=r, saldo_ini=ini, ingreso=ing, amortizacion=amo,
                saldo_fin=fin, saldo_final=s)


def anualizar(serie, anios):
    """Agrega una serie por periodo a anual, como el `SUMIF` de la hoja anual."""
    out = {}
    for a, v in zip(anios, serie):
        if a:
            out[a] = out.get(a, 0.0) + v
    return out
