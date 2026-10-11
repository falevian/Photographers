# -*- coding: utf-8 -*-
"""Pone al día los pesos que el sitio declara de cada documento.

La portada (index.html, etiqueta de cada tarjeta) y el README (última columna de
las tablas, en español y en inglés) dicen cuánto pesa cada archivo. Esas cifras
se escriben a mano y se quedan atrás en cuanto una página cambia. Este script
las recalcula a partir del tamaño real: KB = bytes/1024 redondeado; a partir de
1024 KB, MB con un decimal (coma en español y en la portada, punto en inglés).

Uso, desde la raíz del repositorio:
    python3 scripts/sitio/pesos.py           corrige index.html y README.md
    python3 scripts/sitio/pesos.py --mira    solo dice qué cifras no coinciden
"""
import io, os, re, sys

SOLO_MIRAR = "--mira" in sys.argv


def peso(ruta, coma=True):
    kb = os.path.getsize(ruta) / 1024.0
    if kb < 1023.5:
        return "%d KB" % round(kb)
    s = "%.1f MB" % (kb / 1024.0)
    return s.replace(".", ",") if coma else s


def readme(txt, cambios):
    corte = txt.index("## English")
    fin = txt.index("## Paseo") if "## Paseo" in txt else len(txt)
    fila = re.compile(r"^(\| \[`([^`]+\.html)`\]\([^)]+\) \|.*\| )(\d[\d.,]* [KM]B)( \|)$", re.M)

    def tramo(sec, coma):
        def f(m):
            if not os.path.exists(m.group(2)):
                return m.group(0)
            nuevo = peso(m.group(2), coma)
            if nuevo != m.group(3):
                cambios.append("README %s  %s: %s → %s" % ("es" if coma else "en", m.group(2), m.group(3), nuevo))
            return m.group(1) + nuevo + m.group(4)
        return fila.sub(f, sec)

    # la sección del paseo no se toca: sus pesos los pone integra-ficha-paseo.py
    # (bytes//1024) y tienen que coincidir con los de la portada paseos/index.html
    return tramo(txt[:corte], True) + tramo(txt[corte:fin], False) + txt[fin:]


def portada(txt, cambios):
    tarjeta = re.compile(r'(<div class="fn">([^<]+)</div>.*?<span class="tag">)([^<]+)(</span>)', re.S)

    def f(m):
        ruta = m.group(2).split(" · ")[0].strip()
        if not os.path.exists(ruta):
            return m.group(0)
        nuevo = peso(ruta, True)
        if nuevo != m.group(3):
            cambios.append("index      %s: %s → %s" % (ruta, m.group(3), nuevo))
        return m.group(1) + nuevo + m.group(4)

    return tarjeta.sub(f, txt)


def frase_explorador(txt, cambios, donde):
    """La nota sobre el explorador de distancias cita su peso en el texto."""
    ruta = "explorador_distancias.html"
    for patron, coma in ((r"(explorador de distancias pesa )(\d[\d.,]* MB)", True),
                         (r"(distance explorer weighs )(\d[\d.,]* MB)", False)):
        def f(m, coma=coma):
            nuevo = peso(ruta, coma)
            if nuevo != m.group(2):
                cambios.append("%s  nota del explorador: %s → %s" % (donde, m.group(2), nuevo))
            return m.group(1) + nuevo
        txt = re.sub(patron, f, txt)
    return txt


def main():
    cambios = []
    for nombre, pasos in (("README.md", (readme, lambda t, c: frase_explorador(t, c, "README"))),
                          ("index.html", (portada, lambda t, c: frase_explorador(t, c, "index ")))):
        viejo = io.open(nombre, encoding="utf-8").read()
        nuevo = viejo
        for paso in pasos:
            nuevo = paso(nuevo, cambios)
        if nuevo != viejo and not SOLO_MIRAR:
            io.open(nombre, "w", encoding="utf-8").write(nuevo)
    for c in cambios:
        print(c)
    print("%d cifras %s" % (len(cambios), "por corregir" if SOLO_MIRAR else "corregidas") if cambios else "todos los pesos coinciden")
    return 1 if (cambios and SOLO_MIRAR) else 0


if __name__ == "__main__":
    sys.exit(main())
