"""Costos de operacion del esquema por hitos, de la plantilla al motor.

La plantilla los pide **a precios constantes y por ano calendario**; aca se les
aplica el indice mensual del OPEX (`Hip_Mensual!35`, sin gatillo) y se devuelven
en las dos formas que el modelo necesita: la anual, que entra al flujo, y la
mensual de los seis flujos de O&M, que reparte el PPDMO entre fijo y variable.

El importe mensual a precios constantes es **plano dentro del ano**: una vez
quitado el indice, los doce meses son iguales. Por eso la linea anual de la
plantilla es doce veces el valor mensual, y no la suma de doce cifras distintas.
"""
import ipm_sm as IPM

ANUALES = ("fijo_h1", "fijo_h2", "fijo_h3", "fijo_h4", "variable", "gg_u",
           "otros_op", "igv_op", "repex")
# Estas dos no se reajustan: son importes de contrato, no costos de operacion.
SIN_INDICE = ("pago_obras", "cierre_laguna")
MENSUALES = ("conigv_h1", "conigv_h2", "conigv_h3", "conigv_h4",
             "conigv_var_tar", "conigv_var_sjs")


def series(lineas, anio_mes, flag_op, ipm, anio0=2025, ny=28, ventana=None):
    """`anio_mes` es el ano calendario de cada mes de la malla.

    `ventana` es la del reajuste, del inicio de obra al fin de operacion. Sin
    ella el indice se acumula sobre las fechas del libro de San Martin.
    """
    _, f35 = IPM.factores(ipm, ventana)
    n = len(anio_mes)
    i = lambda t: int(anio_mes[t]) - anio0

    mensual = {}
    for k in MENSUALES:
        v = lineas.get(k, [0.0] * ny)
        mensual[k] = [v[i(t)] / 12 * f35[t] * (1 if flag_op[t] else 0)
                      if 0 <= i(t) < len(v) else 0.0 for t in range(n)]

    anual = {}
    for k in ANUALES:
        v = lineas.get(k, [0.0] * ny)
        out = [0.0] * ny
        for t in range(n):
            if 0 <= i(t) < len(v) and flag_op[t]:
                out[i(t)] += v[i(t)] / 12 * f35[t]
        anual[k] = out
    for k in SIN_INDICE:
        anual[k] = list(lineas.get(k, [0.0] * ny))
    return {"anual": anual, "mensual": mensual}
