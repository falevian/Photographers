#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deriva_solar.py

Mide la deriva de seguimiento de una montura a partir de una serie temporal de
imagenes del Sol, y descompone la deriva observada en sus terminos fisicos:

    1. Refraccion atmosferica variable (dominante a baja altura).
    2. Movimiento propio del Sol en ascension recta (si se sigue a ritmo sideral).
    3. Movimiento propio del Sol en declinacion (nunca compensado por un
       seguidor de un solo eje).
    4. Termino lineal residual: desalineacion polar, error de ritmo y flexion
       sistematica. Se convierte a un error polar equivalente.
    5. Residuo no modelado: ruido aleatorio (estabilizador activo, viento,
       vibracion) y componente periodica (error periodico del reductor).

La posicion NO se mide por centroide de intensidad: durante las fases
parciales el centroide del creciente no coincide con el centro del Sol. Se
localiza el limbo por maximo de gradiente con refinamiento subpixel y se
ajusta una circunferencia de radio fijo por RANSAC, que descarta los puntos
del limbo lunar. La escala angular se deduce del diametro aparente del Sol,
asi que no depende de que la focal declarada del objetivo sea exacta.

Uso tipico:

    python3 deriva_solar.py ./tomas --lat 43.37 --lon -8.40 --utc-offset 2 \
            --focal 500 --pixel 4.35 --ritmo solar

Prueba del procedimiento sin imagenes reales: genera una serie sintetica con
deriva conocida (disco con oscurecimiento de limbo, fase parcial creciente y
ruido de posicion) y despues la analiza.

    python3 deriva_solar.py --demo ./prueba
    python3 deriva_solar.py ./prueba --focal 500 --pixel 4.35

Salidas: <prefijo>.csv con la serie completa, <prefijo>_deriva.png con cuatro
paneles (deriva y modelo, trayectoria, residuo, periodograma) y
<prefijo>_informe.txt.

Dependencias: numpy, scipy, matplotlib, pillow.
Opcionales: rawpy (para NEF, CR2, ARW), exifread (fechas en RAW).
"""

import argparse
import os
import sys
import glob
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy import ndimage, optimize, signal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OMEGA_SID = 15.041069  # arcsec/s, tasa sideral
OMEGA_SOL = 15.000000  # arcsec/s, tasa solar media
EXT_RAW = (".nef", ".cr2", ".cr3", ".arw", ".raf", ".dng", ".orf", ".rw2")
EXT_STD = (".jpg", ".jpeg", ".tif", ".tiff", ".png")


# --------------------------------------------------------------------------
# Lectura de imagenes y marcas de tiempo
# --------------------------------------------------------------------------

def _fecha_exif(ruta):
    """Fecha de la toma (hora local de la camara) o None."""
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            ex = im.getexif()
        if ex:
            try:
                sub = ex.get_ifd(0x8769) or {}   # la sub-IFD Exif, no la principal
            except Exception:
                sub = {}
            cad = sub.get(36867) or sub.get(36868) or ex.get(306)
            frac = sub.get(37521) or sub.get(37520) or "0"
            if cad:
                t = datetime.strptime(str(cad).strip()[:19], "%Y:%m:%d %H:%M:%S")
                return t + timedelta(seconds=float("0." + str(frac).strip()))
    except Exception:
        pass
    try:
        import exifread
        with open(ruta, "rb") as f:
            tags = exifread.process_file(f, details=False,
                                         stop_tag="EXIF SubSecTimeOriginal")
        cad = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        frac = tags.get("EXIF SubSecTimeOriginal")
        if cad:
            t = datetime.strptime(str(cad).strip()[:19], "%Y:%m:%d %H:%M:%S")
            if frac:
                t += timedelta(seconds=float("0." + str(frac).strip()))
            return t
    except Exception:
        pass
    return None


def cargar(ruta, binning=1):
    """Devuelve (imagen monocroma float32, fecha local o None)."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in EXT_RAW:
        import rawpy
        with rawpy.imread(ruta) as raw:
            rgb = raw.postprocess(no_auto_bright=True, output_bps=16,
                                  use_camera_wb=False, gamma=(1, 1),
                                  half_size=False)
        g = rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    else:
        from PIL import Image
        with Image.open(ruta) as im:
            arr = np.asarray(im)
        arr = arr.astype(np.float32)
        g = arr.mean(axis=2) if arr.ndim == 3 else arr
    if binning > 1:
        g = g[::binning, ::binning]
    return g, _fecha_exif(ruta)


# --------------------------------------------------------------------------
# Deteccion del limbo y ajuste de circunferencia
# --------------------------------------------------------------------------

