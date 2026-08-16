#!/usr/bin/env python3
"""
procesar_sol.py  (v2)

Realce de manchas solares en fotografías de disco completo en luz
blanca. Pensado para NEF de Nikon Z8; acepta cualquier RAW soportado
por libraw y también TIFF/PNG/JPEG.

Cambios respecto a v1:
  * Flat RADIAL: se ajusta el perfil de oscurecimiento del limbo como
    mediana de la intensidad por anillos concéntricos y se divide por
    él. El flat gaussiano de v1 producía un anillo brillante y un borde
    hundido porque el desenfoque mezcla disco y fondo; el radial deja
    el cociente plano (1.000 +/- 0.006 hasta r/R = 0.95 en pruebas).
  * La fotosfera se mapea alta (en torno al 90% del blanco), de modo
    que el disco conserva el aspecto de una foto bien expuesta.
  * --apilar: promedia una ráfaga alineando por el centro del disco
    antes de procesar. El ruido cae como 1/sqrt(N).
  * --bin N: binning NxN previo. Con el disco ocupando una fracción
    del sensor de 45 Mpx, la óptica rara vez resuelve al nivel del
    píxel; bin 2 duplica la SNR sin pérdida real de detalle.
  * --recorte: recorta al disco con margen antes de guardar.

Salidas (según --formato: tiff16 defecto, tiff32, png16):
  <nombre>_manchas.tif   resultado estirado y enfocado
  <nombre>_lineal.tif    cociente aplanado sin estirar (--lineal)
  <nombre>_prev.jpg      previsualización de 8 bits

Nota Z8: dispara en compresión RAW "sin pérdida" (Lossless). Los NEF
"Alta eficiencia" (HE/HE*) usan TicoRAW y libraw < 0.21.2 no los abre.

Dependencias:  pip install rawpy opencv-python numpy

Uso:
  python procesar_sol.py DSC_0001.NEF --recorte
  python procesar_sol.py ráfaga*.NEF --apilar --bin 2 --recorte --salida ./out
  python procesar_sol.py DSC_0001.NEF --bajo 0.70 --alto 1.02 --formato tiff32 --lineal
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

try:
    import rawpy
    HAY_RAWPY = True
except ImportError:
    HAY_RAWPY = False

EXT_RAW = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".raf", ".dng",
           ".orf", ".rw2", ".pef", ".srw", ".x3f"}


# ---------------------------------------------------------------- carga

def abrir_raw(ruta: Path):
    if not HAY_RAWPY:
        sys.exit("Falta rawpy para leer RAW: pip install rawpy")
    try:
        return rawpy.imread(str(ruta))
    except rawpy.LibRawError as e:
        sys.exit(f"libraw no pudo abrir {ruta.name}: {e}\n"
                 "Si es un NEF 'Alta eficiencia' (HE/HE*), actualiza "
                 "rawpy o dispara en Lossless.")


def cargar_superpixel(ruta: Path, modo: str) -> np.ndarray:
    """Superpíxel 2x2 sobre el mosaico Bayer crudo, sin demosaicado.

    modo 'super'  suma los cuatro fotositos de cada celda (R + G + G + B).
    modo 'superg' promedia solo los dos verdes.

    Sale a la mitad de resolución lineal y sin interpolar, así que el ruido
    de píxeles vecinos no queda correlacionado. Tampoco se aplica balance de
    blancos: el valor es proporcional a los electrones totales de la celda,
    que es lo que interesa para fotometría.
    """
    if ruta.suffix.lower() not in EXT_RAW:
        sys.exit("Los modos super y superg necesitan un RAW, no un TIFF o JPEG.")
    with abrir_raw(ruta) as raw:
        b = raw.raw_image_visible.astype(np.float32)
        col = np.asarray(raw.raw_colors_visible)
        negro = np.asarray(raw.black_level_per_channel, dtype=np.float32)
        b = np.maximum(b - negro[col], 0.0)
        blanco = max(float(raw.white_level) - float(negro.mean()), 1.0)

    h, w = (b.shape[0] // 2) * 2, (b.shape[1] // 2) * 2
    celdas = b[:h, :w].reshape(h // 2, 2, w // 2, 2)
    if modo == "super":
        out = celdas.mean(axis=(1, 3))
    else:
        # en rawpy 0=R, 1=G, 2=B, 3=G2
        verde = np.isin(col[:h, :w], (1, 3)).astype(np.float32)
        vc = verde.reshape(h // 2, 2, w // 2, 2)
        out = (celdas * vc).sum(axis=(1, 3)) / np.maximum(vc.sum(axis=(1, 3)), 1.0)
    return np.clip(out / blanco, 0.0, 1.0)


def cargar(ruta: Path, canal: str) -> np.ndarray:
    """Imagen como float32 en [0, 1], un solo canal."""
    if canal in ("super", "superg"):
        return cargar_superpixel(ruta, canal)

    if ruta.suffix.lower() in EXT_RAW:
        with abrir_raw(ruta) as raw:
            rgb = raw.postprocess(
                gamma=(1, 1), no_auto_bright=True, output_bps=16,
                use_camera_wb=True, user_flip=0,
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                median_filter_passes=0,
            )
        img = rgb.astype(np.float32) / 65535.0
    else:
        bgr = cv2.imread(str(ruta), cv2.IMREAD_UNCHANGED)
        if bgr is None:
            sys.exit(f"No se pudo leer {ruta}")
        if bgr.dtype == np.uint16:
            img = bgr.astype(np.float32) / 65535.0
        elif bgr.dtype == np.float32:
            img = bgr
        else:
            img = bgr.astype(np.float32) / 255.0
        if img.ndim == 3:
            img = img[:, :, ::-1]

    if img.ndim == 2:
        return img
    canales = {"r": 0, "g": 1, "b": 2}
    if canal in canales:
        return img[:, :, canales[canal]]
    # 'l': luminancia BT.709. Promediar canales demosaicados baja el ruido
    # medido, pero parte de esa bajada es paso-bajo introducido por la
    # interpolación de R y B, no fotones nuevos.
    return (0.2126 * img[:, :, 0] + 0.7152 * img[:, :, 1]
            + 0.0722 * img[:, :, 2])


def binear(g: np.ndarray, n: int) -> np.ndarray:
    """Binning n x n por promedio."""
    if n <= 1:
        return g
    h, w = (g.shape[0] // n) * n, (g.shape[1] // n) * n
    return g[:h, :w].reshape(h // n, n, w // n, n).mean(axis=(1, 3))


# ------------------------------------------------------- geometría disco

def detectar_disco(g: np.ndarray):
    """Máscara del disco, centro (cx, cy) y radio R en píxeles."""
    fondo = np.percentile(g, 5)
    pico = np.percentile(g, 99.5)
    m = (g > fondo + 0.25 * (pico - fondo)).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)

    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        sys.exit("No se detectó el disco solar. Revisa la exposición.")
    c = max(cnts, key=cv2.contourArea)
    (cx, cy), R = cv2.minEnclosingCircle(c)

    m2 = np.zeros_like(m)
    cv2.circle(m2, (int(round(cx)), int(round(cy))), int(R), 1, -1)
    return m2.astype(np.float32), cx, cy, R


# ------------------------------------------------------------ apilado

def apilar(imagenes: list[np.ndarray]) -> np.ndarray:
    """Alinea por el centro del disco (traslación) y promedia."""
    ref = imagenes[0]
    _, cx0, cy0, _ = detectar_disco(ref)
    suma = ref.astype(np.float64).copy()
    for g in imagenes[1:]:
        _, cx, cy, _ = detectar_disco(g)
        M = np.float32([[1, 0, cx0 - cx], [0, 1, cy0 - cy]])
        suma += cv2.warpAffine(g, M, (ref.shape[1], ref.shape[0]),
                               flags=cv2.INTER_LINEAR)
    return (suma / len(imagenes)).astype(np.float32)


# ------------------------------------------------------------ procesado

def flat_radial(g, m, cx, cy, R, nbins=200):
    """Perfil de limbo por mediana de anillos; devuelve el flat 2D."""
    Y, X = np.indices(g.shape)
    rr = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / R
    idx = np.clip((rr * nbins).astype(int), 0, nbins)

    perfil = np.full(nbins + 1, np.nan)
    for i in range(nbins + 1):
        sel = (idx == i) & (m > 0.5)
        if sel.sum() > 100:
            perfil[i] = np.median(g[sel])
    ok = ~np.isnan(perfil)
    perfil = np.interp(np.arange(nbins + 1),
                       np.flatnonzero(ok), perfil[ok])
    perfil[:3] = perfil[3]                 # bins centrales, pocos píxeles
    ker = np.hanning(9)
    ker /= ker.sum()
    # replicar bordes antes de convolucionar: el modo "same" de
    # np.convolve rellena con ceros y hundiría el perfil en los extremos
    perfil = np.convolve(np.pad(perfil, 4, mode="edge"), ker, mode="valid")

    return np.interp(rr.ravel(), np.arange(nbins + 1) / nbins,
                     perfil).reshape(g.shape).astype(np.float32), rr


def procesar(g, bajo, alto, enfoque=0.8):
    """Devuelve (resultado, cociente lineal, máscara, info)."""
    info = {}
    m, cx, cy, R = detectar_disco(g)
    dentro = g[m > 0.5]
    info["radio_px"] = R
    info["centro"] = (cx, cy)
    info["fraccion_saturada"] = float((dentro > 0.985).mean())

    # Suavizado previo. El sigma se escala con el radio del disco, no se fija
    # en píxeles: con sigma constante en píxeles cualquier salida a media
    # resolución (--bin 2, --canal super) recibía el doble de suavizado
    # angular y perdía en torno al 40 % de la profundidad de cada mancha,
    # lo que falseaba toda comparación entre escalas.
    sigma = max(0.5, R / 600.0)
    info["sigma_previo"] = sigma
    g = cv2.GaussianBlur(g, (0, 0), sigma)

    flat, rr = flat_radial(g, m, cx, cy, R)
    cociente = np.where(m > 0.5, g / np.maximum(flat, 1e-6), 0.0)
    cociente = cociente.astype(np.float32)

    # estirado lineal: la fotosfera (cociente = 1) queda en
    # (1 - bajo) / (alto - bajo); con 0.60 y 1.04 eso es 0.91
    r = np.clip((cociente - bajo) / (alto - bajo), 0.0, 1.0)

    # suavizar el borde exterior de la máscara para evitar el aro duro
    borde = np.clip((1.0 - rr) * 40.0, 0.0, 1.0) * m
    r = (r * borde).astype(np.float32)

    # Máscara de enfoque. OJO: con el disco pequeño en el fotograma la
    # escala de imagen (arcsec/px) suele estar por debajo del límite de
    # difracción más seeing, así que a sigma 2 px no hay señal solar que
    # realzar y esto solo amplifica ruido. Usar --enfoque 0 en ese caso.
    if enfoque > 0:
        fina = cv2.GaussianBlur(r, (0, 0), 2.0)
        r = np.clip(r + enfoque * (r - fina), 0.0, 1.0)
        media = cv2.GaussianBlur(r, (0, 0), 8.0)
        r = np.clip(r + 0.375 * enfoque * (r - media), 0.0, 1.0)
    return (r * borde).astype(np.float32), cociente, m, info


# ----------------------------------------------------------- exportación

def guardar(img01, base: Path, sufijo: str, formato: str) -> Path:
    if formato == "tiff32":
        ruta = base.with_name(base.name + sufijo + ".tif")
        cv2.imwrite(str(ruta), img01.astype(np.float32))
    elif formato == "tiff16":
        ruta = base.with_name(base.name + sufijo + ".tif")
        cv2.imwrite(str(ruta), np.round(np.clip(img01, 0, 1)
                                        * 65535).astype(np.uint16))
    else:  # png16
        ruta = base.with_name(base.name + sufijo + ".png")
        cv2.imwrite(str(ruta), np.round(np.clip(img01, 0, 1)
                                        * 65535).astype(np.uint16))
    return ruta


def recortar(imgs, cx, cy, R, margen=1.15):
    """Recorta todas las imágenes al disco con margen."""
    h, w = imgs[0].shape
    r = int(R * margen)
    y0, y1 = max(0, int(cy) - r), min(h, int(cy) + r)
    x0, x1 = max(0, int(cx) - r), min(w, int(cx) + r)
    return [im[y0:y1, x0:x1] for im in imgs]


# ------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser(description="Realce de manchas solares v2")
    ap.add_argument("archivos", nargs="+", help="RAW, TIFF, PNG o JPEG")
    ap.add_argument("--salida", default=".", help="carpeta de salida")
    ap.add_argument("--formato", default="tiff16",
                    choices=["tiff16", "tiff32", "png16"])
    ap.add_argument("--apilar", action="store_true",
                    help="promedia todos los archivos como una ráfaga")
    ap.add_argument("--bin", type=int, default=1, metavar="N",
                    help="binning NxN previo (2 recomendado en la Z8)")
    ap.add_argument("--recorte", action="store_true",
                    help="recorta la salida al disco con margen del 15%%")
    ap.add_argument("--lineal", action="store_true",
                    help="exporta también el cociente sin estirar")
    ap.add_argument("--sin-prev", action="store_true")
    ap.add_argument("--canal", default="g",
                    choices=["r", "g", "b", "l", "super", "superg"],
                    help="g/r/b un canal demosaicado; l luminancia BT.709; "
                         "super superpíxel 2x2 del Bayer con los 4 fotositos; "
                         "superg superpíxel con los 2 verdes. Los dos últimos "
                         "salen a media resolución y sin interpolar")
    ap.add_argument("--bajo", type=float, default=0.60,
                    help="cociente que se mapea a negro (defecto 0.60)")
    ap.add_argument("--alto", type=float, default=1.04,
                    help="cociente que se mapea a blanco (defecto 1.04)")
    ap.add_argument("--enfoque", type=float, default=0.8, metavar="G",
                    help="ganancia de la máscara de enfoque; 0 la desactiva. "
                         "Con menos de 1500 px de diámetro de disco usa 0")
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    rutas = [Path(n) for n in args.archivos]
    if args.apilar:
        print(f"Apilando {len(rutas)} imágenes...")
        imgs = [binear(cargar(p, args.canal), args.bin) for p in rutas]
        lotes = [(rutas[0].stem + f"_apilado{len(imgs)}", apilar(imgs))]
    else:
        lotes = [(p.stem, binear(cargar(p, args.canal), args.bin))
                 for p in rutas]

    for nombre, g in lotes:
        print(f"[{nombre}]")
        r, lineal, m, info = procesar(g, args.bajo, args.alto, args.enfoque)

        print(f"  radio del disco: {info['radio_px']:.0f} px"
              + f"  sigma previo {info['sigma_previo']:.2f} px"
              + (f"  (bin {args.bin})" if args.bin > 1 else ""))
        if info["fraccion_saturada"] > 0.01:
            print(f"  AVISO: {100*info['fraccion_saturada']:.1f}% del disco "
                  "saturado; esa información no es recuperable.")

        if args.recorte:
            cx, cy = info["centro"]
            r, lineal = recortar([r, lineal], cx, cy, info["radio_px"])

        base = salida / nombre
        f = guardar(r, base, "_manchas", args.formato)
        print(f"  -> {f.name}")

        if args.lineal:
            lin = lineal if args.formato == "tiff32" \
                else np.clip(lineal / 1.25, 0, 1)
            f = guardar(lin, base, "_lineal", args.formato)
            print(f"  -> {f.name}")

        if not args.sin_prev:
            prev = base.with_name(base.name + "_prev.jpg")
            cv2.imwrite(str(prev), np.round(r * 255).astype(np.uint8),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"  -> {prev.name}")


if __name__ == "__main__":
    main()
