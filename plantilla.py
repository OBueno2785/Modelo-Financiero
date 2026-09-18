"""Plantilla de entrada del generador: lo que el usuario llena para un proyecto nuevo.

Tres hojas de datos y una de parametros. Todo a **precios constantes**: el
reajuste por IPM y por IPC lo pone el motor, no el usuario.

  `Proyecto`  fechas del cronograma, esquema de pago, financiamiento y tributos
  `CAPEX`     malla mensual de inversion, en S/ miles
  `OPEX`      costos por ano de concesion, en soles corrientes del ano base,
              separados en fijos y variables porque el PPDMO los trata distinto
  `Otros`     las lineas menores que el flujo necesita mes a mes

Viene precargada con Cajamarca, para que se vea la forma esperada. Sobrescribir
los numeros con los del proyecto nuevo es todo lo que hace falta.
"""
import json
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

E = json.load(open("/mnt/project-files/generador/entrada_cajamarca.json"))

TIT = Font(bold=True, size=13, color="1A4B4B")
SUB = Font(size=9, italic=True, color="6B7B7B")
CAB = Font(bold=True, size=9, color="FFFFFF")
ETI = Font(size=9)
ETB = Font(bold=True, size=9)
LLENAR = PatternFill("solid", fgColor="FFF3D6")
BANDA = PatternFill("solid", fgColor="1A4B4B")
FINA = Border(bottom=Side("thin", color="D5DEDE"))

