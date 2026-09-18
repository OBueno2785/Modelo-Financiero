"""Calendario del modelo de pago por hitos funcionales, derivado de las fechas.

El equivalente de `calendario_caj` para San Martin. Su malla es mensual y
arranca en enero del ano del contrato; el periodo [D + C + PM] se numera aparte,
porque el libro cuenta los meses del contrato desde el primero de obra y no
desde el arranque de la malla (`Nec_Fin!nro_mes`), y tanto el cierre financiero
como el calendario de aportes de capital se expresan en esa numeracion.
"""


def _ym(f):
    return int(str(f)[:4]), int(str(f)[5:7])


def malla(anio0, n_meses):
    """Los meses de la malla, en orden, desde enero de `anio0`."""
    return [(anio0 + i // 12, i % 12 + 1) for i in range(n_meses)]


def calendario(anio0, n_meses, inicio_dcpm, fin_dcpm, primer_pago_ppdi,
               cuotas=60):
    """`inicio_dcpm`, `fin_dcpm` y `primer_pago_ppdi` son fechas AAAA-MM."""
    m = malla(anio0, n_meses)
    pos = {(a, mm): i for i, (a, mm) in enumerate(m)}
    i0, i1 = pos[_ym(inicio_dcpm)], pos[_ym(fin_dcpm)]
    p0 = pos[_ym(primer_pago_ppdi)]

    flag_dcpm = [1.0 if i0 <= t <= i1 else 0.0 for t in range(n_meses)]
    nro_mes = [float(t - i0 + 1) if i0 <= t <= i1 else 0.0 for t in range(n_meses)]
    pagos = [p0 + 3 * k for k in range(cuotas) if p0 + 3 * k < n_meses]
    flag_pago = [1.0 if t in set(pagos) else 0.0 for t in range(n_meses)]
    anio = [float(a) for a, _ in m]
    return {"flag_dcpm": flag_dcpm, "nro_mes": nro_mes, "flag_pago": flag_pago,
            "anio": anio, "n": n_meses, "meses_dcpm": i1 - i0 + 1,
            "i_dcpm": (i0, i1), "pagos": pagos}


def ventana_reajuste(cal):
    """La ventana del reajuste por IPM: del primer mes de [D + C + PM] al ultimo
    de operacion. Es lo que `Hip_Mensual` usa para acumular el gatillo, y no
    coincide con la bandera de operacion: arranca en la obra."""
    fdc, fop = cal["flag_dcpm"], cal.get("flag_op") or [0.0] * cal["n"]
    return [1.0 if (fdc[t] or fop[t]) else 0.0 for t in range(cal["n"])]


def validar():
    import json
    D = json.load(open("/mnt/project-files/generador/sanmartin_primitivos.json"))
    S, K = D["series"], D["escalares"]
    # La malla del libro arranca en enero de 2025; la obra corre del mes 11 al
    # 60 de la malla y el PPDI se paga en 60 cuotas desde marzo de 2030.
    c = calendario(2025, K["n"], "2025-11", "2029-12", "2030-03", K["n_cuotas"])
    salida = []
    for nombre, mio, libro in [
            ("flag del periodo D+C+PM", c["flag_dcpm"], S["flag_dcpm"]),
            ("numero de mes del contrato", c["nro_mes"], S["nro_mes"]),
            ("meses de pago del PPDI", c["flag_pago"], S["flag_pago"]),
            ("ano de cada mes", c["anio"], S["anio"])]:
        salida.append((nombre, sum(1 for a, b in zip(mio, libro) if a != b),
                       len(libro)))
    return salida


if __name__ == "__main__":
    print("=== el calendario de hitos derivado de las fechas contra el libro ===")
    for nombre, dif, n in validar():
        print(f"  {nombre:<32} {n:>5} valores, {dif} diferencias")
