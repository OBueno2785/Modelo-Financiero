"""Hoja `Ingresos` de San Martin reconstruida: los pagos mes a mes.

Reemplaza las filas 14 a 22 de `FC` (que hasta ahora se reescalaban del libro)
por su calculo real, para que un proyecto nuevo con pago por hitos pueda
generarlas desde la plantilla.

Las reglas del libro que hay detras, y que no son obvias:

  * La referencia mensual del PPDMO se reparte entre las cuatro patas fijas y la
    variable con los VAN de los seis flujos de O&M (`Ingresos!71:76`): primero
    entre los dos sistemas (`D83`, `D84`) y dentro de cada sistema entre fijo y
    variable (`D87`, `D88`). El reparto depende del Ke, asi que se recalcula
    cuando cambia el costo de capital.
  * El precio unitario NO es un dato: sale de la parte variable de la referencia
    dividida por la carga organica de referencia de los dos sistemas
    (`Ingresos!D109`).
  * El devengo es mensual y el cobro trimestral, con un ajuste en el ultimo
    periodo que paga el residuo (`Ingresos!17` y `131:135`).
"""
import calendario_sm as C
import ipm_sm as IPM


def referencias(ref, rep, corr_tar, corr_sjs):
    """`Ingresos!D94:D97` y `D109`, a partir de la referencia y los repartos."""
    e = rep["e"]
    base = ref * rep["d83"] * (1 - rep["d87"])
    fijo = [base * e[0], base * e[1], base * e[2],
            ref * rep["d84"] * (1 - rep["d88"])]
    precio = ((ref * rep["d83"] * rep["d87"]) + (ref * rep["d84"] * rep["d88"])) \
        / (corr_tar + corr_sjs) * 12
    return fijo, precio


SEIS = ("conigv_h1", "conigv_h2", "conigv_h3", "conigv_h4",
        "conigv_var_tar", "conigv_var_sjs")


def repartos(mensual, tasa_anual, off=0):
    """`Ingresos!D83`, `D84`, `D87`, `D88` y el reparto de las tres patas fijas
    del sistema 1, calculados con los costos de O&M **del proyecto**.

    El libro los saca de `Ingresos!71:76 = NPV($D$80, P62:MC62)`: el VAN de los
    seis flujos de O&M **con IGV**, descontados a la tasa de `Ingresos!D80`.
    Esa celda apunta a `Ke!C25`, que pese al nombre de la hoja es el **WACC**
    (9.951300 % en el libro; el Ke de verdad es `Ke!C23`, 11.896982 %).

    Dos detalles que se ven al reproducirlo:

      * Los cuatro porcentajes son cocientes, asi que el mes al que se ancla el
        VAN se cancela. Lo que no se cancela es el perfil relativo, que es
        propio de cada proyecto: es la razon de calcular esto aca y no leerlo
        del libro.
      * Las series tienen que ser las `conigv_*`. En el libro el IGV no es 18 %
        sobre todo, sino un coeficiente por linea (0.411 en los fijos 1 a 3,
        0.4298 en el 4, 0.283 en el variable del sistema 1 y 0.1771 en el del
        2), y las patas variables llevan bastante menos que las fijas: repartir
        sin IGV corre medio punto de peso hacia lo variable.
    """
    km = (1 + tasa_anual) ** (1 / 12) - 1
    def van(s):
        return sum(s[j] / (1 + km) ** (j - off + 1) for j in range(off, len(s)))
    faltan = [k for k in SEIS if k not in mensual]
    if faltan:
        raise KeyError(f"faltan series de O&M con IGV para repartir el PPDMO: "
                       f"{', '.join(faltan)}")
    v = {k: van(mensual[k]) for k in SEIS}
    tar = v["conigv_h1"] + v["conigv_h2"] + v["conigv_h3"]
    sjs, vt, vs = v["conigv_h4"], v["conigv_var_tar"], v["conigv_var_sjs"]
    tot = tar + sjs + vt + vs
    if tot <= 0:
        raise ValueError("los costos de O&M del proyecto suman cero: no hay con "
                         "que repartir el PPDMO entre las patas fija y variable")
    d83, d84 = (tar + vt) / tot, (sjs + vs) / tot
    d87 = vt / (tar + vt) if tar + vt else 0.0
    d88 = vs / (sjs + vs) if sjs + vs else 0.0
    e = ([v["conigv_h1"] / tar, v["conigv_h2"] / tar, v["conigv_h3"] / tar]
         if tar else [0.0, 0.0, 0.0])
    return dict(d83=d83, d84=d84, d87=d87, d88=d88, e=e,
                kfix=d83 * (1 - d87) + d84 * (1 - d88),
                kvar=d83 * d87 + d84 * d88)


