"""Libro de salida de San Martin, con formulas vivas.

Misma idea que el de Cajamarca, pero el modelo es distinto en tres cosas y el
libro tiene que mostrarlas: el PPDI se paga **por hitos funcionales**, la deuda
se dimensiona **por cobertura** (RCSD 1.25 con cuenta de reserva al 50 % del
servicio del ano siguiente) y el cierre mueve **todo el PPDMO**, la pata fija y
el precio unitario a la vez.

La malla es anual, 28 anos, no mensual: el modelo aprobado de San Martin cierra
sobre el flujo anual.
"""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName

TIT = Font(bold=True, size=13, color="1A4B4B")
SUB = Font(size=9, italic=True, color="6B7B7B")
CAB = Font(bold=True, size=9, color="FFFFFF")
ETI = Font(size=9)
ETB = Font(bold=True, size=9)
ENT = PatternFill("solid", fgColor="FFF3D6")
CALC = PatternFill("solid", fgColor="F2F7F7")
BANDA = PatternFill("solid", fgColor="1A4B4B")
FINA = Border(bottom=Side("thin", color="D5DEDE"))
N2, N6 = "#,##0.00", "0.000000%"

PARAMS = [
    ("Ke, costo del patrimonio", "ke", N6, "CAPM en USD + riesgo pais + devaluacion"),
    ("Kd, costo de la deuda", "kd", N6, "soberano a vida media + spread"),
    ("WACC", "wacc", N6, "despues de impuestos"),
    ("TIR objetivo del cierre", "tir", N6, "Ke redondeado a 4 decimales, Control!M12"),
    ("Cobertura minima, RCSD", "rcsd", "0.00", "dimensiona la amortizacion"),
    ("Cuenta de reserva, CRSD", "crsd", "0.00%", "del servicio del ano siguiente"),
    ("Impuesto a la Renta", "ir", "0.00%", ""),
    ("Participacion de trabajadores", "pt", "0.00%", ""),
    ("Arrastre de perdidas", "arr", "0.00%", "sistema B"),
    ("IPM, reajuste", "ipm", N6, "anual"),
    ("Tipo de cambio", "fx", "0.0000", "solo entra por los reembolsos en dolares"),
    ("Cuotas del PPDI", "cuotas", "0", "trimestrales"),
    ("PPDI anual", "ppdi", N2, "S/ - LA CIERRA Solver"),
    ("PPDMO referencia mensual", "ref", N2, "S/ - LA CIERRA Solver"),
]

# (etiqueta, clave en el detalle, se escala con la incognita, signo)
# El signo esta porque el motor guarda el IR y la participacion como importes
# positivos, igual que `EEFF Anuales`, y en el flujo son salidas.
LINEAS = [
    ("PPD Inversiones", "ppdi", True, 1),
    ("PPD MO fijo", "pfij", True, 1),
    ("PPD MO variable", "pvar", True, 1),
    ("Pago por Obras", "pago_obras", False, 1),
    ("CAPEX", "capex", False, 1),
    ("Otros costos del periodo D+C+PM", "otros_dc", False, 1),
    ("Variacion de IGV del periodo D+C+PM", "igv_dc", False, 1),
    ("Costos de cierre de la laguna SJS", "laguna", False, 1),
    ("Costos de operacion y mantenimiento", "costo_om", False, 1),
    ("Reposiciones", "repex", False, 1),
    ("Variacion del capital de trabajo", "varkt", False, 1),
    ("Otros del periodo operativo", "otros_op", False, 1),
    ("Participacion de trabajadores", "pt", False, -1),
    ("Impuesto a la Renta", "ir", False, -1),
    ("Desembolsos de deuda", "desem", False, 1),
    ("Intereses de construccion", "int_dc", False, 1),
    ("Comisiones de construccion", "com_dc", False, 1),
    ("Intereses del periodo operativo", "int_op", False, 1),
    ("Amortizacion de deuda", "amort", False, 1),
    ("Cuenta de reserva CRSD", "crsd", False, 1),
]


def escribir(d, ruta):
    wb = Workbook()
    _inputs(wb.active, d)
    _hitos(wb.create_sheet("Hitos"), d)
    _flujo(wb.create_sheet("Flujo"), d)
    _activo(wb.create_sheet("Activo financiero"), d)
    _resumen(wb.create_sheet("Resumen", 0), d)
    wb.save(ruta)
    return ruta


