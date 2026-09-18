"""Arma el libro de salida de San Martin y lo guarda en xlsx."""
import correr_final as F
import escribir_excel_sm as EX
import motor_ppdmo_sm as Q
import motor_sanmartin as M


def preparar(escenario="+ TC del MMM", ipm=0.0267):
    nombre = {n: (p, fx, ip) for n, p, fx, ip in F.ESC}
    params, fx, _ = nombre[escenario]
    r = F.corre(params, fx, ipm)
    cc, rep = r["cc"], Q.repartos(r["cc"]["wacc"])
    kr, kc = F.C.mult_ipm(ipm)
    _v, det = Q.flujo(r["ppdi"], r["ref"], r["nec"], cc["kd"], cc["wacc"],
                      round(cc["ke"], 4), rep, kr, kc,
                      (fx - M.FX_LIBRO) * M.REEMB_USD)
    # perfiles: la forma anual de cada pago por unidad de su incognita, para que
    # el Excel pueda escalarlos con una formula en vez de numeros pegados
    perfil = {c: [v / r["ref"] if r["ref"] else 0.0 for v in det[c]]
              for c in ("pfij", "pvar")}
    return {"inputs": {"ke": cc["ke"], "kd": cc["kd"], "wacc": cc["wacc"],
                       "tir": round(cc["ke"], 4), "rcsd": Q.RCSD,
                       "crsd": Q.CRSD_OBJ, "ir": Q.IR, "pt": Q.PT,
                       "arr": Q.BASE_ARR, "ipm": ipm, "fx": fx, "cuotas": 60,
                       "ppdi": r["ppdi"], "ref": r["ref"]},
            "anio": det["anio"], "det": det,
            "perfil_ppdi": [v / r["ppdi"] if r["ppdi"] else 0.0
                            for v in det["ppdi"]],
            "perfil": perfil, "pct_capex": M.K["pct_capex"],
            "ppdmo_hito": r["phito"], "precio": r["precio"]}


if __name__ == "__main__":
    d = preparar()
    ruta = EX.escribir(d, "/mnt/project-files/generador/PTAR_San_Martin_generado.xlsx")
    print("escrito:", ruta)
    print(f"  PPDI anual          {d['inputs']['ppdi']:>18,.4f}")
    print(f"  PPDMO referencia    {d['inputs']['ref']:>18,.4f}")
    print(f"  precio unitario     {d['precio']:>18,.6f}")