PROYECTO = [
    ("IDENTIFICACION", None, None, None),
    ("Nombre del proyecto", "PTAR Cajamarca", "@", ""),
    ("Moneda", "S/ miles", "@", "todo el libro en la misma unidad"),
    ("CRONOGRAMA", None, None, None),
    ("Fecha de cierre del contrato", "2026-10-01", "@", ""),
    ("Fecha de cierre financiero", "2028-05-31", "@", ""),
    ("Inicio de obras", "2028-06-30", "@", ""),
    ("Fin de obras y puesta en marcha", "2030-09-30", "@", ""),
    ("Inicio de operacion", "2030-09-30", "@", "arranca el PPDMO"),
    ("Fin de la concesion", "2052-09-30", "@", ""),
    # Oscar pidio poder elegir como se mueve la curva en la etapa de
    # construccion. `malla` usa la malla mensual del CAPEX tal como esta
    # tipeada y es el UNICO modo que reproduce los libros aprobados al
    # centimo; los parametricos son para el proyecto nuevo, donde la malla
    # todavia no existe. Ver `curva_capex`, que trae medida la forma real de
    # los dos libros.
    ("Curva de la construccion", "malla", "@",
     "malla | uniforme | adelantada | S simetrica | atrasada | beta"),
    ("Parametro a de la curva", 1.25, "0.00", "solo con `beta`; Cajamarca 1.35, San Martin 1.20"),
    ("Parametro b de la curva", 2.0, "0.00", "solo con `beta`; Cajamarca 2.45, San Martin 1.75"),
    # No se llama "adelanto de obra" porque los libros no lo tienen como tal:
    # Cajamarca si paga un adelanto, 20.0000 % de la linea de la planta, pero
    # San Martin no paga ninguno, su bulto son las OBRAS PRELIMINARES, una
    # partida real de dos meses. Los dos se ven igual en la malla, asi que el
    # campo describe la FORMA, que es lo unico comun: cuanto del CAPEX de la
    # ventana de obra cae entero en su primer mes.
    ("Desembolso inicial de obra", 0.0, "0.00%",
     "% del CAPEX de la ventana de obra que cae entero en su primer mes; no aplica con `malla`"),
    ("ESQUEMA DE PAGO", None, None, None),
    # CINIIF 12: en la cofinanciada el concedente se obliga a pagar importes
    # determinables y el derecho de cobro es incondicional, asi que la obra se
    # reconoce como activo financiero (parrafo 16). En la autofinanciada lo que
    # se recibe es la licencia de cobro a usuarios, que depende del uso, y va
    # como activo intangible (parrafo 17); solo en ese caso se capitalizan los
    # costos por prestamos (parrafo 22).
    ("Regimen de la APP", "cofinanciada", "@",
     "cofinanciada (activo financiero) | autofinanciada (activo intangible)"),
    ("Pago del PPDI", "al final de obra", "@", "al final de obra | por hitos"),
    ("Numero de cuotas del PPDI", 60, "0", "trimestrales"),
    ("Factor de conversion a kg DBO5", 0.463078222672749, "0.000000", "kg por m3"),
    ("FINANCIAMIENTO", None, None, None),
    ("Tamano de deuda", 0.8, "0.00%", "% del costo de obra"),
    ("Spread sobre el soberano", 0.035, "0.00%", "sondeo de mercado"),
    # El modo de amortizacion NO lo elige el usuario: lo fija el esquema de pago,
    # y por eso esta fila es informativa. "Al final de obra" va con cuota
    # constante y sin cobertura, como Cajamarca; "por hitos" va dimensionada por
    # cobertura, como San Martin. Los motores no leen esta celda.
    ("Servicio de la deuda", "lo fija el esquema de pago", "@",
     "al final de obra = cuota constante | por hitos = por cobertura"),
    ("Inicio del pago de deuda", "2030-10-31", "@", ""),
    ("Fin del pago de deuda", "2042-09-30", "@", ""),
    ("Costo de estructuracion", 0.02, "0.00%", "sobre la linea aprobada"),
    ("Comision por no uso", 0.01, "0.00%", "anual, sobre la linea no utilizada"),
    # Solo muerden cuando el servicio de la deuda es "por cobertura". Viven aqui
    # y no en `Hitos` para que haya una sola fuente: el lector prefiere este
    # valor y solo cae a `Hitos` si esta hoja no lo trae, por las plantillas
    # viejas.
    ("Cobertura minima RCSD", 1.25, "0.00",
     "SOLO en la rama por hitos; la de final de obra la ignora"),
    ("Cuenta de reserva CRSD", 0.5, "0.00%",
     "SOLO en la rama por hitos; del servicio del ano siguiente"),
    ("REAJUSTE", None, None, None),
    ("IPM, reajuste de ingresos", 0.0267, "0.000000%", "anual"),
    ("Gatillo del reajuste", 0.03, "0.00%", "acumulado que dispara el ajuste"),
    ("IPC, reajuste de costos", 0.02, "0.000000%", "anual, sin gatillo"),
    ("Indice de costos al inicio de O&M", 1.098628385697407, "0.00000000",
     "IPC acumulado desde la fecha de los precios constantes"),
    ("Indice de CAPEX al cierre del contrato", 1.0166391026269779, "0.00000000",
     "IPC acumulado desde la fecha de los precios constantes"),
    ("TRIBUTOS Y MARGENES", None, None, None),
    ("IGV", 0.18, "0.00%", ""),
    # Es lo unico que separa el tratamiento del IGV de operacion de los dos
    # libros aprobados, y NO cuelga del esquema de pago. Es un dato de la zona
    # del proyecto, no una preferencia: Tarapoto esta bajo la ley de la
    # Amazonia, donde no se cobra IGV, asi que el PPD de San Martin no lo
    # repercute y el soportado no tiene contra que acreditarse. Su propio libro
    # lo llama por su nombre en `Opex!143`, "IGV no recuperable (a costos)",
    # 69,668,080.69, que es exactamente su `FC!28`. Cajamarca no esta exonerada:
    # cobra IGV sobre el PPDI y el PPDMO (`IGV!71:73`), acredita el de sus
    # costos (`IGV!74:77`) y su fila de caja (`IGV!83`) solo existe durante la
    # obra y suma cero.
    ("Zona con exoneracion de IGV (ley de la Amazonia)", 0, "0",
     "1 = el PPD no lleva IGV y el de O&M es costo no recuperable | 0 = se repercute y se acredita"),
    ("Impuesto a la Renta", 0.295, "0.00%", ""),
    ("Participacion de trabajadores", 0.05, "0.00%", ""),
    ("Margen del costo fijo", 0.15, "0.00%", "el PPDMO fijo es costo mas margen"),
    ("Supervision del regulador", 0.01, "0.00%", "% del PPD"),
]

