#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eclipse_hdr.py
Fusion HDR lineal y aplanado radial de la corona solar a partir de brackets RAW.

Flujo:
  1) Decodificado RAW lineal (rawpy/LibRaw, gamma 1:1, 16 bits, sin auto-brillo,
     primarios sRGB). La mascara de saturacion se toma del mosaico RAW, antes
     del demosaico, que es donde la saturacion esta bien definida.
  2) Deteccion del limbo lunar: Hough para el centro aproximado y despues
     ajuste subpixel de circunferencia sobre 720 rayos radiales (maximo del
     gradiente de log I a lo largo de cada rayo, ajuste algebraico de Kasa con
     sigma-clipping). Registro por traslacion al centro de referencia.
  3) Fusion HDR: L = sum(w_i * I_i / e_i) / sum(w_i), con e_i = t*ISO/N^2
     relativo, y w_i = 0 en saturacion y cerca del suelo de ruido,
     w_i proporcional a e_i en el resto (ponderacion optima con ruido fotonico).
  4) Sustraccion del fondo de cielo: ajuste polinomico sigma-clipped por canal
     sobre pixeles alejados de la corona (r > k * r_luna). Absorbe el gradiente
     de extincion y el fondo crepuscular a primer orden.
  5) Aplanado radial: division por el perfil radial azimutal (media recortada
     por anillos de 1 px, suavizada en log). Equivalente en primera
     aproximacion a un filtro de paso alto circular.
  6) Realce multiescala opcional (mascaras de enfoque gaussianas) con el disco
     lunar rellenado durante el filtrado para evitar anillos en el limbo.

Uso:
  python eclipse_hdr.py --selftest
  python eclipse_hdr.py IMG_*.CR3 -o salida
  python eclipse_hdr.py *.NEF -o salida --half          # prueba rapida a media resolucion
  python eclipse_hdr.py *.ARW -o salida --bg poly2 --profile rgb

Salidas (en el directorio -o):
  01_hdr_lineal_f32.tif      radiancia lineal fusionada, float32 (fotometrica)
  02_hdr_aplanado_f32.tif    tras fondo + aplanado radial, float32
  03_final_16bit.tif         version estirada (y realzada si procede), 16 bits
  perfil_radial.csv          perfil I(r) usado en el aplanado
  preview.jpg                vista rapida

Dependencias:
  pip install numpy scipy scikit-image tifffile pillow rawpy exifread
  exiftool es opcional, como respaldo de metadatos:  brew install exiftool
