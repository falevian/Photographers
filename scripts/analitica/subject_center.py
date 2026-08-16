#!/usr/bin/env python3
"""
subject_center.py

Recorre uno o varios directorios, estima la posicion del sujeto principal en
cada imagen y mide su desplazamiento respecto al centro del fotograma.

Coordenadas (origen en el centro del fotograma, convencion fisica):

    x_norm = (cx - W/2) / (W/2)      en [-1, 1], positivo hacia la derecha
    y_norm = (H/2 - cy) / (H/2)      en [-1, 1], positivo hacia arriba
    r_norm = hypot(x_norm * a, y_norm) / hypot(a, 1),   a = W/H

r_norm mide la distancia al centro en unidades de semidiagonal, con la
correccion de relacion de aspecto incluida: 0 = centro exacto, 1 = esquina.
Asi 24x36, 6x6 y cualquier recorte son directamente comparables. La misma
metrica se usa para spread_norm (radio de giro del blob del sujeto); una
mascara uniforme sobre todo el fotograma da spread_norm = 1/sqrt(3) = 0.577,
valor que sirve de referencia para la confianza.

Estimadores del sujeto (--method):

  sharpness  energia laplaciana normalizada por luminancia local. A diafragma
             abierto el sujeto es la region enfocada, asi que este mapa es el
             mejor detector disponible sin modelos entrenados. Degrada con
             todo en foco (hiperfocal) o con grano de pelicula muy marcado.
  contrast   contraste de histograma: cada bloque puntua segun lo raro que es
             su color respecto al resto de la imagen. Detecta el sujeto por
             anomalia cromatica o tonal, no por foco.
  both       combinacion convexa, peso --w-sharp sobre el mapa de nitidez.

El centroide no se calcula sobre el mapa completo, que daria un valor
trivialmente proximo al centro, sino sobre la componente conexa que contiene
el maximo, umbralizada a --level de la altura del pico. Si esa componente
invade mas de --max-area del fotograma, el umbral sube hasta que no lo haga.

confidence = 1 - spread_norm/0.577 mide solo la compacidad del blob, no la
existencia real de un sujeto: una imagen de ruido puro puede dar confianza
alta. Sirve para descartar fotogramas sin region dominante (cielos, texturas
uniformes, escenas planas), no para validar la deteccion. Usa --overlay sobre
una muestra de 30 o 40 fotogramas y verifica a ojo antes de fiarte del lote.

Sesgo del estimador: cualquier proxy de saliencia tiene sesgo propio. Para un
contraste entre dos cuerpos o dos epocas eso no invalida el resultado, porque
el sesgo es comun a los dos grupos y el estadistico relevante es la
diferencia. No interpretes r_norm como una medida absoluta.

Dependencias: numpy y Pillow.
    pip install numpy pillow

Descriptores por fotograma, ademas de la geometria del sujeto: clave y latitud
en diafragmas, perfil de once zonas sobre L*, recorte de sombras y luces,
entropia tonal, a* y b* medios, croma, colorido, temperatura de color y Duv,
estadistica circular del tono, tono partido entre sombras y luces, acutancia,
grano, superficie en foco, anisotropia de bordes y pendiente espectral.

Limitacion del grano: se mide en el 20 % de teselas mas planas, donde se supone
que no hay detalle. En escenas con textura fina repartida por todo el cuadro
(follaje, gravilla, tejidos) esa suposicion falla y el valor queda sobrestimado,
por un factor que en las pruebas llega a 1.5. Sirve para comparar dentro de un
corpus homogeneo, no como medida absoluta de la emulsion.

Uso:
    python subject_center.py ./negativos --csv medidas.csv
    python subject_center.py ./M5 ./M4 --group-by top --overlay ./control
    python subject_center.py ./fotos --method sharpness --trim-border --jobs 8
    python subject_center.py ./rollos --infer-focal --tag model=M5 --tag film=TRI-X
    python subject_center.py ./fotos --no-traits        # solo geometria, mas rapido
"""

from __future__ import annotations

import argparse
import csv
import datetime
import math
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict, fields
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

Image.MAX_IMAGE_PIXELS = None  # escaneos grandes de pelicula

RASTER_EXT = {".jpg", ".jpeg", ".jpe", ".png", ".tif", ".tiff", ".webp", ".bmp"}
RAW_EXT = {".dng", ".nef", ".cr2", ".cr3", ".arw", ".raf", ".orf", ".rw2",
           ".pef", ".srw", ".iiq", ".3fr"}

TAG_MAKE, TAG_MODEL, TAG_DATETIME = 0x010F, 0x0110, 0x0132
TAG_EXIF_IFD = 0x8769
TAG_FNUMBER, TAG_DT_ORIGINAL = 0x829D, 0x9003
TAG_FOCAL, TAG_FOCAL35, TAG_LENS = 0x920A, 0xA405, 0xA434

RG_UNIFORM = 1.0 / math.sqrt(3.0)


