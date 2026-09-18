"""Factor de reajuste de ingresos del PPDMO de Cajamarca (hoja `PPDMO`, filas 13-18).

Cajamarca indexa **ingresos y costos con indices distintos**, a diferencia de
San Martin:

  - ingresos: IPM (`Inputs!D35`), con gatillo de 3 % (`Inputs!D37`) y TRUNC a
    5 decimales;
  - costos:   IPC de largo plazo (`Inputs!N23` = 2.00 %), sin gatillo, en
    `'OPEX proyecto'!13`.

Cambiar la proyeccion de IPM mueve **solo la pata de ingresos**.

    PPDMO!13  IPM mensual   = (1 + IPM anual)^(1/12) - 1
    PPDMO!15  = IPM mensual x flag de servicios operativos
    PPDMO!16  = acumulado de 15 desde el ultimo disparo; si llega al gatillo,
                se libera y se reinicia, si no, 0
    PPDMO!18  = TRUNC(anterior x (1 + 16) x flag ; 5)
"""
import json
import math

D = json.load(open("/mnt/project-files/generador/caj_sombra_full.json"))
FLAG = D["Pflag_om"]
N = len(FLAG)
IPM_LIBRO = 0.011892506870546438      # Inputs!D35 = J58
GATILLO = 0.03                        # Inputs!D37


def trunc5(x):
    # Excel trunca sobre su valor a 15 digitos significativos. Truncar el float
    # crudo corta un ulp de menos (1.09448 vive como 1.0944799...) y el error se
    # arrastra por toda la serie, asi que hay que limpiar el ruido antes.
    y = round(x * 1e5, 9)
    return math.floor(y) / 1e5 if y >= 0 else -(math.floor(-y) / 1e5)


def factores(ipm_anual=IPM_LIBRO, flag=None):
    """`flag` es la bandera de operacion del proyecto que se esta corriendo.

    Sin ella el reajuste se acumula sobre el calendario de Cajamarca, que es lo
    que trae el JSON del libro, y en un proyecto nuevo con otras fechas el
    gatillo del 3 % se dispara en el mes equivocado. Se queda como valor por
    defecto solo para reproducir el libro aprobado.
    """
    flag = FLAG if flag is None else flag
    n = len(flag)
    im = (1 + ipm_anual) ** (1 / 12) - 1
    f18, acum_15, acum_16, prev = [0.0] * n, 0.0, 0.0, 1.0
    for t in range(n):
        v15 = im * flag[t]
        acum_15 += v15
        pend = (acum_15 - acum_16) * (1 if v15 > 0 else 0)
        v16 = pend if pend >= GATILLO else 0.0
        acum_16 += v16
        f18[t] = trunc5(1.0 if flag[t] == 0 else prev * (1 + v16) * flag[t])
        prev = f18[t]
    return f18


if __name__ == "__main__":
    f = factores()
    lib = D["Pf18"]
    peor = max(abs(f[t] - lib[t]) for t in range(N) if FLAG[t] == 1)
    print(f"desvio maximo contra PPDMO!18 del libro : {peor:.12f}")
    print(f"factor al primer mes de operacion       : {f[FLAG.index(1)]:.8f}")
    for ipm in (IPM_LIBRO, 0.0267):
        g = factores(ipm)
        i0 = next(t for t in range(N) if FLAG[t] == 1)
        print(f"  IPM {ipm:7.4%}  factor mes 1 de O&M {g[i0]:.5f}   ultimo {g[-1]:.5f}")
