"""Flujo anual del esquema por hitos, armado linea por linea.

Es el equivalente de `flujo_cajamarca` para San Martin: sustituye al atajo de
`motor_ppdmo_sm`, que reescalaba las filas de `FC` del libro, por el calculo de
cada linea a partir de la plantilla. Con eso un proyecto nuevo con pago por
hitos produce su propio flujo y no una version escalada del modelo aprobado.

Lo que arma, y de donde sale cada cosa:

  pagos           `ingresos_sm`, a partir de la referencia del PPDMO y del PPDI
  costos de O&M   `opex_sm`, precios constantes de la plantilla mas el indice
  CAPEX y otros   la plantilla, via `motor_sanmartin`
  deuda           bloque anual por cobertura, RCSD con cuenta de reserva
  tributos        `tributos_sm` mas el arrastre de perdidas, aqui dentro
  capital de trab. cuentas por cobrar y por pagar, aqui dentro
"""
import ingresos_sm as I
import opex_sm as O
import tributos_sm as T

CLAVES_COSTO = ("fijo_h1", "fijo_h2", "fijo_h3", "fijo_h4", "variable",
                "gg_u", "otros_op", "igv_op")


def _anual(mensual, anio_mes, ny, anio0=2025):
    out = [0.0] * ny
    for t, v in enumerate(mensual):
        i = int(anio_mes[t]) - anio0
        if 0 <= i < ny:
            out[i] += v
    return out


