"""Extrae el texto de los PDF de las NIIF que publica el MEF.

pypdf no corre en este contenedor (el backend de cryptography revienta), asi
que se descomprimen los flujos y se rearma el texto por bloques BT..ET. Sale
texto corrido, sin saltos de pagina, suficiente para buscar parrafos.
"""
import re, sys, zlib, pathlib


def texto(ruta):
    d = pathlib.Path(ruta).read_bytes()
    out = []
    for m in re.finditer(rb'stream\r?\n(.*?)endstream', d, re.S):
        try:
            s = zlib.decompress(m.group(1))
        except Exception:
            continue
        for bt in re.finditer(rb'BT(.*?)ET', s, re.S):
            linea = []
            for tj in re.finditer(rb'\[(.*?)\]\s*TJ|\((?:\\.|[^\\()])*\)\s*Tj',
                                  bt.group(1), re.S):
                partes = [x.group(0)[1:-1] for x in
                          re.finditer(rb'\((?:\\.|[^\\()])*\)', tj.group(0))]
                linea.append(b''.join(partes))
            if linea:
                out.append(b''.join(linea))
    t = b'\n'.join(out).decode('latin-1')
    return t.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')


if __name__ == "__main__":
    for p in sys.argv[1:]:
        p = pathlib.Path(p)
        d = p.with_suffix(".txt")
        d.write_text(texto(p))
        print(d.name, len(d.read_text()))