@dataclass
class Row:
    path: str = ""
    group: str = ""
    width: int = 0
    height: int = 0
    orientation: str = ""
    aspect: float = float("nan")
    make: str = ""
    model: str = ""
    lens: str = ""
    focal_mm: float = float("nan")
    focal35_mm: float = float("nan")
    f_number: float = float("nan")
    datetime: str = ""
    method: str = ""
    x_norm: float = float("nan")
    y_norm: float = float("nan")
    r_norm: float = float("nan")
    spread_norm: float = float("nan")
    area_frac: float = float("nan")
    confidence: float = float("nan")
    peak_x_norm: float = float("nan")
    peak_y_norm: float = float("nan")
    # tono
    key_stops: float = float("nan")
    lum_mean: float = float("nan")
    lstar_median: float = float("nan")
    contrast_sd: float = float("nan")
    dr_stops: float = float("nan")
    clip_lo: float = float("nan")
    clip_hi: float = float("nan")
    tone_entropy: float = float("nan")
    z00: float = float("nan")
    z01: float = float("nan")
    z02: float = float("nan")
    z03: float = float("nan")
    z04: float = float("nan")
    z05: float = float("nan")
    z06: float = float("nan")
    z07: float = float("nan")
    z08: float = float("nan")
    z09: float = float("nan")
    z10: float = float("nan")
    # color
    lab_a: float = float("nan")
    lab_b: float = float("nan")
    chroma_mean: float = float("nan")
    chroma_p95: float = float("nan")
    colorfulness: float = float("nan")
    cct_k: float = float("nan")
    duv: float = float("nan")
    hue_mean_deg: float = float("nan")
    hue_conc: float = float("nan")
    hue_sd_deg: float = float("nan")
    sh_a: float = float("nan")
    sh_b: float = float("nan")
    hi_a: float = float("nan")
    hi_b: float = float("nan")
    split_dab: float = float("nan")
    split_dir_deg: float = float("nan")
    # textura
    acutance: float = float("nan")
    grain_levels: float = float("nan")
    focus_frac: float = float("nan")
    edge_vert: float = float("nan")
    alpha_spectral: float = float("nan")
    # desenfoque y cremosidad
    blur_all: float = float("nan")
    blur_subject: float = float("nan")
    blur_bg: float = float("nan")
    blur_sep: float = float("nan")
    bg_micro: float = float("nan")
    subj_micro: float = float("nan")
    bg_rel_micro: float = float("nan")
    creaminess: float = float("nan")
    error: str = ""


FLOAT_FIELDS = {f.name for f in fields(Row) if f.type in ("float", float)}


# --------------------------------------------------------------------------
# Utilidades numericas
# --------------------------------------------------------------------------

