"""La regla de Oscar: el OPEX de un ano de concesion es la suma del OPEX por
hito de ese ano (2026-09-15).

La plantilla pedia el OPEX dos veces, en `OPEX` por ano de concesion y en
`OPEX hitos` repartido por hito, y nada comprobaba que dijeran lo mismo. Aqui
van las dos mitades de la regla:

    `derivar`  escribe `OPEX hitos` a partir de `OPEX` y del reparto por hito de
               la hoja `Hitos`, con lo que la igualdad se cumple por
               construccion y el usuario escribe el OPEX una sola vez.
    `validar`  comprueba la igualdad en una plantilla ya llena y devuelve el
               desvio ano por ano, para las plantillas escritas a mano.

**Lo que se deriva y lo que no.** Se derivan las cuatro patas fijas por hito
(`fijo_hK`), sus versiones con IGV —conservando la proporcion que el usuario ya
tenia escrita—, el costo variable y las reposiciones. **No se derivan**
`gg_u` (gastos generales y utilidad), `otros_op` (otros costos de la concesion)
ni `igv_op`: la hoja `OPEX` no tiene contrapartida de ninguno de los tres, asi
que siguen siendo insumos propios de la rama por hitos y la regla no los toca.

**Unidades.** `OPEX` se escribe en soles y `OPEX hitos` en la moneda del modelo,
que sale de la celda "Moneda" de la hoja `Proyecto`. Con "S/ miles" el factor es
mil; con "S/" es uno.

**El reparto por hito no es el del CAPEX.** En el libro de San Martin el hito 4
carga el 26.7 % del O&M y solo el 15.5 % de la inversion. Por eso el reparto es
un campo propio de `Hitos` y no se toma de los porcentajes de CAPEX.
"""
from openpyxl import load_workbook

import leer_plantilla as LP

HITOS = (1, 2, 3, 4)


def factor_moneda(proyecto):
    m = str(proyecto.get("Moneda", "S/")).strip().lower()
    return 1000.0 if "mil" in m else 1.0


def reparto(hitos):
    """Los cuatro pesos de `Hitos`. Si la plantilla es vieja y no los trae, cae
    al reparto del CAPEX y lo dice quien llame, no esta funcion."""
    r = [hitos.get(f"Hito {k}, reparto del O&M") for k in HITOS]
    if any(v is None for v in r):
        pct = hitos.get("pct_capex") or []
        return (list(pct) + [0.0] * 4)[:4], True
    return r, False


def objetivo(d):
    """Lo que `OPEX hitos` deberia decir, por ano CALENDARIO, en la moneda del
    modelo. Sale de `OPEX`, que esta por ano de concesion, usando el
    emparejamiento de anos que la propia hoja trae en sus dos primeras filas."""
    p, opex = d["proyecto"], d["opex"]
    f = factor_moneda(p)
    pesos, _ = reparto(d["hitos"])
    out = {}
    for a in range(d["anios"]):
        cal = d["anio_calendario"][a]
        fijo = sum(opex[c][a] for c in LP.FIJOS_PPDMO) / f
        var = sum(opex[c][a] for c in LP.VARIABLES) / f
        rep = opex["reposiciones"][a] / f
        out[cal] = {"fijo": fijo, "variable": var, "repex": rep,
                    **{f"fijo_h{k}": fijo * pesos[k - 1] for k in HITOS}}
    return out