def _moneda(d):
    """La unidad del libro, que viene de la plantilla.

    Importa en el precio unitario: la rama por hitos lo calcula en la moneda del
    modelo por kg, sin dividir entre mil como hace la de "al final de obra". Si
    el proyecto esta escrito en S/ miles, un precio de 0.0119 son 11.9 soles por
    kg, y sin la unidad en la etiqueta eso se lee mal.
    """
    return str(d.get("inputs", {}).get("moneda") or "S/")


def _cab(ws, titulo, sub):
    ws["B2"], ws["B2"].font = titulo, TIT
    ws["B3"], ws["B3"].font = sub, SUB
    ws.column_dimensions["B"].width = 42


def _inputs(ws, d, params=None):
    params = PARAMS if params is None else params
    ws.title = "Inputs"
    _cab(ws, "Parametros del modelo",
         "Las celdas en ambar son de entrada. Las dos ultimas las resuelve el cierre.")
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 46
    for i, (etq, clave, fmt, nota) in enumerate(params):
        r = 6 + i
        ws.cell(r, 2, etq).font = ETI
        c = ws.cell(r, 4, d["inputs"][clave])
        c.number_format, c.fill, c.font = fmt, ENT, ETB
        ws.cell(r, 5, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
        ws.parent.defined_names.add(
            DefinedName(f"p_{clave}", attr_text=f"Inputs!$D${r}"))


def _hitos(ws, d):
    _cab(ws, "Hitos funcionales",
         "El PPDI se reparte por la participacion de cada hito en el CAPEX, y el "
         "PPDMO fijo por el VAN de su operacion y mantenimiento.")
    for col, w in (("C", 18), ("D", 20), ("E", 20), ("F", 20)):
        ws.column_dimensions[col].width = w
    enc = ["Hito", "% del CAPEX", "Cuota trimestral del PPDI",
           "PPDMO fijo mensual"]
    for j, e in enumerate(enc):
        c = ws.cell(5, 2 + j, e)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    for i in range(4):
        r = 6 + i
        ws.cell(r, 2, f"Hito {i + 1}").font = ETB
        c = ws.cell(r, 3, d["pct_capex"][i])
        c.number_format, c.fill = "0.0000%", ENT
        ws.cell(r, 4, f"=p_ppdi*C{r}/4").number_format = N2
        c = ws.cell(r, 5, d["ppdmo_hito"][i])
        c.number_format, c.fill = N2, CALC
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
    ws.cell(10, 2, "Total").font = ETB
    ws.cell(10, 3, "=SUM(C6:C9)").number_format = "0.0000%"
    ws.cell(10, 4, "=SUM(D6:D9)").number_format = N2
    ws.cell(10, 5, "=SUM(E6:E9)").number_format = N2


def _flujo(ws, d, lineas=None):
    lineas = LINEAS if lineas is None else lineas
    _cab(ws, "Flujo de caja anual",
         "El VAN de la ultima fila es la celda que Solver lleva a cero.")
    n = len(d["anio"])
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 16
    ws.cell(5, 2, "Ano").font = CAB
    for j, a in enumerate(d["anio"]):
        c = ws.cell(5, 4 + j, a)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    ws.cell(5, 3).fill = BANDA
    r, ref = 7, {}
    for etq, clave, escala, sg in lineas:
        ws.cell(r, 2, etq).font = ETI
        for j in range(n):
            if escala and clave == "ppdi":
                cel = ws.cell(r, 4 + j, f"=p_ppdi*{d['perfil_ppdi'][j]}")
            elif escala:
                cel = ws.cell(r, 4 + j, f"=p_ref*{d['perfil'][clave][j]}")
            else:
                cel = ws.cell(r, 4 + j, sg * d["det"][clave][j])
            cel.number_format, cel.font = N2, ETI
        ref[clave] = r
        r += 1
    d["_filas_flujo"] = ref
    d["_flujo_n"] = n
    r += 1
    ws.cell(r, 2, "Flujo de caja financiero").font = ETB
    for j in range(n):
        c = ws.cell(r, 4 + j,
                    f"=SUM({L(4+j)}{ref[lineas[0][1]]}:{L(4+j)}{ref[lineas[-1][1]]})")
        c.number_format, c.font = N2, ETB
    fcf = r
    r += 1
    ws.cell(r, 2, "Periodo de descuento").font = ETI
    for j in range(n):
        ws.cell(r, 4 + j, d["det"]["per"][j]).number_format = "0.00"
    per = r
    d["_flujo_per"] = per
    r += 2
    ws.cell(r, 2, "VAN del flujo de caja financiero").font = ETB
    c = ws.cell(r, 4, f"=SUMPRODUCT({L(4)}{fcf}:{L(3+n)}{fcf},"
                      f"1/(1+p_tir)^{L(4)}{per}:{L(3+n)}{per})")
    c.number_format, c.fill = N2, ENT
    d["_van"] = r


def _activo(ws, d):
    """`Act_Financ` del libro aprobado, en la malla anual del resto del libro.

    El activo financiero de la CINIIF 12 p.16 nace del **servicio de
    construccion** -- el CAPEX y los otros costos del periodo D+C+PM --, no de
    la necesidad de financiamiento: no entran comisiones, ni IGV, ni reserva, ni
    capital de trabajo, ni intereses capitalizados. El libro lo arma igual,
    `Act_Financ TRIM!14:17`, y su tasa es la TIR de esa misma fila total.

    La malla del libro es trimestral y esta es anual, como el resto de este
    libro; medido contra `Act_Financ`, la tasa sale 12.288384 % contra el
    12.298657 % que da la trimestral llevada al ano, 1.03 puntos base.
    """
    f = d["_filas_flujo"]
    n = len(d["anio"])
    _cab(ws, "Activo financiero del PPDI",
         "CINIIF 12 p.16: el cobro es incondicional, asi que la obra es cuenta "
         "por cobrar. Se reconoce por el servicio de construccion, no por la "
         "necesidad de financiamiento.")
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 16
    ws.cell(5, 2, "Ano").font = CAB
    for j, a in enumerate(d["anio"]):
        c = ws.cell(5, 4 + j, a)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    ws.cell(5, 3).fill = BANDA

    comp = [("Servicio de construccion (CAPEX)", "capex"),
            ("Otros costos del periodo D+C+PM", "otros_dc"),
            ("PPD Inversiones cobrado", "ppdi")]
    for i, (etq, clave) in enumerate(comp):
        ws.cell(7 + i, 2, etq).font = ETI
        for j in range(n):
            c = ws.cell(7 + i, 4 + j, f"=-Flujo!{L(4 + j)}{f[clave]}")
            c.number_format, c.font = N2, ETI
    ws.cell(10, 2, "Total del periodo").font = ETB
    for j in range(n):
        c = ws.cell(10, 4 + j, f"=SUM({L(4 + j)}7:{L(4 + j)}9)")
        c.number_format, c.font = N2, ETB

    ws.cell(12, 2, "Tasa implicita anual").font = ETB
    c = ws.cell(12, 4, f"=IFERROR(IRR($D$10:${L(3 + n)}$10),0)")
    c.number_format, c.fill = N6, CALC

    etqs = ["Saldo inicial del activo", "Ingreso financiero devengado",
            "Saldo final del activo"]
    for i, etq in enumerate(etqs):
        ws.cell(14 + i, 2, etq).font = ETI
    ws.cell(16, 2).font = ETB
    for j in range(n):
        col = L(4 + j)
        ws.cell(14, 4 + j, 0 if j == 0 else f"={L(3 + j)}16").number_format = N2
        ws.cell(15, 4 + j, f"={col}14*$D$12").number_format = N2
        c = ws.cell(16, 4 + j, f"={col}14+{col}10+{col}15")
        c.number_format, c.font = N2, ETB
    ult = L(3 + n)
    controles = [
        ("Saldo maximo del activo", f"=MAX($D$16:${ult}$16)", N2),
        ("Ingreso financiero acumulado", f"=SUM($D$15:${ult}$15)", N2),
        ("Saldo final, debe ser cero", f"={ult}16", N2),
        ("Check AF", f'=IF(ROUND({ult}16,2)=0,"OK","ERROR")', "General"),
        # redondeado a dos decimales como el `AF Negativo` del libro: sin eso
        # los ceros de cola del saldo cuentan como negativos.
        ("Anos con saldo negativo",
         f"=SUMPRODUCT(--(ROUND($D$16:${ult}$16,2)<0))", "0"),
    ]
    for i, (etq, frm, fmt) in enumerate(controles):
        ws.cell(18 + i, 2, etq).font = ETB
        c = ws.cell(18 + i, 4, frm)
        c.number_format, c.fill = fmt, CALC


def _resumen(ws, d):
    _cab(ws, "Resumen del modelo",
         "San Martin paga el PPDI por hitos funcionales y cierra todo el PPDMO a la vez.")
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 40
    filas = [
        ("PPD Inversiones, anual", "=p_ppdi", N2),
        ("PPD Inversiones, cuota trimestral", "=p_ppdi/4", N2),
        ("PPD MO, referencia mensual", "=p_ref", N2),
        ("PPD MO fijo, anual", f"=Hitos!E10*12", N2),
        (f"Precio unitario, {_moneda(d)} por kg DBO", d["precio"], "#,##0.000000"),
        ("VAN financiero, debe ser cero", f"=Flujo!$D${d['_van']}", N2),
        ("Ke", "=p_ke", N6),
        ("Kd", "=p_kd", N6),
        ("WACC", "=p_wacc", N6),
    ]
    for i, (etq, f, fmt) in enumerate(filas):
        r = 6 + i
        ws.cell(r, 2, etq).font = ETB if i < 5 else ETI
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = fmt, CALC, ETB
        for col in range(2, 6):
            ws.cell(r, col).border = FINA


# ================================================================ AUTOFINANCIADA
# Pago por hitos SIN PPDI: la obra es activo intangible (CINIIF 12 p.17) y la
# incognita del cierre es la tarifa al usuario. De "por hitos" queda el perfil de
# inversion, los aportes de capital y la deuda dimensionada por cobertura; los
# hitos NO escalonan el inicio de la operacion, porque en el modelo aprobado las
# cuatro patas fijas arrancan el mismo mes.
PARAMS_AUTO = [p for p in PARAMS if p[1] not in ("cuotas", "ppdi")] + [
    ("Tarifa al usuario", "precio", "#,##0.000000",
     "S/ por kg DBO5, derivada de la referencia"),
    ("Margen del operador", "margen_om", "0.00%",
     "sobre todo el costo de O&M; aca no hay pata fija y variable"),
]
LINEAS_AUTO = ([("Ingreso tarifario al usuario", "pvar", True, 1)]
               + [l for l in LINEAS
                  if l[1] not in ("ppdi", "pfij", "pvar")])


def escribir_auto(d, ruta):
    wb = Workbook()
    _inputs(wb.active, d, PARAMS_AUTO)
    _hitos_auto(wb.create_sheet("Hitos"), d)
    _intangible(wb.create_sheet("Activo intangible"), d)
    _flujo(wb.create_sheet("Flujo"), d, LINEAS_AUTO)
    _memo_amort(wb["Flujo"], d)
    _reparto_auto(wb.create_sheet("Reparto de la tarifa"), d)
    _resumen_auto(wb.create_sheet("Resumen", 0), d)
    wb.save(ruta)
    return ruta


def _reparto_auto(ws, d):
    """Cuanto de la tarifa paga la operacion y cuanto repaga la inversion.

    Lo mismo que hace `escribir_excel._reparto_auto` en la rama al final de
    obra, aqui sobre la malla anual. El reparto es exacto: de cada ano, lo que
    se lleva la operacion es su costo de caja y **lo que queda repaga la
    inversion**; las dos partes suman el ingreso, por construccion.
    """
    _cab(ws, "Reparto de la tarifa",
         "De lo que recauda la tarifa, cuanto paga la operacion y cuanto "
         "repaga la inversion. Las dos partes suman el ingreso.")
    ref, n, per = d["_filas_flujo"], d["_flujo_n"], d["_flujo_per"]
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 16
    ws.cell(5, 2, "Ano").font = CAB
    for j, a in enumerate(d["anio"]):
        c = ws.cell(5, 4 + j, a)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    ws.cell(5, 3).fill = BANDA
    r = 7
    filas = [("Ingreso tarifario", [f"=Flujo!{L(4 + j)}{ref['pvar']}"
                                    for j in range(n)], ETB),
             # la fila de costo de la hoja `Flujo` viene en negativo
             ("Costo de operacion y mantenimiento",
              [f"=-Flujo!{L(4 + j)}{ref['costo_om']}" for j in range(n)], ETI),
             ("Margen del operador",
              [f"=p_margen_om*{L(4 + j)}{r + 1}" for j in range(n)], ETI),
             ("Operacion y mantenimiento",
              [f"={L(4 + j)}{r + 1}+{L(4 + j)}{r + 2}" for j in range(n)], ETI)]
    for etq, formulas, fuente in filas:
        ws.cell(r, 2, etq).font = fuente
        for j, f in enumerate(formulas):
            c = ws.cell(r, 4 + j, f)
            c.number_format, c.font = N2, ETI
        r += 1
    ing, costo, om = r - 4, r - 3, r - 1
    ws.cell(r, 2, "Disponible para repagar la inversion").font = ETB
    for j in range(n):
        c = ws.cell(r, 4 + j, f"={L(4 + j)}{ing}-{L(4 + j)}{om}")
        c.number_format, c.font = N2, ETB
    inv = r
    r += 2
    ult = L(3 + n)
    van = lambda fila: (f"=SUMPRODUCT($D${fila}:${ult}${fila},"
                        f"1/(1+p_tir)^Flujo!$D${per}:${ult}${per})")
    controles = [("VAN del ingreso tarifario", van(ing), N2),
                 ("VAN del costo de O&M, sin margen", van(costo), N2),
                 ("VAN de la operacion, con margen", van(om), N2),
                 ("VAN para la inversion", van(inv), N2),
                 ("Participacion de la operacion", f"=$D${r + 2}/$D${r}", "0.00%"),
                 ("Participacion de la inversion", f"=$D${r + 3}/$D${r}", "0.00%"),
                 ("Las dos partes menos el total, debe ser cero",
                  f"=$D${r + 2}+$D${r + 3}-$D${r}", N2),
                 ("Check del reparto",
                  f'=IF(ROUND($D${r + 6},2)=0,"OK","ERROR")', "General")]
    for etq, formula, fmt in controles:
        ws.cell(r, 2, etq).font = ETB
        c = ws.cell(r, 4, formula)
        c.number_format, c.fill, c.font = fmt, ENT, ETB
        r += 1


def _hitos_auto(ws, d):
    _cab(ws, "Hitos funcionales",
         "Sin PPDI los hitos solo reparten la inversion: no hay cuota que "
         "cobrar y no escalonan el inicio de la operacion.")
    for col, w in (("C", 18), ("D", 24)):
        ws.column_dimensions[col].width = w
    for j, e in enumerate(["Hito", "% del CAPEX", "Inversion del hito"]):
        c = ws.cell(5, 2 + j, e)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    for i in range(4):
        r = 6 + i
        ws.cell(r, 2, f"Hito {i + 1}").font = ETB
        c = ws.cell(r, 3, d["pct_capex"][i])
        c.number_format, c.fill = "0.0000%", ENT
        ws.cell(r, 4, f"='Activo intangible'!$D$7*C{r}").number_format = N2
        for col in range(2, 5):
            ws.cell(r, col).border = FINA
    ws.cell(10, 2, "Total").font = ETB
    ws.cell(10, 3, "=SUM(C6:C9)").number_format = "0.0000%"
    ws.cell(10, 4, "=SUM(D6:D9)").number_format = N2


def _intangible(ws, d):
    """El intangible del p.17, con los intereses de obra capitalizados (p.22).

    Su amortizacion lineal **reemplaza** a la depreciacion del CAPEX y a la
    amortizacion en 10 anos de los gastos financieros de construccion: los
    intereses ya estan dentro del activo y deducirlos por las dos vias seria
    contarlos dos veces. No es caja: entra al resultado, no al flujo.
    """
    _cab(ws, "Activo intangible de la concesion",
         "CINIIF 12 p.17 y p.22. La amortizacion es gasto deducible y NO es caja.")
    a = d["intangible"]
    n = len(d["anio"])
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 46
    esc = [("Inversion capitalizada", a["inversion"], N2,
            "CAPEX, otros del periodo D+C+PM y comisiones"),
           ("Intereses capitalizados", a["interes_capitalizado"], N2,
            "solo los del periodo de obra, NIC 23 via CINIIF 12 p.22"),
           ("Activo intangible al termino de obra", "=$D$6+$D$7", N2, ""),
           ("Meses de operacion", a["meses_operacion"], "0", ""),
           ("Amortizacion lineal mensual", "=$D$8/$D$9", N2, "")]
    for i, (etq, v, fmt, nota) in enumerate(esc):
        r = 6 + i
        ws.cell(r, 2, etq).font = ETB
        c = ws.cell(r, 4, v)
        c.number_format, c.font = fmt, ETB
        c.fill = ENT if isinstance(v, (int, float)) else CALC
        ws.cell(r, 5, nota).font = Font(size=8, italic=True, color="6B7B7B")
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
    inv, cap, base, nop, cuota = 6, 7, 8, 9, 10
    r = 13
    ws.cell(r, 2, "Ano").font = CAB
    for j, y in enumerate(d["anio"]):
        c = ws.cell(r, 4 + j, y)
        c.font, c.fill, c.alignment = CAB, BANDA, Alignment(horizontal="center")
    for j in range(n):
        ws.column_dimensions[L(4 + j)].width = 16
    r += 1
    ws.cell(r, 2, "Meses de operacion del ano").font = ETI
    for j, v in enumerate(d["meses_op"]):
        ws.cell(r, 4 + j, v).number_format = "0.00"
    mes = r
    r += 1
    ws.cell(r, 2, "Amortizacion del intangible").font = ETB
    for j in range(n):
        c = ws.cell(r, 4 + j, f"=$D${cuota}*{L(4+j)}{mes}")
        c.number_format, c.font = N2, ETB
    amo = r
    r += 1
    ws.cell(r, 2, "Saldo del intangible").font = ETB
    for j in range(n):
        c = ws.cell(r, 4 + j,
                    f"={'$D$'+str(base) if j == 0 else L(3+j)+str(r)}-{L(4+j)}{amo}")
        c.number_format, c.font = N2, ETB
    sal = r
    r += 2
    for etq, f in (("Amortizacion acumulada", f"=SUM($D${amo}:${L(3+n)}${amo})"),
                   ("Saldo final, debe ser cero", f"=${L(3+n)}${sal}")):
        ws.cell(r, 2, etq).font = ETB
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = N2, CALC, ETB
        r += 1
    d["_ref_int"] = dict(base=base, cuota=cuota, amort=amo, saldo=sal, n=n)


def _memo_amort(ws, d):
    """La amortizacion del intangible, como memoria, DEBAJO del flujo de caja.

    Va fuera de la suma a proposito: no es caja, solo baja la base imponible.
    """
    t, n = d["_ref_int"], len(d["anio"])
    r = d["_van"] + 2
    ws.cell(r, 2, "Memoria: amortizacion del intangible (no es caja)").font = ETI
    for j in range(n):
        c = ws.cell(r, 4 + j,
                    f"='Activo intangible'!{L(4+j)}{t['amort']}")
        c.number_format, c.font = N2, ETI


def _resumen_auto(ws, d):
    _cab(ws, "Resumen del modelo, APP autofinanciada por hitos",
         "No hay PPDI ni PPDMO: el proyecto se paga con la tarifa al usuario.")
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 40
    t = d["_ref_int"]
    filas = [
        (f"Tarifa al usuario, {_moneda(d)} por kg DBO5", "=p_precio", "#,##0.000000"),
        ("Referencia mensual de ingreso", "=p_ref", N2),
        ("Ingreso tarifario, primer ano de operacion", d["ingreso_1"], N2),
        ("Activo intangible al termino de obra",
         f"='Activo intangible'!$D${t['base']}", N2),
        ("Amortizacion lineal mensual",
         f"='Activo intangible'!$D${t['cuota']}", N2),
        ("Saldo final del intangible, debe ser cero",
         f"='Activo intangible'!${L(3+t['n'])}${t['saldo']}", N2),
        ("VAN financiero, debe ser cero", f"=Flujo!$D${d['_van']}", N2),
        ("Ke", "=p_ke", N6),
        ("Kd", "=p_kd", N6),
        ("WACC", "=p_wacc", N6),
    ]
    for i, (etq, f, fmt) in enumerate(filas):
        r = 6 + i
        ws.cell(r, 2, etq).font = ETB if i < 7 else ETI
        c = ws.cell(r, 4, f)
        c.number_format, c.fill, c.font = fmt, CALC, ETB
        for col in range(2, 6):
            ws.cell(r, col).border = FINA
