"""El Costo Total de la Inversion, como lo calcula el libro aprobado.

Reproducido de la hoja `CTI` del libro de San Martin el 2026-09-17, al centimo.
Oscar decidio ese mismo dia **manejar solo el CTI y dejar el CTP fuera**, asi
que aca no hay CTP: la hoja del libro se titula "COSTO TOTAL DE LA INVERSION &
COSTO TOTAL DEL PROYECTO" pero nunca resuelve el segundo, y no lo inventamos.

## Las tres cosas que hay que saber, porque ninguna se lee del rotulo

1. **La tasa NO es el 10 % que muestra `CTI!D27`.** Ese 10 % es el formato: la
   celda vale `0.099512997361`, que es **el WACC en soles**, `Ke!C25`, al
   digito. Descontar al 10 % redondo deja el CTI 0.36 MM corto.

2. **El exponente de descuento es el flag de contrato ACUMULADO**, `FC!10`
   sumado ano a ano, que arranca en **0.1666667** porque el contrato empieza en
   noviembre. O sea 0.1667, 1.1667, 2.1667, 3.1667, 4.1667 y no 1, 2, 3, 4, 5.
   Es la misma convencion del cierre del PPDMO, no una de esta hoja.

3. **La base es NOMINAL y lleva el IGV adentro**: las diez partidas suman
   673,214,033.91 con 100,573,202.72 de IGV. No es el CAPEX de `Nec_Fin!D14`
   (555,323,846.25), que no lleva ni el IGV ni los preoperativos.

Con las tres, el CTI da **505,246,308.570018** contra `CTI!D30`, desvio
**0.00000000**, y **94,438.5623 UIT** contra `CTI!D33` con la UIT en 5,350.

Las diez partidas del libro, por si hay que rearmarlas: los cuatro CAPEX por
hito, garantia de fiel cumplimiento de obra, seguros, fideicomiso, costos de
administracion y oficina, reembolso de gastos a PRO + BID, e IGV.
"""

# `CTI!D32` del libro. Es un valor de ley, cambia cada ano: va por parametro.
UIT_LIBRO = 5350.0


def flag_acumulado(flag):
    """El exponente de descuento: la suma corrida del flag de contrato `FC!10`.

    El primer ano vale la fraccion del ano que el contrato ocupa (0.1667 en San
    Martin, que arranca en noviembre), no 1.
    """
    out, s = [], 0.0
    for f in flag:
        s += f
        out.append(s)
    return out


def cti(partidas, tasa, flag, uit=None):
    """El CTI: valor presente de las partidas nominales al WACC del proyecto.

    `partidas` es un diccionario `{nombre: serie anual}` o una lista de series,
    todas nominales y con el IGV adentro, sobre la misma malla anual que `flag`.
    `flag` es el flag de contrato anual (`FC!10`), no su acumulado: esta funcion
    lo acumula. `uit` en soles convierte el resultado; sin ella no se reporta.

    Devuelve `(valor en soles, valor en UIT o None, total nominal)`.
    """
    series = list(partidas.values()) if isinstance(partidas, dict) else list(partidas)
    n = len(flag)
    for s in series:
        if len(s) != n:
            raise ValueError(f"una partida trae {len(s)} anios y el flag {n}")
    total = [sum(s[a] for s in series) for a in range(n)]
    exp = flag_acumulado(flag)
    vp = sum(t / (1.0 + tasa) ** e for t, e in zip(total, exp) if abs(t) > 1e-12)
    return vp, (vp / uit if uit else None), sum(total)


def detalle(partidas, tasa, flag):
    """El CTI abierto por partida, que es como lo revisa PROINVERSION."""
    exp = flag_acumulado(flag)
    out = {}
    for nombre, s in partidas.items():
        out[nombre] = dict(
            nominal=sum(s),
            presente=sum(v / (1.0 + tasa) ** e for v, e in zip(s, exp) if abs(v) > 1e-12))
    return out
