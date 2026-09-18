"""Modelo sombra de Cajamarca: cierra la tarifa variable del PPDMO.

Cajamarca cierra **solo la pata variable** (`Resumen!J6` = `Tarifa_Media_Vta`
contra `M.Sombra!D74` = 0). La pata fija es un pass-through de costos con 15 %
de margen y queda fuera del cierre.

Que se recalcula aqui y que se toma del libro
---------------------------------------------
Recalculado: la pata fija y la variable del PPDMO mes a mes con el factor de
reajuste por IPM (`ipm_cajamarca`), su agregacion trimestral con el rezago de
tres meses del libro, la supervision SUNASS (1 % del PPD, `Inputs!D165`), el
PPDI (motor + modulo de deuda) y los intereses, amortizacion y desembolsos
(`deuda_cajamarca`).

Del libro, porque no responden a la tarifa ni al IPM: los costos de operacion
(se indexan con el IPC de largo plazo de `Inputs!N23`, 2.00 %, no con el IPM),
el CAPEX, el flujo neto de IGV (cero en todo trimestre con ingreso variable) y
el efecto ITAN (suma cero).

Los impuestos entran como delta: participacion de trabajadores mas IR sobre la
variacion de la utilidad, al tipo marginal 0.05 + 0.295 x 0.95 = 0.33025, en el
trimestre en que el libro carga el impuesto del ano. Vale mientras la base
imponible siga positiva en los anos en que el libro ya paga.
"""
import json
import deuda_cajamarca as DEUDA
import ipm_cajamarca as IPM

D = json.load(open("/mnt/project-files/generador/caj_sombra_full.json"))
NQ, NM = len(D["fcf"]), len(D["Pf18"])
TAU = 0.05 + 0.295 * 0.95
SUPERV = 0.01                                  # Inputs!D165, supervision SUNASS
PPDI_LIBRO = 46472.546554744986
TARIFA_LIBRO = 4.317668971541212               # PPDMO!D26, S/ por kg DBO5
FIJO_BASE_LIBRO = 555.9856812752989            # PPDMO!D22, S/ miles al mes
KE_LIBRO = (1 + D["ke"]) ** 12 - 1
IPM_LIBRO = IPM.IPM_LIBRO

FLAG_OM, FLAG_T, FLAG_P = D["Pflag_om"], D["Pflagt"], D["Pflag_ppdmo"]
KG, TRIM_M = D["Pkg"], D["Pm_trim"]
IR_Q = [i for i in range(NQ) if abs(D["ir"][i]) > 1e-9]
# la supervision SUNASS se cobra solo mientras corre el contrato de O&M
FLAG_SUP = D["flag_superv"]
MESES = D["meses"]
VIVOS = [i for i in range(NQ) if MESES[i] > 0]


def usar_tributos(part=0.05, ir=0.295, superv=0.01):
    """Tipo marginal y supervision del regulador, de la plantilla.

    El marginal es `part + ir x (1 - part)`, porque el IR se calcula sobre la
    utilidad ya neta de la participacion de trabajadores.
    """
    global TAU, SUPERV
    TAU, SUPERV = part + ir * (1 - part), superv


def usar_calendario(cal):
    """Reemplaza las banderas del libro por las que salen de las fechas de la
    plantilla (`calendario_caj.calendario`). Sin esto el modelo sombra corre
    siempre sobre el cronograma de Cajamarca."""
    global NQ, NM, FLAG_OM, FLAG_T, FLAG_P, TRIM_M, IR_Q, FLAG_SUP, MESES, VIVOS
    NQ, NM = cal["nq"], cal["nm"]
    FLAG_OM, FLAG_T, FLAG_P = cal["flag_om"], cal["flag_t"], cal["flag_p"]
    TRIM_M, IR_Q, FLAG_SUP = cal["trim_m"], cal["ir_q"], cal["flag_superv"]
    MESES = cal["meses"]
    VIVOS = [i for i in range(NQ) if MESES[i] > 0]


