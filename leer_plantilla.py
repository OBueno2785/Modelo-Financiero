"""Lee la plantilla de entrada y arma las series que consume el motor.

El usuario entrega precios constantes; aca se aplican los dos indices del modelo
(IPM a los ingresos, IPC a los costos) y se reparten los totales anuales sobre
la malla mensual, que es exactamente lo que hacen las hojas `Costos`,
`'OPEX proyecto'` y `'CAPEX proyecto'` del libro aprobado.
"""
import json
from openpyxl import load_workbook

RUTA = "/mnt/project-files/generador/Plantilla_Proyecto_Nuevo.xlsx"
FIJOS = ["personal", "mant_obra_civil", "mant_colectores", "energia_electrica",
         "productos_materiales", "gestion_monitoreo", "reposiciones"]
VARIABLES = ["energia_ptar", "reactivos", "residuos"]
# El PPDMO fijo se calcula sobre los costos fijos SIN reposiciones: el libro usa
# `Costos!38`, que es la suma de las lineas de `Costos Cajamarca` y las excluye.
FIJOS_PPDMO = [c for c in FIJOS if c != "reposiciones"]


def leer(ruta=RUTA):
    wb = load_workbook(ruta, data_only=True)
    p = {}
    ws = wb["Proyecto"]
    for r in range(6, ws.max_row + 1):
        etiqueta, valor = ws.cell(r, 2).value, ws.cell(r, 4).value
        if etiqueta and valor is not None:
            p[etiqueta] = valor

    ws = wb["CAPEX"]
    capex, fechas = [], []
    for r in range(6, ws.max_row + 1):
        f, v = ws.cell(r, 2).value, ws.cell(r, 4).value
        if isinstance(f, str) and isinstance(v, (int, float)):
            fechas.append(f)
            capex.append(v)

    ws = wb["OPEX"]
    n = sum(1 for c in range(4, ws.max_column + 1)
            if isinstance(ws.cell(5, c).value, (int, float)))
    opex = {}
    from plantilla import LINEAS_OPEX
    etiqueta_a_clave = {e: c for e, c in LINEAS_OPEX if c}
    for r in range(8, ws.max_row + 1):
        clave = etiqueta_a_clave.get(ws.cell(r, 2).value)
        if clave:
            opex[clave] = [ws.cell(r, 4 + j).value or 0.0 for j in range(n)]

    ws = wb["Otros"]
    from plantilla import OTROS, OTROS_OP
    otros = {clave: [ws.cell(6 + i, 4 + j).value or 0.0 for i in range(len(fechas))]
             for j, (_, clave) in enumerate(OTROS)}
    # segundo bloque: las mismas lineas durante la operacion, que no entran al
    # activo financiero del PPDI sino al flujo de caja financiero
    otros_op = {clave: [ws.cell(6 + i, 4 + len(OTROS) + j).value or 0.0
                        for i in range(len(fechas))]
                for j, (_, clave) in enumerate(OTROS_OP)}

    hitos = {}
    if "Hitos" in wb.sheetnames:
        wh = wb["Hitos"]
        pct = []
        for r in range(6, wh.max_row + 1):
            etiqueta, valor = wh.cell(r, 2).value, wh.cell(r, 4).value
            if not etiqueta or valor is None:
                continue
            if str(etiqueta).startswith("Hito "):
                pct.append(valor)
            else:
                hitos[etiqueta] = valor
        hitos["pct_capex"] = pct

    opex_hitos, anio_hitos = {}, []
    if "OPEX hitos" in wb.sheetnames:
        wo = wb["OPEX hitos"]
        nh = sum(1 for c in range(4, wo.max_column + 1)
                 if isinstance(wo.cell(5, c).value, (int, float)))
        anio_hitos = [wo.cell(5, 4 + j).value for j in range(nh)]
        from plantilla import LINEAS_OPEX_HITOS
        et_a_clave = {e: c for e, c in LINEAS_OPEX_HITOS if c}
        for r in range(7, wo.max_row + 1):
            clave = et_a_clave.get(wo.cell(r, 2).value)
            if clave:
                opex_hitos[clave] = [wo.cell(r, 4 + j).value or 0.0
                                     for j in range(nh)]

    # `Cronograma`: una fila por etapa con su mes de inicio y de fin contados
    # desde el cierre del contrato, con la forma de `Inputs!107:145` de
    # Cajamarca. Cuando la hoja esta, ella manda sobre las fechas sueltas de
    # `Proyecto`; las plantillas viejas no la traen y siguen igual que antes.
    crono = {}
    if "Cronograma" in wb.sheetnames:
        wc = wb["Cronograma"]
        for r in range(6, wc.max_row + 1):
            etiqueta = wc.cell(r, 2).value
            desde, hasta = wc.cell(r, 4).value, wc.cell(r, 5).value
            if etiqueta and isinstance(desde, (int, float)) \
                    and isinstance(hasta, (int, float)):
                crono[str(etiqueta)] = (int(desde), int(hasta))
    if crono:
        p.update(fechas_de_cronograma(crono, fechas,
                                      p["Fecha de cierre del contrato"]))

    # La curva de construccion redistribuye SOLO el CAPEX que cae en la ventana
    # de obra, y solo si el usuario pidio un modo parametrico.
    modo = str(p.get("Curva de la construccion", "malla")).strip()
    if modo != "malla":
        import curva_capex as CU
        ini, fin = p["Inicio de obras"], p["Fin de obras y puesta en marcha"]
        i0 = fechas.index(ini) + 1 if ini in fechas else 0
        i1 = fechas.index(fin) if fin in fechas else len(fechas) - 1
        capex = CU.aplicar(capex, i0, i1, modo,
                           p.get("Parametro a de la curva"),
                           p.get("Parametro b de la curva"),
                           p.get("Desembolso inicial de obra", 0.0) or 0.0)

    anio_con = [wb["OPEX"].cell(5, 4 + j).value for j in range(n)]
    anio_cal = [wb["OPEX"].cell(6, 4 + j).value for j in range(n)]
    return {"proyecto": p, "capex": capex, "fechas": fechas, "opex": opex,
            "cronograma": crono,
            "otros": otros, "otros_op": otros_op, "hitos": hitos,
            "opex_hitos": opex_hitos, "anio_hitos": anio_hitos,
            "anios": n,
            "anio_concesion": anio_con, "anio_calendario": anio_cal}


