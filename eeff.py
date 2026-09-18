"""Los estados financieros proyectados, con los renglones del libro aprobado.

Portado de las hojas `P&G` y `Balance` del libro de San Martin el 2026-09-17.
Oscar pidio que el tablero muestre los EEFF proyectados; el formato no se
inventa, se copia del libro, que es el que revisan PROINVERSION y el regulador.

## Lo que hubo que descubrir

**El EBITDA del P&G es DEVENGADO y el `fc_40` del motor es de CAJA.** Suman lo
mismo sobre toda la concesion (1,224,250,662.03) y **difieren hasta 308 MM en un
solo ano**, porque el P&G reconoce el ingreso financiero del activo
(`Act_Financ!19`) y el flujo reconoce el PPDI cobrado. En total el PPDI es
recuperacion de capital mas ingreso financiero, y por eso el total cuadra
igual. Usar `fc_40` como EBITDA es el caso de manual de
[[total-correcto-reparto-roto]]. El ingreso devengado lo da
`activo_financiero.cuadro`.

**Los gastos financieros del P&G son TRES lineas del motor, no una**:
`int_op` (intereses de operacion) mas `int_dc` (intereses de construccion) mas
`com_dc` (comisiones de deuda). Suman -550,197,750.24 contra `P&G!31`. Con solo
las dos primeras faltan los 18.5 MM de comisiones y el EBT se va 2.7 % arriba.

**La amortizacion del intangible es CERO en la rama cofinanciada** y no una
linea olvidada: ahi la obra es activo financiero, no intangible. La linea existe
en el P&G del libro y esta vacia. En la rama autofinanciada es
`intangible["amort_m"]` y REEMPLAZA a la depreciacion del CAPEX.

## El control

Contra el libro, con `motor_ppdmo_sm.flujo` a los parametros del propio libro:
EBITDA, EBT y resultado neto al centimo, y las once lineas de arriba tambien.
Ver [[control-libro-sanmartin]].
"""

# Los renglones del P&G del libro, en su orden, con la fila de la hoja.
# Un renglon vacio en un regimen (la amortizacion del intangible en la
# cofinanciada) se muestra igual, en cero: el lector cuenta con verlo.
FILAS_PYG = [
    (14, "Ingreso financiero (activo financiero)", "ing_fin"),
    (15, "Ingreso por construccion",               "ing_constr"),
    (16, "Ingresos PPD MO Fijo",                   "pfij"),
    (17, "PPD MO Variable",                        "pvar"),
    (18, "Pago por obra",                          "pago_obras"),
    (19, "Costo construccion",                     "capex"),
    (20, "Costos fijos",                           "costo_fijo"),
    (21, "Costos variables",                       "costo_var"),
    (22, "Otros costos de concesion",              "otros_conc"),
    (23, "Costos cierre laguna",                   "laguna"),
    (24, "IGV operacion",                          "igv_op"),
    (25, "Reposiciones",                           "repex"),
    (26, "EBITDA",                                 "ebitda"),
    (28, "Amortizacion activo intangible",         "amort_intang"),
    (29, "EBIT",                                   "ebit"),
    (31, "Gastos financieros - deuda",             "gf"),
    (34, "EBT",                                    "ebt"),
    (36, "Participacion de trabajadores",          "pt"),
    (37, "Impuesto a la renta",                    "ir"),
    (39, "Resultado neto",                         "rn"),
]


def _serie(d, k, n):
    v = d.get(k)
    return list(v) if isinstance(v, list) else [0.0] * n


def pyg(det, n=None, amort_intangible=None, ing_fin=None):
    """El estado de resultados anual, con los renglones del libro.

    `det` es el detalle que devuelven `motor_ppdmo_sm.flujo` o `flujo_sm.flujo`.
    `ing_fin` es la serie anual del ingreso del activo financiero, la que
    devuelve `activo_financiero.cuadro` agregada por ano; es obligatoria en la
    rama cofinanciada. `amort_intangible` es la serie anual de la rama
    autofinanciada; en la cofinanciada se deja en None y el renglon sale en
    cero, como en el libro.

    Devuelve `{clave: serie anual}` con todas las claves de `FILAS_PYG`.
    """
    n = n or len(det["pfij"])
    g = lambda k: _serie(det, k, n)
    out = {}
    # El ingreso devengado del activo financiero. Sin el, el EBITDA anual esta
    # mal aunque el total cuadre: hay que pasarlo o traerlo en `det`.
    out["ing_fin"] = list(ing_fin) if ing_fin is not None else g("ing_fin")
    # El servicio de construccion se reconoce como ingreso Y como costo por el
    # mismo importe: `P&G!15` y `!19` son la misma cifra con signo opuesto y su
    # neto en el EBITDA es cero. No es redundante, es la CINIIF 12.
    out["capex"] = g("capex")
    out["ing_constr"] = [-v for v in out["capex"]]
    for k in ("pfij", "pvar", "pago_obras", "laguna", "repex", "pt", "ir"):
        out[k] = g(k)
    # El motor trae el O&M en una sola linea; el libro lo abre en tres. Cuando
    # el detalle no las trae separadas se muestra todo en `costos fijos` antes
    # que repartirlo con un supuesto inventado.
    if "costo_fijo" in det:
        out["costo_fijo"], out["costo_var"] = g("costo_fijo"), g("costo_var")
        out["otros_conc"], out["igv_op"] = g("otros_conc"), g("igv_op")
    else:
        out["costo_fijo"] = g("costo_om")
        out["costo_var"] = out["otros_conc"] = out["igv_op"] = [0.0] * n
    # DEVENGADO, no caja: el ingreso financiero del activo en lugar del PPDI
    # cobrado. El servicio de construccion entra y sale por el mismo importe.
    out["ebitda"] = [out["ing_fin"][i] + out["ing_constr"][i] + out["capex"][i]
                     + out["pfij"][i] + out["pvar"][i] + out["pago_obras"][i]
                     + out["costo_fijo"][i] + out["costo_var"][i]
                     + out["otros_conc"][i] + out["igv_op"][i]
                     + out["laguna"][i] + out["repex"][i] for i in range(n)]
    out["amort_intang"] = list(amort_intangible) if amort_intangible else [0.0] * n
    out["ebit"] = [out["ebitda"][i] - out["amort_intang"][i] for i in range(n)]
    # Las TRES lineas: intereses de operacion, de construccion y comisiones.
    io, idc, com = g("int_op"), g("int_dc"), g("com_dc")
    out["gf"] = [io[i] + idc[i] + com[i] for i in range(n)]
    out["ebt"] = [out["ebit"][i] + out["gf"][i] for i in range(n)]
    # `pt` e `ir` vienen POSITIVOS del motor (son salidas de caja); en el P&G
    # restan. Sumarlos con su signo de caja deja el resultado neto al doble.
    out["rn"] = [out["ebt"][i] - out["pt"][i] - out["ir"][i] for i in range(n)]
    return out