def puntos_limbo(g, max_puntos=4000):
    """
    Puntos del limbo por maximo de gradiente. No se usa el umbral de
    semialtura porque el oscurecimiento del limbo lo desplaza hacia dentro
    (con un perfil I = a + b*mu el sesgo llega al 3 % del radio).
    """
    gs = ndimage.gaussian_filter(g.astype(np.float32), 1.2)
    fondo = float(np.median(gs))
    disco = float(np.percentile(gs, 99.5))
    if disco - fondo < 1e-6:
        return None, 0.0
    m = gs > 0.5 * (fondo + disco)
    m = ndimage.binary_opening(m, np.ones((3, 3)))
    et, n = ndimage.label(m)
    if n == 0:
        return None, 0.0
    tam = ndimage.sum(m, et, range(1, n + 1))
    m = et == (1 + int(np.argmax(tam)))
    area = float(m.sum())
    if area < 400:
        return None, 0.0
    # banda estrecha alrededor del contorno, donde debe estar el limbo real
    anillo = (ndimage.binary_dilation(m, iterations=6) ^
              ndimage.binary_erosion(m, iterations=6))
    gy, gx = np.gradient(gs)
    mag = np.hypot(gx, gy)
    pico = float(mag[anillo].max()) if anillo.any() else 0.0
    if pico <= 0:
        return None, area
    borde = anillo & (mag > 0.35 * pico)
    ys, xs = np.nonzero(borde)
    h, w = g.shape
    ok = (xs > 2) & (ys > 2) & (xs < w - 3) & (ys < h - 3)
    xs, ys = xs[ok], ys[ok]
    if xs.size < 50:
        return None, area
    # supresion de no maximos y refinamiento subpixel del maximo de gradiente
    # (una banda simetrica en torno al pico sesgaria el limbo hacia dentro)
    m0 = mag[ys, xs]
    nx, ny = gx[ys, xs] / m0, gy[ys, xs] / m0
    mp = ndimage.map_coordinates(mag, [ys + ny, xs + nx], order=1)
    mm = ndimage.map_coordinates(mag, [ys - ny, xs - nx], order=1)
    keep = (m0 >= mp) & (m0 >= mm)
    xs, ys, nx, ny = xs[keep], ys[keep], nx[keep], ny[keep]
    m0, mp, mm = m0[keep], mp[keep], mm[keep]
    den = mm - 2 * m0 + mp
    off = np.clip(np.where(np.abs(den) > 1e-9, 0.5 * (mm - mp) / den, 0.0), -1, 1)
    xf, yf = xs + off * nx, ys + off * ny
    if xf.size < 50:
        return None, area
    if xf.size > max_puntos:
        i = np.linspace(0, xf.size - 1, max_puntos).astype(int)
        xf, yf = xf[i], yf[i]
    return np.column_stack([xf, yf]), area



def ransac_libre(P, r_min, r_max, iters=800, tol=2.0, rng=None):
    """RANSAC de radio libre: circunferencia definida por ternas separadas."""
    rng = rng or np.random.default_rng(0)
    n = len(P)
    i = rng.integers(0, n, (iters, 3))
    A, B, C = P[i[:, 0]], P[i[:, 1]], P[i[:, 2]]
    sep = ((np.linalg.norm(A - B, axis=1) > 0.6 * r_min) &
           (np.linalg.norm(B - C, axis=1) > 0.6 * r_min) &
           (np.linalg.norm(A - C, axis=1) > 0.6 * r_min))
    A, B, C = A[sep], B[sep], C[sep]
    if len(A) < 5:
        return None
    d = 2 * (A[:, 0] * (B[:, 1] - C[:, 1]) + B[:, 0] * (C[:, 1] - A[:, 1]) +
             C[:, 0] * (A[:, 1] - B[:, 1]))
    val = np.abs(d) > 1e-6
    A, B, C, d = A[val], B[val], C[val], d[val]
    a2, b2, c2 = (A ** 2).sum(1), (B ** 2).sum(1), (C ** 2).sum(1)
    ux = (a2 * (B[:, 1] - C[:, 1]) + b2 * (C[:, 1] - A[:, 1]) +
          c2 * (A[:, 1] - B[:, 1])) / d
    uy = (a2 * (C[:, 0] - B[:, 0]) + b2 * (A[:, 0] - C[:, 0]) +
          c2 * (B[:, 0] - A[:, 0])) / d
    U = np.column_stack([ux, uy])
    r = np.linalg.norm(A - U, axis=1)
    val = (r > r_min) & (r < r_max)
    if not val.any():
        return None
    U, r = U[val], r[val]
    Q = P if n <= 800 else P[np.linspace(0, n - 1, 800).astype(int)]
    dist = np.linalg.norm(Q[None, :, :] - U[:, None, :], axis=2)
    cuenta = (np.abs(dist - r[:, None]) < tol).sum(axis=1)
    k = int(np.argmax(cuenta))
    return U[k, 0], U[k, 1], r[k], int(cuenta[k])


