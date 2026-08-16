# Photographers

**Fotografía para científicos** · **Photography for scientists**

Herramientas de fotografía y física de la luz que funcionan enteras en el navegador.
Photography and light-physics tools that run entirely in the browser.

🔗 **[falevian.github.io/Photographers](https://falevian.github.io/Photographers/)**

[Español](#español) · [English](#english)

---

## Español

Veintidós documentos que resuelven cuestiones fotográficas con el modelo físico o estadístico
delante: simuladores, métricas, catálogos, scripts de procesado y su documentación.

Todo el cálculo ocurre en el navegador. No hay servidor, ni cuenta, ni telemetría, y cada
página es **un solo archivo HTML** que funciona también sin conexión una vez cargado. La
única dependencia externa es d3, y solo en las páginas de red. Las herramientas de
revelado y procesado son scripts de Python que se ejecutan en tu ordenador, no en el
navegador; solo requieren numpy.

Cada página tiene un conmutador **ES / EN** arriba a la derecha. La elección se recuerda de
una página a otra y puede forzarse añadiendo `?lang=es` o `?lang=en` a la dirección. Sin
elección previa se sigue el idioma del navegador.

### Planificar la toma

| Documento | Qué hace | Peso |
|---|---|---:|
| [`simulador-eclipse-coruna.html`](simulador-eclipse-coruna.html) | Encuadre y exposición del eclipse total del 12 de agosto de 2026: si la corona te cabe en el encuadre, horquilla de exposición por fases con la fotometría de Espenak, extinción atmosférica, trípode frente a seguimiento, y ficha de campo imprimible. | 130 KB |
| [`simulador-flash.html`](simulador-flash.html) | Banco óptico de flash. La dureza de una sombra la fija el tamaño angular de la fuente vista desde el sujeto: sombras, caída de luz por número guía, vencer al sol y balance con la luz ambiente. | 53 KB |

### El objetivo y el plano nítido

Qué carácter tiene el objetivo y dónde cae realmente el plano nítido. Lo primero son
las aberraciones que el diseñador decidió no corregir; lo segundo, si el telémetro y el
ojo aciertan a ponerlo donde uno cree, y qué le hace al objetivo el vidrio del sensor.

| Documento | Qué hace | Peso |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 objetivos de montura Leica M, de 1925 a 2026, con 32 descriptores cada uno. Reconstruye el disco de desenfoque por trazado geométrico, mide la distancia de carácter entre dos objetivos y devuelve sus vecinos más próximos. | 166 KB |
| [`telemetro-m11.html`](telemetro-m11.html) | Qué ve el ojo por el visor de la M11 y qué queda de ello en el sensor. Seis lienzos que van del parche del telémetro a la rejilla de fotositos, con el error de coseno al recomponer y una tasa de acierto por Montecarlo. | 90 KB |
| [`stack-sensor.html`](stack-sensor.html) | Por qué un gran angular calculado para película se deshace en las esquinas de una cámara digital: el vidrio que cubre el sensor es una lámina plano-paralela que el objetivo nunca tuvo en cuenta. Traza los rayos reales por hasta tres láminas y compara dos sensores a la vez. Manual: [`manual-stack-sensor.html`](manual-stack-sensor.html). | 50 KB |

### Analizar tus propias fotos

| Documento | Qué hace | Peso |
|---|---|---:|
| [`analisis-centrado.html`](analisis-centrado.html) | Dónde cae el sujeto dentro del fotograma a lo largo de una colección entera, con qué dispersión y con qué sesgo. Contrasta tu práctica real con la regla de los tercios y con el centrado estricto, sin dar por buena ninguna. Salida visual de [`subject_center.py`](scripts/analitica/subject_center.py). | 152 KB |

### Revelar y procesar

Estas tres trabajan sobre archivos ya tomados. El programa es un script de Python y
la página es su manual; el código está en [`scripts/`](scripts/).

| Documento | Qué hace | Peso |
|---|---|---:|
| [`peliculas-icc.html`](peliculas-icc.html) | Cinco películas clásicas modeladas a partir de la respuesta física publicada por el fabricante, no por ajuste visual: el color sale de integrar el espectro a 1 nm entre 380 y 730. Genera perfiles ICC para Capture One, compuestos sobre la respuesta real de tu cámara. Código: [`peliculas.py`](scripts/peliculas/peliculas.py) y [`grano.py`](scripts/peliculas/grano.py). | 75 KB |
| [`manual-eclipse-hdr.html`](manual-eclipse-hdr.html) | Fusión HDR lineal y aplanado radial de la corona solar a partir de horquillas RAW. El gradiente coronal abarca tres órdenes de magnitud y no se comprime con una curva: se elimina dividiendo por el perfil radial. Código: [`eclipse_hdr.py`](scripts/eclipse/eclipse_hdr.py). | 89 KB |
| [`manual-procesar-sol.html`](manual-procesar-sol.html) | El disco solar en luz blanca: oscurecimiento del limbo, manchas y granulación. Qué hacer con el gradiente radial antes de tocar el contraste. Código: [`procesar_sol.py`](scripts/eclipse/procesar_sol.py). | 83 KB |

### Fotógrafos: influencia y parecido

| Documento | Qué hace | Peso |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 autores y 467 relaciones de influencia declaradas. Traza linajes hacia arriba o hacia abajo, busca la ruta entre dos autores y dimensiona los nodos por nivel trófico. | 199 KB |
| [`index_mobile_ios.html`](index_mobile_ios.html) | La misma red, adaptada a pantalla pequeña y a interacción táctil. | 207 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 309 autores colocados por parecido entre sus imágenes, con las fotos incrustadas. Da la distancia de contenido de cada pareja y, a la vez, su distancia en la red de influencia. | 6,4 MB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | Cómo se juzga una imagen a lo largo del tiempo de procesamiento visual, tratado como actualización bayesiana. | 43 KB |

### Publicar en papel

| Documento | Qué hace | Peso |
|---|---|---:|
| [`zine-generator.html`](zine-generator.html) | Maquetación de fanzines y fotolibros a partir de tus propias imágenes, con la imposición de cuadernillo resuelta y exportación a PDF. Las tipografías van incrustadas. | 665 KB |

### Documentación

| Documento | Qué documenta |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | Manual de uso del simulador del eclipse. Sin fórmulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Geometría del encuadre, fotometría, extinción y difracción. Modelo, derivaciones y supuestos declarados. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Manual ilustrado de la carta óptica, con capturas del propio documento y cinco recetas paso a paso. |
| [`guia-simulador.html`](guia-simulador.html) | Guía del banco óptico de flash: qué hace cada control y en qué fórmulas se apoya. |
| [`manual-flash-ttl-q3.html`](manual-flash-ttl-q3.html) | Flash TTL con la Leica Q3 43: cómo mide, cómo sincroniza y por qué a potencia plena el pulso no cabe entero en la ventana de 1/2000 s. Con dos calculadoras. |
| [`manual-telemetro-m11.html`](manual-telemetro-m11.html) | Manual del simulador de telémetro, con el modelo físico, la verificación numérica y un anexo ilustrado sobre el disco de Airy. Seis figuras incrustadas. |
| [`manual-stack-sensor.html`](manual-stack-sensor.html) | Manual del simulador del stack: el modelo de trazado, cómo se leen la mancha RMS y la MTF, y qué es heurístico y qué no. |
| [`manual-medidas.html`](manual-medidas.html) | Referencia de todas las medidas del análisis de centrado: qué es cada una, cómo se define, cómo se interpreta y hasta dónde llega. |

### El código

Las herramientas de revelado y procesado son scripts de Python; sus páginas son los
manuales. El código vive en [`scripts/`](scripts/), una carpeta por herramienta.

| Carpeta | Contiene |
|---|---|
| [`scripts/peliculas/`](scripts/peliculas/) | `peliculas.py` (los cinco modelos, el lector y el escritor de perfiles ICC), `grano.py`, el `LEEME.md` original y un preset de Capture One. Solo requiere numpy. |
| [`scripts/eclipse/`](scripts/eclipse/) | `eclipse_hdr.py`, `procesar_sol.py`, `deriva_solar.py` y su `README.md`. |
| [`scripts/analitica/`](scripts/analitica/) | `subject_center.py`, el análisis que alimenta la página de centrado. |

### Notas

- El explorador de distancias pesa 6,4 MB porque lleva las fotografías incrustadas en
  base64. Es lo que le permite funcionar sin conexión, pero conviene abrirlo con red
  decente y no es el mejor candidato para un móvil con datos.
- El simulador del eclipse está calculado para el 12 de agosto de 2026. Después de esa
  fecha sigue sirviendo como banco de pruebas de encuadre y exposición solar, pero las
  efemérides dejan de corresponder a un evento próximo.
- `index-old.html` queda fuera del índice a propósito: es la versión inglesa anterior de
  la red, conservada como histórico y superada por `red-influencia.html`.

### Cómo abrirlo

Basta con clonar el repositorio y abrir `index.html` en el navegador; los enlaces entre
páginas son rutas relativas y funcionan en local. Para servirlo:

```bash
python3 -m http.server 8000
```

---

## English

Twenty-two documents that settle photographic questions with the physical or statistical
model in plain sight: simulators, metrics, catalogues, processing scripts and their
documentation.

Every calculation happens in the browser. There is no server, no account and no telemetry,
and each page is **a single HTML file** that keeps working offline once loaded. The only
external dependency is d3, and only on the network pages. The developing and processing
tools are Python scripts that run on your own machine rather than in the browser; they
require only numpy.

Every page carries an **ES / EN** switch in the top right corner. The choice is remembered
from one page to the next and can be forced by adding `?lang=en` or `?lang=es` to the
address. With no prior choice, the browser's language is followed.

### Planning the shot

| Document | What it does | Size |
|---|---|---:|
| [`simulador-eclipse-coruna.html`](simulador-eclipse-coruna.html) | Framing and exposure for the total solar eclipse of 12 August 2026: whether the corona fits your frame, the exposure bracket phase by phase using Espenak's photometry, atmospheric extinction, tripod against tracking, and a printable field sheet. | 130 KB |
| [`simulador-flash.html`](simulador-flash.html) | Flash optical bench. The hardness of a shadow is set by the angular size of the source as seen from the subject: shadows, light falloff from the guide number, overpowering the sun, and balance with ambient light. | 53 KB |

### The lens and the plane of focus

What character the lens has and where the plane of focus actually falls. The first is
the aberrations its designer chose not to correct; the second, whether the rangefinder
and the eye manage to put it where you think, and what the sensor's glass does to the lens.

| Document | What it does | Size |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 Leica M-mount lenses, from 1925 to 2026, with 32 descriptors each. Reconstructs the defocus disc by geometric tracing, measures the character distance between two lenses and returns their nearest neighbours. | 166 KB |
| [`telemetro-m11.html`](telemetro-m11.html) | What the eye sees through the M11 viewfinder and what survives of it on the sensor. Six canvases running from the rangefinder patch to the grid of photosites, with the cosine error from recomposing and a Monte Carlo hit rate. | 90 KB |
| [`stack-sensor.html`](stack-sensor.html) | Why a wide-angle computed for film falls apart in the corners of a digital camera: the glass covering the sensor is a plane-parallel plate the lens never accounted for. Traces the real rays through up to three plates and compares two sensors at once. Manual: [`manual-stack-sensor.html`](manual-stack-sensor.html). | 50 KB |

### Analysing your own photographs

| Document | What it does | Size |
|---|---|---:|
| [`analisis-centrado.html`](analisis-centrado.html) | Where the subject falls inside the frame across a whole collection, with how much spread and what bias. Sets your actual practice against the rule of thirds and against strict centring, taking neither for granted. Visual output of [`subject_center.py`](scripts/analitica/subject_center.py). | 152 KB |

### Developing and processing

These three work on files you have already shot. The program is a Python script and
the page is its manual; the code lives in [`scripts/`](scripts/).

| Document | What it does | Size |
|---|---|---:|
| [`peliculas-icc.html`](peliculas-icc.html) | Five classic films modelled from the physical response published by the manufacturer, not by eyeballing: the colour comes from integrating the spectrum at 1 nm between 380 and 730. Generates ICC profiles for Capture One, composed over your camera's real response. Code: [`peliculas.py`](scripts/peliculas/peliculas.py) and [`grano.py`](scripts/peliculas/grano.py). | 75 KB |
| [`manual-eclipse-hdr.html`](manual-eclipse-hdr.html) | Linear HDR merge and radial flattening of the solar corona from RAW brackets. The coronal gradient spans three orders of magnitude and does not compress with a curve: it is removed by dividing by the radial profile. Code: [`eclipse_hdr.py`](scripts/eclipse/eclipse_hdr.py). | 89 KB |
| [`manual-procesar-sol.html`](manual-procesar-sol.html) | The solar disc in white light: limb darkening, sunspots and granulation. What to do with the radial gradient before touching contrast at all. Code: [`procesar_sol.py`](scripts/eclipse/procesar_sol.py). | 83 KB |

### Photographers: influence and likeness

| Document | What it does | Size |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 authors and 467 declared influence relationships. Trace lineages upstream or downstream, look up the route between two authors, and size the nodes by trophic level. | 199 KB |
| [`index_mobile_ios.html`](index_mobile_ios.html) | The same network, adapted to small screens and touch interaction. | 207 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 309 authors placed by the likeness between their images, with the photographs embedded. Gives the content distance for each pair and, alongside it, their distance in the influence network. | 6.4 MB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | How an image is judged across the time course of visual processing, treated as Bayesian updating. | 43 KB |

### Publishing on paper

| Document | What it does | Size |
|---|---|---:|
| [`zine-generator.html`](zine-generator.html) | Layout for fanzines and photobooks from your own images, with the booklet imposition already solved and PDF export. Fonts are embedded. | 665 KB |

### Documentation

| Document | What it documents |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | User manual for the eclipse simulator. No formulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Framing geometry, photometry, extinction and diffraction. Model, derivations and stated assumptions. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Illustrated manual for the optical chart, with screenshots from the document itself and five step-by-step recipes. |
| [`guia-simulador.html`](guia-simulador.html) | Guide to the flash optical bench: what each control does and which formulas it rests on. |
| [`manual-flash-ttl-q3.html`](manual-flash-ttl-q3.html) | TTL flash with the Leica Q3 43: how it meters, how it syncs, and why at full power the pulse does not fit inside the 1/2000 s window. With two calculators. |
| [`manual-telemetro-m11.html`](manual-telemetro-m11.html) | Manual for the rangefinder simulator, with the physical model, the numerical verification and an illustrated annex on the Airy disc. Six embedded figures. |
| [`manual-stack-sensor.html`](manual-stack-sensor.html) | Manual for the stack simulator: the tracing model, how to read the RMS spot and the MTF, and what is heuristic and what is not. |
| [`manual-medidas.html`](manual-medidas.html) | Reference for every measure in the subject-placement analysis: what each one is, how it is defined, how to read it and how far it goes. |

### The code

The developing and processing tools are Python scripts; their pages are the manuals.
The code lives in [`scripts/`](scripts/), one folder per tool.

| Folder | Contents |
|---|---|
| [`scripts/peliculas/`](scripts/peliculas/) | `peliculas.py` (the five models, the ICC profile reader and writer), `grano.py`, the original `LEEME.md` and a Capture One preset. Requires only numpy. |
| [`scripts/eclipse/`](scripts/eclipse/) | `eclipse_hdr.py`, `procesar_sol.py`, `deriva_solar.py` and their `README.md`. |
| [`scripts/analitica/`](scripts/analitica/) | `subject_center.py`, the analysis that feeds the placement page. |

### Notes

- The distance explorer weighs 6.4 MB because it carries the photographs embedded as
  base64. That is what lets it run offline, but it is worth opening on a decent connection
  and it is not the best candidate for a phone on mobile data.
- The eclipse simulator is computed for 12 August 2026. After that date it still serves as
  a test bench for framing and solar exposure, but the ephemerides no longer correspond to
  an upcoming event.
- `index-old.html` is deliberately left out of the index: it is the earlier English version
  of the network, kept as a historical record and superseded by `red-influencia.html`.

### Running it

Clone the repository and open `index.html` in a browser; the links between pages are
relative paths and work locally. To serve it:

```bash
python3 -m http.server 8000
```

---

Rafael Vida