"""

import argparse
import glob
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import (gaussian_filter, gaussian_filter1d,
                           map_coordinates, shift as ndshift)

REC709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def log(msg):
    print(msg, flush=True)


class DetectionError(RuntimeError):
    pass


# ----------------------------------------------------------------------------
# Metadatos de exposicion
# ----------------------------------------------------------------------------

def _exif_via_exifread(path):
    import exifread
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    def num(tag):
        v = tags.get(tag)
        if v is None:
            return None
        val = v.values[0]
        try:
            return float(val.num) / float(val.den)
        except AttributeError:
            return float(val)

    t = num("EXIF ExposureTime")
    fn = num("EXIF FNumber")
    iso_tag = tags.get("EXIF ISOSpeedRatings")
    iso = float(iso_tag.values[0]) if iso_tag else None
    return t, iso, fn


def _exif_via_exiftool(path):
    out = subprocess.run(
        ["exiftool", "-j", "-n", "-ExposureTime", "-ISO", "-FNumber", path],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0 or not out.stdout.strip():
        return None, None, None
    d = json.loads(out.stdout)[0]
    return d.get("ExposureTime"), d.get("ISO"), d.get("FNumber")


def read_exposure(path):
    t = iso = fn = None
    try:
        t, iso, fn = _exif_via_exifread(path)
    except Exception:
        pass
    if t is None:
        try:
            t, iso, fn = _exif_via_exiftool(path)
        except Exception:
            pass
    return t, iso, fn


def parse_time(s):
    s = s.strip()
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def relative_exposures(paths, times_override=None):
    """Devuelve e_i = t*ISO/N^2 normalizado a max(e) = 1."""
    n = len(paths)
    if times_override:
        ts = [parse_time(x) for x in times_override.split(",")]
        if len(ts) != n:
            sys.exit("--times: se esperaban %d valores, hay %d" % (n, len(ts)))
        e = np.asarray(ts, dtype=np.float64)
        return e / e.max(), ts
    ts, isos, fns, missing = [], [], [], []
    for p in paths:
        t, iso, fn = read_exposure(p)
        if t is None:
            missing.append(os.path.basename(p))
        ts.append(t)
        isos.append(iso if iso else 100.0)
        fns.append(fn if fn else 1.0)
    if missing:
        sys.exit("Sin ExposureTime en: %s\n"
                 "Instala exiftool (brew install exiftool) o pasa --times "
                 "t1,t2,... en el mismo orden que los ficheros."
                 % ", ".join(missing[:5]))
    e = np.array([t * i / (f * f) for t, i, f in zip(ts, isos, fns)])
    if np.ptp(np.log2(e)) < 0.5:
        log("aviso: todas las exposiciones relativas son casi iguales "
            "(rango %.2f EV); revisa los metadatos." % np.ptp(np.log2(e)))
    return e / e.max(), ts


# ----------------------------------------------------------------------------
# Carga RAW lineal + mascara de saturacion
# ----------------------------------------------------------------------------

def _match_shape(mask, shape):
    """Ajusta la mascara a shape por rotaciones de 90 y recorte/relleno."""
    for k in range(4):
        m = np.rot90(mask, k) if k else mask
        if m.shape == shape:
            return m
    m = mask if mask.shape[0] <= mask.shape[1] else mask
    out = np.zeros(shape, bool)
    h = min(shape[0], mask.shape[0])
    w = min(shape[1], mask.shape[1])
    out[:h, :w] = mask[:h, :w]
    return out


def load_raw(path, half=False, wb="camera"):
    try:
        import rawpy
    except ImportError:
        sys.exit("Falta rawpy:  pip install rawpy")
    with rawpy.imread(path) as raw:
        mosaic = raw.raw_image_visible.astype(np.float32)
        try:
            black = float(np.mean(raw.black_level_per_channel))
        except Exception:
            black = 0.0
        white = float(raw.white_level)
        satmask = mosaic >= black + 0.97 * (white - black)
        flip = raw.sizes.flip
        kwargs = dict(gamma=(1, 1), no_auto_bright=True, output_bps=16,
                      output_color=rawpy.ColorSpace.sRGB, half_size=half,
                      use_auto_wb=False)
        if wb == "camera":
            kwargs["use_camera_wb"] = True
        else:
            try:
                kwargs["user_wb"] = list(raw.daylight_whitebalance)
            except Exception:
                kwargs["use_camera_wb"] = True
        rgb = raw.postprocess(**kwargs).astype(np.float32) / 65535.0
    if half:
        h2 = satmask.shape[0] // 2 * 2
        w2 = satmask.shape[1] // 2 * 2
        satmask = satmask[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).any(axis=(1, 3))
    if flip == 3:
        satmask = satmask[::-1, ::-1]
    elif flip == 5:
        satmask = np.rot90(satmask, 1)
    elif flip == 6:
        satmask = np.rot90(satmask, 3)
    satmask = _match_shape(satmask, rgb.shape[:2])
    # respaldo por si el mapeo del mosaico fallara en algun modelo
    satmask |= rgb.max(axis=2) > 0.96
    satmask = ndi.binary_dilation(satmask, iterations=2)
    return rgb, satmask


def luminance(img):
    return img @ REC709


# ----------------------------------------------------------------------------
# Deteccion del limbo lunar
# ----------------------------------------------------------------------------

def fit_circle(x, y):
    """Ajuste algebraico de Kasa: minimos cuadrados sobre x^2+y^2 = 2ax+2by+c."""
    A = np.column_stack([x, y, np.ones_like(x)]).astype(np.float64)
    b = (x * x + y * y).astype(np.float64)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    r = np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-12))
    return cx, cy, r


def rough_hough(lum, rmin, rmax):
    from skimage.feature import canny
    from skimage.transform import hough_circle, hough_circle_peaks
    H, W = lum.shape
    ds = max(1, int(np.ceil(min(H, W) / 800.0)))
    s = np.log(np.maximum(lum[::ds, ::ds], 1e-7))
    s = (s - s.min()) / max(np.ptp(s), 1e-9)
    edges = canny(s, sigma=2.0)
    radii = np.unique(np.round(np.linspace(max(rmin / ds, 6),
                                           max(rmax / ds, rmin / ds + 4),
                                           40)).astype(int))
    h = hough_circle(edges, radii)
    _, cxs, cys, rads = hough_circle_peaks(h, radii, total_num_peaks=1)
    if len(cxs) == 0:
        raise DetectionError("Hough no encontro circunferencia")
    return float(cxs[0] * ds), float(cys[0] * ds), float(rads[0] * ds)


def refine_limb(lum, cx, cy, r0, n_rays=720, rtol=0.20, iters=3):
    """Centro y radio subpixel del limbo por maximo gradiente radial."""
    H, W = lum.shape
    Lm = np.log(np.maximum(gaussian_filter(lum, 1.0), 1e-7))
    res = np.array([0.0])
    for _ in range(iters):
        th = np.linspace(0, 2 * np.pi, n_rays, endpoint=False)
        rr = np.linspace(r0 * (1 - rtol), r0 * (1 + rtol), 129)
        RR, TT = np.meshgrid(rr, th)
        X = cx + RR * np.cos(TT)
        Y = cy + RR * np.sin(TT)
        ray_ok = ((X >= 1) & (X <= W - 2) & (Y >= 1) & (Y <= H - 2)).all(axis=1)
        if ray_ok.sum() < 90:
            raise DetectionError("el limbo cae fuera del encuadre")
        prof = map_coordinates(Lm, [Y.ravel(), X.ravel()], order=1,
                               mode="nearest").reshape(n_rays, -1)
        prof = gaussian_filter1d(prof, 2.0, axis=1)
        g = np.gradient(prof, axis=1)
        idx = np.argmax(g, axis=1)
        ar = np.arange(n_rays)
        gmax = g[ar, idx]
        gmed = np.median(gmax[ray_ok])
        ok = ray_ok & (idx > 0) & (idx < len(rr) - 1) & (gmax > 0.3 * gmed)
        gm = g[ar, np.maximum(idx - 1, 0)]
        gp = g[ar, np.minimum(idx + 1, len(rr) - 1)]
        den = gm - 2 * gmax + gp
        safe = np.where(np.abs(den) > 1e-12, den, 1.0)
        delta = np.where(np.abs(den) > 1e-12, 0.5 * (gm - gp) / safe, 0.0)
        delta = np.clip(delta, -1, 1)
        r_edge = np.interp(idx + delta, np.arange(len(rr)), rr)
        xe = (cx + r_edge * np.cos(th))[ok]
        ye = (cy + r_edge * np.sin(th))[ok]
        if xe.size < 60:
            raise DetectionError("puntos de limbo insuficientes")
        for _ in range(4):
            a, b, r = fit_circle(xe, ye)
            res = np.hypot(xe - a, ye - b) - r
            s = max(float(np.std(res)), 1e-3)
            keep = np.abs(res) < 2.5 * s
            if keep.all():
                break
            xe, ye = xe[keep], ye[keep]
            if xe.size < 60:
                raise DetectionError("puntos de limbo insuficientes tras clip")
        cx, cy, r0 = a, b, r
    return cx, cy, r0, float(np.std(res)), int(xe.size)


def detect_center(lum, init=None, rmin=None, rmax=None):
    """Deteccion con cadena de inicializacion y respaldo por Hough."""
    H, W = lum.shape
    if rmin is None:
        rmin = 0.04 * min(H, W)
    if rmax is None:
        rmax = 0.35 * min(H, W)
    if init is not None:
        try:
            return refine_limb(lum, *init)
        except DetectionError:
            pass
    cx, cy, r = rough_hough(lum, rmin, rmax)
    return refine_limb(lum, cx, cy, r)


# ----------------------------------------------------------------------------
# Fusion HDR
# ----------------------------------------------------------------------------

class HDRAccumulator:
    def __init__(self, shape, floor=1.5e-3, trim=True):
        self.swl = np.zeros(shape, np.float32)
        self.sw = np.zeros(shape[:2], np.float32)
        self.floor = float(floor)
        self.trim = bool(trim)
        self.short = None
        self.e_short = None
        self._g = None

    def add(self, img, e_rel, satmask=None, n_eff=1.0):
        m = img.max(axis=2)
        w_hi = np.clip((0.92 - m) / 0.06, 0, 1)
        if satmask is not None:
            w_hi[satmask] = 0.0
        w_lo = np.clip((m - self.floor) / (2 * self.floor), 0, 1)
        w = (w_hi * w_lo * np.float32(e_rel * n_eff)).astype(np.float32)
        L = img / np.float32(e_rel)
        self.swl += w[..., None] * L
        self.sw += w
        if self.e_short is None or e_rel < self.e_short:
            self.e_short = e_rel
            self.short = L

    # --- fusion por grupos de igual exposicion, con recorte de extremos ---
    # Un transitorio (avion, satelite, vibracion) afecta a un solo fotograma
    # del grupo. Con n >= 3 se descarta el maximo por pixel (los transitorios
    # son brillantes) y con n >= 8 tambien el minimo. El coste en SNR es
    # (n-2)/n; el beneficio es que ningun fotograma aislado contamina la media.
    def add_group_frame(self, img, satmask=None):
        if self._g is None:
            self._g = dict(sum=np.zeros(img.shape, np.float32),
                           mx=np.full(img.shape, -np.inf, np.float32),
                           mn=np.full(img.shape, np.inf, np.float32),
                           sat=np.zeros(img.shape[:2], bool), n=0)
        g = self._g
        g["sum"] += img
        np.maximum(g["mx"], img, out=g["mx"])
        np.minimum(g["mn"], img, out=g["mn"])
        if satmask is not None:
            g["sat"] |= satmask
        g["n"] += 1

    def close_group(self, e_rel):
        g = self._g
        self._g = None
        if g is None or g["n"] == 0:
            return None
        n = g["n"]
        if self.trim and n >= 8:
            mean = (g["sum"] - g["mx"] - g["mn"]) / np.float32(n - 2)
            n_eff, mode = n - 2, "max+min"
        elif self.trim and n >= 3:
            mean = (g["sum"] - g["mx"]) / np.float32(n - 1)
            n_eff, mode = n - 1, "max"
        else:
            mean = g["sum"] / np.float32(n)
            n_eff, mode = n, "sin recorte"
        self.add(mean, e_rel, g["sat"], n_eff=n_eff)
        return n, mode

    def result(self):
        L = self.swl / np.maximum(self.sw, 1e-9)[..., None]
        if self.short is not None:
            hole = self.sw < 1e-6
            L[hole] = self.short[hole]
        return L, self.sw


def group_by_exposure(e_rel, tol_ev=0.25):
    """Agrupa indices de fotogramas cuya exposicion coincide dentro de tol_ev."""
    lev = np.log2(e_rel)
    order = np.argsort(lev)
    groups = [[int(order[0])]]
    for a, b in zip(order[:-1], order[1:]):
        if lev[b] - lev[a] > tol_ev:
            groups.append([])
        groups[-1].append(int(b))
    return groups


# ----------------------------------------------------------------------------
# Fondo de cielo (extincion + crepusculo)
# ----------------------------------------------------------------------------

def _poly_cols(xn, yn, kind):
    if kind == "plane":
        return [np.ones_like(xn), xn, yn]
    return [np.ones_like(xn), xn, yn, xn * xn, xn * yn, yn * yn]


def fit_background(L, cx, cy, r_lim, kind="plane", margin=64, k=4.0):
    H, W, _ = L.shape
    bg = np.zeros_like(L)
    if kind == "none":
        return bg
    step = max(1, int(round(min(H, W) / 700.0)))
    yy, xx = np.mgrid[margin:H - margin:step, margin:W - margin:step]
    r = np.hypot(xx - cx, yy - cy)
    sel = r > k * r_lim
    frac = float(sel.mean())
    if kind != "const" and frac < 0.04:
        log("  aviso: solo %.1f%% del campo es cielo lejano; "
            "uso fondo constante." % (100 * frac))
        kind = "const"
    if not sel.any():
        return bg
    if kind == "const":
        for c in range(3):
            v = L[yy, xx, c][sel]
            bg[..., c] = np.percentile(v, 10)
        return bg
    xn = (xx - W / 2.0) / W
    yn = (yy - H / 2.0) / H
    cols = _poly_cols(xn[sel], yn[sel], kind)
    A = np.column_stack(cols)
    Xn = (np.arange(W) - W / 2.0) / W
    Yn = (np.arange(H) - H / 2.0) / H
    XX = np.broadcast_to(Xn[None, :], (H, W))
    YY = np.broadcast_to(Yn[:, None], (H, W))
    cols_full = _poly_cols(XX, YY, kind)
    for c in range(3):
        v = L[yy, xx, c][sel].astype(np.float64)
        good = np.isfinite(v)
        good &= v < np.percentile(v[good], 60)  # descarta corona residual
        for _ in range(6):
            sol, *_ = np.linalg.lstsq(A[good], v[good], rcond=None)
            resid = v - A @ sol
            s = max(float(np.std(resid[good])), 1e-12)
            g2 = (resid < 2.0 * s) & (resid > -4.0 * s)
            if g2.sum() < 50 or np.array_equal(g2, good):
                break
            good = g2
        acc = np.zeros((H, W), np.float32)
        for coef, term in zip(sol, cols_full):
            acc += np.float32(coef) * term.astype(np.float32)
        bg[..., c] = acc
    return bg


# ----------------------------------------------------------------------------
# Aplanado radial
# ----------------------------------------------------------------------------

def radius_map(shape, cx, cy):
    H, W = shape
    dx = np.arange(W, dtype=np.float32) - np.float32(cx)
    dy = np.arange(H, dtype=np.float32) - np.float32(cy)
    return np.hypot(dx[None, :], dy[:, None])


def _clipped_radial_profile(v, ri, nb, valid=None):
    vv = v.ravel().astype(np.float64)
    rr = ri.ravel()
    if valid is not None:
        keep0 = valid.ravel()
        vv, rr = vv[keep0], rr[keep0]
    cnt = np.bincount(rr, minlength=nb)
    s = np.bincount(rr, weights=vv, minlength=nb)
    s2 = np.bincount(rr, weights=vv * vv, minlength=nb)
    mean = s / np.maximum(cnt, 1)
    var = np.maximum(s2 / np.maximum(cnt, 1) - mean * mean, 0)
    std = np.sqrt(var)
    keep = np.abs(vv - mean[rr]) < 3 * std[rr] + 1e-12
    cnt2 = np.bincount(rr[keep], minlength=nb)
    s3 = np.bincount(rr[keep], weights=vv[keep], minlength=nb)
    p = s3 / np.maximum(cnt2, 1)
    good = cnt2 > 0
    idx = np.arange(nb)
    if good.sum() >= 2:
        p = np.interp(idx, idx[good], p[good])
    return np.maximum(p, 1e-12)


def _smooth_log(p, sigma=3.0):
    return np.exp(gaussian_filter1d(np.log(np.maximum(p, 1e-12)), sigma))


def radial_flatten(L, cx, cy, r_lim, mode="lum"):
    H, W, _ = L.shape
    r = radius_map((H, W), cx, cy)
    nb = max(int(min(cx, cy, W - 1 - cx, H - 1 - cy)), 16)
    ri = np.minimum(r.astype(np.int32), nb - 1)
    outside = r >= (r_lim + 3.0)          # el disco no entra en el perfil
    i0 = min(int(np.ceil(r_lim)) + 4, nb - 2)
    centers = np.arange(nb) + 0.5

    def build_profile(v):
        p = _clipped_radial_profile(v, ri, nb, valid=outside)
        p[:i0] = p[i0]                    # suelo del divisor dentro del disco
        return _smooth_log(p, 3.0)

    if mode == "lum":
        p = build_profile(luminance(np.maximum(L, 0)))
        div = np.interp(r, centers, p).astype(np.float32)
        F = L / div[..., None]
        prof = p[None, :]
    else:
        F = np.empty_like(L)
        prof = np.empty((3, nb))
        for c in range(3):
            p = build_profile(np.maximum(L[..., c], 0))
            prof[c] = p
            F[..., c] = L[..., c] / np.interp(r, centers, p).astype(np.float32)
    ann = (r > 1.05 * r_lim) & (r < 1.4 * r_lim)
    med = np.median(F[ann].reshape(-1, 3), axis=0)
    F /= np.maximum(med, 1e-9)[None, None, :]
    return F, r, centers, prof


# ----------------------------------------------------------------------------
# Realce multiescala y salida
# ----------------------------------------------------------------------------

def _struct_annulus(r, r_lim):
    sel = (r > 1.05 * r_lim) & (r < min(3.5 * r_lim, 0.95 * float(r.max())))
    if not sel.any():
        sel = r > 1.02 * r_lim
    return sel


def multiscale_enhance(F, r, r_lim, sigmas, gains):
    # recorte a un rango razonable para que los outliers exteriores
    # (ruido amplificado por el aplanado) no dominen los filtros gaussianos
    ann0 = _struct_annulus(r, r_lim)
    qlo = np.percentile(F[ann0], 0.2)
    qhi = np.percentile(F[ann0], 99.8)
    span = max(qhi - qlo, 1e-6)
    Fc = np.clip(F, qlo - span, qhi + span)
    ann = (r > r_lim + 2) & (r < r_lim + 14)
    fill = np.median(Fc[ann].reshape(-1, 3), axis=0)
    G = Fc.copy()
    G[r < r_lim + 1.5] = fill
    out = G.copy()
    for s, g in zip(sigmas, gains):
        blur = np.stack([gaussian_filter(G[..., c], s) for c in range(3)], -1)
        out += np.float32(g) * (G - blur)
    w = np.clip((r - (r_lim - 1.5)) / 3.0, 0, 1)[..., None]
    return w * out + (1 - w) * Fc


def to_display(F, r, r_lim, gamma=2.2):
    sel = _struct_annulus(r, r_lim)
    lo = np.percentile(F[sel], 0.5)
    hi = np.percentile(F[sel], 99.7)
    x = np.clip((F - lo) / max(hi - lo, 1e-9), 0, 1)
    return x ** (1.0 / gamma)


def save_outputs(outdir, L, F, disp, centers, prof, jpg_quality=92):
    import tifffile
    os.makedirs(outdir, exist_ok=True)
    tifffile.imwrite(os.path.join(outdir, "01_hdr_lineal_f32.tif"),
                     L.astype(np.float32), photometric="rgb")
    tifffile.imwrite(os.path.join(outdir, "02_hdr_aplanado_f32.tif"),
                     F.astype(np.float32), photometric="rgb")
    tifffile.imwrite(os.path.join(outdir, "03_final_16bit.tif"),
                     (np.clip(disp, 0, 1) * 65535 + 0.5).astype(np.uint16),
                     photometric="rgb")
    hdr = "r_px," + ",".join("P%d" % i for i in range(prof.shape[0]))
    np.savetxt(os.path.join(outdir, "perfil_radial.csv"),
               np.column_stack([centers, prof.T]), delimiter=",",
               header=hdr, comments="")
    try:
        from PIL import Image
        stepd = max(1, int(np.ceil(max(disp.shape[:2]) / 2000)))
        im = (np.clip(disp[::stepd, ::stepd], 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(im).save(os.path.join(outdir, "preview.jpg"),
                                 quality=jpg_quality)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Autotest con corona sintetica
# ----------------------------------------------------------------------------

def _streak_mask(shape, c, ang=0.6, width=2.5, half_len=150, off=(280.0, -120.0)):
    """Banda recta anclada al centro c, simula la traza de un satelite."""
    H, W = shape
    x = np.arange(W, dtype=np.float32)[None, :] - (c[0] + off[0])
    y = np.arange(H, dtype=np.float32)[:, None] - (c[1] + off[1])
    ca, sa = np.cos(ang), np.sin(ang)
    par = x * ca + y * sa
    perp = -x * sa + y * ca
    return ((np.abs(perp) < width) & (np.abs(par) < half_len)).astype(np.float32)


def selftest(outdir="selftest_out"):
    rng = np.random.default_rng(7)
    H = W = 1200
    rm = 140.0
    base = np.array([604.3, 591.7])           # centro (x, y) del fotograma 0
    drift = np.array([3.7, -2.9])             # deriva por fotograma, px
    e = 2.0 ** np.arange(0, 17, 2)            # 9 exposiciones, 16 EV
    K = 0.12
    SKY0 = 2.5e-5                             # cielo de totalidad rel. al limbo
    MOON = 2.0e-5
    color = np.array([1.0, 0.95, 0.90], np.float32)

    def corona(cx, cy):
        r = radius_map((H, W), cx, cy)
        th = np.arctan2(np.arange(H, dtype=np.float32)[:, None] - cy,
                        np.arange(W, dtype=np.float32)[None, :] - cx)
        g = np.maximum((r - rm) / rm, 0.0)
        L = (np.exp(-g / 0.35) * (0.75 + 0.25 * np.cos(5 * th + 2 * g) ** 2)
             + 0.004 * np.exp(-g / 1.2))
        L[r < rm] = MOON
        return L.astype(np.float32)

    sky_x = np.broadcast_to(np.arange(W, dtype=np.float32)[None, :] / W, (H, W))
    NREP = 3                                   # tomas por escalon de exposicion
    STREAK_G, STREAK_R = 4, 1                  # el transitorio va en el grupo 4
    truth_centers, frames, e_list = [], [], []
    kf = 0
    for kg, ek in enumerate(e):
        for rep in range(NREP):
            c = base + kf * drift + rng.uniform(-1, 1, 2)
            truth_centers.append(c)
            L = corona(c[0], c[1])[..., None] * color[None, None, :]
            sky = SKY0 * (1.0 + 0.5 * sky_x)
            I_clean = (L + sky[..., None]) * ek * K
            if kg == STREAK_G and rep == STREAK_R:
                # transitorio brillante (satelite) en un unico fotograma
                I_clean += 0.5 * _streak_mask((H, W), c)[..., None]
            noise = rng.normal(0, 8e-4, L.shape) + rng.normal(0, 1, L.shape) * \
                np.sqrt(np.maximum(I_clean, 0) * 3e-5)
            I = np.clip(I_clean + noise, 0, 1).astype(np.float32)
            sat = (I_clean.max(axis=2) > 0.995)
            frames.append((I, sat))
            e_list.append(ek)
            kf += 1
    e_all = np.asarray(e_list)
    e_rel = e_all / e_all.max()

    groups = group_by_exposure(e_rel)
    g_ref = len(groups) // 2
    g_order = [g_ref] + [g for g in range(len(groups)) if g != g_ref]
    prev = None
    acc = HDRAccumulator(frames[0][0].shape, trim=True)
    ref = None
    r_lim = None
    cerrs = np.zeros(len(frames))
    for gi in g_order:
        for i in groups[gi]:
            img, sat = frames[i]
            init = prev if prev is not None else None
            cx, cy, r, q, npts = detect_center(luminance(img), init=init)
            prev = (cx, cy, r)
            cerrs[i] = float(np.hypot(cx - truth_centers[i][0],
                                      cy - truth_centers[i][1]))
            if ref is None:
                ref = (cx, cy)
                r_lim = r
            dy, dx = ref[1] - cy, ref[0] - cx
            if abs(dx) > 0.05 or abs(dy) > 0.05:
                img = np.stack([ndshift(img[..., c], (dy, dx), order=3,
                                        mode="nearest") for c in range(3)], -1)
                sat = ndshift(sat.astype(np.float32), (dy, dx), order=1,
                              mode="nearest") > 0.2
            acc.add_group_frame(img, sat)
        acc.close_group(float(np.mean(e_rel[groups[gi]])))

    L, cov = acc.result()
    bg = fit_background(L, ref[0], ref[1], r_lim, kind="plane", margin=40)
    L = L - bg
    F, r, centers, prof = radial_flatten(L, ref[0], ref[1], r_lim, mode="lum")
    E = multiscale_enhance(F, r, r_lim, sigmas=(3, 10, 30), gains=(0.8, 0.6, 0.4))
    disp = to_display(E, r, r_lim)

    # comparacion fotometrica con la verdad en el sistema de referencia
    Ltrue = corona(*ref)
    lum_rec = luminance(np.maximum(L, 1e-12))
    ann = (r > rm * 1.05) & (r < rm * 3.0) & (cov > 0)
    dfull = np.log10(np.maximum(lum_rec, 1e-12)) - np.log10(Ltrue)
    dfull = dfull - np.median(dfull[ann])
    d = dfull[ann]
    d = d[np.abs(d) < 5 * np.std(d) + 1e-9]
    rms = float(np.sqrt(np.mean(d ** 2)))

    # residuo sobre la traza del transitorio, en coordenadas de referencia
    smask = _streak_mask((H, W), np.asarray(ref)) > 0.5
    smask &= ann
    streak_res = float(np.mean(np.abs(dfull[smask]))) if smask.any() else 0.0

    log("autotest (%d fotogramas, %d grupos, 1 transitorio inyectado):"
        % (len(frames), len(groups)))
    log("  error de centro max = %.3f px  (umbral 0.6)" % cerrs.max())
    log("  RMS fotometrico     = %.4f dex (umbral 0.04, anillo 1.05..3.0 r_luna)"
        % rms)
    log("  residuo transitorio = %.4f dex (umbral 0.05 tras recorte)"
        % streak_res)
    log("  radio detectado     = %.2f px  (verdad %.1f)" % (r_lim, rm))
    ok = (cerrs.max() < 0.6) and (rms < 0.04) and (streak_res < 0.05) \
        and abs(r_lim - rm) < 2.0
    save_outputs(outdir, L, F, disp, centers, prof)
    log("  salidas en %s/" % outdir)
    log("  RESULTADO: %s" % ("PASA" if ok else "FALLA"))
    return 0 if ok else 1


# ----------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Fusion HDR lineal y aplanado radial de la corona solar.")
    ap.add_argument("inputs", nargs="*", help="ficheros RAW (CR2/CR3/NEF/ARW...)")
    ap.add_argument("-o", "--out", default="salida", help="directorio de salida")
    ap.add_argument("--selftest", action="store_true",
                    help="ejecuta la validacion con datos sinteticos y sale")
    ap.add_argument("--half", action="store_true",
                    help="demosaico a media resolucion (prueba rapida)")
    ap.add_argument("--wb", choices=["camera", "daylight"], default="camera")
    ap.add_argument("--times", default=None,
                    help="tiempos de exposicion si faltan metadatos: 1/8000,1/2000,...")
    ap.add_argument("--moon-radius", type=float, default=None,
                    help="radio lunar aproximado en px (resolucion completa)")
    ap.add_argument("--center", default=None,
                    help="centro x,y manual (con --no-align)")
    ap.add_argument("--no-align", action="store_true",
                    help="omite el registro (tripode estable, prueba de flujo)")
    ap.add_argument("--floor", type=float, default=1.5e-3,
                    help="suelo de ruido en fraccion de saturacion")
    ap.add_argument("--trim", choices=["auto", "off"], default="auto",
                    help="recorte de extremos por pixel dentro de cada grupo "
                         "de igual exposicion (rechazo de transitorios)")
    ap.add_argument("--bg", choices=["plane", "poly2", "const", "none"],
                    default="plane", help="modelo de fondo de cielo")
    ap.add_argument("--bg-k", type=float, default=4.0,
                    help="radio interior del fondo en unidades de r_luna")
    ap.add_argument("--profile", choices=["lum", "rgb"], default="lum",
                    help="perfil radial por luminancia (conserva color) o por canal")
    ap.add_argument("--no-enhance", action="store_true")
    ap.add_argument("--sigmas", default="3,10,30,90")
    ap.add_argument("--gains", default="1.0,0.8,0.6,0.4")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    paths = []
    for pat in args.inputs:
        paths.extend(sorted(glob.glob(pat)))
    paths = sorted(dict.fromkeys(paths))
    if len(paths) < 2:
        sys.exit("Se necesitan al menos 2 ficheros. Usa --selftest para validar.")

    log("leyendo exposiciones de %d ficheros..." % len(paths))
    e_rel, ts = relative_exposures(paths, args.times)
    for p, t, er in zip(paths, ts, e_rel):
        log("  %-28s t=%-10s e_rel=2^%+.2f"
            % (os.path.basename(p), ("%.6g s" % t) if t else "?",
               np.log2(er)))
    log("rango dinamico del bracket: %.1f EV" % np.ptp(np.log2(e_rel)))

    sAB = 1.0 if args.half else 2.0
    r_full = args.moon_radius
    rminA = (0.9 * r_full / 2.0) if r_full else None
    rmaxA = (1.1 * r_full / 2.0) if r_full else None

    centersA = [None] * len(paths)
    if not args.no_align:
        log("pase A: deteccion del limbo a media resolucion...")
        prev = None
        for i, p in enumerate(paths):
            lum = luminance(load_raw(p, half=True, wb=args.wb)[0])
            cx, cy, r, q, npts = detect_center(lum, init=prev,
                                               rmin=rminA, rmax=rmaxA)
            prev = (cx, cy, r)
            centersA[i] = (cx, cy, r)
            log("  %-28s centro=(%.1f, %.1f) r=%.1f  sigma=%.2f px  n=%d"
                % (os.path.basename(p), cx, cy, r, q, npts))

    groups = group_by_exposure(e_rel)
    g_ref = len(groups) // 2                     # grupo de exposicion mediana
    g_order = [g_ref] + [g for g in range(len(groups)) if g != g_ref]
    ref_path = paths[groups[g_ref][0]]
    log("pase B: fusion de %d grupos de exposicion (referencia: %s)..."
        % (len(groups), os.path.basename(ref_path)))
    acc = None
    ref = None
    r_lim = None
    max_shift = 0.0
    for gi in g_order:
        members = groups[gi]
        e_g = float(np.mean(e_rel[members]))
        for i in members:
            img, sat = load_raw(paths[i], half=args.half, wb=args.wb)
            if acc is None:
                acc = HDRAccumulator(img.shape, floor=args.floor,
                                     trim=(args.trim == "auto"))
            if args.no_align:
                if ref is None:
                    if args.center:
                        cx, cy = (float(v) for v in args.center.split(","))
                        if r_full:
                            r = r_full * (0.5 if args.half else 1.0)
                        else:
                            cx, cy, r, _, _ = detect_center(luminance(img))
                    else:
                        cx, cy, r, _, _ = detect_center(luminance(img))
                    ref, r_lim = (cx, cy), r
                acc.add_group_frame(img, sat)
                log("  %-28s sin alinear, e_rel=2^%+.2f"
                    % (os.path.basename(paths[i]), np.log2(e_rel[i])))
                continue
            ca = centersA[i]
            init = (ca[0] * sAB, ca[1] * sAB, ca[2] * sAB)
            cx, cy, r, q, npts = detect_center(luminance(img), init=init)
            if ref is None:
                ref, r_lim = (cx, cy), r
            dy, dx = ref[1] - cy, ref[0] - cx
            max_shift = max(max_shift, abs(dx), abs(dy))
            if abs(dx) > 0.05 or abs(dy) > 0.05:
                img = np.stack([ndshift(img[..., c], (dy, dx), order=3,
                                        mode="nearest") for c in range(3)], -1)
                sat = ndshift(sat.astype(np.float32), (dy, dx), order=1,
                              mode="nearest") > 0.2
            acc.add_group_frame(img, sat)
            log("  %-28s desplazamiento=(%+.2f, %+.2f) px  sigma=%.2f"
                % (os.path.basename(paths[i]), dx, dy, q))
        n, mode = acc.close_group(e_g)
        log("  grupo e_rel=2^%+.2f cerrado: %d tomas, recorte: %s"
            % (np.log2(e_g), n, mode))

    L, cov = acc.result()
    log("fondo de cielo (%s)..." % args.bg)
    margin = int(max_shift) + 16
    bg = fit_background(L, ref[0], ref[1], r_lim, kind=args.bg,
                        margin=margin, k=args.bg_k)
    L = L - bg
    log("aplanado radial (%s)..." % args.profile)
    F, r, centers, prof = radial_flatten(L, ref[0], ref[1], r_lim,
                                         mode=args.profile)
    if args.no_enhance:
        out_img = F
    else:
        sig = [float(s) for s in args.sigmas.split(",")]
        gai = [float(g) for g in args.gains.split(",")]
        log("realce multiescala sigmas=%s ganancias=%s" % (sig, gai))
        out_img = multiscale_enhance(F, r, r_lim, sig, gai)
    disp = to_display(out_img, r, r_lim)
    save_outputs(args.out, L, F, disp, centers, prof)
    log("hecho. Salidas en %s/" % args.out)
    log("  01_hdr_lineal_f32.tif   radiancia lineal (para tu propio procesado)")
    log("  02_hdr_aplanado_f32.tif fondo sustraido + aplanado radial")
    log("  03_final_16bit.tif      version estirada para acabar en Photoshop")


if __name__ == "__main__":
    main()
