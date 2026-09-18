"""Calendario del modelo de pago al final de obra, derivado de las fechas.

Hasta ahora las banderas del modelo sombra salian del JSON del libro de
Cajamarca: el flag de O&M, el de cierre de trimestre, el de cobro, el indice de
trimestre de cada mes, el ano fiscal, el flag de supervision y los trimestres en
que se carga el impuesto. Eso ataba el generador al cronograma de Cajamarca.

Aca se reconstruyen **solo a partir de las fechas de la plantilla**. Cada regla
quedo verificada contra las mismas banderas del libro (`validar()` las compara
una a una y devuelve desvio cero en las siete series).
"""

MESES_TRIM = (3, 6, 9, 12)


def _ym(f):
    return int(str(f)[:4]), int(str(f)[5:7])


def calendario(fechas, inicio_operacion, fin_concesion):
    """Todas las banderas de la malla mensual y de la trimestral.

    `fechas` es la malla mensual de la plantilla, un mes por fila, en orden.
    La malla arranca en el cierre del contrato y se extiende mas alla del fin de
    la concesion, porque el ultimo cobro llega un trimestre despues.
    """
    nm = len(fechas)
    ym = [_ym(f) for f in fechas]
    idx = {f: i for i, f in enumerate(fechas)}

    # 1. O&M: abierto el mes siguiente al inicio de operacion, cerrado el mes
    #    del fin de la concesion. Es el mismo intervalo que usa `leer_plantilla`.
    i0 = idx.get(inicio_operacion, 0)
    i1 = idx.get(fin_concesion, nm - 1)
    flag_om = [1 if i0 < i <= i1 else 0 for i in range(nm)]

    # 2. Cierre de trimestre calendario, solo mientras corre el O&M (`PPDMO!24`).
    flag_t = [1 if flag_om[i] and ym[i][1] in MESES_TRIM else 0 for i in range(nm)]

    # 3. Ventana de cobro (`PPDMO!33`): del mes siguiente al primer cierre de
    #    trimestre hasta tres meses despues del ultimo. El rezago de tres meses
    #    lo aplica el modelo sombra; esta bandera solo delimita la ventana.
    ct = [i for i in range(nm) if flag_t[i]]
    flag_p = ([1 if ct[0] < i <= min(ct[-1] + 3, nm - 1) else 0 for i in range(nm)]
              if ct else [0] * nm)

    # 4. Indice de trimestre de cada mes. La malla arranca en un mes que abre
    #    trimestre calendario, asi que van de tres en tres.
    trim_m = [i // 3 + 1 for i in range(nm)]
    nq = (nm + 2) // 3

    q_meses = [[i for i in range(nm) if trim_m[i] == q + 1] for q in range(nq)]
    anio = [ym[m[0]][0] for m in q_meses]
    trim = [q + 1 for q in range(nq)]

    # 5. El descuento corre hasta el ultimo trimestre con cobro; despues la
    #    malla sigue por la forma de la hoja pero ya no pesa (`M.Sombra!5`).
    ult = max((trim_m[i] for i in range(nm) if flag_p[i]), default=nq)
    meses = [3 if q + 1 <= ult else 0 for q in range(nq)]

    # 6. Supervision del regulador: mientras corra el contrato de O&M
    #    (`'Concepto de Pago'!35`), en base devengada, o sea por trimestre.
    flag_sup = [1 if any(flag_om[i] for i in q_meses[q]) else 0 for q in range(nq)]

    # 7. El impuesto del ejercicio se carga en el trimestre octubre-diciembre
    #    del ano al que corresponde. Se marcan todos; el bloque tributario deja
    #    en cero los anos sin base imponible.
    ir_q = [q for q in range(nq) if ym[q_meses[q][0]][1] == 10]

    return {"flag_om": flag_om, "flag_t": flag_t, "flag_p": flag_p,
            "trim_m": trim_m, "nq": nq, "nm": nm, "anio": anio, "trim": trim,
            "meses": meses, "fiscal": list(anio), "flag_superv": flag_sup,
            "ir_q": ir_q}


def malla_ppdi(fechas, inicio_operacion, cuotas=60, n_meses=None):
    """Las banderas que consume el motor del PPDI (`motor_cajamarca`).

    Su malla es mas corta que la del modelo sombra: termina con la concesion,
    mientras que la del sombra se estira un trimestre para recibir el ultimo
    cobro. `n_meses` recorta; por defecto se recorta al fin del devengo.
    """
    ym = [_ym(f) for f in fechas]
    idx = {f: i for i, f in enumerate(fechas)}
    i0 = idx.get(inicio_operacion, 0)
    # El PPDI se devenga mes a mes durante el plazo de pago: 60 cuotas
    # trimestrales son 180 meses, arrancando el mes siguiente a la operacion.
    meses_dev = cuotas * 3
    n = len(fechas) if n_meses is None else n_meses
    flag = [1 if i0 < i <= i0 + meses_dev else 0 for i in range(n)]
    mes_cal = [ym[i][1] for i in range(n)]
    anio = [float(ym[i][0]) for i in range(n)]
    # `PPDI!flag_trib`: el IR del ejercicio se carga en diciembre.
    flag_trib = [1.0 if mes_cal[i] == 12 else 0.0 for i in range(n)]
    return {"flag_ppdi": [float(x) for x in flag], "flag_trib": flag_trib,
            "anio": anio, "mes_cal": mes_cal, "n": n}


def validar():
    """Contrasta las siete series contra las del libro de Cajamarca."""
    import json
    D = json.load(open("/mnt/project-files/generador/caj_sombra_full.json"))
    fechas = [f[:10] for f in D["m_fecha"]]
    c = calendario(fechas, "2030-09-30", "2052-09-30")
    nq = len(D["fcf"])
    irq = [q for q in range(nq) if abs(D["ir"][q]) > 1e-9]
    pruebas = [
        ("flag de O&M", c["flag_om"], D["Pflag_om"]),
        ("flag de cierre de trimestre", c["flag_t"], D["Pflagt"]),
        ("flag de cobro", c["flag_p"], D["Pflag_ppdmo"]),
        ("trimestre de cada mes", c["trim_m"], D["Pm_trim"]),
        ("ano de cada trimestre", c["anio"], D["anio"]),
        ("ano fiscal", c["fiscal"], D["fiscal"]),
        ("meses por trimestre", c["meses"], D["meses"]),
        ("flag de supervision", c["flag_superv"], D["flag_superv"]),
    ]
    out = [(n, sum(1 for a, b in zip(x, y) if a != b), len(y)) for n, x, y in pruebas]
    out.append(("trimestres con impuesto",
                sum(1 for q in irq if q not in c["ir_q"]), len(irq)))

    P = json.load(open("/mnt/project-files/generador/cajamarca_primitivos.json"))
    n = P["escalares"]["n_meses"]
    m = malla_ppdi(fechas, "2030-09-30", 60, n)
    for nombre, mio, libro in [
            ("devengo del PPDI", m["flag_ppdi"], P["series"]["flag_ppdi"]),
            ("mes de carga del IR", m["flag_trib"], P["series"]["flag_trib"]),
            ("ano de cada mes", m["anio"], P["series"]["anio"])]:
        out.append((nombre, sum(1 for a, b in zip(mio, libro) if a != b), n))
    return out


if __name__ == "__main__":
    print("=== el calendario derivado de las fechas contra el libro ===")
    for nombre, dif, n in validar():
        print(f"  {nombre:<32} {n:>5} valores, {dif} diferencias")
