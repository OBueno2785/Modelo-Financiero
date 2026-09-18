"""Cierre del PPDMO del modelo de Hitos Funcionales (PTAR San Martin).

El libro lo resuelve con Solver sobre Control!C49 (referencia mensual de pagos
en operacion) contra FC!D80 = VAN del flujo de caja financiero descontado a la
TIR objetivo = 0.  Aqui se reproduce el bloque anual completo (ingresos, costos,
capex, impuestos, servicio de deuda y CRSD) y se cierra por biseccion.
"""
import json
import motor_sanmartin as M

A = json.load(open("sanmartin_anual.json"))
FC, IMP, DA, INGM, E = A["fc"], A["imp"], A["da"], A["ing_m"], A["esc"]
NY = E["ny"]
f = lambda d, r: d[str(r)]

fop  = f(FC, 8)           # flag operacion
fdc  = f(FC, 6)           # flag D+C+PM
fcon = f(FC, 10)          # flag contrato
IR, PT = E["ir"], E["pt"]
RCSD, CRSD_OBJ = E["rcsd"], E["crsd_obj"]
BASE_ARR, PLAZO_GF = E["base_arrastre"], E["plazo_amort_gf"]

# ---- repartos del PPDMO: dependen del Ke por el VAN de los costos de O&M ----
def repartos(ke_anual):
    km = (1 + ke_anual) ** (1 / 12) - 1
    off = E["off_ing"]
    n = len(INGM["62"])
    van = lambda s: sum(s[j] / (1 + km) ** (j - off + 1) for j in range(off, n))
    v = {r: van(INGM[str(r)]) for r in (62, 63, 64, 65, 66, 67)}
    tar, sjs = v[62] + v[63] + v[64], v[65]
    d83 = (tar + v[66]) / (tar + sjs + v[66] + v[67])
    d84 = (sjs + v[67]) / (tar + sjs + v[66] + v[67])
    d87 = v[66] / (tar + v[66])
    d88 = v[67] / (sjs + v[67])
    kfix = d83 * (1 - d87) + d84 * (1 - d88)
    kvar = d83 * d87 + d84 * d88
    return dict(d83=d83, d84=d84, d87=d87, d88=d88, kfix=kfix, kvar=kvar,
                e=[v[62] / tar, v[63] / tar, v[64] / tar])

R0 = repartos(E["ke_anual"])
KFIX0 = E["d83"] * (1 - E["d87"]) + E["d84"] * (1 - E["d88"])
KVAR0 = E["d83"] * E["d87"] + E["d84"] * E["d88"]
REF0, PPDI0 = E["ref_ppdmo"], E["ppdi_anual"]

# series del libro que se reescalan
ppdi_b  = [sum(f(FC, r)[i] for r in (14, 15, 16, 17)) for i in range(NY)]
pfij_b  = [sum(f(FC, r)[i] for r in (18, 19, 20, 21)) for i in range(NY)]
pvar_b  = f(FC, 22)
cxc_b   = f(FC, 96)
int_dc_b, com_dc_b = sum(f(DA, 27)), sum(f(DA, 31))


def anual_por_year(mensual, anios, anio0=2025):
    out = [0.0] * NY
    for t, v in enumerate(mensual):
        i = anios[t] - anio0
        if 0 <= i < NY:
            out[i] += v
    return out