def tabla(p, anios):
    """El P&G como lista de filas listas para mostrar: (rotulo, serie, total)."""
    return [(rot, p[k], sum(p[k])) for _f, rot, k in FILAS_PYG if k in p]


# ---------------------------------------------------------------- Balance
# Los renglones del `Balance` del libro, en su orden y con su fila.
FILAS_BAL = [
    (15, "Activo financiero",                   "act_fin",   "activo"),
    (16, "Activo intangible",                   "act_int",   "activo"),
    (19, "Caja y equivalentes",                 "caja",      "activo"),
    (20, "CRSD",                                "crsd",      "activo"),
    (23, "CR capital de trabajo inicial",       "kt0",       "activo"),
    (24, "Cuentas por cobrar",                  "cxc",       "activo"),
    (25, "Credito fiscal (IGV construccion)",   "igv_cf",    "activo"),
    (31, "Deuda senior",                        "deuda",     "pasivo"),
    (35, "Cuentas por pagar",                   "cxp",       "pasivo"),
    (39, "Capital",                             "capital",   "patrimonio"),
    (40, "Reservas acumuladas no distribuidas", "reservas",  "patrimonio"),
]


def reservas(rn, flag_contrato=None):
    """El saldo acumulado de reservas: `P&G!45:48` del libro.

        45 saldo inicial = saldo final del ano anterior x (flag de contrato > 0)
        46 incrementos   = el resultado neto del ano si es POSITIVO
        47 reducciones   = el resultado neto del ano si es NEGATIVO
        48 saldo final   = la suma de los tres

    Las "reducciones" NO son dividendos: son la perdida del ano. En San Martin
    son -6,996,528.08 de 2027 y nada mas. Lo que lleva la reserva a cero al
    terminar la concesion es **el flag de contrato**, no una distribucion:
    apagado el flag, el saldo inicial arranca en cero y el renglon se vacia.
    Tratar las reducciones como reparto deja la reserva 450 MM arriba en el
    ultimo ano y rompe el cuadre del balance.
    """
    n = len(rn)
    flag = list(flag_contrato) if flag_contrato else [1.0] * n
    out, prev = [], 0.0
    for i in range(n):
        ini = prev if flag[i] > 0 else 0.0
        prev = ini + rn[i] if flag[i] > 0 else 0.0
        out.append(prev)
    return out


def balance(**stocks):
    """El balance anual con los renglones del libro y sus dos comprobaciones.

    Cada argumento es una serie anual de SALDOS de cierre (no de flujos). Los
    que no se pasan salen en cero, como los renglones vacios del libro.

    Devuelve las series, `total_activo`, `total_pasivo_patrimonio`,
    `check_balance` (su diferencia, que tiene que ser cero) y `check_caja`
    (1 en los anos con caja negativa, que es un error de modelo, no un
    resultado).
    """
    n = max((len(v) for v in stocks.values() if isinstance(v, list)), default=0)
    s = {k: (list(v) if isinstance(v, list) else [0.0] * n)
         for _f, _r, k, _g in FILAS_BAL for v in [stocks.get(k)]}
    act = [sum(s[k][i] for _f, _r, k, g in FILAS_BAL if g == "activo")
           for i in range(n)]
    pas = [sum(s[k][i] for _f, _r, k, g in FILAS_BAL if g != "activo")
           for i in range(n)]
    s["total_activo"] = act
    s["total_pasivo_patrimonio"] = pas
    s["check_balance"] = [act[i] - pas[i] for i in range(n)]
    s["check_caja"] = [1 if round(s["caja"][i], 2) < 0 else 0 for i in range(n)]
    return s