def ransac_fijo(P, r, tol=1.5, iters=400, rng=None):
    """RANSAC con radio fijo: cada par de puntos define dos centros posibles."""
    rng = rng or np.random.default_rng(0)
    n = len(P)
    A, B = P[rng.integers(0, n, iters)], P[rng.integers(0, n, iters)]
    d = np.linalg.norm(B - A, axis=1)
    val = (d > 0.3 * r) & (d < 1.999 * r)
    if not val.any():
        return None
    A, B, d = A[val], B[val], d[val]
    M = 0.5 * (A + B)
    u = (B - A) / d[:, None]
    nv = np.column_stack([-u[:, 1], u[:, 0]])
    h = np.sqrt(np.maximum(r * r - 0.25 * d * d, 0.0))[:, None]
    C = np.vstack([M + h * nv, M - h * nv])
    Q = P if n <= 800 else P[np.linspace(0, n - 1, 800).astype(int)]
    dist = np.linalg.norm(Q[None, :, :] - C[:, None, :], axis=2)
    return C[int(np.argmax((np.abs(dist - r) < tol).sum(axis=1)))]


def ajustar_disco(P, r, tol=1.5):
    """Centro del disco con radio fijo. Devuelve (xc, yc, n_inliers, rms)."""
    c0 = ransac_fijo(P, r, tol=tol)
    if c0 is None:
        return None
    inl = np.abs(np.linalg.norm(P - c0, axis=1) - r) < 3 * tol
    if inl.sum() < 40:
        return None
    Q = P[inl]

    def res(c):
        return np.linalg.norm(Q - c, axis=1) - r

    sol = optimize.least_squares(res, c0, loss="soft_l1", f_scale=tol,
                                 max_nfev=200)
    return (sol.x[0], sol.x[1], int(inl.sum()),
            float(np.sqrt(np.mean(res(sol.x) ** 2))))


# --------------------------------------------------------------------------
# Efemeride solar de baja precision (Meeus) y refraccion
# --------------------------------------------------------------------------

def jd_desde(dt_utc):
    return 2440587.5 + dt_utc.timestamp() / 86400.0


def sol_ecuatorial(jd):
    """RA, Dec (grados), distancia (UA) y semidiametro (arcsec)."""
    d = jd - 2451545.0
    L = math.radians((280.460 + 0.9856474 * d) % 360.0)
    g = math.radians((357.528 + 0.9856003 * d) % 360.0)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    eps = math.radians(23.439 - 3.6e-7 * d)
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))) % 360.0
    dec = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    R = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)
    return ra, dec, R, 959.63 / R


def horizontales(jd, ra, dec, lat, lon):
    """Altura verdadera (grados) y angulo paralactico (grados)."""
    d = jd - 2451545.0
    gmst = (280.46061837 + 360.98564736629 * d) % 360.0
    H = math.radians((gmst + lon - ra) % 360.0)
    phi, delta = math.radians(lat), math.radians(dec)
    alt = math.degrees(math.asin(math.sin(phi) * math.sin(delta) +
                                 math.cos(phi) * math.cos(delta) * math.cos(H)))
    q = math.degrees(math.atan2(math.sin(H),
                                math.tan(phi) * math.cos(delta) -
                                math.sin(delta) * math.cos(H)))
    return alt, q


def refraccion(alt_deg, presion=1010.0, temp=15.0):
    """Refraccion en arcsec (Saemundsson, altura verdadera -> aparente)."""
    h = max(alt_deg, -0.5)
    R = 1.02 / math.tan(math.radians(h + 10.3 / (h + 5.11)))  # arcmin
    R *= (presion / 1010.0) * (283.0 / (273.0 + temp))
    return R * 60.0


# --------------------------------------------------------------------------
# Medida de la serie
# --------------------------------------------------------------------------