def flujo(ppdi_anual, ref, nec, kd_anual, ke_anual, tir_obj, rep,
          kr=None, kc=None, fx_aj=0.0, iteraciones=80):
    """Construye el flujo de caja anual completo y devuelve el VAN del FCF."""
    an = M.S["anio"]
    desem  = anual_por_year(nec["desemb"], an)
    aporte = anual_por_year([-a for a in nec["aporte"]], an)
    int_dc = anual_por_year([-v for v in nec["inter"]], an)
    com_dc = anual_por_year([-v for v in nec["comis"]], an)
    gf_tot = sum(nec["inter"])

    kp = ppdi_anual / PPDI0
    kf = (ref * rep["kfix"]) / (REF0 * KFIX0)
    kv = (ref * rep["kvar"]) / (REF0 * KVAR0)

    kr = kr or [1.0] * NY
    kc = kc or [1.0] * NY
    ppdi = [ppdi_b[i] * kp for i in range(NY)]
    pfij = [pfij_b[i] * kf * kr[i] for i in range(NY)]
    pvar = [pvar_b[i] * kv * kr[i] for i in range(NY)]
    cst = {r: [f(FC, r)[i] * kc[i] for i in range(NY)] for r in (24, 25, 26, 27, 28, 38)}
    # el reembolso a BID y Proinversion se paga en dolares: el tipo de cambio
    # lo mueve en el ano 0, dentro de "otros costos del periodo D+C+PM"
    r35 = [f(FC, 35)[i] - (fx_aj if i == 0 else 0.0) for i in range(NY)]

    # capital de trabajo: la CxC sigue a los ingresos devengados
    dev_b = [pfij_b[i] + pvar_b[i] for i in range(NY)]
    dev   = [pfij[i] + pvar[i] for i in range(NY)]
    cxc = [cxc_b[i] * (dev[i] / dev_b[i]) if dev_b[i] else 0.0 for i in range(NY)]
    aj99 = [cxc[i] * (fop[i] > 0 and (i + 1 >= NY or fop[i + 1] == 0)) for i in range(NY)]
    r98 = [(cxc[i - 1] if i else 0.0) - cxc[i] - (aj99[i - 1] if i else 0.0)
           for i in range(NY)]
    varkt = [r98[i] + aj99[i] + f(FC, 104)[i] + f(FC, 105)[i] for i in range(NY)]

    # amortizacion tributaria de los gastos financieros de construccion
    gf_am = [f(IMP, 70)[i] * (gf_tot / int_dc_b * -1 if int_dc_b else 0) for i in range(NY)]
    gf_am = [f(IMP, 70)[i] * (gf_tot / sum(f(IMP, 68))) for i in range(NY)]

    ir_a = [0.0] * NY
    pt_a = [0.0] * NY
    amort = [0.0] * NY
    int_op = [0.0] * NY
    crsd_dot = [0.0] * NY
    crsd_des = [0.0] * NY
    prim_dot = [0.0] * NY

    for _ in range(iteraciones):
        fc_op = [ppdi[i] + pfij[i] + pvar[i] + f(FC, 23)[i]
                 + sum(cst[r][i] for r in (24, 25, 26, 27, 28))
                 + varkt[i] + f(FC, 119)[i] for i in range(NY)]
        fc_40 = [fc_op[i] + f(FC, 34)[i] + r35[i] + f(FC, 36)[i] + f(FC, 37)[i]
                 + cst[38][i] for i in range(NY)]
        fc_45 = [fc_40[i] - ir_a[i] - pt_a[i] for i in range(NY)]
        fc_50 = [fc_45[i] + aporte[i] + desem[i] for i in range(NY)]

        # --- bloque de deuda ---
        # vencimiento: el ultimo ano con pago del PPDI
        ven = max((i for i in range(NY) if ppdi[i] > 0), default=NY - 1)
        n_am, n_io, n_dot, n_des, n_pri = ([0.0] * NY for _ in range(5))
        saldo, crsd_s = 0.0, 0.0
        sfin = [0.0] * NY
        for i in range(NY):
            ini = saldo
            dis = desem[i]
            serv = (fc_50[i] - prim_dot[i]) * (fop[i] > 0)
            maxsd = serv / RCSD
            io = -kd_anual * (ini + dis + amort[i] / 4) * fop[i]
            am = -min(ini, max(0.0, maxsd + io)) * (fop[i] > 0.5)
            # Mismo cierre que `flujo_sm`: al vencimiento se cancela el saldo.
            # Con coberturas altas el flujo no alcanza para amortizar y, sin
            # esto, el saldo sobrevive pagando intereses sin devolver nunca el
            # principal. A RCSD 1.25 vale cero y el libro sale igual.
            if i == ven:
                am = -(ini + dis)
            n_io[i], n_am[i] = io, am
            saldo = ini + dis + am
            sfin[i] = saldo
        serv_op = [-n_am[i] - n_io[i] for i in range(NY)]
        for i in range(NY):
            obj = serv_op[i + 1] * CRSD_OBJ * (fop[i + 1] == 1) if i + 1 < NY else 0.0
            ini = crsd_s
            n_dot[i] = obj - ini if ini < obj else 0.0
            n_des[i] = -(ini - obj) if ini > obj else 0.0
            crsd_s = ini + n_dot[i] + n_des[i]
            n_pri[i] = obj * (fdc[i] > 0 and (i + 1 >= NY or fdc[i + 1] == 0))

        # --- impuestos ---
        n_ir, n_pt = [0.0] * NY, [0.0] * NY
        arr = 0.0
        for i in range(NY):
            res = (ppdi[i] + pfij[i] + pvar[i] + f(FC, 23)[i]
                   + sum(cst[r][i] for r in (24, 25, 26, 27, 28))
                   + f(FC, 37)[i] + cst[38][i]
                   + n_io[i] + (com_dc[i])
                   - f(IMP, 61)[i] - gf_am[i] + r35[i])
            p = max(0.0, PT * res) * (fop[i] > 0)
            base = res - p
            util = max(0.0, base) * BASE_ARR
            ini_a = arr if arr > 0 else 0.0
            inc = -min(0.0, base)
            red = -max(0.0, min(util, ini_a)) * (ini_a > 0)
            arr = ini_a + inc + red
            n_ir[i] = IR * max(0.0, base + red)
            n_pt[i] = p

        dif = max(max(abs(a - b) for a, b in zip(x, y)) for x, y in
                  [(ir_a, n_ir), (pt_a, n_pt), (amort, n_am), (int_op, n_io),
                   (prim_dot, n_pri)])
        ir_a, pt_a, amort, int_op = n_ir, n_pt, n_am, n_io
        crsd_dot, crsd_des, prim_dot = n_dot, n_des, n_pri
        if dif < 1e-6:
            break

    com_op = [0.0] * NY
    fc_56 = [fc_50[i] + int_op[i] + int_dc[i] + amort[i] + com_dc[i] + com_op[i]
             for i in range(NY)]
    fc_58 = [-(crsd_dot[i] + crsd_des[i]) for i in range(NY)]
    fc_60 = [fc_56[i] + fc_58[i] for i in range(NY)]
    fcf = [-aporte[i] + fc_60[i] for i in range(NY)]

    per, acc = [], 0.0
    for i in range(NY):
        acc += fcon[i]
        per.append(acc)
    van = sum(fcf[i] / (1 + tir_obj) ** per[i] for i in range(NY))
    return van, dict(fcf=fcf, fc_40=fc_40, fc_45=fc_45, fc_50=fc_50, fc_60=fc_60,
                     ir=ir_a, pt=pt_a, amort=amort, int_op=int_op,
                     int_dc=int_dc, com_dc=com_dc, aporte=aporte, desem=desem,
                     ppdi=ppdi, pfij=pfij, pvar=pvar, per=per,
                     # series que necesita el escritor de Excel
                     costo_om=[sum(cst[r][i] for r in (24, 25, 26, 27, 28))
                               for i in range(NY)],
                     otros_dcpm=[f(FC, 34)[i] + r35[i] + f(FC, 36)[i]
                                 + f(FC, 37)[i] + cst[38][i] for i in range(NY)],
                     # las cinco patas de otros_dcpm, abiertas para el libro
                     capex=f(FC, 34), otros_dc=r35, igv_dc=f(FC, 36),
                     laguna=f(FC, 37), repex=cst[38],
                     pago_obras=f(FC, 23), varkt=varkt, otros_op=f(FC, 119),
                     crsd=[-(crsd_dot[i] + crsd_des[i]) for i in range(NY)],
                     fc_op=fc_op, anio=[2025 + i for i in range(NY)])


