"""VALIDACION del cierre de la tarifa variable de Cajamarca (cerrar_caj_var.py).

Prueba tres cosas que el cierre original resuelve de forma aproximada:
  A) el desfase del impuesto: el IR se carga una vez al anio, no en el mismo
     trimestre en que se cobra el ingreso;
  B) la consistencia del PPDI con cada escenario de intereses;
  C) el efecto de tratar el delta de PPDI como no gravado.
"""
import json

d = json.load(open("caj_sombra.json"))
fc, movar, ppdi, inte, meses, ir = (d["fc"], d["movar"], d["ppdi"],
                                    d["inte"], d["meses"], d["ir"])
N = len(fc)
KE_N = 0.12622648560136618
KD_L, KD_N = 0.09288787939497108, 0.1009295682936526
PPDI_L = 46472.546554744986
PPDI_BAJO, PPDI_ALTO = 46457.924728388025, 47008.299493355
TARIFA_L, VAR_L = 0.004317668971541212, 28935.325022853205
TAU = 0.05 + 0.295 * 0.95

VIVOS = [i for i in range(N) if meses[i] > 0]
CARGO_IR = [i for i in VIVOS if abs(ir[i]) > 1e-9]


def descuento(ke):
    km, acc, out = (1 + ke) ** (1 / 12) - 1, 0, []
    for m in meses:
        acc += m
        out.append(0.0 if m == 0 else 1 / (1 + km) ** acc)
    return out


def cuando_paga(i):
    """Trimestre en que se carga el IR del anio al que pertenece i."""
    for j in CARGO_IR:
        if j >= i:
            return j
    return CARGO_IR[-1]


PAGA = {i: cuando_paga(i) for i in VIVOS}


def cerrar(k_int, ppdi_n, desfase_ir, gravar_ppdi):
    f = descuento(KE_N)
    dint = [(KD_N / KD_L - 1) * x * k_int for x in inte]
    rp = ppdi_n / PPDI_L

    def van(k):
        base = sum(fc[i] * f[i] for i in range(N))
        # ingreso variable extra
        if desfase_ir:
            for i in VIVOS:
                dv = movar[i] * (k - 1)
                base += dv * f[i] - TAU * dv * f[PAGA[i]]
        else:
            for i in VIVOS:
                base += movar[i] * (k - 1) * (1 - TAU) * f[i]
        # PPDI
        esc = (1 - TAU) if gravar_ppdi else 1.0
        for i in VIVOS:
            base += ppdi[i] * (rp - 1) * esc * f[i]
        # intereses
        for i in VIVOS:
            base -= dint[i] * (1 - TAU) * f[i]
        return base

    lo, hi = 0.5, 1.6
    for _ in range(200):
        m = (lo + hi) / 2
        if van(m) > 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


casos = [
    ("original del tablero",              1.0, PPDI_BAJO, False, False),
    ("+ IR con su desfase anual",         1.0, PPDI_BAJO, True,  False),
    ("+ delta de PPDI gravado",           1.0, PPDI_BAJO, True,  True),
    ("intereses congelados, original",    0.0, PPDI_BAJO, False, False),
    ("intereses congelados, PPDI coherente y IR desfasado",
                                          0.0, PPDI_ALTO, True,  False),
]
print(f"{'caso':<54}{'k':>10}{'tarifa':>12}{'PPDMO var. anual':>20}{'vs libro':>10}")
for nom, ki, pn, des, gp in casos:
    k = cerrar(ki, pn, des, gp)
    print(f"  {nom:<52}{k:>10.6f}{TARIFA_L*k:>12.7f}{VAR_L*k:>20,.2f}{(k-1)*100:>9.2f} %")
