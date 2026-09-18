"""Extrae el bloque anual del modelo de Hitos Funcionales (FC, Impuestos,
Deuda Anual, Ingresos) para cerrar el PPDMO fuera de Excel."""
import json, openpyxl, warnings
warnings.filterwarnings("ignore")

W = openpyxl.load_workbook("64199c72-Modelo_Hitos_Funcionales.xlsm",
                           data_only=True, keep_vba=True)
F, AG = 6, 33          # columnas anuales F..AG
NY = AG - F + 1

def fila(hoja, r, c1=F, c2=AG):
    ws = W[hoja]
    out = []
    for c in range(c1, c2 + 1):
        v = ws.cell(row=r, column=c).value
        out.append(float(v) if isinstance(v, (int, float)) else 0.0)
    return out

def cel(hoja, ref):
    v = W[hoja][ref].value
    return float(v) if isinstance(v, (int, float)) else v

fc = {r: fila("FC", r) for r in
      [4,5,6,7,8,9,10] + list(range(14,31)) + [32,34,35,36,37,38,40,42,43,45,
       47,48,50,52,53,54,56,58,60,73,78,79,96,98,99,101,103,104,105,107,
       110,111,115,116,119,123,124,125,126]}
imp = {r: fila("Impuestos", r) for r in
       [14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,30,32,34,39,42,43,44,45,
        47,48,50,52,56,57,59,60,61,67,68,70,76,77]}
da = {r: fila("Deuda Anual", r) for r in
      [14,15,16,21,22,23,24,27,28,29,31,32,33,35,36,50,52,53,54,55,57]}

# --- Ingresos mensuales de O&M, para recalcular los repartos con otro Ke ---
MC = 341   # columna MC
ing_m = {r: fila("Ingresos", r, 6, MC) for r in [62,63,64,65,66,67]}

esc = dict(
    ny=NY,
    ke_anual=cel("Ke","C25"),                 # WACC soles (descuento O&M)
    ke_equity=cel("Ke","C23"),                # Ke soles
    tir_objetivo=cel("Control","M12"),
    van_fcf_libro=cel("FC","D80"),
    tir_fcf_libro=cel("FC","D74"),
    ref_ppdmo=cel("Control","C49"),
    ppdmo_fijo_anual=cel("Control","C21"),
    precio_unit=cel("Control","C27"),
    ppdi_anual=cel("Control","C16"),
    d83=cel("Ingresos","D83"), d84=cel("Ingresos","D84"),
    d87=cel("Ingresos","D87"), d88=cel("Ingresos","D88"),
    e71=cel("Ingresos","E71"), e72=cel("Ingresos","E72"), e73=cel("Ingresos","E73"),
    corr=cel("Ingresos","D101")+cel("Ingresos","D102"),
    ir=cel("Control","C34"), pt=cel("Control","C35"),
    rcsd=cel("Deuda Anual","D15"), kd=cel("Deuda Anual","D18"),
    crsd_obj=cel("Deuda Anual","D49"),
    base_arrastre=cel("Impuestos","D38"),
    plazo_amort_gf=cel("Impuestos","D69"),
    pmp=cel("FC","D102"),
    ktinicial=cel("FC","D110"),
    off_ing=10,    # columna P respecto de F, para el VAN de O&M
)
json.dump(dict(fc=fc, imp=imp, da=da, ing_m=ing_m, esc=esc),
          open("sanmartin_anual.json","w"))
print({k: v for k, v in esc.items()})