def _gauss_kernel(sigma: float) -> np.ndarray:
    r = max(1, int(round(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Difuminado gaussiano separable con relleno por replica de borde.

    np.convolve en modo same rellena con ceros, lo que oscurece una orla de
    unos 3 sigma en todo el perimetro. Esa orla falsea cualquier magnitud
    normalizada por la media local: el mapa de nitidez premia las teselas del
    borde, el micro-contraste del fondo se infla y una imagen uniforme llega a
    dar gradiente donde no hay ninguno."""
    if sigma <= 0:
        return a
    k = _gauss_kernel(sigma)
    r = len(k) // 2
    p = np.pad(a, ((r, r), (r, r)), mode="edge")
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, p)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, out)


def _noise_grad_coeff(sigma: float, n: int = 192, seed: int = 0) -> float:
    """Energia de gradiente que aporta ruido blanco de varianza unidad tras
    difuminar con sigma. Se calcula una vez con la misma implementacion de
    difuminado y de gradiente que se usa despues, asi que incluye los efectos
    de la discretizacion."""
    w = np.random.default_rng(seed).standard_normal((n, n))
    g = _blur(w, sigma)
    gy, gx = np.gradient(g)
    return float((gx * gx + gy * gy).mean())


def _downsample(a: np.ndarray, ny: int, nx: int) -> np.ndarray:
    """Media de area exacta sobre una rejilla ny x nx. Acepta 2D y 3D.

    Se usa remuestreo BOX en lugar de reshape por bloques: si el lado no es
    multiplo del numero de celdas, descartar el resto por un solo borde
    desplaza el origen de coordenadas y sesga el centroide (del orden del 6%
    del fotograma, suficiente para arruinar la medida)."""
    if a.ndim == 2:
        im = Image.fromarray(a.astype(np.float32), mode="F")
        return np.asarray(im.resize((nx, ny), Image.BOX), dtype=np.float64)
    out = np.empty((ny, nx, a.shape[2]))
    for c in range(a.shape[2]):
        out[..., c] = _downsample(a[..., c], ny, nx)
    return out


def _norm01(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1e-12:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)


# --------------------------------------------------------------------------
# Mapas de sujeto
# --------------------------------------------------------------------------

def sharpness_map(gray: np.ndarray, ny: int, nx: int) -> np.ndarray:
    """Energia laplaciana normalizada por luminancia local, por bloques."""
    lap = (4.0 * gray
           - np.roll(gray, 1, 0) - np.roll(gray, -1, 0)
           - np.roll(gray, 1, 1) - np.roll(gray, -1, 1))
    lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0.0
    local = _blur(gray, 8.0) + 0.05      # no premiar solo las zonas claras
    m = _downsample(np.abs(lap) / local, ny, nx)
    return _norm01(_blur(m, 1.2))


def contrast_map(rgb: np.ndarray, ny: int, nx: int, bins: int = 4) -> np.ndarray:
    """Contraste de histograma (Cheng et al.): rareza cromatica de cada bloque."""
    blocks = _downsample(rgb, ny, nx)                    # (ny, nx, 3)
    q = np.clip((blocks * bins).astype(np.int64), 0, bins - 1)
    idx = (q[..., 0] * bins + q[..., 1]) * bins + q[..., 2]
    flat = idx.ravel()
    nb = bins ** 3
    counts = np.bincount(flat, minlength=nb).astype(np.float64)
    sums = np.zeros((nb, 3))
    for c in range(3):
        sums[:, c] = np.bincount(flat, weights=blocks[..., c].ravel(), minlength=nb)
    live = counts > 0
    centres = np.zeros((nb, 3))
    centres[live] = sums[live] / counts[live, None]
    d = np.linalg.norm(centres[:, None, :] - centres[None, :, :], axis=2)
    weight = counts / counts.sum()
    sal_bin = d @ weight
    m = sal_bin[idx]
    return _norm01(_blur(m, 1.2))


def subject_map(rgb: np.ndarray, gray: np.ndarray, method: str,
                w_sharp: float, grid: int) -> np.ndarray:
    h, w = gray.shape
    if w >= h:
        nx, ny = grid, max(8, int(round(grid * h / w)))
    else:
        ny, nx = grid, max(8, int(round(grid * w / h)))
    if method == "sharpness":
        return sharpness_map(gray, ny, nx)
    if method == "contrast":
        return contrast_map(rgb, ny, nx)
    sh = sharpness_map(gray, ny, nx)
    ct = contrast_map(rgb, ny, nx)
    return _norm01(w_sharp * sh + (1.0 - w_sharp) * ct)


def _flood(mask: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    ny, nx = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    if not mask[start]:
        seen[start] = True
        return seen
    stack = [start]
    seen[start] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < ny and 0 <= xx < nx and mask[yy, xx] and not seen[yy, xx]:
                seen[yy, xx] = True
                stack.append((yy, xx))
    return seen


def centroid(m: np.ndarray, aspect: float, level: float,
             max_area: float) -> dict:
    """Centroide de la componente conexa que contiene el maximo del mapa."""
    m = _norm01(m)
    ny, nx = m.shape
    peak = np.unravel_index(int(np.argmax(m)), m.shape)
    thr = float(level)
    comp = _flood(m >= thr, peak)
    while comp.mean() > max_area and thr < 0.95:
        thr = min(0.95, thr + 0.05)
        comp = _flood(m >= thr, peak)

    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    xn = 2.0 * (xs + 0.5) / nx - 1.0
    yn = 1.0 - 2.0 * (ys + 0.5) / ny
    w = np.where(comp, m, 0.0)
    total = float(w.sum())
    s = math.hypot(aspect, 1.0)

    if total <= 0:
        return dict(x_norm=0.0, y_norm=0.0, r_norm=0.0, spread_norm=RG_UNIFORM,
                    area_frac=1.0, confidence=0.0,
                    peak_x_norm=0.0, peak_y_norm=0.0), comp

    cx = float((w * xn).sum() / total)
    cy = float((w * yn).sum() / total)
    var = float((w * (((xn - cx) * aspect / s) ** 2
                      + ((yn - cy) / s) ** 2)).sum() / total)
    rg = math.sqrt(max(var, 0.0))
    return dict(
        x_norm=cx,
        y_norm=cy,
        r_norm=math.hypot(cx * aspect, cy) / s,
        spread_norm=rg,
        area_frac=float(comp.mean()),
        confidence=max(0.0, min(1.0, 1.0 - rg / RG_UNIFORM)),
        peak_x_norm=2.0 * (peak[1] + 0.5) / nx - 1.0,
        peak_y_norm=1.0 - 2.0 * (peak[0] + 0.5) / ny,
    ), comp


# --------------------------------------------------------------------------
# Descriptores de tono, color y textura
# --------------------------------------------------------------------------
# Convenios y referencias:
#   sRGB IEC 61966-2-1 para linealizar, matriz sRGB/D65 para XYZ,
#   CIE L*a*b* con blanco D65, temperatura de color por McCamy (1992),
#   Duv por la aproximacion de Ohno (2013), colorido por Hasler y
#   Susstrunk (2003), pendiente espectral segun Field (1987): la potencia
#   de una escena natural cae como f^-alpha con alpha proximo a 2.
#
# Advertencia sobre escaneos de pelicula: estos descriptores miden la
# emulsion, el revelado y el perfil del escaner tanto como la luz de la
# escena. Comparar color entre dos cuerpos cargados con emulsiones
# distintas no dice nada del fotografo. Si el software del escaner
# equilibra el color fotograma a fotograma, la dominante media queda
# destruida y solo sobreviven los descriptores de tono y textura.

WHITE_D65 = np.array([0.95047, 1.0, 1.08883])
M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]])
MID_GRAY = 0.18


def srgb_to_linear(a: np.ndarray) -> np.ndarray:
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def rgb_to_lab(rgb_lin: np.ndarray) -> np.ndarray:
    xyz = rgb_lin @ M_RGB2XYZ.T
    t = xyz / WHITE_D65
    d = 216.0 / 24389.0
    f = np.where(t > d, np.cbrt(np.maximum(t, 1e-12)), (841.0 / 108.0) * t + 4.0 / 29.0)
    return np.stack([116.0 * f[..., 1] - 16.0,
                     500.0 * (f[..., 0] - f[..., 1]),
                     200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def mccamy_cct(x: float, y: float) -> float:
    """Temperatura de color correlacionada. Solo tiene sentido si |Duv| es pequeno."""
    if not (np.isfinite(x) and np.isfinite(y)) or abs(y - 0.1858) < 1e-9:
        return float("nan")
    n = (x - 0.3320) / (y - 0.1858)
    return -449.0 * n ** 3 + 3525.0 * n ** 2 - 6823.3 * n + 5520.33


def ohno_duv(u: float, v: float) -> float:
    """Distancia firmada al locus planckiano en el espacio CIE 1960 UCS."""
    du, dv = u - 0.292, v - 0.24
    lfp = math.hypot(du, dv)
    if lfp < 1e-12:
        return float("nan")
    a = math.acos(max(-1.0, min(1.0, du / lfp)))
    k = [-0.471106, 1.925865, -2.4243787, 1.5317403, -0.5179722, 0.0893944, -0.00616793]
    lbb = sum(c * a ** i for i, c in enumerate(k))
    return lfp - lbb


def spectral_slope(gray: np.ndarray, f_lo: float = 4.0, f_hi_frac: float = 0.25) -> float:
    """Exponente alpha del espectro de potencia radial, ajustado en log-log."""
    h, w = gray.shape
    n = min(h, w)
    if n < 64:
        return float("nan")
    g = gray[:n, :n] - gray[:n, :n].mean()
    win = np.hanning(n)
    g = g * win[:, None] * win[None, :]
    p = np.abs(np.fft.fftshift(np.fft.fft2(g))) ** 2
    c = n // 2
    ys, xs = np.mgrid[0:n, 0:n]
    r = np.hypot(xs - c, ys - c)
    f_hi = f_hi_frac * n
    nb = 28
    edges = np.logspace(np.log10(f_lo), np.log10(f_hi), nb + 1)
    fs, ps = [], []
    for i in range(nb):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if m.sum() >= 6:
            fs.append(math.sqrt(edges[i] * edges[i + 1]))
            ps.append(p[m].mean())
    if len(fs) < 6:
        return float("nan")
    lf = np.log(np.array(fs))
    lp = np.log(np.array(ps) + 1e-30)
    slope = np.polyfit(lf, lp, 1)[0]
    return float(-slope)


def tone_traits(rgb: np.ndarray, lab: np.ndarray) -> dict:
    lin = srgb_to_linear(rgb)
    Y = np.clip(lin @ np.array([0.2126729, 0.7151522, 0.0721750]), 1e-5, None)
    L = lab[..., 0]
    ys = np.sort(Y.ravel())
    p = lambda q: float(ys[min(len(ys) - 1, max(0, int(q * (len(ys) - 1))))])
    lo, hi = p(0.005), p(0.995)
    hist = np.histogram(L, bins=64, range=(0, 100))[0].astype(np.float64)
    hist /= max(hist.sum(), 1)
    nz = hist[hist > 0]
    # Zonas: once bandas iguales de L*. Los escalones del sistema de zonas en
    # copia son aproximadamente equidistantes en claridad, no en diafragmas de
    # la escena, y L* es la claridad CIE: el gris del 18 % tiene L* = 49.6 y
    # cae en la zona V, el negro en la 0 y el blanco de papel en la X. Definir
    # las zonas como diafragmas sobre el gris medio dejaria las tres ultimas
    # vacias, porque de 0.18 al blanco solo hay 2.47 diafragmas.
    z = np.clip((L / 100.0 * 11.0).astype(int), 0, 10)
    zc = np.bincount(z.ravel(), minlength=11).astype(np.float64)
    zc /= max(zc.sum(), 1)
    out = dict(
        key_stops=float(np.log2(float(np.median(Y)) / MID_GRAY)),
        lum_mean=float(np.mean(Y)),
        lstar_median=float(np.median(L)),
        contrast_sd=float(np.std(L)),
        dr_stops=float(np.log2(hi / lo)) if lo > 0 else float("nan"),
        clip_lo=float((rgb.max(axis=-1) <= 2 / 255).mean()),
        clip_hi=float((rgb.min(axis=-1) >= 253 / 255).mean()),
        tone_entropy=float(-(nz * np.log2(nz)).sum()),
    )
    for i in range(11):
        out[f"z{i:02d}"] = float(zc[i])
    return out


def color_traits(rgb: np.ndarray, lab: np.ndarray) -> dict:
    lin = srgb_to_linear(rgb)
    xyz = lin.reshape(-1, 3).mean(axis=0) @ M_RGB2XYZ.T
    s = float(xyz.sum())
    x = float(xyz[0] / s) if s > 0 else float("nan")
    y = float(xyz[1] / s) if s > 0 else float("nan")
    den = xyz[0] + 15 * xyz[1] + 3 * xyz[2]
    u = float(4 * xyz[0] / den) if den > 0 else float("nan")
    v = float(6 * xyz[1] / den) if den > 0 else float("nan")
    a, b = lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    # colorido de Hasler y Susstrunk sobre los ejes oponentes
    R, G, B = rgb[..., 0] * 255, rgb[..., 1] * 255, rgb[..., 2] * 255
    rg, yb = R - G, 0.5 * (R + G) - B
    colorfulness = float(math.hypot(rg.std(), yb.std())
                         + 0.3 * math.hypot(rg.mean(), yb.mean()))
    # estadistica circular del tono, ponderada por croma
    m = C > 3.0
    if m.sum() > 32:
        h = np.arctan2(b[m], a[m])
        wgt = C[m]
        cs = float((wgt * np.cos(h)).sum()), float((wgt * np.sin(h)).sum())
        W = float(wgt.sum())
        Rbar = math.hypot(*cs) / W
        hue_mean = math.degrees(math.atan2(cs[1], cs[0])) % 360.0
        hue_sd = math.degrees(math.sqrt(max(0.0, -2.0 * math.log(max(Rbar, 1e-12)))))
    else:
        Rbar, hue_mean, hue_sd = float("nan"), float("nan"), float("nan")
    # tono partido: dominante de las sombras frente a las luces
    L = lab[..., 0]
    q1, q3 = np.percentile(L, [25, 75])
    sh, hi = L <= q1, L >= q3
    sa, sb = float(a[sh].mean()), float(b[sh].mean())
    ha, hb = float(a[hi].mean()), float(b[hi].mean())
    duv = ohno_duv(u, v)
    cct = mccamy_cct(x, y)
    # McCamy y la aproximacion de Ohno son ajustes polinomicos validos solo en
    # el entorno del locus planckiano. Con una dominante saturada la formula
    # atraviesa su singularidad en y = 0.1858 y devuelve valores absurdos, asi
    # que se anula fuera de rango: cct_k vacio significa que el color medio de
    # la escena no se parece a ningun cuerpo negro, caso en el que la calidez
    # se lee en lab_b y no en kelvin.
    if not (math.isfinite(cct) and 1000.0 <= cct <= 25000.0):
        cct, duv = float("nan"), float("nan")
    elif math.isfinite(duv) and abs(duv) > 0.05:
        cct = float("nan")
    return dict(
        lab_a=float(a.mean()), lab_b=float(b.mean()),
        chroma_mean=float(C.mean()), chroma_p95=float(np.percentile(C, 95)),
        colorfulness=colorfulness,
        cct_k=cct, duv=duv,
        hue_mean_deg=hue_mean, hue_conc=Rbar, hue_sd_deg=hue_sd,
        sh_a=sa, sh_b=sb, hi_a=ha, hi_b=hb,
        split_dab=float(math.hypot(ha - sa, hb - sb)),
        split_dir_deg=float(math.degrees(math.atan2(hb - sb, ha - sa)) % 360.0),
    )


def texture_traits(gray: np.ndarray) -> dict:
    lap = (4.0 * gray
           - np.roll(gray, 1, 0) - np.roll(gray, -1, 0)
           - np.roll(gray, 1, 1) - np.roll(gray, -1, 1))
    lap = lap[1:-1, 1:-1]
    gy, gx = np.gradient(gray)
    ax, ay = float(np.abs(gx).sum()), float(np.abs(gy).sum())
    sigma = estimate_noise(gray)
    # fraccion del fotograma en foco, con el mapa de nitidez por teselas
    sh = _downsample(np.abs(lap), 32, 32)
    ref = float(np.percentile(sh, 98))
    return dict(
        acutance=float(np.median(np.abs(lap)) * 255),
        grain_levels=float(sigma * 255),
        focus_frac=float((sh > 0.25 * ref).mean()) if ref > 0 else float("nan"),
        edge_vert=float((ax - ay) / (ax + ay)) if (ax + ay) > 0 else float("nan"),
        alpha_spectral=spectral_slope(gray),
    )


def all_traits(rgb: np.ndarray, gray: np.ndarray) -> dict:
    lab = rgb_to_lab(srgb_to_linear(rgb))
    out = {}
    out.update(tone_traits(rgb, lab))
    out.update(color_traits(rgb, lab))
    out.update(texture_traits(gray))
    return out


def _box1(a: np.ndarray, k: int, axis: int) -> np.ndarray:
    ker = np.ones(k) / k
    return np.apply_along_axis(lambda m: np.convolve(m, ker, mode="same"), axis, a)


BLUR_S1, BLUR_S2 = 1.0, 3.0
K_S1, K_S2 = _noise_grad_coeff(BLUR_S1), _noise_grad_coeff(BLUR_S2)


def estimate_noise(gray: np.ndarray, tile: int = 16) -> float:
    """Sigma robusto del ruido, medido en el 20 % de teselas mas planas.

    Var(laplaciano) = 20 sigma^2 con ruido blanco, de donde el factor. En
    escenas con textura fina en todo el cuadro no hay teselas realmente
    planas y el valor queda sobrestimado."""
    lap = (4.0 * gray
           - np.roll(gray, 1, 0) - np.roll(gray, -1, 0)
           - np.roll(gray, 1, 1) - np.roll(gray, -1, 1))[1:-1, 1:-1]
    h, w = lap.shape
    ny, nx = max(1, h // tile), max(1, w // tile)
    var = _downsample(lap ** 2, ny, nx)
    keep = np.argsort(var.ravel())[:max(1, int(0.2 * var.size))]
    ys, xs = np.unravel_index(keep, var.shape)
    bh, bw = h // ny, w // nx
    parts = [lap[j * bh:(j + 1) * bh, i * bw:(i + 1) * bw].ravel() for j, i in zip(ys, xs)]
    v = np.concatenate(parts) if parts else lap.ravel()
    return 1.4826 * float(np.median(np.abs(v - np.median(v)))) / math.sqrt(20.0)


def blur_ratio(gray: np.ndarray, mask: np.ndarray | None = None,
               noise: float | None = None) -> float:
    """Indice de desenfoque por cociente de energia de gradiente entre escalas.

    E(s) es la energia media del gradiente tras difuminar con sigma s. El
    indice es E(s2)/E(s1) en (0, 1]: en una imagen nitida el segundo
    difuminado destruye mucho mas que el primero y el cociente es pequeno; en
    una imagen ya borrosa ninguno de los dos cambia gran cosa y el cociente
    tiende a 1. Crece de forma monotona con el desenfoque propio de la imagen.

    Se descuenta antes la energia que aporta el ruido, estimado sobre las
    teselas planas: el ruido blanco contribuye a E(s) como sigma^2 k(s), con
    k decreciente en s, de modo que en un fotograma muy desenfocado el ruido
    de cuantificacion de un archivo de 8 bits domina E(s1) y hunde el
    cociente. Sin esa correccion el indice deja de ser monotono a partir de
    unos cuatro pixeles de desenfoque y pierde la invariancia al contraste.
    Si tras el descuento no queda senal apreciable, el indice sale vacio.

    Se prefiere este cociente al indice de reenfoque de Crete y otros (2007)
    porque, al ser un cociente, se cancela el contraste global: un fondo
    cremoso de bajo contraste no se confunde con uno nitido."""
    if noise is None:
        noise = estimate_noise(gray)
    g1, g2 = _blur(gray, BLUR_S1), _blur(gray, BLUR_S2)

    def energy(g: np.ndarray) -> float:
        gy, gx = np.gradient(g)
        e = gx * gx + gy * gy
        if mask is not None:
            return float(e[mask].mean()) if mask.sum() else float("nan")
        return float(e.mean())

    e1, e2 = energy(g1), energy(g2)
    if not (math.isfinite(e1) and math.isfinite(e2)):
        return float("nan")
    n2 = noise * noise
    s1 = e1 - n2 * K_S1
    s2 = e2 - n2 * K_S2
    if s1 <= 0.05 * max(e1, 1e-15) or s2 <= 0:
        return float("nan")
    return float(min(1.0, s2 / s1))


def blur_traits(gray: np.ndarray, comp: np.ndarray) -> dict:
    """Reparto del desenfoque entre sujeto y fondo, y cremosidad del fondo.

    cremosidad = blur_bg x (1 - bg_rel_micro), donde bg_rel_micro es la parte
    del micro-contraste total que aporta el fondo, bgm/(bgm+sjm). Fondo muy
    difuminado y con poca estructura residual frente al sujeto. Es un convenio
    explicito, producto de dos magnitudes medidas y sin constantes libres, no
    una medida canonica de bokeh. Nada aqui distingue un desenfoque suave de
    un doble contorno por aberracion esferica: para eso hay que mirar los
    circulos de las luces especulares uno por uno. Depende de la nitidez del
    sujeto por construccion, lo que es razonable, porque un fotograma cuyo
    sujeto no esta nitido no tiene fondo cremoso en ningun sentido util."""
    nan = float("nan")
    out = dict(blur_all=nan, blur_subject=nan, blur_bg=nan, blur_sep=nan,
               bg_micro=nan, subj_micro=nan, bg_rel_micro=nan, creaminess=nan)
    h, w = gray.shape
    noise = estimate_noise(gray)
    out["blur_all"] = blur_ratio(gray, None, noise)
    m = np.asarray(Image.fromarray(comp.astype(np.float32), mode="F")
                   .resize((w, h), Image.NEAREST)) > 0.5
    grow = _blur(m.astype(np.float64), max(2.0, 0.02 * math.hypot(h, w))) > 0.02
    bg = ~grow
    if m.sum() < 64 or bg.sum() < 1024:
        return out
    out["blur_subject"] = blur_ratio(gray, m, noise)
    out["blur_bg"] = blur_ratio(gray, bg, noise)
    if math.isfinite(out["blur_bg"]) and math.isfinite(out["blur_subject"]):
        out["blur_sep"] = out["blur_bg"] - out["blur_subject"]
    lap = np.abs(4.0 * gray
                 - np.roll(gray, 1, 0) - np.roll(gray, -1, 0)
                 - np.roll(gray, 1, 1) - np.roll(gray, -1, 1))
    lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0.0
    norm = lap / (_blur(gray, 8.0) + 0.05)
    bgm = float(np.sqrt(np.mean(norm[bg] ** 2)) * 255)
    sjm = float(np.sqrt(np.mean(norm[m] ** 2)) * 255)
    out["bg_micro"], out["subj_micro"] = bgm, sjm
    if bgm + sjm > 1e-12:
        out["bg_rel_micro"] = bgm / (bgm + sjm)
    if math.isfinite(out["blur_bg"]) and math.isfinite(out["bg_rel_micro"]):
        out["creaminess"] = float(out["blur_bg"] * (1.0 - out["bg_rel_micro"]))
    return out


DATE_RES = [
    re.compile(r"(19|20)(\d{2})[-_./](\d{2})[-_./](\d{2})"),
    re.compile(r"(?<!\d)(19|20)(\d{2})(\d{2})(\d{2})(?!\d)"),
]
MONTH_RE = re.compile(r"(19|20)(\d{2})[-_./](\d{2})(?![\d])")
YEAR_DIR_RE = re.compile(r"^(19|20)(\d{2})(?:[^\d].*)?$")
MAX_YEAR = datetime.date.today().year


def infer_date(path: Path) -> str:
    """Fecha a partir de la ruta, para negativos sin EXIF de captura.

    El ano suelto solo se acepta cuando es un componente de directorio que
    empieza por el ano: un nombre de archivo como DSC_1988.jpg lleva un numero
    de serie, no una fecha, y aceptarlo llena el eje temporal de fotogramas
    falsos repartidos por los anos ochenta. Tampoco se aceptan anos
    posteriores al actual."""
    s = str(path)
    for rx in DATE_RES:
        m = rx.search(s)
        if not m:
            continue
        y, mo, d = int(m.group(1) + m.group(2)), int(m.group(3)), int(m.group(4))
        if 1900 <= y <= MAX_YEAR and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}:{mo:02d}:{d:02d} 12:00:00"
    m = MONTH_RE.search(s)
    if m:
        y, mo = int(m.group(1) + m.group(2)), int(m.group(3))
        if 1900 <= y <= MAX_YEAR and 1 <= mo <= 12:
            return f"{y:04d}:{mo:02d}:15 12:00:00"
    for part in path.parts[:-1]:
        m = YEAR_DIR_RE.match(part)
        if m:
            y = int(m.group(1) + m.group(2))
            if 1900 <= y <= MAX_YEAR:
                return f"{y:04d}:07:01 12:00:00"
    return ""


FOCAL_RE = re.compile(r"(?<!\d)(\d{2,3})\s?mm", re.I)


def infer_focal(path: Path) -> float:
    m = FOCAL_RE.search(str(path))
    if not m:
        return float("nan")
    v = float(m.group(1))
    return v if 6.0 <= v <= 1200.0 else float("nan")


# --------------------------------------------------------------------------
# Carga de imagen y EXIF
# --------------------------------------------------------------------------

def _rat(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def read_exif(img: Image.Image) -> dict:
    out = dict(make="", model="", lens="", datetime="",
               focal_mm=float("nan"), focal35_mm=float("nan"),
               f_number=float("nan"))
    try:
        exif = img.getexif()
    except Exception:
        return out
    if not exif:
        return out
    out["make"] = str(exif.get(TAG_MAKE, "") or "").strip()
    out["model"] = str(exif.get(TAG_MODEL, "") or "").strip()
    out["datetime"] = str(exif.get(TAG_DATETIME, "") or "").strip()
    try:
        ifd = exif.get_ifd(TAG_EXIF_IFD)
    except Exception:
        ifd = {}
    if ifd:
        out["lens"] = str(ifd.get(TAG_LENS, "") or "").strip()
        out["focal_mm"] = _rat(ifd.get(TAG_FOCAL))
        out["focal35_mm"] = _rat(ifd.get(TAG_FOCAL35))
        out["f_number"] = _rat(ifd.get(TAG_FNUMBER))
        if ifd.get(TAG_DT_ORIGINAL):
            out["datetime"] = str(ifd[TAG_DT_ORIGINAL]).strip()
    return out


def trim_uniform_border(gray: np.ndarray, tol: float = 0.02):
    """Descarta bordes planos, tipicos de escaneos con marco o portanegativos."""
    h, w = gray.shape
    rsd, csd = gray.std(axis=1), gray.std(axis=0)
    y0, y1, x0, x1 = 0, h, 0, w
    while y0 < h // 3 and rsd[y0] < tol:
        y0 += 1
    while y1 > 2 * h // 3 and rsd[y1 - 1] < tol:
        y1 -= 1
    while x0 < w // 3 and csd[x0] < tol:
        x0 += 1
    while x1 > 2 * w // 3 and csd[x1 - 1] < tol:
        x1 -= 1
    return x0, y0, x1, y1


def analyse(path_str: str, cfg: dict) -> dict:
    row = Row(path=path_str)
    path = Path(path_str)
    try:
        with Image.open(path) as im:
            exif = read_exif(im)
            row.width, row.height = im.size
            if min(im.size) < cfg["min_side"]:
                row.error = "imagen demasiado pequena"
                return asdict(row)
            # draft descomprime el JPEG a 1/2, 1/4 o 1/8 en el dominio DCT,
            # lo que evita decodificar escaneos completos de 50 Mpx
            try:
                im.draft("RGB", (2 * cfg["max_side"], 2 * cfg["max_side"]))
            except Exception:
                pass
            im = ImageOps.exif_transpose(im)
            if (im.size[0] > im.size[1]) != (row.width > row.height):
                row.width, row.height = row.height, row.width   # giro EXIF
            im = im.convert("RGB")
            im.thumbnail((cfg["max_side"], cfg["max_side"]), Image.BILINEAR)
            arr = np.asarray(im, dtype=np.float64) / 255.0
            preview = im.copy() if cfg["overlay"] else None
    except Exception as exc:
        row.error = f"{type(exc).__name__}: {exc}"
        return asdict(row)

    gray = arr @ np.array([0.2126, 0.7152, 0.0722])
    box = None
    if cfg["trim_border"]:
        x0, y0, x1, y1 = trim_uniform_border(gray)
        if (x1 - x0) > 0.5 * gray.shape[1] and (y1 - y0) > 0.5 * gray.shape[0]:
            arr, gray = arr[y0:y1, x0:x1], gray[y0:y1, x0:x1]
            box = (x0, y0, x1, y1)

    aspect = gray.shape[1] / gray.shape[0]
    m = subject_map(arr, gray, cfg["method"], cfg["w_sharp"], cfg["grid"])
    res, comp = centroid(m, aspect, cfg["level"], cfg["max_area"])

    for k, v in exif.items():
        setattr(row, k, v)
    row.aspect = row.width / row.height if row.height else float("nan")
    row.orientation = ("cuadrado" if abs(row.aspect - 1.0) < 0.02
                       else "horizontal" if row.aspect > 1.0 else "vertical")
    row.method = cfg["method"]
    for k, v in res.items():
        setattr(row, k, v)

    if cfg["traits"]:
        try:
            for k, v in all_traits(arr, gray).items():
                setattr(row, k, v)
            for k, v in blur_traits(gray, comp).items():
                setattr(row, k, v)
        except Exception as exc:
            row.error = f"descriptores: {type(exc).__name__}: {exc}"

    if cfg["infer_date"] and not row.datetime:
        row.datetime = infer_date(path)
    if cfg["infer_focal"] and not math.isfinite(row.focal35_mm):
        f = infer_focal(path)
        if math.isfinite(f):
            row.focal35_mm = f
    for k, v in cfg["tags"].items():
        if k in FLOAT_FIELDS:
            try:
                setattr(row, k, float(v))
            except ValueError:
                pass
        else:
            setattr(row, k, v)

    row.group = group_key(path, cfg, row)

    if cfg["overlay"] and preview is not None:
        try:
            draw_overlay(preview, res, box, cfg, path)
        except Exception:
            pass
    return asdict(row)


def group_key(path: Path, cfg: dict, row: Row) -> str:
    mode = cfg["group_by"]
    if mode == "exif":
        return " ".join(t for t in (row.make, row.model) if t) or "sin EXIF"
    if mode == "path":
        return str(path.parent)
    if mode == "top":
        for root in cfg["roots"]:
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
            return rel.parts[0] if len(rel.parts) > 1 else Path(root).name
    return path.parent.name


def draw_overlay(preview: Image.Image, res: dict, box, cfg: dict,
                 path: Path) -> None:
    """Miniatura anotada, para verificar a ojo que el estimador acierta."""
    out_dir = Path(cfg["overlay"])
    out_dir.mkdir(parents=True, exist_ok=True)
    im = preview.convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    if box:
        x0, y0, x1, y1 = box
        d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(80, 80, 255))
        ox, oy, ow, oh = x0, y0, x1 - x0, y1 - y0
    else:
        ox, oy, ow, oh = 0, 0, W, H
    cx = ox + (res["x_norm"] + 1.0) / 2.0 * ow
    cy = oy + (1.0 - res["y_norm"]) / 2.0 * oh
    d.line([ox + ow / 2, oy, ox + ow / 2, oy + oh], fill=(120, 120, 120))
    d.line([ox, oy + oh / 2, ox + ow, oy + oh / 2], fill=(120, 120, 120))
    rad = max(4.0, res["spread_norm"] * math.hypot(ow, oh) / 2.0)
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
              outline=(255, 60, 60), width=2)
    d.line([cx - 12, cy, cx + 12, cy], fill=(255, 60, 60), width=2)
    d.line([cx, cy - 12, cx, cy + 12], fill=(255, 60, 60), width=2)
    im.save(out_dir / f"r{res['r_norm']:.3f}__{path.stem[:60]}.jpg", quality=88)


# --------------------------------------------------------------------------
# Recorrido de directorios
# --------------------------------------------------------------------------

def iter_images(roots: list[str], recursive: bool = True):
    found, skipped_raw = [], 0
    for root in roots:
        base = Path(root)
        if base.is_file():
            found.append(base)
            continue
        for p in (base.rglob("*") if recursive else base.glob("*")):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in RASTER_EXT:
                found.append(p)
            elif ext in RAW_EXT:
                skipped_raw += 1
    found.sort()
    return found, skipped_raw


# --------------------------------------------------------------------------
# Estadistica
# --------------------------------------------------------------------------

def mad(v: np.ndarray) -> float:
    return float(np.median(np.abs(v - np.median(v))))


def bootstrap_ci(v: np.ndarray, iters: int = 4000, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(iters, len(v)))
    meds = np.median(v[idx], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def permutation_test(a: np.ndarray, b: np.ndarray, iters: int = 20000,
                     seed: int = 0):
    """Diferencia de medianas observada y p bilateral por permutacion."""
    rng = np.random.default_rng(seed)
    obs = float(np.median(a) - np.median(b))
    pool = np.concatenate([a, b])
    n, N = len(a), len(a) + len(b)
    perm = np.argsort(rng.random((iters, N)), axis=1)
    draws = pool[perm]
    diffs = np.median(draws[:, :n], axis=1) - np.median(draws[:, n:], axis=1)
    p = (np.sum(np.abs(diffs) >= abs(obs) - 1e-15) + 1) / (iters + 1)
    return obs, float(p)


def summarise(rows: list[dict], min_conf: float, centred_thr: float) -> None:
    ok = [r for r in rows if not r["error"] and r["confidence"] >= min_conf]
    weak = [r for r in rows if not r["error"] and r["confidence"] < min_conf]
    bad = [r for r in rows if r["error"]]

    print(f"\n{len(rows)} imagenes: {len(ok)} utiles, {len(weak)} con "
          f"confianza < {min_conf:.2f}, {len(bad)} con error.")
    for r in bad[:5]:
        print(f"  error en {r['path']}: {r['error']}")
    if not ok:
        return

    groups: dict[str, list[dict]] = {}
    for r in ok:
        groups.setdefault(r["group"], []).append(r)

    hdr = (f"{'grupo':<22}{'n':>5}{'r med':>8}{'MAD':>7}{'IC95 de la mediana':>22}"
           f"{'|x| med':>9}{'|y| med':>9}{'r<' + f'{centred_thr:.2f}':>8}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for name, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        r = np.array([x["r_norm"] for x in rs])
        ax = np.array([abs(x["x_norm"]) for x in rs])
        ay = np.array([abs(x["y_norm"]) for x in rs])
        lo, hi = bootstrap_ci(r) if len(r) >= 6 else (float("nan"), float("nan"))
        print(f"{name[:21]:<22}{len(rs):>5}{np.median(r):>8.3f}{mad(r):>7.3f}"
              f"{f'[{lo:.3f}, {hi:.3f}]':>22}{np.median(ax):>9.3f}"
              f"{np.median(ay):>9.3f}{(r < centred_thr).mean():>8.1%}")

    big = [(k, v) for k, v in groups.items() if len(v) >= 8]
    if len(big) == 2:
        (na, ra), (nb, rb) = big
        a = np.array([x["r_norm"] for x in ra])
        b = np.array([x["r_norm"] for x in rb])
        diff, p = permutation_test(a, b)
        print(f"\nContraste {na} frente a {nb}")
        print(f"  diferencia de medianas de r_norm: {diff:+.4f}")
        print(f"  p bilateral (permutacion, 20000 iteraciones): {p:.4f}")
        print("  r_norm menor significa sujeto mas centrado. Empareja por focal "
              "y tipo de escena antes de dar por buena una diferencia.")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Mide el desplazamiento del sujeto principal respecto al "
                    "centro del fotograma en colecciones de fotografias.")
    ap.add_argument("roots", nargs="+", help="directorios o archivos")
    ap.add_argument("--csv", default="subject_center.csv")
    ap.add_argument("--method", choices=["sharpness", "contrast", "both"],
                    default="both")
    ap.add_argument("--w-sharp", type=float, default=0.65,
                    help="peso del mapa de nitidez cuando method=both")
    ap.add_argument("--level", type=float, default=0.5,
                    help="umbral, en fraccion de la altura del pico")
    ap.add_argument("--max-area", type=float, default=0.35,
                    help="fraccion maxima del fotograma que puede ocupar el blob")
    ap.add_argument("--grid", type=int, default=48,
                    help="celdas del mapa en el lado mayor")
    ap.add_argument("--group-by", choices=["dir", "path", "top", "exif"],
                    default="dir",
                    help="los escaneos de pelicula no llevan EXIF de camara: "
                         "agrupa por directorio")
    ap.add_argument("--max-side", type=int, default=512)
    ap.add_argument("--min-side", type=int, default=200)
    ap.add_argument("--min-confidence", type=float, default=0.3)
    ap.add_argument("--centred-threshold", type=float, default=0.15)
    ap.add_argument("--trim-border", action="store_true")
    ap.add_argument("--no-traits", action="store_true",
                    help="salta los descriptores de tono, color y textura")
    ap.add_argument("--infer-date", action="store_true",
                    help="lee la fecha de la ruta cuando falta en el EXIF, "
                         "buscando 2019-07-14, 2019_07 o 2019")
    ap.add_argument("--infer-focal", action="store_true",
                    help="lee la focal de la ruta cuando falta en el EXIF, "
                         "buscando patrones tipo _35mm_")
    ap.add_argument("--tag", action="append", default=[], metavar="CAMPO=VALOR",
                    help="fija una columna para todo el lote, util en pelicula "
                         "sin EXIF: --tag model=M5 --tag focal35_mm=50. Repetible")
    ap.add_argument("--overlay", default="",
                    help="directorio para miniaturas anotadas de control")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-recursive", action="store_true")
    args = ap.parse_args(argv)

    files, skipped_raw = iter_images(args.roots, recursive=not args.no_recursive)
    if args.limit:
        files = files[:args.limit]
    if not files:
        print("No se han encontrado imagenes rasterizadas.", file=sys.stderr)
        return 1
    if skipped_raw:
        print(f"Aviso: {skipped_raw} ficheros RAW ignorados. Exporta a TIFF o "
              f"JPEG para incluirlos.", file=sys.stderr)

    tags = {}
    for t in args.tag:
        if "=" not in t:
            print(f"Aviso: etiqueta ignorada, falta el signo igual: {t}", file=sys.stderr)
            continue
        k, v = t.split("=", 1)
        k = k.strip()
        if k not in {f.name for f in fields(Row)}:
            print(f"Aviso: la columna {k} no existe, etiqueta ignorada.", file=sys.stderr)
            continue
        tags[k] = v.strip()

    cfg = dict(method=args.method, w_sharp=args.w_sharp, level=args.level,
               max_area=args.max_area, grid=args.grid, group_by=args.group_by,
               max_side=args.max_side, min_side=args.min_side,
               trim_border=args.trim_border, overlay=args.overlay,
               traits=not args.no_traits, infer_focal=args.infer_focal,
               infer_date=args.infer_date,
               tags=tags, roots=[str(Path(r)) for r in args.roots])

    rows, total = [], len(files)
    if args.jobs > 1 and total > 4:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futs = [ex.submit(analyse, str(f), cfg) for f in files]
            for i, fut in enumerate(as_completed(futs), 1):
                rows.append(fut.result())
                if i % 20 == 0 or i == total:
                    print(f"\r{i}/{total}", end="", file=sys.stderr, flush=True)
    else:
        for i, f in enumerate(files, 1):
            rows.append(analyse(str(f), cfg))
            if i % 20 == 0 or i == total:
                print(f"\r{i}/{total}", end="", file=sys.stderr, flush=True)
    print("", file=sys.stderr)

    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[f.name for f in fields(Row)])
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["path"]):
            w.writerow(r)

    summarise(rows, args.min_confidence, args.centred_threshold)
    print(f"\nDatos por imagen en {args.csv}")
    if args.overlay:
        print(f"Miniaturas de control en {args.overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
