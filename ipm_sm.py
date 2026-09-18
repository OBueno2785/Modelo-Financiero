"""Replica el bloque de reajuste por IPM del libro (Hip_Mensual 29-35).

El PPDMO se reajusta con gatillo de 3 % (fila 33) y el OPEX se reajusta sin
gatillo (fila 35); por eso la proyeccion del IPM mueve el cierre.
"""
from datetime import date

INI, FIN, N0 = date(2025, 11, 1), date(2049, 10, 31), date(2025, 1, 1)
TRIGGER = 0.03
NM = 336


def meses():
    out = []
    y, m = N0.year, N0.month
    for _ in range(NM):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


MESES = meses()
FLAG = [1 if (date(y, m, 1) >= INI and date(y, m, 1) <= FIN) else 0
        for y, m in MESES]


def factores(ipm_anual, flag=None):
    """`flag` es la ventana de reajuste del proyecto que se esta corriendo: 1
    desde el primer mes de [D + C + PM] hasta el ultimo de operacion.

    Sin ella el reajuste se acumula sobre la ventana de San Martin, que es la
    que arma `FLAG` con las fechas del libro, y en un proyecto nuevo con otras
    fechas y otra malla el gatillo del 3 % se dispara en el mes equivocado o
    directamente fuera de la malla. Se queda como valor por defecto solo para
    reproducir el libro aprobado.

    Ojo que la ventana arranca en el **inicio de la obra**, no en el de la
    operacion: es lo que hace `Hip_Mensual` y por eso difiere de la de
    Cajamarca, que acumula desde el inicio de O&M.
    """
    flag = FLAG if flag is None else flag
    nm = len(flag)
    im = (1 + ipm_anual) ** (1 / 12) - 1
    r30 = [im * flag[t] for t in range(nm)]
    r32 = [0.0] * nm
    f33 = [0.0] * nm
    f35 = [0.0] * nm
    prev33, prev35 = 1.0, 1.0
    acc30 = 0.0
    acc32 = 0.0
    for t in range(nm):
        f33[t] = round(1.0 if flag[t] == 0 else prev33 * (1 + (r32[t-1] if t else 0.0)), 5)
        f35[t] = 1.0 if flag[t] == 0 else prev35 * (1 + (r30[t-1] if t else 0.0))
        acc30 += r30[t]
        pend = (acc30 - acc32) * (1 if r30[t] > 0 else 0)
        r32[t] = pend if pend >= TRIGGER else 0.0
        acc32 += r32[t]
        prev33, prev35 = f33[t], f35[t]
    return f33, f35


def por_anio(f, anio0=2025, ny=28):
    """El factor es constante dentro de cada anio calendario (escala en enero)."""
    out = [0.0] * ny
    cnt = [0] * ny
    for t, (y, _m) in enumerate(MESES):
        i = y - anio0
        if 0 <= i < ny and FLAG[t]:
            out[i] += f[t]
            cnt[i] += 1
    return [out[i] / cnt[i] if cnt[i] else 1.0 for i in range(ny)]


if __name__ == "__main__":
    for tasa in (0.0119, 0.0267):
        a, b = factores(tasa)
        print(f"IPM {tasa:.2%}  ingresos(2030,2040,2049) "
              f"{por_anio(a)[5]:.5f} {por_anio(a)[15]:.5f} {por_anio(a)[24]:.5f}"
              f"   opex {por_anio(b)[5]:.5f} {por_anio(b)[15]:.5f} {por_anio(b)[24]:.5f}")
