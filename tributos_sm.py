"""Las tres filas de `Impuestos` que el flujo por hitos necesita.

Ninguna es un dato: las tres salen del CAPEX, del calendario y de los intereses
de construccion, asi que un proyecto nuevo las produce solo.

  `Impuestos!61`  Cuota de amortizacion tributaria del CAPEX. Se reparte lineal
                  sobre los meses de operacion en que todavia se cobra PPDI, no
                  sobre toda la concesion.
  `Impuestos!68`  Intereses del periodo [D + C + PM], del modulo de deuda.
  `Impuestos!70`  Su amortizacion, en cuotas iguales durante los primeros anos
                  de operacion (10 en el libro, `Impuestos!D69`).
"""


def amortizacion_capex(capex_total, flag_op, hay_ppdi):
    """`Impuestos!59:61`. `hay_ppdi[i]` dice si el ano i todavia cobra PPDI."""
    ny = len(flag_op)
    meses = [12 * flag_op[i] * (1 if hay_ppdi[i] else 0) for i in range(ny)]
    restantes = [sum(meses[i:]) * (1 if flag_op[i] > 0 else 0) for i in range(ny)]
    tope = max(restantes) if restantes else 0.0
    if not tope:
        return [0.0] * ny
    return [capex_total * meses[i] / tope for i in range(ny)]


def amortizacion_gastos_fin(interes_construccion, flag_op, plazo=10.0):
    """`Impuestos!67:70`."""
    ny = len(flag_op)
    out, vivos = [0.0] * ny, 0
    for i in range(ny):
        activo = 1 if flag_op[i] == 1 else 0
        vivos += activo
        if activo and vivos <= plazo:
            out[i] = interes_construccion / plazo
    return out
