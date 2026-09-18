"""Modelo sombra de Cajamarca armado linea por linea, con impuestos calculados.

Reemplaza el atajo del primer modelo sombra, que partia de los flujos en cache
del libro y les sumaba deltas con un tipo marginal. Aca cada linea se construye
y el bloque tributario corre entero, con deduccion del ingreso financiero en
construccion, adicion en cuotas de 1/15 y arrastre de perdidas.

Del libro queda UNA primitiva: el efecto ITAN, que necesita el balance, y vale
-376 S/ miles de valor presente al Ke del modelo. El tramo complementario de
`M.Sombra!192:195` ya no es primitiva: era enteramente la facilidad de capital de
trabajo de operacion, que `capital_trabajo` reproduce trimestre a trimestre desde
su regla de dimensionamiento (desvio maximo 4e-6). El CAPEX de caja y el flujo
neto de IGV salen del motor, no del libro.
"""
import json
import capital_trabajo as KT
import deuda_cajamarca as DE
import motor_cajamarca as M
import sombra_cajamarca as S
import tributos_cajamarca as TR

D = S.D
NQ, NM = S.NQ, S.NM
# `EEFF Anuales` agrega por el ano de EEPPGG, que NO es el de M.Sombra:
# las dos hojas etiquetan los mismos trimestres con anos distintos.
# `EEFF Anuales` agrega por trimestre fiscal de EEPPGG, y el estado de
# resultados DEVENGA el PPDMO en su trimestre mientras la caja lo cobra al
# siguiente: `EEPPGG!10` lee `PPDMO!23` y `M.Sombra!10` lee `PPDMO!34`.
ANIO = D["fiscal"]
ANIOS = sorted(set(ANIO))
# Perfil del PPDI: 60 cuotas iguales por unidad de PPDI anual, desde el primer
# trimestre de operacion. Por defecto el del libro; `usar_calendario` lo deriva.
PERFIL_PPDI = [D["ppdi"][i] / S.PPDI_LIBRO for i in range(NQ)]
# Las dos primitivas que siguen saliendo del libro de Cajamarca. Para un
# proyecto nuevo van en cero, y valen -376 y +305 S/ miles de valor presente.
EXTRA = {k: list(D[k]) for k in ("itan", "des2", "srv2", "int2")}
LIBRO = ("itan", "des2", "srv2")
COSTOS = ("costo_fijo", "costo_var", "gastos_spv", "seguros", "fianzas",
          "promocion", "fideicomiso")


def usar_calendario(cal, cuotas=60, extras_del_libro=False):
    """Deriva de las fechas todo lo que antes salia del JSON del libro.

    `extras_del_libro` deja el efecto ITAN con el valor de Cajamarca; para un
    proyecto nuevo va en cero, que es lo unico honesto mientras no este modelado.
    El capital de trabajo ya NO depende de esta bandera: se modela siempre.
    """
    global ANIO, ANIOS, NQ, NM, PERFIL_PPDI, EXTRA
    S.usar_calendario(cal)
    NQ, NM = S.NQ, S.NM
    ANIO = cal["fiscal"]
    ANIOS = sorted(set(ANIO))
    q0 = next(q for q in range(NQ) if cal["flag_superv"][q])
    PERFIL_PPDI = [0.25 if q0 <= q < q0 + cuotas else 0.0 for q in range(NQ)]
    if not extras_del_libro:
        EXTRA = {k: [0.0] * NQ for k in EXTRA}


def _anual(serie):
    return {a: sum(serie[i] for i in range(NQ) if ANIO[i] == a) for a in ANIOS}


# Las lineas de costo sobre las que el libro calcula el IGV de operacion
# (`IGV!77 IGV Gastos OM`): la promocion queda fuera, como en el libro.
COSTOS_CON_IGV = ("costo_fijo", "costo_var", "gastos_spv", "seguros",
                  "fianzas", "fideicomiso")


