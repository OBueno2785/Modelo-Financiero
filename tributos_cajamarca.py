"""Bloque tributario anual de Cajamarca (`EEFF Anuales` filas 82-98).

Se calcula dos veces con la misma mecanica, primero la participacion de
trabajadores y despues el Impuesto a la Renta sobre la utilidad ya neta de esa
participacion:

    DEDUCCIONES  el ingreso financiero del activo financiero no es renta
                 gravada mientras dura la construccion (`fila 84`)
    ADICIONES    lo deducido se devuelve en cuotas de 1/15 desde que empieza a
                 cobrarse el PPDI (`fila 85`)
    PERDIDAS     arrastre "sistema B": la perdida se acumula y se aplica entera
                 contra la primera utilidad que aparece (`filas 87 y 88`)
"""
import json

D = json.load(open("/mnt/project-files/generador/caj_tributos.json"))
TASA_PART = 0.05          # Inputs!D13
TASA_IR = 0.295           # Inputs!D14
PLAZO = 15                # Inputs!D214, anos de pago del PPDI


def usar_tributos(part=TASA_PART, ir=TASA_IR):
    """Las tasas vienen de la plantilla. Los valores de arriba son los del libro
    y quedan como defecto para reproducirlo."""
    global TASA_PART, TASA_IR
    TASA_PART, TASA_IR = part, ir


def _bloque(uai, deduccion, adicion):
    """Filas 86 a 88: utilidad tributaria, perdidas acumuladas y base imponible."""
    base, perd = [], 0.0
    for i in range(len(uai)):
        u = uai[i] + deduccion[i] + adicion[i]
        perd_ant = perd
        perd = min(0.0, u + perd_ant)
        if perd_ant + u < 0 and perd == 0:
            b = u
        elif perd < 0:
            b = 0.0
        else:
            b = u + perd_ant
        base.append(max(0.0, b))
    return base


def _deducciones(serv_constr, ing_fin, flag_ppdi):
    """`PPDI!481` deduce mientras el ANO tenga servicio de construccion (`D411>1`,
    no un mes de corte) y `PPDI!482` devuelve el acumulado en cuotas de 1/PLAZO.

    La formula del libro NO cuenta cuotas: emite acumulado/PLAZO en todo ano con
    cobro de PPDI y sin deduccion, indefinidamente. Que salgan exactamente 15 es
    una coincidencia de Cajamarca: sus 60 cuotas trimestrales tocan 16 anos
    calendario y el primero se apaga solo porque ese ano todavia deduce. Con 80
    cuotas la formula del libro adicionaria 20/15 = 133 % de lo deducido. El
    divisor es un plazo TRIBUTARIO y el cobro un plazo CONTRACTUAL; aqui son dos
    campos independientes, asi que el tope va explicito. Reproduce Cajamarca
    identico y no se dispara fuera de su punto."""
    ded = [(-ing_fin[i] if serv_constr[i] > 1 else 0.0) for i in range(len(ing_fin))]
    adi, acum, emitidas = [], 0.0, 0
    for i in range(len(ded)):
        acum += ded[i]
        if ded[i] < 0 or flag_ppdi[i] <= 0 or emitidas >= PLAZO:
            adi.append(0.0)
            continue
        emitidas += 1
        adi.append(-acum / PLAZO)
    return ded, adi


def tributos(ventas, costos_sin_part, ing_fin, gastos_fin, serv_constr, flag_ppdi):
    """Devuelve participacion de trabajadores e Impuesto a la Renta, por ano."""
    ded, adi = _deducciones(serv_constr, ing_fin, flag_ppdi)
    uai_p = [ventas[i] - costos_sin_part[i] + ing_fin[i] - gastos_fin[i]
             for i in range(len(ventas))]
    part = [b * TASA_PART for b in _bloque(uai_p, ded, adi)]
    uai_i = [uai_p[i] - part[i] for i in range(len(ventas))]
    ir = [b * TASA_IR for b in _bloque(uai_i, ded, adi)]
    return part, ir


if __name__ == "__main__":
    n = len(D["anio"])
    costos = [sum(D[f"c{r}"][i] for r in (56, 57, 58, 59, 60, 61, 62, 63))
              + D["c_constr"][i] for i in range(n)]
    part, ir = tributos(D["ventas"], costos, D["ing_fin"], D["gastos_fin"],
                        D["serv_constr"], D["f11"])
    print(f"{'':<28}{'motor':>16}{'libro':>16}{'desvio':>14}")
    print(f"  {'participacion, total':<26}{sum(part):>16,.6f}"
          f"{sum(D['p89']):>16,.6f}{sum(part) - sum(D['p89']):>14.8f}")
    print(f"  {'Impuesto a la Renta, total':<26}{sum(ir):>16,.6f}"
          f"{sum(D['i98']):>16,.6f}{sum(ir) - sum(D['i98']):>14.8f}")
    print(f"  {'desvio maximo ano a ano':<26}{'':>16}{'':>16}"
          f"{max(max(abs(part[i] - D['p89'][i]), abs(ir[i] - D['i98'][i])) for i in range(n)):>14.8f}")
