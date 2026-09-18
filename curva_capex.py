"""Como se reparte el CAPEX de obra dentro de la ventana de construccion.

Oscar pidio poder **seleccionar como se movera la curva S en la etapa de
construccion**. Antes de ofrecer curvas conviene decir que hacen los libros
aprobados, porque no es lo que el nombre sugiere.

**Ninguno de los dos usa una curva S.** Medido sobre su malla mensual, en la
ventana de obras mas puesta en marcha:

                             Cajamarca (27 meses)   San Martin (29 meses)
    CAPEX en esa ventana      244,570.74 = 93.5%    522,934,773 = 94.2%
    primer mes                    16.66%                 6.87%
    mediana del gasto             mes 10 de 27          mes 12 de 29
    mejor ajuste Beta(a,b)      (1.35 , 2.45)          (1.20 , 1.75)
    error rms del ajuste           0.046                 0.026

Lo que hay en los dos es un **bulto en el primer mes de obra** y despues mesetas
planas que escalonan, y las dos son **adelantadas**, no simetricas: en Beta,
a < b en los dos casos.

El bulto se ve igual en la malla pero **no es lo mismo en los dos libros**, y
conviene saberlo antes de darle un nombre:

  - **Cajamarca si paga un adelanto**: `'CAPEX proyecto'!21`, la linea de la
    planta de tratamiento, desembolsa 23,217.43 a precios constantes en el primer
    mes de obra sobre un total de linea de 116,087.17, o sea **20.0000 %**
    exactos, y despues no paga nada durante cinco meses: la planta recien vuelve
    a facturar en enero de 2029, en dos mesetas de 8 y 4 meses.
  - **San Martin no paga ningun adelanto**: su bulto son las `OBRAS
    PRELIMINARES` (`Capex!18` y `!122`), una partida real de 29,287,212.48, el
    5.27 % del CAPEX, que se ejecuta entera en los dos primeros meses de obra y
    se termina.

Por eso el campo se llama `Desembolso inicial de obra` y no "adelanto": describe
la FORMA, que es lo unico comun a los dos. La curva no es un supuesto libre, es
consecuencia del cronograma y de las partidas.

Por eso el modo por defecto es `malla`, que usa la malla mensual del CAPEX tal
como esta tipeada: **es el unico que reproduce los libros al centimo**. Los modos
parametricos son para el proyecto nuevo, donde la malla todavia no existe.

Los presets salen de esas dos mediciones, no de criterio:

    uniforme      Beta(1.00, 1.00)   gasto parejo
    adelantada    Beta(1.25, 2.00)   entre las dos medidas, (1.20,1.75) y (1.35,2.45)
    S simetrica   Beta(2.00, 2.00)   arranca lento, acelera al medio, cierra lento
    atrasada      Beta(2.00, 1.25)   el espejo de `adelantada`

Y con `beta` se tipean `a` y `b` a mano, para reproducir la forma exacta de un
libro (Cajamarca 1.35 y 2.45, San Martin 1.20 y 1.75).
"""
import math

MODOS = ("malla", "uniforme", "adelantada", "S simetrica", "atrasada", "beta")

PRESETS = {"uniforme": (1.00, 1.00), "adelantada": (1.25, 2.00),
           "S simetrica": (2.00, 2.00), "atrasada": (2.00, 1.25)}

# Las formas medidas sobre los libros aprobados, para quien quiera reproducirlas
# con el modo `beta`.
LIBROS = {"cajamarca": (1.35, 2.45), "san martin": (1.20, 1.75)}


def _betacf(a, b, x, it=300, eps=3e-16):
    """Fraccion continua de la beta incompleta, metodo de Lentz."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d, h = 1.0 / d, 1.0 / d
    for m in range(1, it + 1):
        m2 = 2 * m
        for num in (m * (b - m) * x / ((qam + m2) * (a + m2)),
                    -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + num * d
            c = 1.0 + num / c
            if abs(d) < 1e-300:
                d = 1e-300
            if abs(c) < 1e-300:
                c = 1e-300
            d = 1.0 / d
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def beta_cdf(x, a, b):
    """Beta incompleta regularizada, I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
          + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(ln) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln) * _betacf(b, a, 1.0 - x) / b


def pesos(n, modo="uniforme", a=None, b=None, adelanto=0.0):
    """Los `n` pesos mensuales de la ventana de obra, que suman 1.

    `adelanto` es la fraccion que cae entera el PRIMER mes de la ventana; el
    resto se reparte segun la curva.
    """
    if n <= 0:
        return []
    if modo == "beta":
        if a is None or b is None:
            raise ValueError("el modo `beta` necesita los parametros a y b")
        par = (float(a), float(b))
    elif modo in PRESETS:
        par = PRESETS[modo]
    else:
        raise ValueError(f"modo de curva desconocido: {modo!r}")
    if not 0.0 <= adelanto < 1.0:
        raise ValueError("el adelanto de obra va entre 0 y 1")

    if n == 1:
        return [1.0]
    # La curva reparte lo que no es adelanto. El adelanto ocupa el primer mes, y
    # la curva corre sobre los `n - 1` restantes para no acumular dos veces en el
    # mismo mes; sin adelanto corre sobre los `n`.
    m = n - 1 if adelanto > 0 else n
    prev, w = 0.0, []
    for k in range(1, m + 1):
        cur = beta_cdf(k / m, *par)
        w.append(cur - prev)
        prev = cur
    s = sum(w)
    w = [v / s for v in w]
    if adelanto > 0:
        return [adelanto] + [v * (1.0 - adelanto) for v in w]
    return w


def aplicar(capex, i0, i1, modo="malla", a=None, b=None, adelanto=0.0):
    """Redistribuye el CAPEX que cae en la ventana [i0, i1] segun la curva.

    Conserva el total de esa ventana y **no toca nada fuera de ella**: los
    estudios tecnicos y la supervision que corren antes de la obra se quedan
    donde el cronograma los pone.
    """
    if modo == "malla":
        return list(capex)
    if not 0 <= i0 <= i1 < len(capex):
        raise ValueError("la ventana de obra cae fuera de la malla")
    total = sum(capex[i0:i1 + 1])
    w = pesos(i1 - i0 + 1, modo, a, b, adelanto)
    out = list(capex)
    for k, peso in enumerate(w):
        out[i0 + k] = total * peso
    return out


if __name__ == "__main__":
    for modo in ("uniforme", "adelantada", "S simetrica", "atrasada"):
        w = pesos(27, modo)
        acum, s = [], 0.0
        for v in w:
            s += v
            acum.append(s)
        med = next(k for k, v in enumerate(acum) if v >= 0.5) + 1
        print(f"{modo:<14} primer mes {w[0]:>7.2%}  mediana mes {med:>2} de 27  "
              f"suma {sum(w):.10f}")
    for nom, (a, b) in LIBROS.items():
        w = pesos(27, "beta", a, b)
        print(f"{nom:<14} Beta({a},{b}) primer mes {w[0]:>7.2%}  suma {sum(w):.10f}")
    w = pesos(27, "adelantada", adelanto=0.1666)
    print(f"\ncon adelanto de 16.66 %: primer mes {w[0]:.2%}, segundo {w[1]:.2%}, "
          f"suma {sum(w):.10f}")