def flujo(tarifa, ipm=S.IPM_LIBRO, ke=None, kd=None, ppdi=None,
          kg=None, fijo_base_cte=None, costos=None, deuda=None,
          ext=None, gfin_ext=None, exonera_igv=0, igv=None):
    """`deuda` es la salida de `deuda_cajamarca.corrida`, y `ext` / `gfin_ext`
    las primitivas de construccion que salen de la plantilla. Sin ellos corre
    con el libro de Cajamarca."""
    ke = S.KE_LIBRO if ke is None else ke
    kd = DE.KD_LIBRO if kd is None else kd
    ppdi = S.PPDI_LIBRO if ppdi is None else ppdi
    costos = costos or {k: D[k] for k in COSTOS}

    fijo, var, _, _, fijo_acc, var_acc = S.pagos(ipm, tarifa, kg, fijo_base_cte)
    ppdi_q = [PERFIL_PPDI[i] * ppdi for i in range(NQ)]

    deu = DE.corrida(kd) if deuda is None else deuda
    pad = lambda s: list(s) + [0.0] * (NM - len(s))
    interes_q = S._a_trimestres(pad(deu["interes"]))
    srv_q = S._a_trimestres(pad(deu["servicio"]))
    des_q = S._a_trimestres(pad(deu["desemb"]))

    # Facilidad de capital de trabajo de operacion: `M.Sombra!123` la dimensiona
    # con los costos fijos y variables del trimestre, que son exactamente
    # `costos["costo_fijo"]` y `costos["costo_var"]` (no las patas del PPDMO).
    kt = KT.corrida([abs(x) for x in costos["costo_fijo"]],
                    [abs(x) for x in costos["costo_var"]],
                    S.FLAG_SUP, NQ)

    superv = [-S.SUPERV * (ppdi_q[i] + fijo[i] + var[i]) * S.FLAG_SUP[i]
              for i in range(NQ)]
    # En zona exonerada (ley de la Amazonia) el PPD no lleva IGV, asi que el
    # soportado en la operacion no tiene contra que acreditarse y es costo, como
    # `Opex!143` de San Martin. Cajamarca NO esta exonerada: cobra IGV sobre el
    # PPDI y el PPDMO (`IGV!71:73`) y acredita el de sus costos, por eso su fila
    # de caja (`IGV!83`) solo existe en obra y suma cero. Con la exoneracion en
    # cero esta linea vale cero y el libro se reproduce igual.
    tasa_igv = M.IGV if igv is None else igv
    igv_op = [(-tasa_igv * abs(sum(costos[k][i] for k in COSTOS_CON_IGV))
               if exonera_igv else 0.0) for i in range(NQ)]
    costo_total = [sum(costos[k][i] for k in COSTOS) + superv[i] + igv_op[i]
                   for i in range(NQ)]

    # --- bloque tributario, sobre el estado de resultados, no sobre la caja ---
    R = M.corrida(ppdi / 12, gfin_ext=gfin_ext, ext=ext)
    pad_sc = lambda s: list(s) + [0.0] * (NM - len(s))
    sc_q = S._a_trimestres(pad_sc(R["sc"]))
    igv_q = S._a_trimestres(pad_sc(R["igv"]))
    ing_fin_a = _anual(S._a_trimestres(pad_sc(R["ing_fin"])))
    sc_a = _anual(sc_q)
    gf_a = _anual([interes_q[i] + kt["interes"][i] for i in range(NQ)])
    fijo_a, var_a = _anual(fijo_acc), _anual(var_acc)
    costo_a = _anual(costo_total)
    ppdi_a = _anual(ppdi_q)

    part_a, ir_a = TR.tributos(
        [fijo_a[a] + var_a[a] for a in ANIOS],
        [-costo_a[a] for a in ANIOS],
        [ing_fin_a.get(a, 0.0) for a in ANIOS],
        [gf_a[a] for a in ANIOS],
        [sc_a.get(a, 0.0) for a in ANIOS],
        [ppdi_a[a] for a in ANIOS])

    # El impuesto de cada ano se paga al ano siguiente: el libro carga en el
    # trimestre de regularizacion, no en el ejercicio que lo genera. El del
    # ultimo ano queda fuera de la malla, igual que en el libro.
    imp = [0.0] * NQ
    for k, a in enumerate(ANIOS):
        q = [i for i in S.IR_Q if ANIO[i] == a]
        if q:
            imp[q[0]] = -(part_a[k] + ir_a[k])

    fcf = [ppdi_q[i] + fijo[i] + var[i] + costo_total[i]
           + EXTRA["itan"][i] - sc_q[i] + igv_q[i] + imp[i]
           + des_q[i] - srv_q[i] + kt["desembolso"][i] - kt["servicio"][i]
           for i in range(NQ)]
    f = S.descuento(ke)
    return {"fcf": fcf, "van": sum(fcf[i] * f[i] for i in range(NQ)),
            "fijo": fijo, "var": var, "ppdi": ppdi_q, "impuestos": imp,
            "superv": superv, "part": part_a, "ir": ir_a,
            "costo_total": costo_total, "sc": sc_q, "igv": igv_q,
            "interes": interes_q, "servicio": srv_q, "desembolso": des_q,
            "anios": ANIOS}


def cerrar(ipm=S.IPM_LIBRO, lo=0.5, hi=12.0, it=120, **kw):
    for _ in range(it):
        m = (lo + hi) / 2
        if flujo(m, ipm, **kw)["van"] > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


if __name__ == "__main__":
    r = flujo(S.TARIFA_LIBRO)
    print("=== el modelo sombra estructural contra el libro ===")
    print(f"  participacion, total : {sum(r['part']):>16,.6f}   libro    18,338.001922")
    print(f"  IR, total            : {sum(r['ir']):>16,.6f}   libro   102,784.500775")
    d = max(abs(r["fcf"][i] - D["fcf"][i]) for i in range(NQ))
    print(f"  FCF trimestral, desvio maximo : {d:.8f}")
    print(f"  VAN con la tarifa del libro   : {r['van']:.6f}")
    print(f"  tarifa que cierra             : {cerrar():.10f}"
          f"   (libro {S.TARIFA_LIBRO:.10f})")