def carga_mensual(carga_anual, anio, flag_dcpm, flag_op, anio0=2025):
    """`Ingresos!105:106`: la carga anual repartida por doceavos, mientras corre
    el contrato. Ojo: cuenta tambien la construccion, no solo la operacion."""
    n = len(anio)
    return [carga_anual[int(anio[t]) - anio0] / 12 * (flag_dcpm[t] + flag_op[t])
            if 0 <= int(anio[t]) - anio0 < len(carga_anual) else 0.0
            for t in range(n)]


def pagos(ref, rep, carga_tar, carga_sjs, corr_tar, corr_sjs, cal, ipm,
          frecuencia=3, anio0=2025, ke_mensual=None):
    """Las cinco series de pago, mensuales (devengo) y trimestrales (cobro)."""
    n = cal["n"]
    anio = cal["anio"]
    fop = cal["flag_op"]
    fdc = cal["flag_dcpm"]
    f11, _ = IPM.factores(ipm, C.ventana_reajuste(cal))
    fijo_ref, precio = referencias(ref, rep, corr_tar, corr_sjs)

    c_tar = carga_mensual(carga_tar, anio, fdc, fop, anio0)
    c_sjs = carga_mensual(carga_sjs, anio, fdc, fop, anio0)
    carga = [c_tar[t] + c_sjs[t] for t in range(n)]

    # `Ingresos!112:116`, el devengo mensual
    dev = [[fijo_ref[h] * f11[t] * fop[t] for t in range(n)] for h in range(4)]
    dev.append([precio * f11[t] * carga[t] * fop[t] for t in range(n)])

    # `Ingresos!16` y `!17`: mes de cobro y ajuste del ultimo periodo
    mes_cal = [t % 12 + 1 for t in range(n)]
    f16 = [1.0 if (mes_cal[t] % frecuencia == 0 and fop[t] > 0) else 0.0
           for t in range(n)]
    f17 = [1.0 if (fop[t] == 1 and (t + 1 >= n or fop[t + 1] == 0) and f16[t] == 0)
           else 0.0 for t in range(n)]

    # El ultimo pago cae fuera de trimestre y el libro lo descuenta hasta el
    # cierre de trimestre siguiente (`Ingresos!118:123`): el plazo son los meses
    # que faltan para ese cierre y la tasa es el Ke mensual del reparto.
    desc = 1.0
    if ke_mensual:
        u = next((t for t in range(n) if f17[t]), None)
        if u is not None:
            faltan = (frecuencia - mes_cal[u] % frecuencia) % frecuencia
            desc = (1 + ke_mensual) ** -faltan

    cobro = []
    for serie in dev:
        total, acum, out = sum(serie), 0.0, [0.0] * n
        for t in range(n):
            ventana = sum(serie[max(0, t - frecuencia + 1):t + 1])
            out[t] = ventana * f16[t] + (total - acum) * desc * f17[t]
            acum += ventana * f16[t] + (total - acum) * f17[t]
        cobro.append(out)
    return {"devengo": dev, "cobro": cobro, "precio": precio,
            "fijo_ref": fijo_ref, "carga": carga, "f16": f16, "f17": f17}


def caja(cobro_ppdi, cobro_ppdmo, cal, desfase_ppdi=1, desfase_ppdmo=3,
         total_conc=None):
    """`Ingresos!154:161`: el cobro efectivo y la cuenta por cobrar.

    El PPDI y el PPDMO se cobran con desfases distintos, un mes y un trimestre,
    y la cuenta por cobrar de diciembre es lo devengado y no cobrado.
    """
    n = cal["n"]
    fop = cal["flag_op"]
    mes_cal = [t % 12 + 1 for t in range(n)]

    def _caja(serie, d, ultimo):
        cja, cxc = [0.0] * n, [0.0] * n
        for t in range(n):
            prev = serie[t - d] if t - d >= 0 else 0.0
            fin = fop[t] == 1 and (t + 1 >= n or fop[t + 1] == 0)
            cja[t] = prev * fop[t] + (ultimo[t] if fin else 0.0)
            if mes_cal[t] == 12:
                cxc[t] = sum(serie[max(0, t - d + 1):t + 1])
        return cja, cxc

    c1, x1 = _caja(cobro_ppdi, desfase_ppdi, cobro_ppdi)
    ult = total_conc if total_conc is not None else cobro_ppdmo
    c2, x2 = _caja(cobro_ppdmo, desfase_ppdmo, ult)
    return {"caja_ppdi": c1, "cxc_ppdi": x1, "caja_ppdmo": c2, "cxc_ppdmo": x2,
            "cxc": [x1[t] + x2[t] for t in range(n)]}