def _trimestral(mensual):
    """Suma movil de tres meses x flag trimestral, y rezago de tres meses.

    Replica PPDMO!25 y !31 (SUMPRODUCT de los tres meses por el flag de O&M,
    por el flag trimestral) y PPDMO!34 y !35 (`=+AD$33*AA25`, tres columnas
    a la izquierda).
    """
    t = [sum(mensual[max(0, m - 2):m + 1]) * FLAG_T[m] for m in range(NM)]
    return [FLAG_P[m] * (t[m - 3] if m >= 3 else 0.0) for m in range(NM)]


def _a_trimestres(mensual_q):
    out = [0.0] * NQ
    for m in range(NM):
        q = TRIM_M[m]
        if 1 <= q <= NQ:
            out[q - 1] += mensual_q[m]
    return out


def pagos(ipm=IPM_LIBRO, tarifa=TARIFA_LIBRO, kg=None, fijo_base_cte=None):
    """`kg` y `fijo_base_cte` vienen de la plantilla cuando hay proyecto nuevo.

    `fijo_base_cte` es la base a precios constantes del mes de la oferta; el
    ajuste de un mes de IPM (`PPDMO!17`) se aplica aca, porque depende del IPM
    que se este corriendo.
    """
    f18 = IPM.factores(ipm, FLAG_OM)
    im = (1 + ipm) ** (1 / 12) - 1
    im_l = (1 + IPM_LIBRO) ** (1 / 12) - 1
    kg = KG if kg is None else kg
    fijo_base = (FIJO_BASE_LIBRO * (1 + im) / (1 + im_l)   # PPDMO!D21, via fila 17
                 if fijo_base_cte is None else fijo_base_cte * (1 + im))
    fijo_m = [fijo_base * f18[m] * FLAG_OM[m] for m in range(NM)]
    var_m = [(0.0 if FLAG_OM[m] == 0 else tarifa * kg[m] * f18[m]) / 1000
             for m in range(NM)]
    # Dos vistas del mismo pago, y el libro usa cada una en su sitio: el estado
    # de resultados lo devenga en el trimestre (`EEPPGG!10` lee `PPDMO!23`) y la
    # caja lo cobra un trimestre despues (`M.Sombra!10` lee `PPDMO!34`).
    return (_a_trimestres(_trimestral(fijo_m)), _a_trimestres(_trimestral(var_m)),
            fijo_base, f18,
            _a_trimestres(fijo_m), _a_trimestres(var_m))


def descuento(ke_anual):
    km, acc, out = (1 + ke_anual) ** (1 / 12) - 1, 0, []
    for m in MESES:
        acc += m
        out.append(0.0 if m == 0 else 1 / (1 + km) ** acc)
    return out


def van(tarifa, ipm=IPM_LIBRO, ke=None, kd=None, ppdi=None):
    ke = KE_LIBRO if ke is None else ke
    kd = DEUDA.KD_LIBRO if kd is None else kd
    ppdi = PPDI_LIBRO if ppdi is None else ppdi
    fijo, var, _, _, _, _ = pagos(ipm, tarifa)
    deu = DEUDA.corrida(kd)
    # intereses, amortizacion y desembolsos mensuales -> trimestres del sombra
    # las dos mallas arrancan el mismo mes (oct-2026); la de deuda es mas corta,
    # asi que se rellena por el final, no por el principio.
    pad = lambda s: list(s) + [0.0] * (NM - len(s))
    inte_q = _a_trimestres(pad(deu["interes"]))
    srv_q = _a_trimestres(pad(deu["servicio"]))
    des_q = _a_trimestres(pad(deu["desemb"]))
    rp = ppdi / PPDI_LIBRO
    f = descuento(ke)

    d_rev = [0.0] * NQ
    for i in range(NQ):
        d_ppdi = D["ppdi"][i] * (rp - 1)
        d_fijo = fijo[i] - D["fijo"][i]
        d_var = var[i] - D["var"][i]
        d_sup = -SUPERV * (d_ppdi + d_fijo + d_var) * FLAG_SUP[i]   # EEPPGG!18
        d_rev[i] = d_ppdi + d_fijo + d_var + d_sup

    d_int = [inte_q[i] - INTE_LIBRO_Q[i] for i in range(NQ)]
    d_srv = [-(srv_q[i] - SRV_LIBRO_Q[i]) for i in range(NQ)]
    d_des = [des_q[i] - DES_LIBRO_Q[i] for i in range(NQ)]

    # impuesto: sobre la utilidad, en el trimestre en que el libro lo carga
    d_tax = [0.0] * NQ
    for i in VIVOS:
        base = d_rev[i] - d_int[i]
        if abs(base) > 1e-12:
            j = next((q for q in IR_Q if q >= i), IR_Q[-1])
            d_tax[j] -= TAU * base

    total = sum((D["fcf"][i] + d_rev[i] + d_srv[i] + d_des[i] + d_tax[i]) * f[i]
                for i in range(NQ))
    return total