def flujo(ref, ppdi, ent, iteraciones=120):
    """`ent` trae todo lo que no depende de la incognita; ver `preparar`."""
    ny, cal = ent["ny"], ent["cal"]
    anio_mes, anio0 = cal["anio"], ent["anio0"]
    fop, fdc, fcon = ent["fop"], ent["fdc"], ent["fcon"]
    kd, tir = ent["kd"], ent["tir"]
    IR, PT, RCSD, CRSD_OBJ, ARR = (ent["ir"], ent["pt"], ent["rcsd"],
                                   ent["crsd_obj"], ent["base_arrastre"])
    # Regimen de la APP. En autofinanciada no hay PPDI ni PPDMO: la obra es
    # activo intangible (CINIIF 12 p.17) y la incognita del cierre es la tarifa
    # al usuario. Todo lo demas (calendario, necesidades, aportes, deuda por
    # cobertura, CRSD, arrastre) es identico, y por eso va en el mismo motor.
    AUTO = str(ent.get("regimen", "cofinanciada")).lower().startswith("auto")

    # --- pagos ---
    pg = I.pagos(ref, ent["rep"], ent["carga_1"], ent["carga_2"],
                 ent["corr_1"], ent["corr_2"], cal, ent["ipm"],
                 ke_mensual=ent["ke_mensual"], anio0=anio0)
    ppdi_m = [ppdi * ent["pct_ppdi"] * cal["flag_pago"][t] / 4
              for t in range(cal["n"])]
    pfij_m = [sum(pg["cobro"][h][t] for h in range(4)) for t in range(cal["n"])]
    pvar_m = pg["cobro"][4]
    ppdi_a = _anual(ppdi_m, anio_mes, ny, anio0)
    pfij_a = _anual(pfij_m, anio_mes, ny, anio0)
    pvar_a = _anual(pvar_m, anio_mes, ny, anio0)

    # --- capital de trabajo: cuentas por cobrar y por pagar ---
    ppdmo_m = [pfij_m[t] + pvar_m[t] for t in range(cal["n"])]
    conc = [ppdi_m[t] + ppdmo_m[t] for t in range(cal["n"])]
    cj = I.caja(ppdi_m, ppdmo_m, cal, ent["desfase_ppdi"], ent["desfase_ppdmo"],
                conc)
    cxc = _anual(cj["cxc"], anio_mes, ny, anio0)
    # El IGV de operacion solo es costo cuando no hay contra que acreditarlo.
    # San Martin esta bajo la ley de la Amazonia y su propio libro lo llama
    # `Opex!143 IGV no recuperable (a costos)`, 69,668,080.69 = `FC!28`. Fuera
    # de esas zonas el PPD se cobra con IGV y el soportado se acredita, asi que
    # la linea se lava y no entra al flujo.
    k_igv = 1.0 if ent.get("exonera_igv", 1) else 0.0
    costo_om = [-(ent["costos"]["fijo_h1"][i] + ent["costos"]["fijo_h2"][i]
                  + ent["costos"]["fijo_h3"][i] + ent["costos"]["fijo_h4"][i]
                  + ent["costos"]["variable"][i] + ent["costos"]["gg_u"][i]
                  + ent["costos"]["otros_op"][i]
                  + k_igv * ent["costos"]["igv_op"][i])
                for i in range(ny)]
    # `FC!103`: los costos de O&M del ano divididos entre sus meses, por el
    # periodo medio de pago
    cxp = [(-costo_om[i] / (12 * fcon[i]) * ent["pmp"]) if fcon[i] else 0.0
           for i in range(ny)]
    aj99 = [cxc[i] * (fop[i] > 0 and (i + 1 >= ny or fop[i + 1] == 0))
            for i in range(ny)]
    aj105 = [-cxp[i] * (fop[i] > 0 and (i + 1 >= ny or fop[i + 1] == 0))
             for i in range(ny)]
    r98 = [(cxc[i - 1] if i else 0.0) - cxc[i] - (aj99[i - 1] if i else 0.0)
           for i in range(ny)]
    r104 = [cxp[i] - (cxp[i - 1] if i else 0.0) - (aj105[i - 1] if i else 0.0)
            for i in range(ny)]
    varkt = [r98[i] + aj99[i] + r104[i] + aj105[i] for i in range(ny)]
    # capital de trabajo inicial: se dota el ultimo ano de obra y se libera
    kt0 = ent["kt_inicial"]
    dot = [kt0 if (fop[i] == 0 and i + 1 < ny and fop[i + 1] > 0) else 0.0
           for i in range(ny)]
    desdot = [(dot[i - 1] if i else 0.0) for i in range(ny)]
    r119 = [-dot[i] + desdot[i] for i in range(ny)]

    # --- amortizaciones tributarias ---
    if AUTO:
        # El intangible se reconoce al termino de obra por la inversion mas los
        # intereses capitalizados (p.22) y se amortiza lineal sobre la
        # operacion. Esa amortizacion REEMPLAZA a la depreciacion del capex y a
        # la amortizacion en 10 anos de los gastos financieros de construccion:
        # los intereses ya estan dentro del activo y deducirlos por las dos
        # vias seria contarlos dos veces.
        inv = -sum(ent["capex"][i] + ent["otros_dc"][i] + ent["com_dc"][i]
                   for i in range(ny))
        cap = -sum(ent["int_dc"][i] for i in range(ny))
        n_op_m = sum(1 for t in range(cal["n"]) if cal["flag_op"][t])
        base_int = inv + cap
        amort_int_m = [base_int / n_op_m * cal["flag_op"][t]
                       for t in range(cal["n"])] if n_op_m else [0.0] * cal["n"]
        amort_capex = _anual(amort_int_m, anio_mes, ny, anio0)
        gf_am = [0.0] * ny
        intangible = {"inversion": inv, "interes_capitalizado": cap,
                      "base": base_int, "meses_operacion": n_op_m,
                      "amort_m": amort_int_m}
    else:
        amort_capex = T.amortizacion_capex(ent["capex_total"], fop,
                                           [p > 0 for p in ppdi_a])
        gf_am = T.amortizacion_gastos_fin(ent["int_dc_total"], fop,
                                          ent["plazo_gf"])
        intangible = None

    # Vencimiento de la deuda: por defecto el ultimo ano con pago del PPDI, que
    # es el horizonte contractual del proyecto. `Deuda Anual!40` del libro es
    # una SALIDA, el ultimo ano en que hubo amortizacion, no un dato.
    VEN = ent.get("ven")
    if VEN is None:
        # Sin PPDI (autofinanciada) el horizonte es el ultimo ano de operacion.
        VEN = max((i for i in range(ny) if ppdi_a[i] > 0),
                  default=max((i for i in range(ny) if fop[i] > 0),
                              default=ny - 1))

    ir_a = pt_a = amort = int_op = prim_dot = [0.0] * ny
    crsd_dot = crsd_des = [0.0] * ny
    desem, aporte = ent["desem"], ent["aporte"]
    int_dc, com_dc = ent["int_dc"], ent["com_dc"]
    obra, capex, otros_dc, igv_dc, laguna, repex = (
        ent["pago_obras"], ent["capex"], ent["otros_dc"], ent["igv_dc"],
        ent["laguna"], ent["repex"])

    for _ in range(iteraciones):
        fc_op = [ppdi_a[i] + pfij_a[i] + pvar_a[i] + obra[i] + costo_om[i]
                 + varkt[i] + r119[i] for i in range(ny)]
        fc_40 = [fc_op[i] + capex[i] + otros_dc[i] + igv_dc[i] + laguna[i]
                 + repex[i] for i in range(ny)]
        fc_45 = [fc_40[i] - ir_a[i] - pt_a[i] for i in range(ny)]
        fc_50 = [fc_45[i] + aporte[i] + desem[i] for i in range(ny)]

        n_am, n_io, n_dot, n_des, n_pri = ([0.0] * ny for _ in range(5))
        saldo, crsd_s = 0.0, 0.0
        for i in range(ny):
            ini, dis = saldo, desem[i]
            serv = (fc_50[i] - prim_dot[i]) * (fop[i] > 0)
            io = -kd * (ini + dis + amort[i] / 4) * fop[i]
            am = -min(ini, max(0.0, serv / RCSD + io)) * (fop[i] > 0.5)
            # Al vencimiento se cancela el saldo que quede. Sin esto, con
            # coberturas altas el flujo no alcanza para amortizar, el saldo
            # sobrevive hasta el fin de la concesion devengando intereses que se
            # pagan pero sin devolver nunca el principal, y el PPDMO cierra
            # artificialmente barato. A RCSD 1.25 este renglon vale cero, porque
            # el libro ya repaga entero en 2042 (`Deuda Anual!40`, Ultimo
            # Repago) antes del ultimo PPDI, asi que la validacion no lo ve.
            if i == VEN:
                am = -(ini + dis)
            n_io[i], n_am[i] = io, am
            saldo = ini + dis + am
        serv_op = [-n_am[i] - n_io[i] for i in range(ny)]
        for i in range(ny):
            obj = serv_op[i + 1] * CRSD_OBJ * (fop[i + 1] == 1) if i + 1 < ny else 0.0
            ini = crsd_s
            n_dot[i] = obj - ini if ini < obj else 0.0
            n_des[i] = -(ini - obj) if ini > obj else 0.0
            crsd_s = ini + n_dot[i] + n_des[i]
            n_pri[i] = obj * (fdc[i] > 0 and (i + 1 >= ny or fdc[i + 1] == 0))

        n_ir, n_pt, arr = [0.0] * ny, [0.0] * ny, 0.0
        for i in range(ny):
            res = (ppdi_a[i] + pfij_a[i] + pvar_a[i] + obra[i] + costo_om[i]
                   + laguna[i] + repex[i] + n_io[i] + com_dc[i]
                   - amort_capex[i] - gf_am[i] + otros_dc[i])
            p = max(0.0, PT * res) * (fop[i] > 0)
            base = res - p
            util = max(0.0, base) * ARR
            ini_a = arr if arr > 0 else 0.0
            red = -max(0.0, min(util, ini_a)) * (ini_a > 0)
            arr = ini_a - min(0.0, base) + red
            n_ir[i] = IR * max(0.0, base + red)
            n_pt[i] = p

        dif = max(max(abs(a - b) for a, b in zip(x, y)) for x, y in
                  [(ir_a, n_ir), (pt_a, n_pt), (amort, n_am), (int_op, n_io),
                   (prim_dot, n_pri)])
        ir_a, pt_a, amort, int_op = n_ir, n_pt, n_am, n_io
        crsd_dot, crsd_des, prim_dot = n_dot, n_des, n_pri
        if dif < 1e-6:
            break

    fc_56 = [fc_50[i] + int_op[i] + int_dc[i] + amort[i] + com_dc[i]
             for i in range(ny)]
    fc_58 = [-(crsd_dot[i] + crsd_des[i]) for i in range(ny)]
    fcf = [-aporte[i] + fc_56[i] + fc_58[i] for i in range(ny)]

    per, acc = [], 0.0
    for i in range(ny):
        acc += fcon[i]
        per.append(acc)
    van = sum(fcf[i] / (1 + tir) ** per[i] for i in range(ny))
    return {"van": van, "fcf": fcf, "per": per, "fc_op": fc_op, "fc_40": fc_40,
            "fc_45": fc_45, "fc_50": fc_50, "ppdi": ppdi_a, "pfij": pfij_a,
            "pvar": pvar_a, "costo_om": costo_om, "varkt": varkt, "cxc": cxc,
            "ir": ir_a, "pt": pt_a, "amort": amort, "int_op": int_op,
            "crsd": fc_58, "precio": pg["precio"], "r119": r119,
            "amort_capex": amort_capex, "gf_am": gf_am,
            "intangible": intangible, "ingreso": pvar_a if AUTO else None}


def cerrar(ppdi, ent, lo=1.0, hi=5e7, it=90):
    for _ in range(it):
        m = (lo + hi) / 2
        if flujo(m, ppdi, ent)["van"] > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2