def fechas_de_cronograma(crono, fechas, cierre):
    """Las fechas sueltas de `Proyecto`, derivadas del cronograma por hitos.

    El mes `k` del cronograma es el **cierre del mes k-esimo** contado desde la
    fecha de cierre del contrato, o sea `fechas[k - 1]`; el mes 0 es la fecha de
    cierre misma. Es la convencion de `Inputs!107:145`, donde el mes 12 cae en
    2027-09-30 con un cierre en 2026-10-01.
    """
    from plantilla import FECHAS_DERIVADAS

    def fecha(k):
        if k <= 0:
            return cierre
        return fechas[min(k - 1, len(fechas) - 1)]

    out = {}
    for destino, etapa, extremo in FECHAS_DERIVADAS:
        if etapa in crono:
            out[destino] = fecha(crono[etapa][0 if extremo == "ini" else 1])
    return out


def indice_costos(fechas, ipc, mes_inicio_om, base_idx=1.0):
    """Replica `'OPEX proyecto'!13`: acumula el IPC mes a mes, sin gatillo.

    No arranca en 1: el libro llega al inicio de O&M con el IPC ya acumulado
    desde la fecha de los precios constantes (`Inputs!77`). Ese arranque es un
    dato de la plantilla.

    En Cajamarca ese arranque es 1.098628385697407, que es **exactamente** 57
    meses de IPC 2.00 %: los precios constantes son de **diciembre de 2025** y la
    operacion arranca en setiembre de 2030. El indice del CAPEX,
    1.016639102626978, son **exactamente** 10 meses del mismo IPC desde la misma
    fecha hasta el cierre del contrato, octubre de 2026. O sea que no mezcla IPC
    observado con proyectado: es IPC proyectado al 2.00 % de punta a punta.
    """
    im = (1 + ipc) ** (1 / 12) - 1
    idx, f = [], base_idx
    base = fechas.index(mes_inicio_om) if mes_inicio_om in fechas else 0
    for i in range(len(fechas)):
        if i > base:
            f *= 1 + im
        idx.append(f)
    return idx


def indice_capex(fechas, ipc, base_idx=1.0):
    """Replica `'CAPEX proyecto'!16`: el indice del CAPEX compone el IPC desde el
    cierre del contrato, partiendo del acumulado que ya trae desde la fecha de
    los precios constantes."""
    im = (1 + ipc) ** (1 / 12) - 1
    return [base_idx * (1 + im) ** i for i in range(len(fechas))]


def construccion(datos):
    """CAPEX a precios corrientes y la inversion que entra al modulo de deuda.

    `'CAPEX proyecto'!37` es el costo de obra que consume el cierre del PPDI, y
    `Deuda!12` lo filtra por el flag de obra y puesta en marcha.
    """
    p, fechas = datos["proyecto"], datos["fechas"]
    idx = indice_capex(fechas, p["IPC, reajuste de costos"],
                       p.get("Indice de CAPEX al cierre del contrato", 1.0))
    costo_obra = [datos["capex"][i] * idx[i] for i in range(len(fechas))]
    ini, fin = p["Inicio de obras"], p["Fin de obras y puesta en marcha"]
    i0 = fechas.index(ini) if ini in fechas else 0
    i1 = fechas.index(fin) if fin in fechas else len(fechas) - 1
    flag = [1 if i0 < i <= i1 else 0 for i in range(len(fechas))]
    return {"costo_obra": costo_obra, "flag_obra": flag,
            "inversion": [costo_obra[i] * flag[i] for i in range(len(fechas))],
            "indice_capex": idx}