def cerrar(ppdi_anual, nec, kd, ke_wacc, ke_eq, tir_obj, rep,
           kr=None, kc=None, fx_aj=0.0, lo=1.0, hi=5e7, it=90):
    # Ver el comentario de `motor_cajamarca.cerrar`: sin cambio de signo esto
    # devolveria el borde del intervalo como si fuera el cierre.
    f = lambda m: flujo(ppdi_anual, m, nec, kd, ke_wacc, tir_obj, rep,
                        kr, kc, fx_aj)[0]
    if f(lo) * f(hi) > 0:
        raise ValueError(
            f"la referencia no cierra en [{lo:,.2f}, {hi:,.2f}]: "
            f"VAN {f(lo):,.2f} y {f(hi):,.2f}, sin cambio de signo")
    for _ in range(it):
        m = (lo + hi) / 2
        v, _d = flujo(ppdi_anual, m, nec, kd, ke_wacc, tir_obj, rep, kr, kc, fx_aj)
        if v > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


if __name__ == "__main__":
    nec = M.necesidades(M.K["kd"])
    P, _van, _ = M.ppdi_anual(M.K["wacc_anual"], M.K["kd"])
    van0, det = flujo(P, REF0, nec, M.K["kd"], M.K["wacc_anual"],
                      E["tir_objetivo"], R0)
    print("VALIDACION del bloque anual, con la referencia del libro")
    print(f"  VAN FCF calculado   : {van0:20,.2f}")
    print(f"  VAN FCF del libro   : {E['van_fcf_libro']:20,.2f}")
    # Las seis lineas sobre TODA la concesion, no solo el ano 1: un ajuste de
    # ano 1 puede leer +-0.1 % en las tres patas y tener -18 % en la variable
    # sobre los veinte anios, con el hueco de interes cancelandolo.
    # Referencias leidas del libro, no del motor: `Cons_Anual!46` y `!47`
    # ("Total PPD MO Fijo" y "Total PPD MO Variable"), confirmadas ademas en
    # `FC!124/125`. Un control cuya referencia sale de lo que se esta probando
    # no prueba nada.
    print(f"  PPDMO pata fija     : {sum(det['pfij']):20,.2f}  vs {1139027113.51:,.2f}")
    print(f"  PPDMO pata variable : {sum(det['pvar']):20,.2f}  vs {383922299.79:,.2f}")
    print(f"  IR total            : {sum(det['ir']):20,.2f}  vs {188359633.5256:,.2f}")
    print(f"  Part. trabajadores  : {sum(det['pt']):20,.2f}  vs {35545679.5018:,.2f}")
    print(f"  Intereses operacion : {sum(det['int_op']):20,.2f}  vs {-465238895.9083:,.2f}")
    print(f"  Amortizacion        : {sum(det['amort']):20,.2f}  vs {-558486229.4540:,.2f}")
    print(f"  FC libre concesion. : {sum(det['fc_60']):20,.2f}  vs {589769156.1280:,.2f}")
    print(f"  FCF total           : {sum(det['fcf']):20,.2f}  vs {450147598.7645:,.2f}")
