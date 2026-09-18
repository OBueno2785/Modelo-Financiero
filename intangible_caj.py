"""Rama autofinanciada: la obra como ACTIVO INTANGIBLE, y la tarifa al usuario.

CINIIF 12 parrafo 17: cuando lo que recibe el concesionario es el derecho a
cobrar a los usuarios, el cobro depende del uso y no hay importe determinable
exigible al concedente, asi que la contraprestacion se reconoce como activo
intangible y no como cuenta por cobrar. En ese caso, y solo en ese caso, el
parrafo 22 manda capitalizar los costos por prestamos del periodo de
construccion (NIC 23).

Diferencias con la rama cofinanciada, que estan todas aqui y en ningun otro
sitio:

1. No hay PPDI ni PPDMO. El concedente no paga nada. La incognita del cierre
   pasa a ser el **ingreso tarifario al usuario**, un precio unitario por kg
   DBO5 que se reajusta por IPM igual que la pata variable.
2. No hay activo financiero, no hay tasa implicita, no hay deduccion del
   ingreso financiero durante la construccion ni adicion en cuotas de 1/15.
   Esas tres reglas son del parrafo 16 y no aplican.
3. El intangible se reconoce al termino de obra por la inversion MAS los
   intereses de la deuda devengados durante la construccion, y se amortiza
   linealmente a lo largo de la operacion. La amortizacion es gasto deducible y
   NO es caja: entra al estado de resultados y no al flujo.
4. El interes posterior al inicio de operacion si es gasto del periodo.
5. El usuario paga IGV sobre la tarifa, asi que el credito fiscal de la
   construccion se recupera contra ese debito y no contra el PPDI.

Lo que NO cambia, porque no depende del regimen: el calendario, el CAPEX, el
OPEX y su indexacion, el dimensionamiento de la deuda, la supervision del
regulador y el arrastre de perdidas del bloque tributario.

Decidido por Oscar el 2026-09-15: las reposiciones siguen entrando como costo de
caja, igual que en el libro aprobado, y NO como provision del parrafo 21 /
NIC 37 ("no lo provisiones"). Vale para las dos ramas.
"""
import ipm_cajamarca as IPM
import tributos_cajamarca as TR

COSTOS = ("costo_fijo", "costo_var", "gastos_spv", "seguros", "fianzas",
          "promocion", "fideicomiso")


def _a_trim(mensual, cal):
    out = [0.0] * cal["nq"]
    for m in range(min(cal["nm"], len(mensual))):
        q = cal["trim_m"][m]
        if 1 <= q <= cal["nq"]:
            out[q - 1] += mensual[m]
    return out


def _descuento(ke, cal):
    km, acc, out = (1 + ke) ** (1 / 12) - 1, 0, []
    for m in cal["meses"]:
        acc += m
        out.append(0.0 if m == 0 else 1 / (1 + km) ** acc)
    return out


def intangible(sc, interes, cal):
    """Activo intangible: inversion del periodo de construccion mas intereses
    capitalizados (parrafo 22), amortizado linealmente durante la operacion."""
    nm, fo = cal["nm"], cal["flag_om"]
    # Ojo: `flag_om` es 0 **antes** de la operacion y tambien **despues** de que
    # acaba la concesion, porque la malla dura mas que el contrato. Capitalizar
    # por "no esta en operacion" mete los meses de la cola. Se capitaliza solo
    # lo anterior al primer mes de operacion.
    ini = next((m for m in range(nm) if fo[m]), nm)
    obra = lambda m: m < ini
    inv = sum(sc[m] for m in range(nm) if obra(m))
    cap = sum(interes[m] for m in range(nm) if obra(m))
    n_op = sum(fo)
    base = inv + cap
    amort_m = [base / n_op * fo[m] if n_op else 0.0 for m in range(nm)]
    saldo, acc = [0.0] * nm, 0.0
    for m in range(nm):
        acc += (sc[m] + interes[m] if obra(m) else 0.0) - amort_m[m]
        saldo[m] = acc
    return {"inversion": inv, "interes_capitalizado": cap, "base": base,
            "meses_operacion": n_op, "amort_m": amort_m, "saldo_m": saldo,
            "mes_inicio_op": ini,
            "cap_m": [interes[m] if obra(m) else 0.0 for m in range(nm)]}


# Las lineas sobre las que se calcula el IGV de operacion, como `IGV!77` del
# libro de Cajamarca: la promocion queda fuera.
COSTOS_CON_IGV = ("costo_fijo", "costo_var", "gastos_spv", "seguros",
                  "fianzas", "fideicomiso")


