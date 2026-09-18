"""Escribe el libro de salida del generador, con formulas vivas.

El entregable tiene que ser un Excel que PROINVERSION, el MEF y el regulador
puedan abrir y auditar, no una tabla de numeros pegados. Asi que cada hoja
reconstruye su bloque con formulas que apuntan a `Inputs`, igual que los libros
aprobados: si alguien cambia el Kd o el IPM, el libro se recalcula solo.

Lo unico que no se recalcula solo es el cierre, exactamente como en los libros
aprobados: la tarifa variable y el PPDI van como celdas de entrada y la hoja
`Flujo` trae la celda de VAN que Buscar Objetivo mueve a cero. El motor en
Python ya las deja resueltas, asi que el libro abre cuadrado.
"""
import json
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

TITULO = Font(bold=True, size=13, color="1A4B4B")
CABEZA = Font(bold=True, size=9, color="FFFFFF")
ETIQ = Font(size=9)
ETIQ_B = Font(bold=True, size=9)
ENTRADA = PatternFill("solid", fgColor="FFF3D6")
CALC = PatternFill("solid", fgColor="F2F7F7")
BANDA = PatternFill("solid", fgColor="1A4B4B")
FINA = Border(bottom=Side("thin", color="D5DEDE"))
N2, N4, N6 = "#,##0.00", "#,##0.0000", "0.000000%"


def _cabecera(ws, titulo, sub=None):
    ws["B2"], ws["B2"].font = titulo, TITULO
    if sub:
        ws["B3"], ws["B3"].font = sub, Font(size=9, italic=True, color="6B7B7B")
    ws.column_dimensions["B"].width = 44
    ws.column_dimensions["C"].width = 16
    ws.freeze_panes = "D6"


def _fila(ws, r, etiqueta, formulas, fmt=N2, negrita=False, col0=4):
    c = ws.cell(r, 2, etiqueta)
    c.font = ETIQ_B if negrita else ETIQ
    for i, f in enumerate(formulas):
        cel = ws.cell(r, col0 + i, _valor(f))
        cel.number_format, cel.font = fmt, ETIQ
    return r + 1


def _valor(f):
    """Una cadena que no empieza con `=` la guarda Excel como TEXTO, y basta una
    para que toda la fila que la resta propague `#VALUE!`. Las constantes de las
    filas (el cero del primer mes) se escriben como numero."""
    if isinstance(f, str) and not f.startswith("="):
        try:
            return float(f)
        except ValueError:
            pass
    return f


def escribir(datos, ruta):
    """`datos` es el dict que arma `preparar_cajamarca`."""
    wb = Workbook()
    _inputs(wb.active, datos)
    _deuda(wb.create_sheet("Deuda"), datos)
    _activo(wb.create_sheet("Activo financiero"), datos)
    _ppdmo(wb.create_sheet("PPDMO"), datos)
    _flujo(wb.create_sheet("Flujo"), datos)
    _resumen(wb.create_sheet("Resumen", 0), datos)
    wb.save(ruta)
    return ruta


# --------------------------------------------------------------- Inputs
PARAMS = [
    ("Costo de obra a financiar", "costo_obra", N2, "S/ miles"),
    ("Tamano de deuda", "tamano_deuda", "0.00%", "% del costo de obra"),
    ("Kd, costo de la deuda", "kd", N6, "soberano a vida media + spread"),
    ("Spread de deuda", "spread", N6, "sondeo de mercado"),
    ("Ke, costo del patrimonio", "ke", N6, "CAPM en USD + riesgo pais + devaluacion"),
    ("WACC", "wacc", N6, "despues de impuestos"),
    ("Numero de pagos de la deuda", "pagos", "0", "meses"),
    ("IPM, reajuste de ingresos", "ipm", N6, "anual"),
    ("Gatillo del reajuste", "gatillo", "0.00%", "acumulado que dispara el ajuste"),
    ("IPC, reajuste de costos", "ipc", N6, "anual, sin gatillo"),
    ("Tasa de Impuesto a la Renta", "ir", "0.00%", ""),
    ("Participacion de trabajadores", "part", "0.00%", ""),
    ("Supervision SUNASS", "superv", "0.00%", "% del PPD"),
    ("Margen del costo fijo", "margen_cf", "0.00%", "pass-through de costos"),
    ("PPDMO fijo base mensual", "fijo_base", N2, "S/ miles, calculado de costos"),
    ("Tarifa variable", "tarifa", "#,##0.0000000", "S/ por kg DBO5 - LA CIERRA Buscar Objetivo"),
    ("PPDI anual", "ppdi_anual", N2, "S/ miles - LA CIERRA Buscar Objetivo"),
]


