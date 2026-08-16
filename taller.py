#!/usr/bin/env python3
"""taller.py — el taller: las herramientas del repositorio encadenadas.

Un servidor local mínimo (solo biblioteca estándar) que sirve las páginas
del repositorio y añade lo que una página estática no puede hacer: ejecutar
los scripts de Python sobre tus carpetas y encadenar los resultados.

    python3 taller.py            # abre http://127.0.0.1:8123/taller.html

El itinerario:
  1. Mirar tu archivo   — subject_center.py sobre una carpeta de fotos,
                          y el análisis se abre ya cargado con tus datos.
  2. El color y el grano — peliculas.py genera (e instala) el perfil ICC;
                          grano.py se aplica por lotes a una carpeta.
  3. Del sensor al papel — el cierre de la cadena, con las páginas estáticas.

Solo escucha en 127.0.0.1. Los resultados van a ~/Photographers-taller/.
Dependencias de los scripts: numpy (peliculas) y además pillow (análisis y
grano). El propio taller no necesita ninguna.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

RAIZ = Path(__file__).resolve().parent
TRABAJO = Path.home() / "Photographers-taller"
PUERTO = 8123

EXT_IMG = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}

# rutas típicas de los perfiles de entrada de Capture One
DIRS_PERFILES = [
    Path("/Applications/Capture One.app/Contents/Frameworks/ImageProcessing.framework/Versions/A/Resources/Profiles/Input"),
    Path.home() / "Library/ColorSync/Profiles",
]

PELICULAS = ["k64", "k25", "velvia50", "pro400h", "trix"]
VIRADOS = ["neutro", "frio", "calido", "sepia", "selenio"]


# ---------------------------------------------------------------- tareas

class Tarea:
    """Un proceso en segundo plano con registro de líneas consultable."""

    def __init__(self, nombre):
        self.nombre = nombre
        self.lineas = []
        self.estado = "corriendo"     # corriendo | ok | error
        self.extra = {}
        self.candado = threading.Lock()

    def log(self, linea):
        with self.candado:
            self.lineas.append(linea.rstrip("\n"))

    def snapshot(self, desde=0):
        with self.candado:
            return {
                "nombre": self.nombre,
                "estado": self.estado,
                "lineas": self.lineas[desde:],
                "total": len(self.lineas),
                "extra": self.extra,
            }


TAREAS: dict[str, Tarea] = {}
CONTADOR = {"n": 0}


def nueva_tarea(nombre):
    CONTADOR["n"] += 1
    tid = f"t{CONTADOR['n']}"
    TAREAS[tid] = Tarea(nombre)
    return tid, TAREAS[tid]


def correr(tarea, cmd, cwd=None):
    """Ejecuta un comando volcando stdout+stderr al registro. Devuelve rc."""
    tarea.log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.Popen(
        [str(c) for c in cmd], cwd=cwd or RAIZ,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", bufsize=1,
    )
    for linea in proc.stdout:
        tarea.log(linea)
    return proc.wait()


# ---------------------------------------------------------------- trabajos

def trabajo_analizar(tarea, p):
    carpeta = Path(p["carpeta"]).expanduser()
    if not carpeta.is_dir():
        tarea.log(f"!! no es una carpeta: {carpeta}")
        tarea.estado = "error"
        return
    TRABAJO.mkdir(exist_ok=True)
    csv = TRABAJO / "analisis.csv"
    cmd = [sys.executable, RAIZ / "scripts/analitica/subject_center.py",
           carpeta, "--csv", csv]
    if p.get("limite"):
        cmd += ["--limit", str(int(p["limite"]))]
    if p.get("inferir_fecha"):
        cmd += ["--infer-date"]
    if p.get("sin_recursion"):
        cmd += ["--no-recursive"]
    rc = correr(tarea, cmd)
    if rc == 0 and csv.exists():
        n = sum(1 for _ in csv.open(encoding="utf-8")) - 1
        tarea.extra = {"csv": str(csv), "filas": n}
        tarea.log(f"listo: {n} fotografías medidas -> {csv}")
        tarea.estado = "ok"
    else:
        tarea.estado = "error"


def trabajo_icc(tarea, p):
    TRABAJO.mkdir(exist_ok=True)
    pel = p.get("pelicula", "k64")
    if pel not in PELICULAS:
        tarea.log(f"!! película desconocida: {pel}")
        tarea.estado = "error"
        return
    cmd = [sys.executable, RAIZ / "scripts/peliculas/peliculas.py"]
    if p.get("perfil"):
        cmd += [p["perfil"]]
    else:
        cmd += ["--generico"]
    cmd += ["--pelicula", pel]
    for clave, bandera in (("ev", "--ev"), ("copia", "--copia"),
                           ("gain", "--gain"), ("n", "--n")):
        if p.get(clave) not in (None, "", 0, "0"):
            cmd += [bandera, str(p[clave])]
    if pel == "trix" and p.get("virado") in VIRADOS:
        cmd += ["--virado", p["virado"]]
    if p.get("instalar"):
        cmd += ["--instalar"]
    else:
        cmd += ["-o", TRABAJO / f"{pel}.icc"]
    rc = correr(tarea, cmd)
    tarea.estado = "ok" if rc == 0 else "error"
    if rc == 0 and not p.get("instalar"):
        tarea.extra = {"icc": str(TRABAJO / f"{pel}.icc")}


def trabajo_grano(tarea, p):
    carpeta = Path(p["carpeta"]).expanduser()
    if not carpeta.is_dir():
        tarea.log(f"!! no es una carpeta: {carpeta}")
        tarea.estado = "error"
        return
    pel = p.get("pelicula", "trix")
    salida = TRABAJO / "grano"
    salida.mkdir(parents=True, exist_ok=True)
    imgs = sorted(f for f in carpeta.iterdir()
                  if f.suffix.lower() in EXT_IMG and not f.name.startswith("."))
    if p.get("limite"):
        imgs = imgs[: int(p["limite"])]
    if not imgs:
        tarea.log("!! la carpeta no contiene imágenes JPEG/PNG/TIFF")
        tarea.estado = "error"
        return
    tarea.log(f"{len(imgs)} imágenes -> {salida}")
    fallos = 0
    for i, img in enumerate(imgs, 1):
        destino = salida / f"{img.stem}_{pel}{img.suffix}"
        cmd = [sys.executable, RAIZ / "scripts/peliculas/grano.py",
               img, destino, "--pelicula", pel]
        if p.get("intensidad") not in (None, "", 1, "1"):
            cmd += ["--intensidad", str(p["intensidad"])]
        rc = correr(tarea, cmd)
        fallos += (rc != 0)
        tarea.extra = {"hechas": i, "total": len(imgs), "salida": str(salida)}
    tarea.log(f"terminado: {len(imgs) - fallos} bien, {fallos} con error")
    tarea.estado = "ok" if fallos == 0 else "error"


TRABAJOS = {"analizar": trabajo_analizar, "icc": trabajo_icc, "grano": trabajo_grano}


# ---------------------------------------------------------------- estado

def modulo_disponible(nombre):
    import importlib.util
    return importlib.util.find_spec(nombre) is not None


def api_estado():
    csv = TRABAJO / "analisis.csv"
    return {
        "python": sys.version.split()[0],
        "ejecutable": sys.executable,
        "numpy": modulo_disponible("numpy"),
        "pillow": modulo_disponible("PIL"),
        "orden_pillow": f"{sys.executable} -m pip install pillow",
        "trabajo": str(TRABAJO),
        "csv_existe": csv.exists(),
        "csv_filas": (sum(1 for _ in csv.open(encoding="utf-8")) - 1) if csv.exists() else 0,
        "inicio": str(Path.home()),
    }


def api_dirs(ruta):
    base = Path(ruta).expanduser() if ruta else Path.home()
    if not base.is_dir():
        return {"error": f"no es una carpeta: {base}"}
    subdirs, nimg = [], 0
    try:
        for f in sorted(base.iterdir()):
            if f.name.startswith("."):
                continue
            if f.is_dir():
                subdirs.append(f.name)
            elif f.suffix.lower() in EXT_IMG:
                nimg += 1
    except PermissionError:
        return {"error": f"sin permiso de lectura: {base}"}
    return {"ruta": str(base), "padre": str(base.parent),
            "carpetas": subdirs[:400], "imagenes": nimg}


def api_perfiles():
    encontrados = []
    for d in DIRS_PERFILES:
        if d.is_dir():
            for f in sorted(d.glob("*.ic[cm]")):
                encontrados.append({"nombre": f.stem, "ruta": str(f)})
    return {"perfiles": encontrados}


# ---------------------------------------------------------------- servidor

# El cargador de la página de análisis se dispara por su propio <input>:
# así funciona aunque ingest() viva en cualquier ámbito.
INYECCION = """
<script>
/* Inyectado por taller.py: carga el CSV recién calculado en el cargador
   propio de la página, como si el usuario lo hubiera soltado a mano. */
