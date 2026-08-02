# Photographers

**Fotografía para científicos** · **Photography for scientists**

Herramientas de fotografía y física de la luz que funcionan enteras en el navegador.
Photography and light-physics tools that run entirely in the browser.

🔗 **[falevian.github.io/Photographers](https://falevian.github.io/Photographers/)**

[Español](#español) · [English](#english)

---

## Español

Trece documentos que resuelven cuestiones fotográficas con el modelo físico o estadístico
delante: simuladores, métricas, catálogos y su documentación.

Todo el cálculo ocurre en el navegador. No hay servidor, ni cuenta, ni telemetría, y cada
página es **un solo archivo HTML** que funciona también sin conexión una vez cargado. La
única dependencia externa es d3, y solo en las páginas de red.

Cada página tiene un conmutador **ES / EN** arriba a la derecha. La elección se recuerda de
una página a otra y puede forzarse añadiendo `?lang=es` o `?lang=en` a la dirección. Sin
elección previa se sigue el idioma del navegador.

### Planificar la toma

| Documento | Qué hace | Peso |
|---|---|---:|
| [`simulador-eclipse-coruna.html`](simulador-eclipse-coruna.html) | Encuadre y exposición del eclipse total del 12 de agosto de 2026: si la corona te cabe en el encuadre, horquilla de exposición por fases con la fotometría de Espenak, extinción atmosférica, trípode frente a seguimiento, y ficha de campo imprimible. | 80 KB |
| [`simulador-flash.html`](simulador-flash.html) | Banco óptico de flash. La dureza de una sombra la fija el tamaño angular de la fuente vista desde el sujeto: sombras, caída de luz por número guía, vencer al sol y balance con la luz ambiente. | 56 KB |

### Carácter óptico

| Documento | Qué hace | Peso |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 objetivos de montura Leica M, de 1925 a 2026, con 32 descriptores cada uno. Reconstruye el disco de desenfoque por trazado geométrico, mide la distancia de carácter entre dos objetivos y devuelve sus vecinos más próximos. | 168 KB |

### Fotógrafos: influencia y parecido

| Documento | Qué hace | Peso |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 autores y 467 relaciones de influencia declaradas. Traza linajes hacia arriba o hacia abajo, busca la ruta entre dos autores y dimensiona los nodos por nivel trófico. | 200 KB |
| [`index_mobile_ios.html`](index_mobile_ios.html) | La misma red, adaptada a pantalla pequeña y a interacción táctil. | 208 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 309 autores colocados por parecido entre sus imágenes, con las fotos incrustadas. Da la distancia de contenido de cada pareja y, a la vez, su distancia en la red de influencia. | 6,4 MB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | Cómo se juzga una imagen a lo largo del tiempo de procesamiento visual, tratado como actualización bayesiana. | 44 KB |

### Publicar en papel

| Documento | Qué hace | Peso |
|---|---|---:|
| [`zine-generator.html`](zine-generator.html) | Maquetación de fanzines y fotolibros a partir de tus propias imágenes, con la imposición de cuadernillo resuelta y exportación a PDF. Las tipografías van incrustadas. | 668 KB |

### Documentación

| Documento | Qué documenta |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | Manual de uso del simulador del eclipse. Sin fórmulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Geometría del encuadre, fotometría, extinción y difracción. Modelo, derivaciones y supuestos declarados. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Manual ilustrado de la carta óptica, con capturas del propio documento y cinco recetas paso a paso. |
| [`guia-simulador.html`](guia-simulador.html) | Guía del banco óptico de flash: qué hace cada control y en qué fórmulas se apoya. |

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

Thirteen documents that settle photographic questions with the physical or statistical
model in plain sight: simulators, metrics, catalogues and their documentation.

Every calculation happens in the browser. There is no server, no account and no telemetry,
and each page is **a single HTML file** that keeps working offline once loaded. The only
external dependency is d3, and only on the network pages.

Every page carries an **ES / EN** switch in the top right corner. The choice is remembered
from one page to the next and can be forced by adding `?lang=en` or `?lang=es` to the
address. With no prior choice, the browser's language is followed.

### Planning the shot

| Document | What it does | Size |
|---|---|---:|
| [`simulador-eclipse-coruna.html`](simulador-eclipse-coruna.html) | Framing and exposure for the total solar eclipse of 12 August 2026: whether the corona fits your frame, the exposure bracket phase by phase using Espenak's photometry, atmospheric extinction, tripod against tracking, and a printable field sheet. | 80 KB |
| [`simulador-flash.html`](simulador-flash.html) | Flash optical bench. The hardness of a shadow is set by the angular size of the source as seen from the subject: shadows, light falloff from the guide number, overpowering the sun, and balance with ambient light. | 56 KB |

### Optical character

| Document | What it does | Size |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 Leica M-mount lenses, from 1925 to 2026, with 32 descriptors each. Reconstructs the defocus disc by geometric tracing, measures the character distance between two lenses and returns their nearest neighbours. | 168 KB |

### Photographers: influence and likeness

| Document | What it does | Size |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 authors and 467 declared influence relationships. Trace lineages upstream or downstream, look up the route between two authors, and size the nodes by trophic level. | 200 KB |
| [`index_mobile_ios.html`](index_mobile_ios.html) | The same network, adapted to small screens and touch interaction. | 208 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 309 authors placed by the likeness between their images, with the photographs embedded. Gives the content distance for each pair and, alongside it, their distance in the influence network. | 6.4 MB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | How an image is judged across the time course of visual processing, treated as Bayesian updating. | 44 KB |

### Publishing on paper

| Document | What it does | Size |
|---|---|---:|
| [`zine-generator.html`](zine-generator.html) | Layout for fanzines and photobooks from your own images, with the booklet imposition already solved and PDF export. Fonts are embedded. | 668 KB |

### Documentation

| Document | What it documents |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | User manual for the eclipse simulator. No formulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Framing geometry, photometry, extinction and diffraction. Model, derivations and stated assumptions. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Illustrated manual for the optical chart, with screenshots from the document itself and five step-by-step recipes. |
| [`guia-simulador.html`](guia-simulador.html) | Guide to the flash optical bench: what each control does and which formulas it rests on. |

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