def validar(ruta=LP.RUTA):
    """Desvio de la igualdad, ano por ano. Devuelve la lista de diferencias que
    superan la tolerancia relativa, vacia si la plantilla cumple la regla."""
    d = LP.leer(ruta)
    obj, lin = objetivo(d), d["opex_hitos"]
    anios = d["anio_hitos"]
    fallos = []
    # Anos que `OPEX hitos` cubre y `OPEX` no: ahi la regla no tiene con que
    # comparar, asi que lo unico admisible es que esten en cero.
    for j, cal in enumerate(anios):
        if cal in obj:
            continue
        suma = (sum(lin.get(f"fijo_h{k}", [0.0] * len(anios))[j] for k in HITOS)
                + lin.get("variable", [0.0] * len(anios))[j]
                + lin.get("repex", [0.0] * len(anios))[j])
        if abs(suma) > 1e-9:
            fallos.append((cal, "fuera de OPEX", 0.0, suma, -suma))
    for cal, o in obj.items():
        if cal not in anios:
            fallos.append((cal, "falta en hitos", o["fijo"] + o["variable"]
                           + o["repex"], 0.0, o["fijo"] + o["variable"] + o["repex"]))
            continue
        j = anios.index(cal)
        suma = sum(lin.get(f"fijo_h{k}", [0.0] * len(anios))[j] for k in HITOS)
        for nombre, mio, suyo in (("fijo", o["fijo"], suma),
                                  ("variable", o["variable"],
                                   lin.get("variable", [0.0] * len(anios))[j]),
                                  ("repex", o["repex"],
                                   lin.get("repex", [0.0] * len(anios))[j])):
            ref = max(abs(mio), abs(suyo))
            if ref > 1e-9 and abs(mio - suyo) / ref > 1e-9:
                fallos.append((cal, nombre, mio, suyo, mio - suyo))
    return fallos


def derivar(ruta, salida=None):
    """Reescribe `OPEX hitos` de forma que cumpla la regla, y devuelve la ruta.

    Conserva la proporcion con IGV que la hoja ya tenia por linea; si no tenia
    ninguna, usa `1 + IGV` de la hoja `Proyecto`.
    """
    from plantilla import LINEAS_OPEX_HITOS
    d = LP.leer(ruta)
    obj = objetivo(d)
    anios = d["anio_hitos"]
    lin = d["opex_hitos"]
    igv = 1 + d["proyecto"].get("IGV", 0.18)

    def razon(clave, base, j):
        b = lin.get(base, [0.0] * len(anios))[j]
        c = lin.get(clave, [0.0] * len(anios))[j]
        return c / b if abs(b) > 1e-12 else igv

    nuevo = {k: list(v) for k, v in lin.items()}
    for j, cal in enumerate(anios):
        if cal not in obj:
            continue
        o = obj[cal]
        for k in HITOS:
            r = razon(f"conigv_h{k}", f"fijo_h{k}", j)
            nuevo.setdefault(f"fijo_h{k}", [0.0] * len(anios))[j] = o[f"fijo_h{k}"]
            nuevo.setdefault(f"conigv_h{k}", [0.0] * len(anios))[j] = o[f"fijo_h{k}"] * r
        r1 = razon("conigv_var_tar", "variable", j)
        r2 = razon("conigv_var_sjs", "variable", j)
        nuevo.setdefault("variable", [0.0] * len(anios))[j] = o["variable"]
        nuevo.setdefault("conigv_var_tar", [0.0] * len(anios))[j] = o["variable"] * r1
        nuevo.setdefault("conigv_var_sjs", [0.0] * len(anios))[j] = o["variable"] * r2
        nuevo.setdefault("repex", [0.0] * len(anios))[j] = o["repex"]

    wb = load_workbook(ruta)
    ws = wb["OPEX hitos"]
    clave_de = {e: c for e, c in LINEAS_OPEX_HITOS if c}
    for r in range(7, ws.max_row + 1):
        c = clave_de.get(ws.cell(r, 2).value)
        if c in nuevo:
            for j in range(len(anios)):
                ws.cell(r, 4 + j).value = nuevo[c][j]
    wb.save(salida or ruta)
    return salida or ruta


if __name__ == "__main__":
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else LP.RUTA
    fallos = validar(ruta)
    print(f"plantilla: {ruta}")
    if not fallos:
        print("  el OPEX por hito suma el OPEX del ano. La regla se cumple.")
    else:
        print(f"  {len(fallos)} desvios; los diez mayores:")
        for cal, nom, mio, suyo, dif in sorted(
                fallos, key=lambda f: -abs(f[4]))[:10]:
            print(f"    {cal}  {nom:<9} OPEX {mio:>16,.2f}   "
                  f"por hito {suyo:>16,.2f}   dif {dif:>16,.2f}")