def flujo(tarifa, ipm, ke, kd, kg, costos, deuda, sc, cal, ext,
          igv_tasa=0.18, superv=0.01, exonera_igv=0):
    """`costos` son las lineas trimestrales NEGATIVAS, `sc` el servicio de
    construccion mensual y `deuda` la salida de `deuda_cajamarca.corrida`."""
    nm, nq, fo = cal["nm"], cal["nq"], cal["flag_om"]
    f18 = IPM.factores(ipm, cal["flag_om"])
    pad = lambda s: (list(s) + [0.0] * nm)[:nm]

    # --- ingreso tarifario al usuario, la incognita del cierre ---
    ing_m = [tarifa * kg[m] * f18[m] / 1000 * fo[m] for m in range(nm)]
    sup_m = [-superv * ing_m[m] for m in range(nm)]
    ing_q, sup_q = _a_trim(ing_m, cal), _a_trim(sup_m, cal)

    # --- deuda: el interes de construccion se capitaliza, el de operacion no ---
    interes = pad(deuda["interes"])
    _ini = next((m for m in range(nm) if fo[m]), nm)
    int_constr = [interes[m] if m < _ini else 0.0 for m in range(nm)]
    int_op = [interes[m] * fo[m] for m in range(nm)]
    int_op_q = _a_trim(int_op, cal)
    srv_q, des_q = _a_trim(pad(deuda["servicio"]), cal), _a_trim(pad(deuda["desemb"]), cal)

    ai = intangible(pad(sc), int_constr, cal)
    amort_q = _a_trim(ai["amort_m"], cal)
    sc_q = _a_trim(pad(sc), cal)

    # --- IGV: el usuario paga IGV sobre la tarifa y contra ese debito se
    #     recupera el credito de la construccion, con un mes de anticipo ---
    g = lambda k: pad(ext.get(k, [0.0] * nm))
    obra, reem, fid, seg = g("obra"), g("reem"), g("fid"), g("seg")
    compras = [(-obra[m] - reem[m] - fid[m] - seg[m]) * igv_tasa for m in range(nm)]
    igv_m, credito = [0.0] * nm, 0.0
    for m in range(nm):
        dif = ing_m[m] * igv_tasa + compras[m] + (-compras[m - 1] if m else 0.0)
        acum = dif + credito if m else dif
        credito = min(acum, 0.0)
        igv_m[m] = dif - (0.0 if credito < 0 else acum)
    igv_q = _a_trim(igv_m, cal)

    # En zona exonerada (ley de la Amazonia) la tarifa al usuario no lleva IGV,
    # asi que el soportado en la operacion no tiene contra que acreditarse y es
    # costo. Con la exoneracion en cero esta linea vale cero.
    igv_op = [(-igv_tasa * abs(sum(costos[k][i] for k in COSTOS_CON_IGV))
               if exonera_igv else 0.0) for i in range(nq)]
    costo_q = [sum(costos[k][i] for k in COSTOS) + sup_q[i] + igv_op[i]
               for i in range(nq)]

    # --- bloque tributario anual: sin deducciones ni adiciones del p.16 ---
    anio, anios = cal["fiscal"], sorted(set(cal["fiscal"]))
    an = lambda s: [sum(s[i] for i in range(nq) if anio[i] == a) for a in anios]
    ventas, cost_a = an(ing_q), an(costo_q)
    amort_a, gf_a = an(amort_q), an(int_op_q)
    cero = [0.0] * len(anios)
    uai_p = [ventas[k] + cost_a[k] - amort_a[k] - gf_a[k] for k in range(len(anios))]
    part = [b * TR.TASA_PART for b in TR._bloque(uai_p, cero, cero)]
    uai_i = [uai_p[k] - part[k] for k in range(len(anios))]
    ir = [b * TR.TASA_IR for b in TR._bloque(uai_i, cero, cero)]

    imp = [0.0] * nq
    for k, a in enumerate(anios):
        q = [i for i in cal["ir_q"] if anio[i] == a]
        if q:
            imp[q[0]] = -(part[k] + ir[k])

    fcf = [ing_q[i] + costo_q[i] - sc_q[i] + igv_q[i] + imp[i]
           + des_q[i] - srv_q[i] for i in range(nq)]
    f = _descuento(ke, cal)
    return {"fcf": fcf, "van": sum(fcf[i] * f[i] for i in range(nq)),
            "ingreso": ing_q, "superv": sup_q, "costo_total": costo_q,
            "sc": sc_q, "igv": igv_q, "impuestos": imp, "amort": amort_q,
            "interes_op": int_op_q, "servicio": srv_q, "desembolso": des_q,
            "part": part, "ir": ir, "anios": anios, "intangible": ai,
            "ing_m": ing_m, "saldo_m": ai["saldo_m"], "amort_m": ai["amort_m"]}


def cerrar(ipm, lo=0.5, hi=200.0, it=140, **kw):
    for _ in range(it):
        m = (lo + hi) / 2
        if flujo(m, ipm, **kw)["van"] > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2