LINEAS_OPEX = [
    ("FIJOS", None),
    ("Personal", "personal"),
    ("Mantenimiento de obra civil", "mant_obra_civil"),
    ("Mantenimiento de colectores", "mant_colectores"),
    ("Energia electrica", "energia_electrica"),
    ("Productos, materiales y servicios", "productos_materiales"),
    ("Gestion, monitoreo y ensayos", "gestion_monitoreo"),
    ("Reposiciones", "reposiciones"),
    ("VARIABLES", None),
    ("Energia de la PTAR", "energia_ptar"),
    ("Consumo de reactivos", "reactivos"),
    ("Retirada de residuos", "residuos"),
    ("OTROS", None),
    ("Gastos de la SPV", "gastos_spv"),
    ("DEMANDA", None),
    ("Demanda tratada, m3 al ano", "demanda_m3"),
]


# Con la forma de `Inputs!107:145` del libro de Cajamarca: una fila por etapa,
# con su mes de inicio y su mes de fin contados desde el cierre del contrato. El
# mes `k` es el cierre del mes k-esimo de la malla, y el mes 0 es la fecha de
# cierre. Las etapas se SOLAPAN (la certificacion de obra corre dentro de la
# puesta en marcha), asi que no alcanza con una lista de duraciones: cada una
# trae su propio desde y hasta, como en el libro.
CRONOGRAMA = [
    ("ESTUDIOS TECNICOS", None, None, None),
    ("Elaboracion y presentacion completa", 0, 12, "Inputs!110"),
    ("Conformidad", 12, 16, "Inputs!111"),
    ("CIERRE FINANCIERO", None, None, None),
    ("Fecha de cierre financiero", 16, 20, "Inputs!113"),
    ("OBRAS", None, None, None),
    ("Inicio de obra", 21, 21, "Inputs!115"),
    ("Fin de obra", 21, 39, "Inputs!116"),
    ("Puesta en marcha", 39, 45, "Inputs!118"),
    ("Certificacion de obra", 39, 43, "Inputs!119"),
    ("Certificado de puesta en marcha", 45, 48, "Inputs!121"),
    ("Ejecucion de obras y puesta en marcha", 21, 48, "Inputs!122"),
    ("PAGOS", None, None, None),
    ("Vigencia del periodo de PPDI", 48, 228, "Inputs!124"),
    ("PPDMO", 51, 316, "Inputs!127:128"),
    ("Pago de deuda", 49, 192, "Inputs!130"),
    ("Periodo de O&M", 48, 312, "Inputs!143"),
]

# Que fila del cronograma alimenta cada fecha suelta de `Proyecto`. `ini` toma el
# mes de inicio de la etapa, `fin` el de fin.
FECHAS_DERIVADAS = [
    ("Fecha de cierre financiero", "Fecha de cierre financiero", "fin"),
    ("Inicio de obras", "Inicio de obra", "ini"),
    ("Fin de obras y puesta en marcha", "Ejecucion de obras y puesta en marcha", "fin"),
    ("Inicio de operacion", "Periodo de O&M", "ini"),
    ("Fin de la concesion", "Periodo de O&M", "fin"),
    ("Inicio del pago de deuda", "Pago de deuda", "ini"),
    ("Fin del pago de deuda", "Pago de deuda", "fin"),
]


def _cab(ws, titulo, sub):
    ws["B2"], ws["B2"].font = titulo, TIT
    ws["B3"], ws["B3"].font = sub, SUB
    ws.column_dimensions["B"].width = 42


def escribir(ruta):
    wb = Workbook()
    _proyecto(wb.active)
    _cronograma(wb.create_sheet("Cronograma"))
    _capex(wb.create_sheet("CAPEX"))
    _opex(wb.create_sheet("OPEX"))
    _otros(wb.create_sheet("Otros"))
    _hitos(wb.create_sheet("Hitos"))
    _opex_hitos(wb.create_sheet("OPEX hitos"))
    wb.save(ruta)
    return ruta


