"""Rehace el factor de reajuste del PPDMO fijo de Cajamarca y lo corre con otros IPM.

Reproduce PPDMO!D21 y la fila 23 (servicio fijo mensual) del libro desde las
primitivas: costo fijo anual, margen de 15 %, gatillo de 3 % y la malla de
flags. Valida contra el libro y luego cambia la proyeccion de IPM.
"""
import json, math

d = json.load(open("caj_ppdmo_rows.json"))
f14 = [v or 0 for v in d["flag14"]]
s30 = d["serv30"]
CF, MARGEN, GAT = 5795876.831843245, 0.15, 0.03
N = len(f14)


def construir(ipm_anual):
    im = (1 + ipm_anual) ** (1 / 12) - 1
    f15 = [im * f14[t] for t in range(N)]
    f16 = [0.0] * N
    for t in range(1, N):
        acc = sum(f15[:t + 1]) - sum(f16[:t])
        f16[t] = acc if (f15[t] > 0 and acc >= GAT) else 0.0
    f17 = [1.0] * N
    for t in range(1, N):
        f17[t] = f17[t - 1] * (1 + im) if (f14[t] == 0 and t + 1 < N and f14[t + 1] == 1) else 1.0
    f18 = [1.0] * N
    for t in range(1, N):
        v = 1.0 if f14[t] == 0 else f18[t - 1] * (1 + f16[t]) * f14[t]
        f18[t] = math.trunc(v * 1e5) / 1e5
    d21 = CF / 12000 * sum(v for v in f17 if v > 1) * (1 + MARGEN)
    return d21, [d21 * f18[t] * f14[t] for t in range(N)]


if __name__ == "__main__":
    pos = [t for t in range(N) if isinstance(s30[t], (int, float)) and s30[t] > 0]
    base = None
    for ipm, nom in [(0.011892506870546438, "libro 1.1893 %"),
                     (0.0267, "IPM de hoy 2.67 %"),
                     (0.0226, "IPC del MMM 2.26 %")]:
        d21, s23 = construir(ipm)
        a1, tot = min(s23[t] for t in pos) * 12, sum(s23)
        base = base or (a1, tot)
        print(f"{nom:<22} D21={d21:.6f}  fijo anio 1={a1:10.3f} "
              f"({a1/base[0]-1:+.4%})  nominal={tot:11.1f} ({tot/base[1]-1:+.1%})")
