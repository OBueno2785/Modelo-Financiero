"""La malla mensual de obra: ventanas uniformes por partida, no una curva.

Leido de `Capex!14:152` del libro de San Martin el 2026-09-17, y es lo que
convierte la curva de construccion de un supuesto libre en un dato del
cronograma.

**Cada partida de CAPEX se ejecuta a monto PAREJO dentro de su propia ventana
de meses.** No hay curva S, no hay beta, no hay centroide. Lo que parece una
curva en la malla total es la SUPERPOSICION de ventanas que empiezan y terminan
en meses distintos.

La prueba, sobre el libro de San Martin:

1. La malla total `Nec_Fin!14` cambia de nivel en los meses 11, 21, 32, 34, 37,
   54 y 58, y ese conjunto es EXACTAMENTE la union de los arranques y los
   cierres de las ventanas de las partidas (arranques en 11, 32, 37 y 54;
   cierres en 20, 31, 33, 53, 57 y 60).
2. Dentro de su ventana, cada partida crece mes a mes un **0.0986 % constante**,
   que es el indice (1.000986^12 - 1 = 1.19 % anual, el IPM proyectado del
   libro). O sea que **a precios constantes es exactamente plana**.
3. Los siete niveles de la malla son la suma de las partidas activas en cada
   tramo.

Las quince ventanas del libro estan en `SAN_MARTIN` como referencia. La
`UTILIDAD` no es una ventana: es un margen sobre las demas, por eso su serie
tiene huecos donde solo corre supervision.

**Por que importa.** Con una curva parametrica el gasto se adelanta: al mes 21
una beta acumula ~22 % del CAPEX y el libro lleva **5.33 %**. La deuda gira
contra el gasto, asi que una curva adelantada adelanta el primer giro y cambia
el interes de construccion. La forma no es un supuesto, es el cronograma.

Ver `curva_capex`, que mide la forma resultante, y `plantilla.volcar_cronograma`,
que es quien manda sobre las fechas sueltas de la hoja `Proyecto`.
"""

# Las ventanas del libro de San Martin, en meses de la malla (columna F = mes 1
# = 2025-01). Fraccion del CAPEX total, a precios del libro.
SAN_MARTIN = [
    ("Expediente tecnico",                    11, 20),
    ("Interferencias",                        11, 20),
    ("Intervencion social en expediente",     11, 20),
    ("Supervision del expediente",            11, 31),
    ("Obras preliminares",                    32, 33),
    ("Obras civiles",                         32, 53),
    ("Medidas de mitigacion ambiental",       32, 53),
    ("Intervencion social en obra",           32, 53),
    ("Obras complementarias",                 32, 53),
    ("Costo indirecto",                       32, 57),
    ("Supervision de obra y puesta en marcha", 32, 60),
    ("Equipos electromecanicos",              37, 53),
    ("Equipos electricos y automatizacion",   37, 53),
    ("Puesta en marcha",                      54, 57),
    ("Fortalecimiento de capacidades",        54, 60),
]


def malla(partidas, n, indice=None):
    """Arma la malla mensual de CAPEX repartiendo cada partida en su ventana.

    `partidas` es una lista de `(nombre, monto, mes_ini, mes_fin)` con los meses
    en base 1 sobre una malla de `n` meses; `monto` va a precios constantes.
    `indice` es la serie de `n` factores que lleva cada mes a precios corrientes;
    si no se pasa, la malla queda a precios constantes.

    Devuelve la lista de `n` importes mensuales.
    """
    if n <= 0:
        raise ValueError("la malla necesita al menos un mes")
    if indice is not None and len(indice) != n:
        raise ValueError(f"el indice tiene {len(indice)} meses y la malla {n}")
    out = [0.0] * n
    for nombre, monto, i0, i1 in partidas:
        if not 1 <= i0 <= i1 <= n:
            raise ValueError(f"la ventana de {nombre!r} ({i0}..{i1}) cae fuera "
                             f"de la malla de {n} meses")
        cuota = monto / (i1 - i0 + 1)
        for m in range(i0, i1 + 1):
            out[m - 1] += cuota
    if indice is not None:
        out = [v * f for v, f in zip(out, indice)]
    return out


def bandas(serie, tol=1e-6):
    """Los tramos de nivel de una malla, para mostrarla sin listar 50 meses.

    Devuelve `(mes_ini, mes_fin, importe_mensual, total)` por tramo. Dos meses
    caen en el mismo tramo cuando su importe coincide dentro de `tol` relativo,
    asi que una malla indexada hay que pasarla a precios constantes primero o
    cada mes sera su propio tramo.
    """
    out = []
    for m, v in enumerate(serie, start=1):
        if out and abs(v - out[-1][2]) <= tol * max(1.0, abs(out[-1][2])):
            i0, _, imp, tot = out[-1]
            out[-1] = (i0, m, imp, tot + v)
        else:
            out.append((m, m, v, v))
    return out


def acumulado(serie):
    """La fraccion acumulada mes a mes, que es contra lo que gira la deuda."""
    tot = sum(serie)
    if tot <= 0:
        return [0.0] * len(serie)
    acum, s = [], 0.0
    for v in serie:
        s += v
        acum.append(s / tot)
    return acum
