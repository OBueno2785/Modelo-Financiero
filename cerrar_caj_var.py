"""Recierra la tarifa variable del PPDMO de Cajamarca con parametros de hoy.

Usa los flujos en cache del modelo sombra del libro (M.Sombra, fila 70) y
resuelve el factor k = tarifa_nueva / tarifa_libro que vuelve a poner el VAN
financiero al Ke en cero. Solo se mueven tres cosas: el Ke de descuento, el
PPDI (que ya viene cerrado del motor) y los intereses de la deuda senior,
escalados por Kd_nuevo / Kd_libro. La pata fija no entra: es cost-plus.
"""
import json

d = json.load(open("caj_sombra.json"))
fc, movar, ppdi, inte, meses = d["fc"], d["movar"], d["ppdi"], d["inte"], d["meses"]

KE_L, KE_N = 0.12896919132096363, 0.12622648560136618
KD_L, KD_N = 0.09288787939497108, 0.1009295682936526
PPDI_L, PPDI_N = 46472.546554744986, 46457.924728388025
TARIFA_L = 0.004317668971541212           # Resumen!J6
VAR_L = 28935.325022853205                # Resumen!C7, S/ miles del ano 2031
TAU = 0.05 + 0.295 * 0.95                 # participacion + IR sobre el margen


def descuento(ke):
    km, acc, out = (1 + ke) ** (1 / 12) - 1, 0, []
    for m in meses:
        acc += m
        out.append(0.0 if m == 0 else 1 / (1 + km) ** acc)
    return out


def cerrar(k_int):
    f = descuento(KE_N)
    dint = [(KD_N / KD_L - 1) * x * k_int for x in inte]
    rp = PPDI_N / PPDI_L

    def van(k):
        return sum((fc[i] + movar[i] * (k - 1) * (1 - TAU)
                    + ppdi[i] * (rp - 1) - dint[i] * (1 - TAU)) * f[i]
                   for i in range(len(fc)))
    lo, hi = 0.5, 1.6
    for _ in range(200):
        m = (lo + hi) / 2
        if van(m) > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


if __name__ == "__main__":
    f = descuento(KE_L)
    print(f"VAN del libro con su propio Ke : {sum(fc[i]*f[i] for i in range(len(fc))):.6f}")
    for lbl, ki in [("intereses corregidos por el Kd", 1.0),
                    ("intereses como en el libro", 0.0)]:
        k = cerrar(ki)
        print(f"{lbl:<32} k={k:.6f}  tarifa={TARIFA_L*k:.7f}  "
              f"PPDMO variable anual={VAR_L*k:,.2f} S/ miles ({(k-1)*100:+.2f} %)")