def calendario(fechas, inicio_contrato):
    """Ano calendario y ano de concesion de cada mes de la malla."""
    base = fechas.index(inicio_contrato) if inicio_contrato in fechas else 0
    cal = [int(f[:4]) for f in fechas]
    con = [(i - base) // 12 + 1 for i in range(len(fechas))]
    return cal, con


def series(datos):
    """Costos de operacion mensuales a precios corrientes, y produccion en kg."""
    p, opex = datos["proyecto"], datos["opex"]
    fechas, nA = datos["fechas"], datos["anios"]
    ipc = p["IPC, reajuste de costos"]
    conv = p["Factor de conversion a kg DBO5"]
    ini_om = p["Inicio de operacion"]
    idx = indice_costos(fechas, ipc, ini_om,
                        p.get("Indice de costos al inicio de O&M", 1.0))
    cal, con = calendario(fechas, datos["proyecto"]["Fecha de cierre del contrato"])
    fin = p["Fin de la concesion"]
    i0 = fechas.index(ini_om)
    i1 = fechas.index(fin) if fin in fechas else len(fechas) - 1
    vivo = [1 if i0 < i <= i1 else 0 for i in range(len(fechas))]

    # El libro busca cada linea por una clave distinta: el OPEX por ano de
    # concesion (`'OPEX proyecto'!T$6`) y la demanda por ano calendario
    # (`PPDMO!27`, que entra a `Costos` con el ano calendario).
    por_con = {datos["anio_concesion"][a]: a for a in range(nA)}
    por_cal = {datos["anio_calendario"][a]: a for a in range(nA)}

    def mensualizar(anual, clave, llaves):
        out = [0.0] * len(fechas)
        for i in range(len(fechas)):
            a = llaves.get(clave[i])
            if a is not None and vivo[i]:
                out[i] = anual[a] / 12 / 1000
        return out

    # Los costos fijos y los gastos de la SPV van por ano de concesion; los
    # variables y la demanda, por ano calendario, porque siguen al caudal.
    fijo = mensualizar([sum(opex[c][a] for c in FIJOS) for a in range(nA)], con, por_con)
    var = mensualizar([sum(opex[c][a] for c in VARIABLES) for a in range(nA)], cal, por_cal)
    spv = mensualizar([opex["gastos_spv"][a] for a in range(nA)], con, por_con)
    kg = mensualizar([opex["demanda_m3"][a] * conv * 1000 for a in range(nA)],
                     cal, por_cal)

    # Base del PPDMO fijo a precios constantes: promedio de los costos fijos
    # SIN reposiciones (`Costos!38`), mas el margen. El mes de IPM que le suma
    # `PPDMO!17` lo aplica el modelo sombra, porque depende del IPM que se corra.
    prom_fijo = sum(sum(opex[c][a] for c in FIJOS_PPDMO)
                    for a in range(nA)) / nA
    fijo_base_cte = prom_fijo / 12 / 1000 * (1 + p["Margen del costo fijo"])
    ipm_m = (1 + p["IPM, reajuste de ingresos"]) ** (1 / 12) - 1
    fijo_base = fijo_base_cte * (1 + ipm_m)

    # El libro redondea a dos decimales de S/ miles cada total mensual
    # (`'OPEX proyecto'!67`, `!76`), no al final.
    rd = lambda x: -round(x, 2)
    return {"costo_fijo": [rd(fijo[i] * idx[i]) for i in range(len(fechas))],
            "costo_var": [rd(var[i] * idx[i]) for i in range(len(fechas))],
            "gastos_spv": [rd(spv[i] * idx[i]) for i in range(len(fechas))],
            "kg": kg, "fijo_base": fijo_base, "fijo_base_cte": fijo_base_cte,
            "indice_costos": idx}


if __name__ == "__main__":
    d = leer()
    s = series(d)
    print(f"proyecto              : {d['proyecto']['Nombre del proyecto']}")
    print(f"meses de la malla     : {len(d['fechas'])}   anos de OPEX: {d['anios']}")
    print(f"CAPEX total           : {sum(d['capex']):>16,.2f} S/ miles")
    print(f"PPDMO fijo base       : {s['fijo_base']:>16,.4f} S/ miles al mes")
    print(f"costo fijo total      : {sum(s['costo_fijo']):>16,.2f}")
    print(f"costo variable total  : {sum(s['costo_var']):>16,.2f}")
    print(f"produccion total (kg) : {sum(s['kg']):>16,.0f}")
