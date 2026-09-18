import openpyxl, json, warnings
warnings.filterwarnings("ignore")
from openpyxl.utils import column_index_from_string as ci
wb = openpyxl.load_workbook("0484bdc3-2026abr09_MODEF_PTAR_Cajamarca_v_sending.xlsm", data_only=True)
ws = wb["PPDI"]
c0, c1 = ci("D"), ci("LC")          # meses 1..288
def row(r):
    out=[]
    for c in range(c0, c1+1):
        v = ws.cell(r,c).value
        out.append(float(v) if isinstance(v,(int,float)) else 0.0)
    return out
rows = {
 "flag_ppdi":11, "costo_obra":56, "fideicomiso":57, "seguros":58, "garantias":59,
 "reembolso":60, "estructuracion":61, "comision":62, "flag_trib":93,
 "ing_fin":113, "ppdi":114, "af_saldo":115, "ir":88, "igv_neto":139,
 "fc_antes_deuda":168, "uai":87, "servicio_constr":55, "anio":6,
 "ppdi_mensual":13, "ppdi_trim":14, "gastos_fin":83, "flag_mes":9,
}
data = {k: row(r) for k,r in rows.items()}
scal = {
 "tasa_implicita_mensual": ws["D366"].value,
 "wacc_mensual": ws["D379"].value,
 "wacc_anual": ws["D380"].value,
 "ppdi_base_mensual": ws["H367"].value,
 "van_ppdi": ws["D378"].value,
 "igv": wb["Inputs"]["D12"].value,
 "ir": wb["Inputs"]["D14"].value,
 "part_trab": wb["Inputs"]["D13"].value,
 "n_meses": c1-c0+1,
}
json.dump({"series":data,"escalares":scal}, open("cajamarca_primitivos.json","w"))
print(json.dumps(scal, indent=1, default=str))
print("meses con flag PPDI:", sum(data["flag_ppdi"]))
print("suma costo obra:", round(sum(data["costo_obra"]),2))
print("suma PPDI (neg):", round(sum(data["ppdi"]),2))