def _proyecto(ws):
    ws.title = "Proyecto"
    _cab(ws, "Datos del proyecto",
         "Las celdas en ambar son las que hay que llenar. Vienen con Cajamarca de ejemplo.")
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 44
    r = 6
    for etiqueta, valor, fmt, nota in PROYECTO:
        if valor is None:
            c = ws.cell(r, 2, etiqueta)
            c.font, c.fill = CAB, BANDA
            for col in range(3, 6):
                ws.cell(r, col).fill = BANDA
            r += 1
            continue
        ws.cell(r, 2, etiqueta).font = ETI
        c = ws.cell(r, 4, valor)
        c.number_format, c.fill, c.font = fmt, LLENAR, ETB
        c.alignment = Alignment(horizontal="right")
        ws.cell(r, 5, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        r += 1


def offsets_de_fechas(proy, fechas):
    """El inverso de `leer_plantilla.fechas_de_cronograma`.

    Lo usa cualquier escritor que arme una plantilla nueva: si deja el
    `Cronograma` con las etapas de Cajamarca, esas fechas MANDAN y pisan las del
    proyecto. Es la trampa de siempre, los datos del caso aprobado donde van los
    del proyecto, asi que hay que reescribir la hoja junto con las fechas.

    Devuelve `{etapa: (desde, hasta)}` solo para las etapas que las fechas de
    `Proyecto` determinan; las demas quedan fuera y el escritor las vacia.
    """
    idx = {f: i + 1 for i, f in enumerate(fechas)}
    cierre = proy["Fecha de cierre del contrato"]

    def k(f):
        return 0 if f == cierre else idx.get(f)

    out = {}
    for destino, etapa, extremo in FECHAS_DERIVADAS:
        v = k(proy.get(destino))
        if v is None:
            continue
        desde, hasta = out.get(etapa, (None, None))
        out[etapa] = (v, hasta) if extremo == "ini" else (desde, v)
    # La ejecucion de obras abarca de la primera a la ultima: su inicio es el de
    # la obra, que `Proyecto` si trae.
    ejec = "Ejecucion de obras y puesta en marcha"
    if ejec in out and out[ejec][0] is None:
        ini = k(proy.get("Inicio de obras"))
        if ini is not None:
            out[ejec] = (ini, out[ejec][1])
    # Al resto, las fechas sueltas les dan un solo extremo, asi que quedan como
    # etapas de un punto, igual que `Inicio de Obra` en el libro (21 a 21).
    return {e: (v, v) if None in (d, h) else (d, h)
            for e, (d, h) in out.items()
            for v in [d if d is not None else h]}


def volcar_cronograma(wb, proy, fechas):
    """Reescribe la hoja `Cronograma` con las etapas de ESTE proyecto.

    Las etapas que las fechas no determinan se vacian, para que no quede el
    cronograma de Cajamarca colgado en una plantilla de otro proyecto.
    """
    if "Cronograma" not in wb.sheetnames:
        return
    crono = offsets_de_fechas(proy, fechas)
    ws = wb["Cronograma"]
    for r in range(6, ws.max_row + 1):
        etiqueta = ws.cell(r, 2).value
        if not etiqueta or ws.cell(r, 4).value is None:
            continue
        if etiqueta in crono:
            ws.cell(r, 4).value, ws.cell(r, 5).value = crono[etiqueta]
        else:
            ws.cell(r, 4).value = ws.cell(r, 5).value = None
    return crono


def fila_proyecto(etiqueta):
    """Fila de `Proyecto` en la que cae una etiqueta, para armar las formulas."""
    r = 6
    for et, valor, _fmt, _nota in PROYECTO:
        if et == etiqueta:
            return r
        r += 1
    raise KeyError(etiqueta)


def _cronograma(ws):
    _cab(ws, "Cronograma por hitos",
         "Con la forma de la hoja `Inputs` del libro de Cajamarca. Los meses se "
         "cuentan desde el cierre del contrato; las fechas se derivan solas.")
    ws.column_dimensions["C"].width = 4
    for col, ancho in (("D", 10), ("E", 10), ("F", 9), ("G", 13), ("H", 13),
                       ("I", 16)):
        ws.column_dimensions[col].width = ancho
    cierre = f"DATEVALUE(Proyecto!$D${fila_proyecto('Fecha de cierre del contrato')})"
    for col, tit in ((2, "Etapa"), (4, "Desde (mes)"), (5, "Hasta (mes)"),
                     (6, "Meses"), (7, "F. Inicio"), (8, "F. Fin"),
                     (9, "En el libro")):
        c = ws.cell(5, col, tit)
        c.font, c.fill = CAB, BANDA
    ws.cell(5, 3).fill = BANDA
    r = 6
    for etiqueta, desde, hasta, nota in CRONOGRAMA:
        if desde is None:
            c = ws.cell(r, 2, etiqueta)
            c.font, c.fill = CAB, BANDA
            for col in range(3, 10):
                ws.cell(r, col).fill = BANDA
            r += 1
            continue
        ws.cell(r, 2, etiqueta).font = ETI
        for col, v in ((4, desde), (5, hasta)):
            c = ws.cell(r, col, v)
            c.number_format, c.fill, c.font = "0", LLENAR, ETB
            c.alignment = Alignment(horizontal="right")
        ws.cell(r, 6, f"=E{r}-D{r}").number_format = "0"
        ws.cell(r, 6).font = ETI
        # El mes `k` es el cierre del mes k-esimo contado desde el cierre del
        # contrato, asi que EOMONTH lleva k-1. El mes 0 es el cierre mismo.
        for col, ref in ((7, f"D{r}"), (8, f"E{r}")):
            ws.cell(r, col,
                    f'=IF({ref}=0,Proyecto!$D${fila_proyecto("Fecha de cierre del contrato")},'
                    f'TEXT(EOMONTH({cierre},{ref}-1),"yyyy-mm-dd"))').font = ETI
        ws.cell(r, 9, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 10):
            ws.cell(r, col).border = FINA
        r += 1
    r += 1
    c = ws.cell(r, 2, "Las fechas sueltas de `Proyecto` salen de esta hoja: el "
                      "motor prefiere el cronograma y solo cae a `Proyecto` si "
                      "esta hoja no esta.")
    c.font = SUB


def _capex(ws):
    _cab(ws, "CAPEX",
         "Malla mensual de inversion a PRECIOS CONSTANTES, en S/ miles, sin IGV. "
         "El motor le aplica el indice de CAPEX.")
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 18
    ws.cell(5, 2, "Mes").font = CAB
    ws.cell(5, 4, "Inversion").font = CAB
    for col in (2, 3, 4):
        ws.cell(5, col).fill = BANDA
    for i, (f, v) in enumerate(zip(E["capex_fecha"], E["capex_mensual"])):
        ws.cell(6 + i, 2, f).font = ETI
        c = ws.cell(6 + i, 4, v)
        c.number_format, c.fill, c.font = "#,##0.00", LLENAR, ETI
    r = 6 + len(E["capex_fecha"]) + 1
    ws.cell(r, 2, "Total").font = ETB
    ws.cell(r, 4, f"=SUM(D6:D{r-2})").number_format = "#,##0.00"
    ws.cell(r, 4).font = ETB


def _opex(ws):
    _cab(ws, "OPEX y demanda",
         "Por ano de concesion, en soles del ano base. El reajuste lo pone el motor.")
    n = len(E["anio_concesion"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 15
    ws.cell(5, 2, "Ano de concesion").font = CAB
    ws.cell(6, 2, "Ano calendario").font = CAB
    for j in range(n):
        for fila, clave in ((5, "anio_concesion"), (6, "anio_calendario")):
            c = ws.cell(fila, 4 + j, E[clave][j])
            c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    for col in (2, 3):
        ws.cell(5, col).fill = ws.cell(6, col).fill = BANDA
    r = 8
    for etiqueta, clave in LINEAS_OPEX:
        if clave is None:
            c = ws.cell(r, 2, etiqueta)
            c.font, c.fill = CAB, BANDA
            for j in range(n):
                ws.cell(r, 4 + j).fill = BANDA
            ws.cell(r, 3).fill = BANDA
            r += 1
            continue
        ws.cell(r, 2, etiqueta).font = ETI
        for j in range(n):
            c = ws.cell(r, 4 + j, E[clave][j])
            c.number_format, c.fill, c.font = "#,##0.00", LLENAR, ETI
        r += 1


LINEAS_OPEX_HITOS = [
    ("COSTOS FIJOS DE O&M, POR HITO", None),
    ("Hito 1", "fijo_h1"),
    ("Hito 2", "fijo_h2"),
    ("Hito 3", "fijo_h3"),
    ("Hito 4", "fijo_h4"),
    ("LOS MISMOS COSTOS FIJOS, CON IGV", None),
    ("Hito 1 con IGV", "conigv_h1"),
    ("Hito 2 con IGV", "conigv_h2"),
    ("Hito 3 con IGV", "conigv_h3"),
    ("Hito 4 con IGV", "conigv_h4"),
    ("COSTOS VARIABLES DE O&M", None),
    ("Total sin IGV", "variable"),
    ("Sistema 1, con IGV", "conigv_var_tar"),
    ("Sistema 2, con IGV", "conigv_var_sjs"),
    ("OTRAS LINEAS DE OPERACION", None),
    ("Gastos generales y utilidad", "gg_u"),
    ("Otros costos de la concesion", "otros_op"),
    ("IGV de operacion", "igv_op"),
    ("Reposiciones", "repex"),
    ("Pago por obras", "pago_obras"),
    ("Costos de cierre", "cierre_laguna"),
    ("CARGA ORGANICA REMOVIDA, kg DBO AL ANO", None),
    ("Sistema 1", "carga_1"),
    ("Sistema 2", "carga_2"),
]


def _opex_hitos(ws):
    _cab(ws, "OPEX del esquema por hitos",
         "Por ano calendario y a precios constantes. REGLA: la suma de las cuatro "
         "patas por hito de un ano tiene que ser el OPEX de ese ano en la hoja "
         "`OPEX`; `opex_consistente.derivar` la escribe sola desde alli. Las "
         "lineas con IGV van aparte porque no todas las partidas lo llevan. "
         "Precargada con San Martin, que no es el proyecto de la hoja `OPEX`, "
         "asi que tal cual viene NO cumple la regla: es solo el ejemplo de la forma.")
    datos = json.load(open("/mnt/project-files/generador/sanmartin_opex_cte.json"))
    car = json.load(open("/mnt/project-files/generador/sanmartin_ingresos.json"))["carga"]
    lin = dict(datos["lineas"])
    lin["carga_1"], lin["carga_2"] = car["tar"], car["sjs"]
    anios = datos["anio"]
    n = len(anios)
    ws.cell(5, 2, "Ano calendario").font = CAB
    ws.cell(5, 2).fill = ws.cell(5, 3).fill = BANDA
    for j, a in enumerate(anios):
        c = ws.cell(5, 4 + j, a)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
        ws.column_dimensions[L(4 + j)].width = 15
    r = 7
    for etiqueta, clave in LINEAS_OPEX_HITOS:
        if clave is None:
            c = ws.cell(r, 2, etiqueta)
            c.font, c.fill = CAB, BANDA
            for j in range(n):
                ws.cell(r, 4 + j).fill = BANDA
            ws.cell(r, 3).fill = BANDA
            r += 1
            continue
        ws.cell(r, 2, etiqueta).font = ETI
        v = lin.get(clave, [0.0] * n)
        for j in range(n):
            c = ws.cell(r, 4 + j, abs(v[j]) if j < len(v) else 0.0)
            c.number_format, c.fill, c.font = "#,##0.00", LLENAR, ETI
        r += 1


# La hoja `Hitos` solo se usa cuando el esquema de pago es "por hitos". Viene
# precargada con San Martin, que es el modelo aprobado de ese esquema.
HITOS_SM = {
    "pct_capex": [0.7596493958055023, 0.06251337369777438,
                  0.02282498436332182, 0.1550122461334009],
}
HITOS_PARAMS = [
    ("CRONOGRAMA DEL CONTRATO", None, None, None),
    ("Primer ano de la malla", 2025, "0", "la malla arranca en enero de ese ano"),
    ("Meses de la malla", 336, "0", ""),
    ("Inicio del periodo D + C + PM", "2025-11", "@", "AAAA-MM"),
    ("Fin del periodo D + C + PM", "2029-12", "@", "AAAA-MM"),
    ("Primer pago del PPDI", "2030-03", "@", "AAAA-MM, luego trimestral"),
    ("Fin de la operacion", "2049-10", "@", "AAAA-MM, ultimo mes de O&M"),
    ("Mes del cierre financiero", 20, "0", "contado desde el inicio de D+C+PM"),
    ("FINANCIAMIENTO", None, None, None),
    ("Apalancamiento", 0.8, "0.00%", "deuda sobre necesidades totales"),
    ("Comision de estructuracion", 0.02, "0.00%", "sobre el total desembolsado"),
    ("Comision por no uso", 0.01, "0.00%", "anual, sobre el saldo no desembolsado"),
    ("APORTES DE CAPITAL", None, None, None),
    ("Aporte 1, porcentaje", 0.25, "0.00%", ""),
    ("Aporte 1, mes del contrato", 1, "0", ""),
    ("Aporte 2, porcentaje", 0.25, "0.00%", ""),
    ("Aporte 2, mes del contrato", 10, "0", ""),
    ("Aporte 3, porcentaje", 0.50, "0.00%", ""),
    ("Aporte 3, mes del contrato", 16, "0", ""),
    ("IMPORTES DE UNA VEZ", None, None, None),
    ("Capital de trabajo inicial", 10133000.0, "#,##0.00",
     "se carga al cierre de la construccion"),
    ("Periodo medio de pago a proveedores", 1.0, "0.00", "meses"),
    # Oscar, 2026-09-15: "el OPEX por ano de concesion debe ser igual a la suma
    # del OPEX por hito de ese ano". Con este reparto la hoja `OPEX hitos` se
    # deriva de `OPEX` y la igualdad se cumple por construccion, en vez de
    # depender de que el usuario escriba lo mismo dos veces.
    # Precargado con el reparto medido en el libro de San Martin (ano 2031). No
    # es el reparto del CAPEX: el hito 4 pesa 26.7 % del O&M y solo 15.5 % de la
    # inversion. En el libro se mueve menos de un punto en toda la concesion.
    ("REPARTO DEL O&M POR HITO", None, None, None),
    ("Hito 1, reparto del O&M", 0.674423, "0.0000%", ""),
    ("Hito 2, reparto del O&M", 0.044200, "0.0000%", ""),
    ("Hito 3, reparto del O&M", 0.014198, "0.0000%", ""),
    ("Hito 4, reparto del O&M", 0.267179, "0.0000%", ""),
    ("CARGA ORGANICA DE REFERENCIA", None, None, None),
    ("Sistema 1, kg DBO al ano", 4700560.56, "#,##0.00",
     "la de diseno, no la del primer ano"),
    ("Sistema 2, kg DBO al ano", 278722.2349700822, "#,##0.00", ""),
]


def _hitos(ws):
    _cab(ws, "Hitos funcionales",
         "Solo para el esquema de pago por hitos. Precargada con San Martin.")
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 46
    r = 6
    for etiqueta, valor, fmt, nota in HITOS_PARAMS:
        if valor is None:
            c = ws.cell(r, 2, etiqueta)
            c.font, c.fill = CAB, BANDA
            for col in range(3, 6):
                ws.cell(r, col).fill = BANDA
            r += 1
            continue
        ws.cell(r, 2, etiqueta).font = ETI
        c = ws.cell(r, 4, valor)
        c.number_format, c.fill, c.font = fmt, LLENAR, ETB
        ws.cell(r, 5, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        r += 1
    r += 1
    c = ws.cell(r, 2, "REPARTO DEL CAPEX POR HITO")
    c.font, c.fill = CAB, BANDA
    for col in range(3, 6):
        ws.cell(r, col).fill = BANDA
    r += 1
    for i, pct in enumerate(HITOS_SM["pct_capex"]):
        ws.cell(r, 2, f"Hito {i + 1}").font = ETI
        c = ws.cell(r, 4, pct)
        c.number_format, c.fill, c.font = "0.0000%", LLENAR, ETB
        r += 1


# El libro trata estas lineas en dos sitios distintos y el generador tambien:
# durante la construccion alimentan el activo financiero del PPDI, y durante la
# operacion son costos del flujo de caja financiero. Por eso van en dos bloques.
OTROS = [("Seguros", "seguros"), ("Fianzas", "fianzas"),
         ("Fideicomiso", "fideicomiso"), ("Gastos de promocion", "promocion"),
         ("Garantias", "garantias"), ("Reembolsos", "reembolso")]
OTROS_OP = [("Seguros", "seguros"), ("Fianzas", "fianzas"),
            ("Fideicomiso", "fideicomiso"), ("Gastos de promocion", "promocion")]


def _mensualizar_trim(serie_q, trim_m, nm):
    """Reparte un importe trimestral del libro entre los tres meses del
    trimestre. El modelo sombra agrega por trimestre, asi que el reparto no
    cambia ningun resultado; solo le da al usuario una malla mensual que llenar."""
    cuenta = {}
    for m in range(nm):
        cuenta[trim_m[m]] = cuenta.get(trim_m[m], 0) + 1
    out = [0.0] * nm
    for m in range(nm):
        q = trim_m[m] - 1
        if 0 <= q < len(serie_q):
            out[m] = serie_q[q] / cuenta[trim_m[m]]
    return out


def _otros(ws):
    _cab(ws, "Otros costos",
         "Malla mensual en S/ miles. Si el proyecto nuevo no los tiene, van en cero.")
    ws.cell(5, 2, "Mes").font = CAB
    ws.cell(5, 2).fill = BANDA
    ws.cell(4, 4, "PERIODO DE CONSTRUCCION").font = ETB
    ws.cell(4, 4 + len(OTROS), "PERIODO DE OPERACION").font = ETB
    cols = [(j, e) for j, (e, _) in enumerate(OTROS)]
    cols += [(len(OTROS) + j, e) for j, (e, _) in enumerate(OTROS_OP)]
    for j, etiqueta in cols:
        c = ws.cell(5, 4 + j, etiqueta)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
        ws.column_dimensions[L(4 + j)].width = 16
    prim = json.load(open("/mnt/project-files/generador/cajamarca_primitivos.json"))["series"]
    sombra = json.load(open("/mnt/project-files/generador/caj_sombra_full.json"))
    nm = len(E["capex_fecha"])
    op = {c: _mensualizar_trim(sombra[c], sombra["Pm_trim"], nm)
          for _e, c in OTROS_OP}
    for i, f in enumerate(E["capex_fecha"]):
        ws.cell(6 + i, 2, f).font = ETI
        for j, (_, clave) in enumerate(OTROS):
            v = prim.get(clave, [])
            c = ws.cell(6 + i, 4 + j, v[i] if i < len(v) else 0.0)
            c.number_format, c.fill, c.font = "#,##0.00", LLENAR, ETI
        for j, (_, clave) in enumerate(OTROS_OP):
            c = ws.cell(6 + i, 4 + len(OTROS) + j, op[clave][i])
            c.number_format, c.fill, c.font = "#,##0.00", LLENAR, ETI


if __name__ == "__main__":
    print("escrita:",
          escribir("/mnt/project-files/generador/Plantilla_Proyecto_Nuevo.xlsx"))