def medir_serie(ficheros, binning, radio_px, verbose=True):
    """Dos pasadas: primero el radio del disco, luego el centro de cada toma."""
    limbos, areas, fechas, usados = [], [], [], []
    for i, f in enumerate(ficheros):
        try:
            g, t = cargar(f, binning)
        except Exception as e:
            print(f"  aviso: no se pudo leer {os.path.basename(f)} ({e})")
            continue
        P, area = puntos_limbo(g)
        limbos.append(P)
        areas.append(area)
        fechas.append(t)
        usados.append(f)
        if verbose and (i % 10 == 0):
            print(f"  leyendo {i + 1}/{len(ficheros)}", end="\r", flush=True)
    if verbose:
        print(" " * 40, end="\r")

    if radio_px is not None:
        r0 = radio_px / binning
    else:
        # el radio es constante durante la sesion: se estima con ajuste libre
        # sobre las tomas de mayor area, que son las menos eclipsadas
        a = np.array([x if x else 0.0 for x in areas])
        if not (a > 0).any():
            sys.exit("No se ha detectado el disco en ninguna imagen.")
        orden = np.argsort(a)[::-1][:max(3, len(a) // 4)]
        cand = []
        for k in orden:
            P = limbos[k]
            if P is None:
                continue
            ra = math.sqrt(a[k] / math.pi)
            s = ransac_libre(P, 0.8 * ra, 3.0 * ra)
            if s is not None:
                cand.append((s[3], s[2]))
        if not cand:
            sys.exit("No se ha podido ajustar el limbo. Prueba con --radio-px.")
        cand.sort(reverse=True)
        r0 = float(np.median([c[1] for c in cand[:max(3, len(cand) // 2)]]))

    filas = []
    for f, P, t in zip(usados, limbos, fechas):
        aj = ajustar_disco(P, r0) if P is not None else None
        if aj is None:
            filas.append((f, t, np.nan, np.nan, 0, np.nan))
        else:
            xc, yc, n, rms = aj
            filas.append((f, t, xc * binning, yc * binning, n, rms))
    return filas, r0 * binning



# --------------------------------------------------------------------------
# Modelo astronomico y ajuste por minimos cuadrados
# --------------------------------------------------------------------------

def construir_modelo(tiempos_utc, lat, lon, ritmo, presion, temp):
    """
    Desplazamientos conocidos, en arcsec, referidos a la primera toma y
    expresados en el marco ecuatorial (x hacia el este, y hacia el norte).
    Devuelve un diccionario con cada termino por separado y la suma.
    """
    n = len(tiempos_utc)
    dra = np.zeros(n); ddec = np.zeros(n); dref = np.zeros(n)
    alt = np.zeros(n); q = np.zeros(n); ref = np.zeros(n)
    ra0 = dec0 = ref0 = None
    for i, t in enumerate(tiempos_utc):
        jd = jd_desde(t)
        ra, dec, _, _ = sol_ecuatorial(jd)
        a, qq = horizontales(jd, ra, dec, lat, lon)
        R = refraccion(a, presion, temp)
        if ra0 is None:
            ra0, dec0, ref0 = ra, dec, R
        dra[i] = ((ra - ra0 + 180.0) % 360.0 - 180.0) * 3600.0 * math.cos(math.radians(dec))
        ddec[i] = (dec - dec0) * 3600.0
        dref[i] = R - ref0
        alt[i], q[i], ref[i] = a, qq, R
    k = 1.0 if ritmo == "sideral" else 0.0
    qr = np.radians(q)
    mx = k * dra + dref * np.sin(qr)
    my = ddec + dref * np.cos(qr)
    return dict(mx=mx, my=my, dra=k * dra, ddec=ddec, dref=dref,
                alt=alt, q=q, ref=ref)


def ajuste_global(t, dx, dy, mx, my, con_modelo=True, clip=4.0, n_iter=3):
    """
    dx = a0 + a1 t + p11 mx + p12 my
    dy = b0 + b1 t + p21 mx + p22 my

    Se resuelve conjuntamente para ambos ejes. La submatriz p absorbe la
    orientacion desconocida del sensor respecto al marco ecuatorial (giro y
    eventual inversion de paridad). El termino lineal recoge lo que la montura
    hace mal: desalineacion polar, error de ritmo y flexion lineal. Se aplica
    rechazo iterativo de atipicos con sigma robusta, porque una sola toma con
    el disco mal ajustado bastaria para falsear la pendiente.
    """
    n = len(t)
    cols = 8 if con_modelo else 4
    tc = t - np.mean(t)          # centrado: mejora el condicionamiento
    A = np.zeros((2 * n, cols))
    A[:n, 0] = 1.0
    A[:n, 1] = tc
    A[n:, 2] = 1.0
    A[n:, 3] = tc
    if con_modelo:
        A[:n, 4] = mx
        A[:n, 5] = my
        A[n:, 6] = mx
        A[n:, 7] = my
    b = np.concatenate([dx, dy])
    esc = np.linalg.norm(A, axis=0)
    esc[esc == 0] = 1.0
    A = A / esc                  # columnas normalizadas antes de resolver
    bueno = np.ones(n, bool)
    for _ in range(n_iter):
        sel = np.concatenate([bueno, bueno])
        par, *_ = np.linalg.lstsq(A[sel], b[sel], rcond=1e-10)
        res = b - A @ par
        d = np.hypot(res[:n], res[n:])
        mad = float(np.median(np.abs(d - np.median(d))))
        sig = 1.4826 * mad if mad > 0 else float(np.std(d))
        nuevo_b = d < np.median(d) + clip * max(sig, 1e-9)
        if nuevo_b.sum() < max(6, cols) or (nuevo_b == bueno).all():
            bueno = nuevo_b if nuevo_b.sum() >= max(6, cols) else bueno
            break
        bueno = nuevo_b
    sel = np.concatenate([bueno, bueno])
    par, *_ = np.linalg.lstsq(A[sel], b[sel], rcond=1e-10)
    pred = A @ par
    res = b - pred
    dof = max(2 * int(bueno.sum()) - cols, 1)
    s2 = float(res[sel] @ res[sel]) / dof
    cov = s2 * np.linalg.pinv(A[sel].T @ A[sel])
    par = par / esc              # se deshace el escalado
    cov = cov / np.outer(esc, esc)
    return dict(par=par, cov=cov, px=pred[:n], py=pred[n:],
                rx=res[:n], ry=res[n:], sigma=math.sqrt(s2),
                cond=float(np.linalg.cond(A[sel])), bueno=bueno)


def periodograma(t, y, pmin=20.0, pmax=None):
    """Lomb-Scargle sobre muestreo irregular. Devuelve periodos (min) y potencia."""
    y = np.asarray(y, float) - np.mean(y)
    span = float(t[-1] - t[0])
    if span <= 0 or np.allclose(y, 0) or len(t) < 8:
        return np.array([]), np.array([])
    pmax = pmax or span / 2.0
    if pmax <= pmin:
        return np.array([]), np.array([])
    per = np.linspace(pmin, pmax, 600)
    pw = signal.lombscargle(np.asarray(t, float), y, 2 * math.pi / per,
                            normalize=True)
    return per / 60.0, pw


# --------------------------------------------------------------------------
# Serie sintetica para validar el procedimiento sin imagenes reales
# --------------------------------------------------------------------------

def generar_demo(destino, n=45, radio=180.0, w=1400, h=1000, cad=120.0,
                 deriva=(0.90, 0.35), ruido_px=0.5, semilla=1):
    """Disco con oscurecimiento de limbo, fase parcial y deriva conocida."""
    from PIL import Image
    os.makedirs(destino, exist_ok=True)
    rng = np.random.default_rng(semilla)
    yy, xx = np.mgrid[0:h, 0:w]

    def borde(d):  # perfil de borde suave sin desbordar la exponencial
        return 1.0 / (1.0 + np.exp(np.clip(d / 0.8, -60, 60)))

    t0 = datetime(2026, 8, 12, 17, 31, 0, tzinfo=timezone.utc)  # 19:31 CEST
    for i in range(n):
        xc = w / 2 + deriva[0] * i + rng.normal(0, ruido_px)
        yc = h / 2 + deriva[1] * i + rng.normal(0, ruido_px)
        rr = np.hypot(xx - xc, yy - yc)
        mu = np.sqrt(np.clip(1 - (rr / radio) ** 2, 0, 1))
        img = borde(rr - radio) * (0.35 + 0.65 * mu)
        # la Luna entra por la izquierda y cubre hasta ~el 80 % al final
        avance = 2.1 - 3.0 * i / max(n - 1, 1)
        rl = np.hypot(xx - (xc + avance * radio), yy - yc)
        img *= 1.0 - borde(rl - 1.03 * radio)
        img = np.clip(img * 225 + rng.normal(0, 1.5, img.shape) + 6, 0, 255)
        nom = os.path.join(destino, f"demo_{i:03d}.jpg")
        Image.fromarray(img.astype(np.uint8)).save(nom, quality=95)
        ts = (t0 + timedelta(seconds=cad * i)).timestamp()
        os.utime(nom, (ts, ts))  # sin EXIF: el script usara la fecha del fichero
    print(f"Serie sintetica en {destino}: {n} tomas, cadencia {cad:.0f} s, "
          f"deriva inyectada {deriva[0]:.3f} y {deriva[1]:.3f} px/toma, "
          f"radio {radio:.1f} px")


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Mide y descompone la deriva de seguimiento sobre imagenes del Sol.")
    p.add_argument("directorio", nargs="?", help="carpeta con la serie de imagenes")
    p.add_argument("--focal", type=float, default=None, help="focal en mm")
    p.add_argument("--pixel", type=float, default=None, help="paso de pixel en um")
    p.add_argument("--lat", type=float, default=43.37, help="latitud en grados")
    p.add_argument("--lon", type=float, default=-8.40, help="longitud, este positivo")
    p.add_argument("--inicio", default=None,
                   help='hora local de la primera toma, "2026-08-12 19:31:00"')
    p.add_argument("--cadencia", type=float, default=None,
                   help="segundos entre tomas, impone base de tiempos uniforme")
    p.add_argument("--utc-offset", type=float, default=0.0,
                   help="horas de la hora EXIF respecto a UTC (CEST = 2)")
    p.add_argument("--ritmo", choices=["solar", "sideral"], default="solar",
                   help="ritmo al que seguia la montura")
    p.add_argument("--presion", type=float, default=1010.0, help="hPa")
    p.add_argument("--temp", type=float, default=15.0, help="grados C")
    p.add_argument("--bin", type=int, default=1, dest="binning",
                   help="submuestreo de lectura para acelerar")
    p.add_argument("--radio-px", type=float, default=None,
                   help="radio del disco en px si ya se conoce")
    p.add_argument("--escala", type=float, default=None,
                   help="arcsec/px impuesta; por defecto se deduce del disco")
    p.add_argument("--sin-modelo", action="store_true",
                   help="ajusta solo recta, sin terminos astronomicos")
    p.add_argument("--salida", default="deriva", help="prefijo de los ficheros de salida")
    p.add_argument("--demo", metavar="DIR", default=None,
                   help="genera una serie sintetica en DIR y termina")
    a = p.parse_args()

    if a.demo:
        generar_demo(a.demo)
        return
    if not a.directorio:
        p.error("falta el directorio de imagenes (o usa --demo DIR)")

    fich = sorted(f for f in glob.glob(os.path.join(a.directorio, "*"))
                  if f.lower().endswith(EXT_RAW + EXT_STD))
    if not fich:
        sys.exit("No hay imagenes en " + a.directorio)
    print(f"{len(fich)} imagenes en {a.directorio}")

    filas, r_disco = medir_serie(fich, a.binning, a.radio_px)

    # marcas de tiempo: EXIF (hora local) si existe, si no la del fichero (UTC)
    tiempos, sin_exif = [], 0
    for fila in filas:
        f, t = fila[0], fila[1]
        if t is None:
            sin_exif += 1
            tiempos.append(datetime.fromtimestamp(os.path.getmtime(f), timezone.utc))
        else:
            tiempos.append(t.replace(tzinfo=timezone.utc) -
                           timedelta(hours=a.utc_offset))
    if sin_exif:
        print(f"  AVISO: {sin_exif} tomas sin fecha EXIF, se usa la del fichero. "
              "La fecha del fichero se pierde al copiar o exportar; si el "
              "intervalo sale absurdo, usa --inicio y --cadencia.")

    # base de tiempos uniforme impuesta a mano
    if a.cadencia:
        if a.inicio:
            t0 = datetime.strptime(a.inicio, "%Y-%m-%d %H:%M:%S")
            t0 = t0.replace(tzinfo=timezone.utc) - timedelta(hours=a.utc_offset)
        else:
            t0 = tiempos[0]
        tiempos = [t0 + timedelta(seconds=a.cadencia * i)
                   for i in range(len(tiempos))]
        print(f"  base de tiempos impuesta: inicio {t0.isoformat()} UTC, "
              f"cadencia {a.cadencia:.3f} s")
    elif a.inicio:
        t0 = datetime.strptime(a.inicio, "%Y-%m-%d %H:%M:%S")
        t0 = t0.replace(tzinfo=timezone.utc) - timedelta(hours=a.utc_offset)
        desfase = t0 - tiempos[0]
        tiempos = [x + desfase for x in tiempos]

    ok = np.array([not (isinstance(r[2], float) and math.isnan(r[2])) for r in filas])
    if ok.sum() < 5:
        sys.exit("Disco detectado en menos de 5 imagenes. Revisa la exposicion "
                 "o fija --radio-px.")

    idx = np.nonzero(ok)[0]
    tut = [tiempos[i] for i in idx]
    t = np.array([(x - tut[0]).total_seconds() for x in tut])
    xpx = np.array([filas[i][2] for i in idx])
    ypx = np.array([filas[i][3] for i in idx])
    ninl = np.array([filas[i][4] for i in idx])
    rms_aj = np.array([filas[i][5] for i in idx])
    orden = np.argsort(t)
    t, xpx, ypx, ninl, rms_aj = (t[orden], xpx[orden], ypx[orden],
                                 ninl[orden], rms_aj[orden])
    tut = [tut[i] for i in orden]

    # sin una base de tiempos sana, la pendiente no significa nada
    span = float(t[-1] - t[0])
    cad = float(np.median(np.diff(t))) if len(t) > 1 else 0.0
    if span < 60.0 or cad < 0.5:
        sys.exit(
            f"\nBASE DE TIEMPOS INVALIDA: el intervalo entre la primera y la "
            f"ultima toma\nsale de {span:.3f} s y la cadencia mediana de "
            f"{cad:.3f} s. Con eso la pendiente\ndel ajuste diverge y la "
            f"desalineacion estimada es un numero sin sentido.\n"
            f"Causa habitual: las tomas no llevan EXIF y la fecha del fichero "
            f"se perdio al\ncopiarlas o exportarlas, con lo que todas comparten "
            f"el mismo instante.\n"
            f"Solucion: repite indicando la base de tiempos, por ejemplo\n"
            f'  --inicio "2026-08-12 19:31:00" --cadencia 15\n')
    if len(set(t.tolist())) < len(t):
        print(f"  aviso: hay marcas de tiempo repetidas "
              f"({len(t) - len(set(t.tolist()))} tomas)")

    # escala angular: el diametro del Sol es un patron conocido
    sd = sol_ecuatorial(jd_desde(tut[0]))[3]
    esc_disco = sd / r_disco
    esc_geom = (206.265 * a.pixel / a.focal) if (a.pixel and a.focal) else None
    escala = a.escala or esc_disco

    # marco cielo: se invierte el eje y de la imagen para obtener un sistema
    # con y hacia arriba, como el (este, norte) del modelo
    dx = (xpx - xpx[0]) * escala
    dy = -(ypx - ypx[0]) * escala

    M = construir_modelo(tut, a.lat, a.lon, a.ritmo, a.presion, a.temp)
    F = ajuste_global(t, dx, dy, M["mx"], M["my"], con_modelo=not a.sin_modelo)
    par, cov, sigma = F["par"], F["cov"], F["sigma"]

    a1, b1 = par[1] * 60.0, par[3] * 60.0           # arcsec/min
    err = np.sqrt(np.abs(np.diag(cov))) * 60.0
    tasa = math.hypot(a1, b1)
    etasa = math.hypot(a1 * err[1], b1 * err[3]) / max(tasa, 1e-9)
    # una desalineacion polar D produce como maximo omega*D de deriva.
    # D[arcmin] = tasa[arcsec/min] * 206264.8 / (60 * OMEGA_SID * 60) = tasa * 3.8093
    desalin = tasa * 206264.8 / (3600.0 * OMEGA_SID)

    bn = F["bueno"]
    per_x, pw_x = periodograma(t[bn], F["rx"][bn])
    per_y, pw_y = periodograma(t[bn], F["ry"][bn])

    # ---------------------------------------------------------------- informe
    L = []
    ap = L.append
    ap("=" * 68)
    ap("DERIVA DE SEGUIMIENTO")
    ap("=" * 68)
    ap(f"Tomas con disco ajustado    : {ok.sum()} de {len(filas)}")
    ap(f"Intervalo                   : {t[-1] / 60.0:.1f} min "
       f"(cadencia mediana {np.median(np.diff(t)):.1f} s)")
    ap(f"Radio del disco             : {r_disco:.2f} px, "
       f"{int(np.median(ninl))} puntos de limbo, "
       f"rms del ajuste {np.median(rms_aj):.2f} px")
    ap(f"Escala por diametro solar   : {escala:.4f} arcsec/px")
    if esc_geom:
        ap(f"Escala 206.265 p/f          : {esc_geom:.4f} arcsec/px "
           f"(discrepancia {100 * (esc_geom / escala - 1):+.1f} %)")
    ap(f"Altura del Sol              : {M['alt'][0]:.2f} a {M['alt'][-1]:.2f} grados")
    ap("")
    ap(f"Deriva total observada      : x {dx[-1] - dx[0]:+8.1f} arcsec "
       f"({(dx[-1] - dx[0]) / escala:+8.1f} px)")
    ap(f"                              y {dy[-1] - dy[0]:+8.1f} arcsec "
       f"({(dy[-1] - dy[0]) / escala:+8.1f} px)")
    ap(f"Modulo                      : {math.hypot(dx[-1] - dx[0], dy[-1] - dy[0]):.1f} arcsec")
    ap("")
    if not a.sin_modelo:
        ap("Terminos conocidos en el intervalo:")
        ap(f"  refraccion diferencial    : {M['dref'][-1] - M['dref'][0]:+8.1f} arcsec"
           f"   [{M['ref'][0] / 60:.2f} a {M['ref'][-1] / 60:.2f} arcmin]")
        ap(f"  Sol en ascension recta    : {M['dra'][-1] - M['dra'][0]:+8.1f} arcsec"
           f"   [seguimiento {a.ritmo}]")
        ap(f"  Sol en declinacion        : {M['ddec'][-1] - M['ddec'][0]:+8.1f} arcsec")
        ap(f"  numero de condicion       : {F['cond']:.1f}"
           + ("  (alto: modelo y recta poco separables)" if F["cond"] > 5e3 else ""))
        ap("")
    ap("Termino lineal residual, atribuible a la montura:")
    ap(f"  eje x  {a1:+8.3f} +- {err[1]:.3f} arcsec/min")
    ap(f"  eje y  {b1:+8.3f} +- {err[3]:.3f} arcsec/min")
    ap(f"  modulo {tasa:8.3f} +- {etasa:.3f} arcsec/min  "
       f"({tasa / escala:.2f} px/min)")
    if desalin > 600.0:
        ap("  desalineacion polar equivalente: NO FISICA "
           f"({desalin:.3g} arcmin)")
        ap("  Revisa la base de tiempos: la linea 'Intervalo' de arriba debe")
        ap("  coincidir con la duracion real de la sesion.")
    else:
        ap(f"  desalineacion polar equivalente: {desalin:.1f} arcmin "
           f"({desalin / 60.0:.2f} grados)")
    ap("")
    nrech = int((~F["bueno"]).sum())
    ap(f"Residuo tras el modelo      : rms {sigma:.2f} arcsec "
       f"({sigma / escala:.2f} px), {nrech} tomas rechazadas por atipicas")
    if per_x.size:
        ix, iy = int(np.argmax(pw_x)), int(np.argmax(pw_y))
        ap(f"Pico del periodograma       : x {per_x[ix]:5.1f} min (potencia {pw_x[ix]:.2f}), "
           f"y {per_y[iy]:5.1f} min (potencia {pw_y[iy]:.2f})")
    ap("")
    ap("Lectura:")
    sist = math.hypot(dx[-1] - dx[0], dy[-1] - dy[0])
    if sigma > 0.35 * max(sist, 1e-9):
        ap("  El residuo domina sobre la deriva sistematica: el salto entre")
        ap("  fotogramas es aleatorio. Sospechosos por orden: estabilizador")
        ap("  optico o IBIS activo, viento sobre el tubo, asentamiento del")
        ap("  tripode, tiron de cables.")
    else:
        ap("  La deriva es sistematica y queda descrita por el modelo mas una")
        ap("  recta. El termino lineal se reduce mejorando la puesta en")
        ap("  estacion; la refraccion diferencial no la corrige la montura.")
    if per_x.size and max(pw_x.max(), pw_y.max()) > 0.5:
        ap("  Hay componente periodica significativa: compatible con el error")
        ap("  periodico del reductor o con flexion modulada por el giro en AR.")
    ap("=" * 68)
    informe = "\n".join(L)
    print(informe)
    with open(a.salida + "_informe.txt", "w") as fh:
        fh.write(informe + "\n")

    # -------------------------------------------------------------------- csv
    with open(a.salida + ".csv", "w") as fh:
        fh.write("fichero,utc,t_s,x_px,y_px,n_limbo,rms_px,dx_arcsec,dy_arcsec,"
                 "modelo_x,modelo_y,resid_x,resid_y,alt_deg,refr_arcsec,usada\n")
        for j in range(len(t)):
            fh.write(f"{os.path.basename(filas[idx[orden[j]]][0])},"
                     f"{tut[j].isoformat()},{t[j]:.2f},{xpx[j]:.3f},{ypx[j]:.3f},"
                     f"{ninl[j]},{rms_aj[j]:.3f},{dx[j]:.2f},{dy[j]:.2f},"
                     f"{F['px'][j]:.2f},{F['py'][j]:.2f},{F['rx'][j]:.2f},"
                     f"{F['ry'][j]:.2f},{M['alt'][j]:.3f},{M['ref'][j]:.1f},"
                     f"{int(F['bueno'][j])}\n")

    # ----------------------------------------------------------------- figuras
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9,
                         "axes.grid": True, "grid.alpha": 0.3})
    fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
    tm = t / 60.0

    ax[0, 0].plot(tm, dx, ".", ms=4, color="#4C72B0", label="x medido")
    ax[0, 0].plot(tm, F["px"], "-", lw=1.2, color="#4C72B0", label="x modelo")
    ax[0, 0].plot(tm, dy, ".", ms=4, color="#DD8452", label="y medido")
    ax[0, 0].plot(tm, F["py"], "-", lw=1.2, color="#DD8452", label="y modelo")
    ax[0, 0].set_xlabel("tiempo (min)")
    ax[0, 0].set_ylabel("desplazamiento (arcsec)")
    ax[0, 0].set_title("Deriva medida y modelo ajustado")
    ax[0, 0].legend(fontsize=7)

    sc = ax[0, 1].scatter(dx, dy, c=tm, s=12, cmap="viridis")
    ax[0, 1].set_aspect("equal", adjustable="datalim")
    ax[0, 1].set_xlabel("x (arcsec)")
    ax[0, 1].set_ylabel("y (arcsec)")
    ax[0, 1].set_title("Trayectoria del centro del disco")
    plt.colorbar(sc, ax=ax[0, 1], label="min")

    ax[1, 0].plot(tm[bn], F["rx"][bn], ".", ms=4, label="residuo x")
    ax[1, 0].plot(tm[bn], F["ry"][bn], ".", ms=4, label="residuo y")
    if (~bn).any():
        ax[1, 0].plot(tm[~bn], F["rx"][~bn], "x", ms=5, color="crimson")
        ax[1, 0].plot(tm[~bn], F["ry"][~bn], "x", ms=5, color="crimson",
                      label="rechazadas")
    ax[1, 0].axhline(0, color="k", lw=0.6)
    ax[1, 0].set_xlabel("tiempo (min)")
    ax[1, 0].set_ylabel("residuo (arcsec)")
    ax[1, 0].set_title(f"Residuo, rms {sigma:.2f} arcsec ({sigma / escala:.2f} px)")
    ax[1, 0].legend(fontsize=7)

    if per_x.size:
        ax[1, 1].plot(per_x, pw_x, lw=1, label="x")
        ax[1, 1].plot(per_y, pw_y, lw=1, label="y")
        ax[1, 1].set_xlabel("periodo (min)")
        ax[1, 1].set_ylabel("potencia normalizada")
        ax[1, 1].set_title("Periodograma del residuo")
        ax[1, 1].legend(fontsize=7)
    else:
        ax[1, 1].axis("off")
    fig.tight_layout()
    fig.savefig(a.salida + "_deriva.png", bbox_inches="tight")
    print(f"\nSalidas: {a.salida}.csv, {a.salida}_deriva.png, "
          f"{a.salida}_informe.txt")


if __name__ == "__main__":
    main()