fetch('/api/analisis.csv').then(function(r){
  if(!r.ok) throw new Error('sin CSV');
  return r.text();
}).then(function(texto){
  var input=document.getElementById('file');
  var dt=new DataTransfer();
  dt.items.add(new File([texto],'analisis.csv',{type:'text/csv'}));
  input.files=dt.files;
  input.dispatchEvent(new Event('change',{bubbles:true}));
}).catch(function(e){ console.warn('taller:', e.message); });
</script>
"""


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):          # silencio en consola
        pass

    def _json(self, obj, codigo=200):
        cuerpo = json.dumps(obj).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _bytes(self, datos, tipo):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        ruta = unquote(u.path)

        if ruta == "/api/estado":
            return self._json(api_estado())
        if ruta == "/api/dirs":
            return self._json(api_dirs(q.get("ruta", "")))
        if ruta == "/api/perfiles":
            return self._json(api_perfiles())
        if ruta == "/api/tarea":
            t = TAREAS.get(q.get("id", ""))
            if not t:
                return self._json({"error": "tarea desconocida"}, 404)
            return self._json(t.snapshot(int(q.get("desde", 0))))
        if ruta == "/api/analisis.csv":
            csv = TRABAJO / "analisis.csv"
            if not csv.exists():
                return self._json({"error": "aún no hay análisis"}, 404)
            return self._bytes(csv.read_bytes(), "text/csv; charset=utf-8")

        if ruta == "/analisis-live":
            pagina = (RAIZ / "analisis-centrado.html").read_text(encoding="utf-8")
            pagina = pagina.replace("</body>", INYECCION + "</body>")
            return self._bytes(pagina.encode("utf-8"), "text/html; charset=utf-8")

        # estáticos del repositorio
        if ruta == "/":
            ruta = "/taller.html"
        destino = (RAIZ / ruta.lstrip("/")).resolve()
        if not str(destino).startswith(str(RAIZ)) or not destino.is_file():
            return self._json({"error": "no existe"}, 404)
        tipo = mimetypes.guess_type(destino.name)[0] or "application/octet-stream"
        if tipo.startswith("text/"):
            tipo += "; charset=utf-8"
        return self._bytes(destino.read_bytes(), tipo)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        try:
            p = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "JSON inválido"}, 400)

        if u.path == "/api/run":
            trabajo = TRABAJOS.get(p.get("herramienta", ""))
            if not trabajo:
                return self._json({"error": "herramienta desconocida"}, 400)
            tid, tarea = nueva_tarea(p["herramienta"])

            def envoltura():
                try:
                    trabajo(tarea, p)
                except Exception as e:      # el error se enseña, no se traga
                    tarea.log(f"!! excepción: {e}")
                    tarea.estado = "error"

            threading.Thread(target=envoltura, daemon=True).start()
            return self._json({"id": tid})

        return self._json({"error": "no existe"}, 404)


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO
    TRABAJO.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    url = f"http://127.0.0.1:{puerto}/taller.html"
    print(f"El taller: {url}   (Ctrl+C para salir)")
    est = api_estado()
    if not est["pillow"]:
        print(f"AVISO: falta pillow (lo usan el análisis y el grano):\n  {est['orden_pillow']}")
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nhasta otra")


if __name__ == "__main__":
    main()
