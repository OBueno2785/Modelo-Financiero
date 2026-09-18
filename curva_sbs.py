"""Curva cupon cero soberana de la SBS al 11-set-2026, leida del reporte de dos
curvas que descargo Oscar. Interpola a cualquier plazo en anios, que es como la
usan los dos libros: el soberano base del Kd sale de la curva a la vida media de
la deuda (San Martin 8.84 anios, Cajamarca 9.2545)."""
import re, html

FECHA = "2026-09-11"


def _leer(path="sbs_dos_curvas.html"):
    txt = html.unescape(re.sub(r"<[^>]+>", "|", open(path, encoding="latin-1").read()))
    campos = [c.strip() for c in re.split(r"\|+", txt) if c.strip()]
    sol, usd = {}, {}
    i = 0
    while i < len(campos) - 3:
        if re.fullmatch(r"\d+", campos[i]) and re.fullmatch(r"\d{2}/\d{2}/\d{4}", campos[i+1]):
            dias = int(campos[i+2])
            try:
                sol[dias] = float(campos[i+3]) / 100
            except ValueError:
                i += 1
                continue
            if i + 4 < len(campos):
                try:
                    usd[dias] = float(campos[i+4]) / 100
                except ValueError:
                    pass
            i += 5
        else:
            i += 1
    return sol, usd


SOL, USD = _leer()


def punto(curva, anios):
    """Interpolacion lineal en dias, igual que FORECAST.LINEAR del libro."""
    d = anios * 360
    ks = sorted(curva)
    if d <= ks[0]:
        return curva[ks[0]]
    if d >= ks[-1]:
        return curva[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= d <= b:
            return curva[a] + (curva[b] - curva[a]) * (d - a) / (b - a)


if __name__ == "__main__":
    print(f"Curva SBS {FECHA}: {len(SOL)} plazos en soles, {len(USD)} en dolares")
    for nom, anios in [("San Martin (vida media 8.84)", 8.84),
                       ("Cajamarca (vida media 9.2545)", 9.254513642313936),
                       ("15 anios", 15.0)]:
        print(f"  {nom:<32} soles {punto(SOL, anios):.6%}   dolares {punto(USD, anios):.6%}")