def _libro_deuda():
    deu = DEUDA.corrida()
    pad = lambda s: list(s) + [0.0] * (NM - len(s))
    return (_a_trimestres(pad(deu["interes"])), _a_trimestres(pad(deu["servicio"])),
            _a_trimestres(pad(deu["desemb"])))


INTE_LIBRO_Q, SRV_LIBRO_Q, DES_LIBRO_Q = _libro_deuda()


def cerrar(ipm=IPM_LIBRO, ke=None, kd=None, ppdi=None, lo=0.5, hi=12.0, it=200):
    # Ver el comentario de `motor_cajamarca.cerrar`: sin cambio de signo esto
    # devolveria el borde del intervalo como si fuera el cierre.
    f = lambda m: van(m, ipm, ke, kd, ppdi)
    if f(lo) * f(hi) > 0:
        raise ValueError(
            f"la tarifa variable no cierra en [{lo:,.4f}, {hi:,.4f}]: "
            f"VAN {f(lo):,.2f} y {f(hi):,.2f}, sin cambio de signo")
    for _ in range(it):
        m = (lo + hi) / 2
        if van(m, ipm, ke, kd, ppdi) > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def resumen(ipm=IPM_LIBRO, tarifa=None, ke=None, kd=None, ppdi=None):
    """Las tres cifras de `Resumen`, en S/ miles sin IGV del ano 1 de operacion.

    El libro las arma con MINIFS sobre la serie mensual por 12, es decir el
    primer mes de operacion anualizado, no la suma del ano calendario.
    """
    tarifa = cerrar(ipm, ke, kd, ppdi) if tarifa is None else tarifa
    f18 = IPM.factores(ipm, FLAG_OM)
    im, im_l = (1 + ipm) ** (1 / 12) - 1, (1 + IPM_LIBRO) ** (1 / 12) - 1
    base = FIJO_BASE_LIBRO * (1 + im) / (1 + im_l)
    fijo_m = [base * f18[m] * FLAG_OM[m] for m in range(NM)]
    var_m = [(0.0 if FLAG_OM[m] == 0 else tarifa * KG[m] * f18[m]) / 1000
             for m in range(NM)]
    pos = [m for m in range(NM) if var_m[m] > 0]
    return {"tarifa": tarifa, "ppdi_anual": PPDI_LIBRO if ppdi is None else ppdi,
            "ppdmo_fijo": min(fijo_m[m] for m in pos) * 12,
            "ppdmo_variable": min(var_m[m] for m in pos) * 12}


if __name__ == "__main__":
    fijo, var, base, f18, _, _ = pagos()
    print("=== control contra el libro ===")
    print(f"  PPDMO fijo trimestral, desvio maximo   : "
          f"{max(abs(fijo[i] - D['fijo'][i]) for i in range(NQ)):.9f}")
    print(f"  PPDMO variable trimestral, desvio max  : "
          f"{max(abs(var[i] - D['var'][i]) for i in range(NQ)):.9f}")
    print(f"  VAN del sombra con parametros del libro: {van(TARIFA_LIBRO):.6f}")
    print(f"  tarifa que cierra                      : {cerrar():.10f}"
          f"   (libro {TARIFA_LIBRO:.10f})")