def _inputs(ws, d, params=None):
    params = PARAMS if params is None else params
    ws.title = "Inputs"
    _cabecera(ws, "Parametros del modelo",
              "Las celdas en ambar son de entrada. Las dos ultimas las resuelve el cierre.")
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 46
    r = 6
    for etiqueta, clave, fmt, nota in params:
        ws.cell(r, 2, etiqueta).font = ETIQ
        c = ws.cell(r, 4, d["inputs"][clave])
        c.number_format, c.fill, c.font = fmt, ENTRADA, ETIQ_B
        ws.cell(r, 5, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        ws.defined_names  # los nombres se crean abajo
        r += 1
    _nombres(ws, d, params)


def _nombres(ws, d, params=None):
    from openpyxl.workbook.defined_name import DefinedName
    params = PARAMS if params is None else params
    wb = ws.parent
    for i, (_, clave, _, _) in enumerate(params):
        ref = f"Inputs!$D${6 + i}"
        wb.defined_names.add(DefinedName(f"p_{clave}", attr_text=ref))


# --------------------------------------------------------------- Deuda
def _deuda(ws, d):
    _cabecera(ws, "Deuda financiera",
              "Cuota constante: el servicio sale de PMT y la amortizacion es el residuo.")
    m = d["meses"]
    n = len(m["fecha"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    ws.cell(r, 2, "Mes").font = CABEZA
    for j, f in enumerate(m["fecha"]):
        c = ws.cell(r, 4 + j, f)
        c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
    r += 1
    r = _fila(ws, r, "Flag obra y puesta en marcha", m["flag_obra"], "0")
    r = _fila(ws, r, "Flag de pago de deuda", m["flag_deuda"], "0")
    r = _fila(ws, r, "Inversion a financiarse", m["inversion"], N2)
    fo, fd, inv = r - 3, r - 2, r - 1
    des = r
    r = _fila(ws, r, "Desembolsos",
              [f"={L(4+j)}{fo}*{L(4+j)}{inv}*p_tamano_deuda" for j in range(n)])
    tasa = '((1+p_kd)^(1/12)-1)'
    ws.cell(r, 2, "Tasa mensual").font = ETIQ
    ws.cell(r, 4, f"=(1+p_kd)^(1/12)-1").number_format = N6
    tm, r = r, r + 1
    # La cuota necesita el saldo del mes base, y el saldo de abajo necesita la
    # cuota: referenciarlos entre si deja el libro en referencia circular y Excel
    # y Calc devuelven error en toda la hoja. Por eso el saldo de obra se
    # acumula aparte, con lo unico de lo que depende hasta el mes base: el
    # desembolso y el interes que se capitaliza. Es identico al de abajo, porque
    # mientras no hay servicio la amortizacion es el interes con signo cambiado.
    base = d["mes_base"]
    obra_sal = r
    r = _fila(ws, r, "Saldo de obra capitalizado (base de la cuota)",
              [(f"={'0' if j == 0 else L(3+j)+str(obra_sal)}*(1+$D${tm})"
                f"+{L(4+j)}{des}") if j <= base else 0.0 for j in range(n)])
    ws.cell(r, 2, "Cuota constante").font = ETIQ_B
    ws.cell(r, 4, f"=-PMT($D${tm},p_pagos,{L(4+base)}{obra_sal})").number_format = N2
    cuota, r = r, r + 1
    ints, amort, srv, sal = r, r + 1, r + 2, r + 3
    r = _fila(ws, r, "Interes",
              [f"={'0' if j == 0 else L(3+j)}{sal}*$D${tm}" if j else "0" for j in range(n)])
    r = _fila(ws, r, "Amortizacion",
              [f"={L(4+j)}{srv}-{L(4+j)}{ints}" for j in range(n)])
    r = _fila(ws, r, "Servicio de deuda",
              [f"={L(4+j)}{fd}*$D${cuota}" for j in range(n)])
    r = _fila(ws, r, "Saldo deudor",
              [f"={'0' if j == 0 else L(3+j)+str(sal)}+{L(4+j)}{des}-{L(4+j)}{amort}"
               for j in range(n)], negrita=True)
    d["_ref_deuda"] = dict(interes=ints, servicio=srv, desembolso=des, saldo=sal)


# ----------------------------------------------------- Activo financiero
def _activo(ws, d):
    """La obra como activo financiero, con su amortizacion explicita.

    CINIIF 12 parrafo 16: en una APP cofinanciada el concedente se obliga a
    pagar importes determinables y el derecho de cobro es incondicional, asi
    que lo que reconoce el concesionario no es un intangible sino una cuenta
    por cobrar. Devenga al tipo implicito, que es la TIR de sus propios flujos.

    **La amortizacion es el cobro del mes menos el ingreso financiero
    devengado, sin truncar en cero.** En los meses sin cobro sale negativa
    porque el activo crece, y truncarla infla el total amortizado.
    """
    _cabecera(ws, "Activo financiero del PPDI",
              "CINIIF 12 p.16: derecho incondicional de cobro, no intangible. "
              "Amortizacion = cobro del mes menos ingreso financiero devengado.")
    a = d["activo"]
    n = len(a["fecha"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    ws.cell(r, 2, "Mes").font = CABEZA
    for j, f in enumerate(a["fecha"]):
        c = ws.cell(r, 4 + j, f)
        c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
    r += 1
    ws.cell(r, 2, "Tasa implicita mensual").font = ETIQ_B
    ws.cell(r, 3, "TIR del activo").font = Font(size=8, italic=True, color="6B7B7B")
    c = ws.cell(r, 4, a["tasa"])
    c.number_format, c.fill, c.font = N6, ENTRADA, ETIQ_B
    tasa = r
    r += 1

    fdev, fpag = r, r + 1
    dev, cob, acu = r + 2, r + 3, r + 4
    ini, sc, ifi, amo, fin = r + 5, r + 6, r + 7, r + 8, r + 9
    ant = lambda j, fila: "0" if j == 0 else f"{L(3 + j)}{fila}"

    r = _fila(ws, r, "Flag de devengo del PPDI", a["flag"], "0")
    r = _fila(ws, r, "Flag de cobro (cierre de trimestre)", a["paga"], "0")
    r = _fila(ws, r, "PPDI devengado",
              [f"={L(4+j)}{fdev}*p_ppdi_anual/12" for j in range(n)])
    r = _fila(ws, r, "PPDI cobrado",
              [f"=IF({L(4+j)}{fpag}=1,{ant(j, acu)}+{L(4+j)}{dev},0)"
               for j in range(n)])
    r = _fila(ws, r, "Devengado pendiente de cobro",
              [f"={ant(j, acu)}+{L(4+j)}{dev}-{L(4+j)}{cob}" for j in range(n)])
    r = _fila(ws, r, "Saldo inicial del activo",
              [0 if j == 0 else f"={L(3+j)}{fin}" for j in range(n)])
    r = _fila(ws, r, "Servicio de construccion del periodo", a["sc"], N2)
    r = _fila(ws, r, "Ingreso financiero devengado",
              [f"={L(4+j)}{ini}*$D${tasa}" for j in range(n)])
    r = _fila(ws, r, "Amortizacion del activo (cobro - ingreso financiero)",
              [f"={L(4+j)}{cob}-{L(4+j)}{ifi}" for j in range(n)], N2,
              negrita=True)
    r = _fila(ws, r, "Saldo final del activo",
              [f"={L(4+j)}{ini}+{L(4+j)}{sc}+{L(4+j)}{ifi}-{L(4+j)}{cob}"
               for j in range(n)], N2, negrita=True)
    r += 1
    for etiq, f in (
        ("Saldo maximo del activo", f"=MAX($D${fin}:${L(3+n)}${fin})"),
        ("Amortizacion acumulada", f"=SUM($D${amo}:${L(3+n)}${amo})"),
        ("Saldo final, debe ser cero", f"=${L(3+n)}${fin}"),
        ("Meses con amortizacion negativa (el activo crece)",
         f'=COUNTIF($D${amo}:${L(3+n)}${amo},"<0")'),
    ):
        ws.cell(r, 2, etiq).font = ETIQ_B
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = N2, CALC, ETIQ_B
        r += 1
    d["_ref_activo"] = dict(n=n, saldo=fin, amort=amo, ingreso=ifi, cobro=cob,
                            tasa=tasa)


# --------------------------------------------------------------- PPDMO
def _ppdmo(ws, d):
    _cabecera(ws, "PPD de operacion y mantenimiento",
              "Ingresos reajustados por IPM con gatillo; la pata fija es costo mas margen.")
    m = d["meses"]
    n = len(m["fecha"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    ws.cell(r, 2, "Mes").font = CABEZA
    for j, f in enumerate(m["fecha"]):
        c = ws.cell(r, 4 + j, f)
        c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
    r += 1
    r = _fila(ws, r, "Flag de operacion", m["flag_om"], "0")
    r = _fila(ws, r, "Flag trimestral", m["flag_trim"], "0")
    r = _fila(ws, r, "Flag de pago del PPDMO", m["flag_pago"], "0")
    r = _fila(ws, r, "Produccion efectiva, kg DBO5", m["kg"], N2)
    fom, ftr, fpa, kg = r - 4, r - 3, r - 2, r - 1
    r = _fila(ws, r, "IPM mensual",
              [f"=((1+p_ipm)^(1/12)-1)*{L(4+j)}{fom}" for j in range(n)], N6)
    ipm = r - 1
    r = _fila(ws, r, "Acumulado desde el ultimo disparo",
              [f"=IF({L(4+j)}{ipm}=0,0,SUM($D{ipm}:{L(4+j)}{ipm})-SUM($D{r}:{L(3+j)}{r}))"
               if j else f"=IF({L(4)}{ipm}=0,0,{L(4)}{ipm})" for j in range(n)], N6)
    pend = r - 1
    r = _fila(ws, r, "Ajuste liberado",
              [f"=IF({L(4+j)}{pend}>=p_gatillo,{L(4+j)}{pend},0)" for j in range(n)], N6)
    aj = r - 1
    ws.cell(pend, 2).value = "Acumulado pendiente"
    for j in range(n):
        ws.cell(pend, 4 + j).value = (
            f"=IF({L(4+j)}{ipm}=0,0,SUM($D{ipm}:{L(4+j)}{ipm})-SUM($D{aj}:{L(3+j)}{aj}))"
            if j else f"=IF($D{ipm}=0,0,$D{ipm})")
    r = _fila(ws, r, "Factor de reajuste",
              [f"=TRUNC(IF({L(4+j)}{fom}=0,1,{'1' if j == 0 else L(3+j)+str(r)}*"
               f"(1+{L(4+j)}{aj})*{L(4+j)}{fom}),5)" for j in range(n)], "0.00000")
    fac = r - 1
    r = _fila(ws, r, "PPDMO fijo mensual",
              [f"=p_fijo_base*{L(4+j)}{fac}*{L(4+j)}{fom}" for j in range(n)])
    fijo = r - 1
    r = _fila(ws, r, "PPDMO variable mensual",
              [f"=IF({L(4+j)}{fom}=0,0,p_tarifa*{L(4+j)}{kg}*{L(4+j)}{fac})/1000"
               for j in range(n)])
    var = r - 1
    r = _fila(ws, r, "Fijo trimestral",
              [f"=SUM({L(max(4,4+j-2))}{fijo}:{L(4+j)}{fijo})*{L(4+j)}{ftr}" for j in range(n)])
    fijo_t = r - 1
    r = _fila(ws, r, "Variable trimestral",
              [f"=SUM({L(max(4,4+j-2))}{var}:{L(4+j)}{var})*{L(4+j)}{ftr}" for j in range(n)])
    var_t = r - 1
    r = _fila(ws, r, "Fijo a cobrar",
              [f"={L(4+j)}{fpa}*{L(1+j)}{fijo_t}" if j >= 3 else "0" for j in range(n)],
              negrita=True)
    r = _fila(ws, r, "Variable a cobrar",
              [f"={L(4+j)}{fpa}*{L(1+j)}{var_t}" if j >= 3 else "0" for j in range(n)],
              negrita=True)
    # Marca del primer mes de operacion. El libro saca las cifras de portada con
    # MINIFS, que no sobrevive el viaje entre Excel y otros lectores de xlsx;
    # una marca y un SUMPRODUCT dicen lo mismo y abren en cualquier parte.
    r = _fila(ws, r, "Primer mes de operacion",
              [f"=IF(AND({L(4+j)}{fom}=1,{'0' if j == 0 else 'SUM($D'+str(fom)+':'+L(3+j)+str(fom)+')'}=0),1,0)"
               for j in range(n)], "0")
    d["_ref_ppdmo"] = dict(fijo=fijo, var=var, factor=fac, marca=r - 1)


# --------------------------------------------------------------- Flujo
# Estas lineas entran como valores, no como formulas: hoy salen del motor y de
# las primitivas del libro. Cuando el generador tome el CAPEX y el OPEX del
# usuario pasan a calcularse aqui, en hojas propias.
LINEAS_LIBRO = [("Costo fijo (del motor)", "costo_fijo"),
                ("Costo variable (del motor)", "costo_var"),
                ("Gastos SPV (del motor)", "gastos_spv"),
                ("Seguros (del motor)", "seguros"),
                ("Fianzas (del motor)", "fianzas"),
                ("Gastos de promocion (del motor)", "promocion"),
                ("Fideicomiso (del motor)", "fideicomiso"),
                ("Efecto ITAN (del motor)", "itan"),
                ("CAPEX (del motor)", "capex"),
                ("Flujo de caja de IGV (del motor)", "igv")]


def _flujo(ws, d):
    _cabecera(ws, "Flujo de caja financiero",
              "El VAN de la ultima fila es la celda que Buscar Objetivo lleva a cero.")
    q = d["trimestres"]
    n = len(q["anio"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    for etiq, clave in (("Ano", "anio"), ("Trimestre", "trim"), ("Meses vivos", "meses")):
        ws.cell(r, 2, etiq).font = CABEZA
        for j, v in enumerate(q[clave]):
            c = ws.cell(r, 4 + j, v)
            c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
        r += 1
    mes = r - 1
    r = _fila(ws, r, "PPD Inversiones", q["ppdi_perfil"], N2)
    ppdi = r - 1
    for j in range(n):
        ws.cell(ppdi, 4 + j).value = f"=p_ppdi_anual*{q['ppdi_perfil'][j]}"
    r = _fila(ws, r, "PPD MO fijo", q["fijo"], N2)
    r = _fila(ws, r, "PPD MO variable", q["var"], N2)
    fijo, var = r - 2, r - 1
    r = _fila(ws, r, "Flag de supervision", q["flag_superv"], "0")
    fsup = r - 1
    r = _fila(ws, r, "Supervision SUNASS",
              [f"=-p_superv*SUM({L(4+j)}{ppdi}:{L(4+j)}{var})*{L(4+j)}{fsup}"
               for j in range(n)])
    sup = r - 1
    prim = {}
    for etiq, clave in LINEAS_LIBRO:
        r = _fila(ws, r, etiq, q[clave], N2)
        prim[clave] = r - 1
    r = _fila(ws, r, "Intereses de la deuda", q["interes"], N2)
    inte = r - 1
    r = _fila(ws, r, "Utilidad antes de impuestos",
              [f"=SUM({L(4+j)}{ppdi}:{L(4+j)}{var})+{L(4+j)}{sup}"
               f"+SUM({L(4+j)}{prim['costo_fijo']}:{L(4+j)}{prim['fideicomiso']})-{L(4+j)}{inte}"
               for j in range(n)], N2, negrita=True)
    uai = r - 1
    r = _fila(ws, r, "Participacion e Impuesto a la Renta (del motor)", q["impuestos"], N2)
    imp = r - 1
    r = _fila(ws, r, "Desembolsos de deuda", q["desembolso"], N2)
    r = _fila(ws, r, "Servicio de deuda", [-x for x in q["servicio"]], N2)
    r = _fila(ws, r, "Deuda complementaria, desembolsos (del motor)", q["des2"], N2)
    r = _fila(ws, r, "Deuda complementaria, servicio (del motor)",
              [-x for x in q["srv2"]], N2)
    des, srv, des2, srv2 = r - 4, r - 3, r - 2, r - 1
    r = _fila(ws, r, "Flujo de caja financiero",
              [f"=SUM({L(4+j)}{ppdi}:{L(4+j)}{var})+{L(4+j)}{sup}"
               f"+SUM({L(4+j)}{prim['costo_fijo']}:{L(4+j)}{prim['igv']})+{L(4+j)}{imp}"
               f"+SUM({L(4+j)}{des}:{L(4+j)}{srv2})" for j in range(n)], N2, negrita=True)
    fcf = r - 1
    r = _fila(ws, r, "Factor de actualizacion",
              [f"=IF({L(4+j)}{mes}=0,0,1/(1+(1+p_ke)^(1/12)-1)^SUM($D{mes}:{L(4+j)}{mes}))"
               for j in range(n)], "0.00000000")
    fd = r - 1
    r += 1
    ws.cell(r, 2, "VAN financiero").font = ETIQ_B
    c = ws.cell(r, 4, f"=SUMPRODUCT({L(4)}{fcf}:{L(3+n)}{fcf},{L(4)}{fd}:{L(3+n)}{fd})")
    c.number_format, c.fill = N2, ENTRADA
    d["_ref_flujo"] = dict(van=r, fcf=fcf, ppdi=ppdi, fijo=fijo, var=var)


# --------------------------------------------------------------- Resumen
def _resumen(ws, d):
    _cabecera(ws, "Resumen del modelo",
              "S/ miles sin IGV, primer mes de operacion anualizado.")
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 40
    p = d["_ref_ppdmo"]
    n = len(d["meses"]["fecha"])
    filas = [
        ("PPD Inversiones, anual", "=p_ppdi_anual", N2),
        ("PPD MO fijo, anual",
         f"=SUMPRODUCT(PPDMO!$D${p['marca']}:${L(3+n)}${p['marca']},"
         f"PPDMO!$D${p['fijo']}:${L(3+n)}${p['fijo']})*12", N2),
        ("PPD MO variable, anual",
         f"=SUMPRODUCT(PPDMO!$D${p['marca']}:${L(3+n)}${p['marca']},"
         f"PPDMO!$D${p['var']}:${L(3+n)}${p['var']})*12", N2),
        ("PPD MO total, anual", "=D7+D8", N2),
        ("PPD total, anual", "=D6+D9", N2),
        ("Tarifa unitaria, S/ por kg DBO5", "=p_tarifa", "#,##0.0000000"),
        ("VAN financiero, debe ser cero", f"=Flujo!$D${d['_ref_flujo']['van']}", N2),
        ("WACC", "=p_wacc", N6),
        ("Kd", "=p_kd", N6),
        ("Ke", "=p_ke", N6),
    ]
    act = d["_ref_activo"]
    ua = L(3 + act["n"])
    filas += [
        ("Activo financiero, saldo maximo",
         f"=MAX('Activo financiero'!$D${act['saldo']}:${ua}${act['saldo']})", N2),
        ("Activo financiero, amortizacion acumulada",
         f"=SUM('Activo financiero'!$D${act['amort']}:${ua}${act['amort']})", N2),
        ("Activo financiero, saldo final",
         f"='Activo financiero'!${ua}${act['saldo']}", N2),
        ("Tasa implicita del activo, anual",
         f"=(1+'Activo financiero'!$D${act['tasa']})^12-1", N6),
    ]
    r = 6
    for etiq, f, fmt in filas:
        ws.cell(r, 2, etiq).font = ETIQ_B if r < 11 else ETIQ
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = fmt, CALC, ETIQ_B
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        r += 1


# ================================================================ AUTOFINANCIADA
# CINIIF 12 p.17: el concesionario recibe el derecho a cobrar a los usuarios, no
# un importe determinable del concedente, asi que la obra es activo INTANGIBLE.
# No hay PPDI, no hay PPDMO y no hay activo financiero; la incognita del cierre
# es la tarifa al usuario. El p.22 solo aqui capitaliza los costos por prestamos.
LINEAS_AUTO = LINEAS_LIBRO[:7]      # los siete costos; ITAN, CAPEX e IGV van aparte

PARAMS_AUTO = [
    ("Costo de obra a financiar", "costo_obra", N2, "S/ miles"),
    ("Tamano de deuda", "tamano_deuda", "0.00%", "% del costo de obra"),
    ("Kd, costo de la deuda", "kd", N6, "soberano a vida media + spread"),
    ("Spread de deuda", "spread", N6, "sondeo de mercado"),
    ("Ke, costo del patrimonio", "ke", N6, "CAPM en USD + riesgo pais + devaluacion"),
    ("WACC", "wacc", N6, "despues de impuestos"),
    ("Numero de pagos de la deuda", "pagos", "0", "meses"),
    ("IPM, reajuste de ingresos", "ipm", N6, "anual"),
    ("Gatillo del reajuste", "gatillo", "0.00%", "acumulado que dispara el ajuste"),
    ("IPC, reajuste de costos", "ipc", N6, "anual, sin gatillo"),
    ("Tasa de Impuesto a la Renta", "ir", "0.00%", ""),
    ("Participacion de trabajadores", "part", "0.00%", ""),
    ("Supervision del regulador", "superv", "0.00%", "% del ingreso tarifario"),
    ("IGV", "igv", "0.00%", "lo paga el usuario sobre la tarifa"),
    ("Tarifa al usuario", "tarifa_usuario", "#,##0.0000000",
     "S/ por kg DBO5 - LA CIERRA Buscar Objetivo"),
    # Es el mismo `Margen del costo fijo` de la plantilla, aplicado a TODO el
    # costo de O&M: en la rama autofinanciada no hay pata fija y pata variable
    # que separar, el operador opera el servicio entero.
    ("Margen del operador", "margen_om", "0.00%",
     "sobre todo el costo de O&M; aca no hay pata fija y variable"),
]


def escribir_auto(datos, ruta):
    """Libro de salida de la rama autofinanciada (activo intangible)."""
    wb = Workbook()
    _inputs(wb.active, datos, PARAMS_AUTO)
    _deuda(wb.create_sheet("Deuda"), datos)
    _ingresos_auto(wb.create_sheet("Ingresos"), datos)
    _intangible(wb.create_sheet("Activo intangible"), datos)
    _flujo_auto(wb.create_sheet("Flujo"), datos)
    _reparto_auto(wb.create_sheet("Reparto de la tarifa"), datos)
    _resumen_auto(wb.create_sheet("Resumen", 0), datos)
    wb.save(ruta)
    return ruta


def _malla(ws, fechas):
    n = len(fechas)
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    ws.cell(6, 2, "Mes").font = CABEZA
    for j, f in enumerate(fechas):
        c = ws.cell(6, 4 + j, f)
        c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
    return n, 7


def _ingresos_auto(ws, d):
    _cabecera(ws, "Ingreso tarifario al usuario",
              "Mismo reajuste por IPM con gatillo que la pata variable; aqui es "
              "todo el ingreso del proyecto.")
    m = d["meses"]
    n, r = _malla(ws, m["fecha"])
    r = _fila(ws, r, "Flag de operacion", m["flag_om"], "0")
    r = _fila(ws, r, "Trimestre del mes", m["trim_m"], "0")
    r = _fila(ws, r, "Produccion efectiva, kg DBO5", m["kg"], N2)
    fom, tri, kg = r - 3, r - 2, r - 1
    r = _fila(ws, r, "IPM mensual",
              [f"=((1+p_ipm)^(1/12)-1)*{L(4+j)}{fom}" for j in range(n)], N6)
    ipm = r - 1
    aj = r + 1
    r = _fila(ws, r, "Acumulado pendiente",
              [f"=IF({L(4+j)}{ipm}=0,0,SUM($D{ipm}:{L(4+j)}{ipm})-SUM($D{aj}:{L(3+j)}{aj}))"
               if j else f"=IF($D{ipm}=0,0,$D{ipm})" for j in range(n)], N6)
    pend = r - 1
    r = _fila(ws, r, "Ajuste liberado",
              [f"=IF({L(4+j)}{pend}>=p_gatillo,{L(4+j)}{pend},0)" for j in range(n)], N6)
    r = _fila(ws, r, "Factor de reajuste",
              [f"=TRUNC(IF({L(4+j)}{fom}=0,1,{'1' if j == 0 else L(3+j)+str(r)}*"
               f"(1+{L(4+j)}{aj})*{L(4+j)}{fom}),5)" for j in range(n)], "0.00000")
    fac = r - 1
    r = _fila(ws, r, "Ingreso tarifario mensual",
              [f"=IF({L(4+j)}{fom}=0,0,p_tarifa_usuario*{L(4+j)}{kg}*{L(4+j)}{fac})/1000"
               for j in range(n)], N2, negrita=True)
    ingm = r - 1
    r = _fila(ws, r, "Primer mes de operacion",
              [f"=IF(AND({L(4+j)}{fom}=1,"
               f"{'0' if j == 0 else 'SUM($D'+str(fom)+':'+L(3+j)+str(fom)+')'}=0),1,0)"
               for j in range(n)], "0")
    d["_ref_ing"] = dict(n=n, ing=ingm, trim=tri, factor=fac, fom=fom,
                         kg=kg, marca=r - 1)


def _intangible(ws, d):
    """El intangible del p.17, con los intereses de construccion capitalizados
    por el p.22 y amortizacion lineal durante la operacion.

    La amortizacion NO es caja: entra al estado de resultados como gasto
    deducible y no al flujo. Por eso la hoja `Flujo` la muestra aparte, dentro
    del bloque de utilidad, y no dentro del flujo de caja.
    """
    _cabecera(ws, "Activo intangible de la concesion",
              "CINIIF 12 p.17: derecho a cobrar al usuario, no importe "
              "determinable del concedente. p.22: intereses de obra capitalizados.")
    m = d["meses"]
    a = d["intangible"]
    n = len(m["fecha"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    ws.cell(r, 2, "Mes").font = CABEZA
    for j, f in enumerate(m["fecha"]):
        c = ws.cell(r, 4 + j, f)
        c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
    r += 1
    tri = r + 3
    fob, fom, sc, itot, icap, adi, amo, sal = (r + 4, r + 5, r + 6, r + 7,
                                               r + 8, r + 9, r + 10, r + 11)
    ua = L(3 + n)
    esc = [("Meses de operacion", f"=SUM($D${fom}:${ua}${fom})", "0"),
           ("Base del intangible al termino de obra",
            f"=SUM($D${adi}:${ua}${adi})", N2),
           ("Amortizacion lineal mensual", f"=$D${r+1}/$D${r}", N2)]
    for etiq, f, fmt in esc:
        ws.cell(r, 2, etiq).font = ETIQ_B
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = fmt, ENTRADA, ETIQ_B
        r += 1
    n_op, base, cuota = r - 3, r - 2, r - 1
    r = _fila(ws, r, "Trimestre del mes", m["trim_m"], "0")
    # No es `1 - flag_om`: la malla dura mas que la concesion, asi que despues
    # del ultimo mes de operacion `flag_om` vuelve a cero y capitalizaria la cola
    r = _fila(ws, r, "Flag anterior a la operacion", a["flag_obra"], "0")
    r = _fila(ws, r, "Flag de operacion", m["flag_om"], "0")
    r = _fila(ws, r, "Servicio de construccion del periodo", a["sc"], N2)
    r = _fila(ws, r, "Interes de la deuda del periodo", a["interes"], N2)
    r = _fila(ws, r, "Interes capitalizado (solo obra, p.22)",
              [f"={L(4+j)}{itot}*{L(4+j)}{fob}" for j in range(n)])
    r = _fila(ws, r, "Adicion al intangible",
              [f"={L(4+j)}{sc}*{L(4+j)}{fob}+{L(4+j)}{icap}" for j in range(n)])
    r = _fila(ws, r, "Amortizacion del intangible",
              [f"=$D${cuota}*{L(4+j)}{fom}" for j in range(n)], N2, negrita=True)
    r = _fila(ws, r, "Saldo del intangible",
              [f"={'0' if j == 0 else L(3+j)+str(sal)}+{L(4+j)}{adi}-{L(4+j)}{amo}"
               for j in range(n)], N2, negrita=True)
    r += 1
    for etiq, f in (
        ("Inversion capitalizada",
         f"=SUMPRODUCT($D${fob}:${ua}${fob},$D${sc}:${ua}${sc})"),
        ("Intereses capitalizados", f"=SUM($D${icap}:${ua}${icap})"),
        ("Amortizacion acumulada", f"=SUM($D${amo}:${ua}${amo})"),
        ("Saldo final, debe ser cero", f"=${ua}${sal}"),
    ):
        ws.cell(r, 2, etiq).font = ETIQ_B
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = N2, CALC, ETIQ_B
        r += 1
    d["_ref_int"] = dict(n=n, amort=amo, saldo=sal, base=base, n_op=n_op,
                         cuota=cuota, trim=tri)


def _flujo_auto(ws, d):
    _cabecera(ws, "Flujo de caja financiero",
              "El VAN de la ultima fila es la celda que Buscar Objetivo lleva a cero.")
    q, t = d["trimestres"], d["_ref_int"]
    ing = d["_ref_ing"]
    n, nm, ua = len(q["anio"]), t["n"], L(3 + t["n"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    for etiq, clave in (("Ano", "anio"), ("Trimestre", "trim"), ("Meses vivos", "meses")):
        ws.cell(r, 2, etiq).font = CABEZA
        for j, v in enumerate(q[clave]):
            c = ws.cell(r, 4 + j, v)
            c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
        r += 1
    mes, qn = r - 1, r - 2

    r = _fila(ws, r, "Ingreso tarifario",
              [f"=SUMPRODUCT((Ingresos!$D${ing['trim']}:${L(3+ing['n'])}${ing['trim']}"
               f"={L(4+j)}{qn}+0)*Ingresos!$D${ing['ing']}:${L(3+ing['n'])}${ing['ing']})"
               for j in range(n)], N2, negrita=True)
    ingf = r - 1
    r = _fila(ws, r, "Supervision del regulador",
              [f"=-p_superv*{L(4+j)}{ingf}" for j in range(n)])
    sup = r - 1
    prim = {}
    for etiq, clave in LINEAS_AUTO:
        r = _fila(ws, r, etiq, q[clave], N2)
        prim[clave] = r - 1
    r = _fila(ws, r, "Amortizacion del intangible (no es caja)",
              [f"=SUMPRODUCT(('Activo intangible'!$D${t['trim']}:${ua}${t['trim']}"
               f"={L(4+j)}{qn}+0),'Activo intangible'!$D${t['amort']}:${ua}${t['amort']})"
               for j in range(n)], N2)
    amo = r - 1
    r = _fila(ws, r, "Intereses de operacion", q["interes_op"], N2)
    inte = r - 1
    r = _fila(ws, r, "Utilidad antes de impuestos",
              [f"={L(4+j)}{ingf}+{L(4+j)}{sup}"
               f"+SUM({L(4+j)}{prim['costo_fijo']}:{L(4+j)}{prim['fideicomiso']})"
               f"-{L(4+j)}{amo}-{L(4+j)}{inte}" for j in range(n)], N2, negrita=True)
    r = _fila(ws, r, "Participacion e Impuesto a la Renta (del motor)",
              q["impuestos"], N2)
    imp = r - 1
    r = _fila(ws, r, "CAPEX de caja", [-x for x in q["capex_caja"]], N2)
    r = _fila(ws, r, "Efecto neto del IGV", q["igv"], N2)
    r = _fila(ws, r, "Desembolsos de deuda", q["desembolso"], N2)
    r = _fila(ws, r, "Servicio de deuda", [-x for x in q["servicio"]], N2)
    cap, igv, des, srv = r - 4, r - 3, r - 2, r - 1
    r = _fila(ws, r, "Flujo de caja financiero",
              [f"={L(4+j)}{ingf}+{L(4+j)}{sup}"
               f"+SUM({L(4+j)}{prim['costo_fijo']}:{L(4+j)}{prim['fideicomiso']})"
               f"+{L(4+j)}{imp}+SUM({L(4+j)}{cap}:{L(4+j)}{srv})"
               for j in range(n)], N2, negrita=True)
    fcf = r - 1
    r = _fila(ws, r, "Factor de actualizacion",
              [f"=IF({L(4+j)}{mes}=0,0,1/(1+(1+p_ke)^(1/12)-1)^SUM($D{mes}:{L(4+j)}{mes}))"
               for j in range(n)], "0.00000000")
    fd = r - 1
    r += 1
    ws.cell(r, 2, "VAN financiero").font = ETIQ_B
    c = ws.cell(r, 4, f"=SUMPRODUCT({L(4)}{fcf}:{L(3+n)}{fcf},{L(4)}{fd}:{L(3+n)}{fd})")
    c.number_format, c.fill = N2, ENTRADA
    d["_ref_flujo"] = dict(van=r, fcf=fcf, ing=ingf, sup=sup, fd=fd,
                           anio=qn - 1, trim=qn, mes=mes, n=n,
                           costo0=prim["costo_fijo"], costo1=prim["fideicomiso"])


def _reparto_auto(ws, d):
    """Cuanto de la tarifa repaga la inversion y cuanto paga la operacion.

    Oscar lo pidio el 2026-09-16: "aun siendo autofinanciada se debe proyectar
    la necesidad de flujos recaudados por tarifa para que se logre el VAN 0 y
    estos flujos tambien deben discriminarse de cuanto va para repagar la
    inversion y cuanto para la operacion y mantenimiento".

    El reparto es exacto y no tiene nada de convencional: de cada trimestre, lo
    que se lleva la operacion es su costo de caja, supervision del regulador
    incluida, y **lo que queda es lo que repaga la inversion**, o sea el
    servicio de la deuda, los impuestos y el remanente del flujo de caja financiero. Las dos
    partes suman el ingreso por construccion.

    Es la misma particion que en la rama cofinanciada hacen el PPDMO y el PPDI,
    y las dos ramas se pueden comparar por ahi: medido sobre Cajamarca, el VAN
    del costo de O&M da 166,135.84 autofinanciada contra 166,092.35
    cofinanciada, **0.03 % de diferencia**, y toda la diferencia entre regimenes
    esta en la pata de inversion.
    """
    _cabecera(ws, "Reparto de la tarifa",
              "De lo que recauda la tarifa, cuanto paga la operacion y cuanto "
              "repaga la inversion. Las dos partes suman el ingreso.")
    f, ing = d["_ref_flujo"], d["_ref_ing"]
    n, ui = f["n"], L(3 + ing["n"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 13
    r = 6
    for etiq, fila in (("Ano", f["anio"]), ("Trimestre", f["trim"])):
        ws.cell(r, 2, etiq).font = CABEZA
        for j in range(n):
            c = ws.cell(r, 4 + j, f"=Flujo!{L(4 + j)}{fila}")
            c.font, c.fill, c.alignment = CABEZA, BANDA, Alignment(horizontal="center")
        r += 1
    r += 1
    r = _fila(ws, r, "Ingreso tarifario",
              [f"=Flujo!{L(4 + j)}{f['ing']}" for j in range(n)], N2, negrita=True)
    ingf = r - 1
    # Las lineas de costo de la hoja `Flujo` ya vienen en negativo, y la
    # supervision tambien, asi que se les da vuelta el signo para leerlas como
    # lo que se lleva la operacion.
    r = _fila(ws, r, "Costo de operacion y mantenimiento, con supervision",
              [f"=-(Flujo!{L(4 + j)}{f['sup']}"
               f"+SUM(Flujo!{L(4 + j)}{f['costo0']}:{L(4 + j)}{f['costo1']}))"
               for j in range(n)], N2)
    costo = r - 1
    r = _fila(ws, r, "Margen del operador",
              [f"=p_margen_om*{L(4 + j)}{costo}" for j in range(n)], N2)
    mar = r - 1
    r = _fila(ws, r, "Operacion y mantenimiento",
              [f"={L(4 + j)}{costo}+{L(4 + j)}{mar}" for j in range(n)], N2)
    om = r - 1
    r = _fila(ws, r, "Disponible para repagar la inversion",
              [f"={L(4 + j)}{ingf}-{L(4 + j)}{om}" for j in range(n)], N2,
              negrita=True)
    inv = r - 1
    r += 1
    r = _fila(ws, r, "Produccion facturada, kg DBO5",
              [f"=SUMPRODUCT((Ingresos!$D${ing['trim']}:${ui}${ing['trim']}"
               f"={L(4 + j)}{f['trim']}+0)*Ingresos!$D${ing['kg']}:${ui}${ing['kg']})"
               for j in range(n)], N2)
    kg = r - 1
    for etiq, fila in (("Tarifa unitaria del trimestre", ingf),
                       ("  de la operacion, con margen", om),
                       ("  de la inversion", inv)):
        r = _fila(ws, r, etiq,
                  [f"=IF({L(4 + j)}{kg}=0,0,{L(4 + j)}{fila}/{L(4 + j)}{kg}*1000)"
                   for j in range(n)], "#,##0.0000000")
    r += 1
    r = _fila(ws, r, "Factor de actualizacion",
              [f"=Flujo!{L(4 + j)}{f['fd']}" for j in range(n)], "0.00000000")
    fd = r - 1
    r += 1
    ult = L(3 + n)
    van = lambda fila: f"=SUMPRODUCT($D${fila}:${ult}${fila},$D${fd}:${ult}${fd})"
    controles = [
        ("VAN del ingreso tarifario", van(ingf), N2),
        ("VAN del costo de O&M, sin margen", van(costo), N2),
        ("VAN de la operacion, con margen", van(om), N2),
        ("VAN para la inversion", van(inv), N2),
        ("Participacion de la operacion", f"=$D${r + 2}/$D${r}", "0.00%"),
        ("Participacion de la inversion", f"=$D${r + 3}/$D${r}", "0.00%"),
        ("Las dos partes menos el total, debe ser cero",
         f"=$D${r + 2}+$D${r + 3}-$D${r}", N2),
        ("Check del reparto",
         f'=IF(ROUND($D${r + 6},2)=0,"OK","ERROR")', "General"),
    ]
    d["_ref_reparto"] = dict(van_ing=r, van_costo=r + 1, van_om=r + 2,
                             van_inv=r + 3, pct_om=r + 4, pct_inv=r + 5,
                             check=r + 7)
    for etiq, formula, fmt in controles:
        ws.cell(r, 2, etiq).font = ETIQ_B
        c = ws.cell(r, 4, formula)
        c.number_format, c.fill, c.font = fmt, CALC, ETIQ_B
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        r += 1


def _resumen_auto(ws, d):
    _cabecera(ws, "Resumen del modelo, APP autofinanciada",
              "S/ miles sin IGV. No hay PPDI ni PPDMO: el proyecto se paga con "
              "la tarifa al usuario.")
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 40
    t, ing = d["_ref_int"], d["_ref_ing"]
    ua, ui = L(3 + t["n"]), L(3 + ing["n"])
    filas = [
        ("Tarifa al usuario, S/ por kg DBO5", "=p_tarifa_usuario", "#,##0.0000000"),
        ("Ingreso tarifario, primer mes de operacion anualizado",
         f"=SUMPRODUCT(Ingresos!$D${ing['marca']}:${ui}${ing['marca']},"
         f"Ingresos!$D${ing['ing']}:${ui}${ing['ing']})*12", N2),
        ("Ingreso tarifario, promedio mensual de la operacion",
         f"=SUMPRODUCT(Ingresos!$D${ing['fom']}:${ui}${ing['fom']},"
         f"Ingresos!$D${ing['ing']}:${ui}${ing['ing']})"
         f"/SUM(Ingresos!$D${ing['fom']}:${ui}${ing['fom']})", N2),
        ("Tarifa que paga la operacion con su margen, S/ por kg DBO5",
         f"=p_tarifa_usuario*'Reparto de la tarifa'!$D${d['_ref_reparto']['pct_om']}",
         "#,##0.0000000"),
        ("Tarifa que repaga la inversion, S/ por kg DBO5",
         f"=p_tarifa_usuario*'Reparto de la tarifa'!$D${d['_ref_reparto']['pct_inv']}",
         "#,##0.0000000"),
        ("VAN del ingreso tarifario",
         f"='Reparto de la tarifa'!$D${d['_ref_reparto']['van_ing']}", N2),
        ("  del que va a la operacion",
         f"='Reparto de la tarifa'!$D${d['_ref_reparto']['van_om']}", N2),
        ("  del que repaga la inversion",
         f"='Reparto de la tarifa'!$D${d['_ref_reparto']['van_inv']}", N2),
        ("Activo intangible al termino de obra", f"='Activo intangible'!$D${t['base']}", N2),
        ("Amortizacion lineal mensual", f"='Activo intangible'!$D${t['cuota']}", N2),
        ("Meses de operacion", f"='Activo intangible'!$D${t['n_op']}", "0"),
        ("Saldo final del intangible, debe ser cero", f"='Activo intangible'!${ua}${t['saldo']}", N2),
        ("VAN financiero, debe ser cero", f"=Flujo!$D${d['_ref_flujo']['van']}", N2),
        ("WACC", "=p_wacc", N6),
        ("Kd", "=p_kd", N6),
        ("Ke", "=p_ke", N6),
    ]
    r = 6
    for etiq, f, fmt in filas:
        ws.cell(r, 2, etiq).font = ETIQ_B if r < 12 else ETIQ
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = fmt, CALC, ETIQ_B
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        r += 1
