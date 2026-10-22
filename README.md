# Photographers

**Fotografía para científicos** · **Photography for scientists**

Herramientas de fotografía y física de la luz que funcionan enteras en el navegador.
Photography and light-physics tools that run entirely in the browser.

🔗 **[lab.rafaelvida.com](https://lab.rafaelvida.com/)**

[Español](#español) · [English](#english)

---

## Español

Treinta y siete documentos que resuelven cuestiones fotográficas con el modelo físico o estadístico
delante: simuladores, métricas, catálogos, scripts de procesado y su documentación.

Todo el cálculo ocurre en el navegador. No hay servidor, ni cuenta, ni telemetría, y cada
página es **un solo archivo HTML** que funciona también sin conexión una vez cargado —
con dos excepciones declaradas: la predicción de niebla y el índice de cielo consultan
Open-Meteo (la niebla, además, los METAR del Iowa Environmental Mesonet) y sin red cargan pero no pueden predecir. Las pocas librerías de terceros (d3, Chart.js, jsPDF, exifr)
se sirven desde el propio repositorio (`vendor/`), no desde un servidor ajeno. Las herramientas de revelado y procesado son scripts de Python
que se ejecutan en tu ordenador, no en el navegador; solo requieren numpy.

Cada página tiene un conmutador **ES / EN** arriba a la derecha. La elección se recuerda de
una página a otra y puede forzarse añadiendo `?lang=es` o `?lang=en` a la dirección. Sin
elección previa se sigue el idioma del navegador.

### Planificar la toma

| Documento | Qué hace | Peso |
|---|---|---:|
| [`simulador-eclipse.html`](simulador-eclipse.html) | Encuadre y exposición del eclipse total del 2 de agosto de 2027 (sur de España, norte de Marruecos, Egipto): si la corona te cabe en el encuadre, horquilla por fases con la fotometría de Espenak, nueve sitios de Tarifa a Luxor con sus horas locales, y ficha de campo imprimible. | 187 KB |
| [`simulador-flash.html`](simulador-flash.html) | Banco óptico de flash. La dureza de una sombra la fija el tamaño angular de la fuente vista desde el sujeto: sombras, caída de luz por número guía, vencer al sol y balance con la luz ambiente. | 97 KB |
| [`exposicion-larga.html`](exposicion-larga.html) | Exposición larga: las seis técnicas de la chuleta de Pit Haupert, y una séptima (cámara quieta, el sujeto deja traza), con el tiempo que piden en tu escena, no el de la receta. Calcula el arrastre del sujeto en píxeles (b = f·v·t/(d·p)), si lo sostienes a pulso con la escalera de apoyos (codos, correa tensada, apoyo, OIS, IBIS, trípode), qué filtro hace falta y qué ISO sin él. Con el sujeto (persona, ciclista, coche, tren) dibujado a su tamaño real en el fotograma y la traza que deja, curva de arrastre frente a trepidación y comparación de los tres cuerpos. | 81 KB |
| [`programa-camara.html`](programa-camara.html) | La automática no es neutral: contiene un programa. Dibuja la línea que sigue —tiempo, diafragma e ISO a cada nivel de luz—, superpone el borrón y la profundidad de campo que tu intención exigía, y señala dónde chocan. Nace de la sección Flusser del ensayo del marco. | 108 KB |
| [`niebla.html`](niebla.html) | Si la niebla se va a formar mañana al amanecer. Índice horario a 48 h sobre la convergencia de temperatura y punto de rocío, y una fusión bayesiana multimodelo —ahora con conjuntos ICON EPS, GFS ENS y ECMWF ENS de 30 a 50 miembros— que reajusta sus pesos con tus propias observaciones y se recalibra (Platt) con tu registro. Las fuentes se resuelven por emplazamiento: en Galicia entra HARMONIE‑AROME de 2 km, y una tabla dice qué modelo hay detrás de cada una, con qué malla y a qué distancia del borde de su dominio. La previsión se congela automáticamente cada noche, así que la observación de la mañana se compara con lo que se predijo la víspera y no con nada posterior. Cada mañana propone la etiqueta a partir del METAR del aeropuerto cercano, y una tercera pestaña calibra las fuentes con el histórico de esa estación: sesgo de T − Td, curva de probabilidad y peso inicial de cada una. Necesita conexión: los datos son de Open-Meteo y, los METAR, del Iowa Environmental Mesonet. Manual: [`manual-niebla.html`](manual-niebla.html); guía rápida: [`guia-niebla.html`](guia-niebla.html). | 182 KB |
| [`astro.html`](astro.html) | Si la noche servirá para fotografiar el cielo. Índice horario que combina nubes por capas, transparencia por aerosoles (AOD de CAMS), seeing por viento en altura, rocío y Luna, con pesos que se reajustan según fotografíes cielo profundo, planetaria o paisaje nocturno. Misma fusión bayesiana, mismas fuentes por emplazamiento y mismo aprendizaje que la niebla. Manual: [`manual-astro.html`](manual-astro.html). | 121 KB |
| [`luz-natural.html`](luz-natural.html) | Cuándo hay buena luz y dónde estará la Luna, para cualquier lugar y fecha: horas dorada y azul con su duración real, acimuts de salidas y puestas, fase lunar dibujada, y el buscador de alineaciones para planificar la Luna sobre tu encuadre. Toda la astronomía en local: funciona sin conexión. | 85 KB |

### El objetivo y el plano nítido

Qué carácter tiene el objetivo y dónde cae realmente el plano nítido. Lo primero son
las aberraciones que el diseñador decidió no corregir; lo segundo, si el telémetro y el
ojo aciertan a ponerlo donde uno cree, y qué le hace al objetivo el vidrio del sensor.

| Documento | Qué hace | Peso |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 objetivos de montura Leica M, de 1925 a 2026, con 32 descriptores cada uno. Reconstruye el disco de desenfoque por trazado geométrico, mide la distancia de carácter entre dos objetivos y devuelve sus vecinos más próximos. | 242 KB |
| [`caracter-optico-reducido.html`](caracter-optico-reducido.html) | Carta reducida de *rendering*: los mismos objetivos en los siete ejes que deciden el carácter visible (esfericidad residual, cromatismo longitudinal, microcontraste, velo, viñeteo, recorte de pupila, rizado asférico), cuatro índices estéticos con su fórmula impresa, par enfrentado, vecinos y mapa. | 111 KB |
| [`telemetro-m11.html`](telemetro-m11.html) | Qué ve el ojo por el visor de la M11 y qué queda de ello en el sensor. Seis lienzos que van del parche del telémetro a la rejilla de fotositos, con el error de coseno al recomponer y una tasa de acierto por Montecarlo. | 134 KB |
| [`sensor.html`](sensor.html) | El sensor en seis pestañas: datos medidos de M11, Q3 y SL3-S (ruido de lectura, ganancia dual, PDR, calculadora SNR), el multishot del SL3-S (Bayer animado, √N, Nyquist, deriva sidérea, software de apilado, asistente de decisión), la Triple Resolution de la M11 y la pestaña de difracción y diafragma, con el disco de Airy como techo físico (objetivo perfecto): techo práctico y límite duro de megapíxeles por formato y diafragma (≈1 865/N² y ≈11 400/N² en 24×36), y para cada sensor o modo (M11 L/M/S-DNG, SL3-S 24/48/96 MP, otros formatos, paso a medida) hasta dónde cerrar, qué modo o archivo basta, cuándo aporta el multishot y qué pueden y qué no los tres apilados (enfoque, con número de tomas; promedio; dither); con comparador A/B de dos diafragmas, el disco de Airy dibujado sobre la retícula de cada sensor, carta de resolución simulada, MTF frente a frecuencia, mapa de calor cámaras × diafragmas y la curva de la escena (detalle en los extremos frente a diafragma, con el apilado como alternativa). Las dos últimas pestañas son el filtro ND y su fuga infrarroja (tecnologías, filtro del propio sensor, dominante por escena, deriva de esquinas, cómo medirla) y el stack óptico del sensor con trazado de rayos, mancha RMS, MTF y simulación de esquina. Fusiona las antiguas leica-sensores, multishot-sl3s, binning-m11, filtro-nd-infrarrojo, stack-sensor y filtro-sensor, que redirigen aquí. Chart.js, que usa la pestaña de datos, se sirve desde `vendor/`. Manual del stack: [`manual-stack-sensor.html`](manual-stack-sensor.html). | 554 KB |

### Analizar tus propias fotos

| Documento | Qué hace | Peso |
|---|---|---:|
| [`analisis-centrado.html`](analisis-centrado.html) | Dónde cae el sujeto dentro del fotograma a lo largo de una colección entera, con qué dispersión y con qué sesgo. Contrasta tu práctica real con la regla de los tercios y con el centrado estricto, sin dar por buena ninguna. Salida visual de [`subject_center.py`](scripts/analitica/subject_center.py). | 215 KB |
| [`equipo-real.html`](equipo-real.html) | Arrastra una carpeta de fotos y lee su EXIF en el navegador, sin subir nada: focales, diafragmas, ISO, velocidades, EV de escena y horas por cuerpo y por objetivo, con lector propio sin dependencias (JPEG, TIFF y DNG). Veredictos con los umbrales de las otras fichas —difracción por cuerpo, trepidación 1/f, ganancia dual—, mapa focal × diafragma, cobertura de una focal o dos y comparación entre periodos. La distancia entre lo que crees que usas y lo que usas. | 101 KB |

### Revelar y procesar

Estas tres trabajan sobre archivos ya tomados. El programa es un script de Python y
la página es su manual; el código está en [`scripts/`](scripts/).

| Documento | Qué hace | Peso |
|---|---|---:|
| [`peliculas-icc.html`](peliculas-icc.html) | Cinco películas clásicas modeladas a partir de la respuesta física publicada por el fabricante, no por ajuste visual: el color sale de integrar el espectro a 1 nm entre 380 y 730. Genera perfiles ICC para Capture One, compuestos sobre la respuesta real de tu cámara. Código: [`peliculas.py`](scripts/peliculas/peliculas.py) y [`grano.py`](scripts/peliculas/grano.py). | 98 KB |
| [`manual-eclipse-hdr.html`](manual-eclipse-hdr.html) | Fusión HDR lineal y aplanado radial de la corona solar a partir de horquillas RAW. El gradiente coronal abarca tres órdenes de magnitud y no se comprime con una curva: se elimina dividiendo por el perfil radial. Código: [`eclipse_hdr.py`](scripts/eclipse/eclipse_hdr.py). | 94 KB |
| [`manual-procesar-sol.html`](manual-procesar-sol.html) | El disco solar en luz blanca: oscurecimiento del limbo, manchas y granulación. Qué hacer con el gradiente radial antes de tocar el contraste. Código: [`procesar_sol.py`](scripts/eclipse/procesar_sol.py). | 86 KB |
| [`manual-siril-apilado.html`](manual-siril-apilado.html) | Siril paso a paso para apilar cielo profundo con la M11P y filtro UHC frontal: captura, calibración con flats con el filtro puesto, registro, apilado con rechazo Winsorized y postprocesado (SPCC, GHS, StarNet++), con el mapa de la interfaz, la equivalencia en clics de cada comando, la variante sin darks para el CMOS moderno, casillas de progreso y modo nocturno rojo. | 82 KB |

### Fotógrafos: influencia y parecido

| Documento | Qué hace | Peso |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 autores y 467 relaciones de influencia declaradas. Traza linajes hacia arriba o hacia abajo, busca la ruta entre dos autores y dimensiona los nodos por nivel trófico. Se adapta a pantalla pequeña y a interacción táctil. | 247 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 292 autores colocados por parecido entre sus imágenes, con las fotos incrustadas. Da la distancia de contenido de cada pareja y, a la vez, su distancia en la red de influencia. | 6,5 MB |
| [`cronologia-red.html`](cronologia-red.html) | La tercera vista del mismo dato: los 293 autores sobre dos siglos, los movimientos como carriles y las influencias como arcos que cruzan décadas, con el salto medio en años de las 467 relaciones calculado del propio corpus. | 245 KB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | Cómo se juzga una imagen a lo largo del tiempo de procesamiento visual, tratado como actualización bayesiana; dónde cae cada herramienta de la ficha del marco en las tres fases, y un protocolo en tres tiempos para juzgar lo propio sin engañarse. La ficha hermana dice qué hacer; esta, cómo se juzga lo hecho. | 82 KB |
| [`ficha-marco-pensar.html`](ficha-marco-pensar.html) | Ficha de consulta del ensayo «Marco para pensar la fotografía»: las cuatro fases de la práctica, el eje técnica frente a sentido —la demostración, el programa cumplido, la repetibilidad— con Szarkowski, Minor White, Robert y Ansel Adams, Provoke y Nakahira; nueve autores y ocho conceptos japoneses con los lemas de campo y las trampas de *La Foto Rota*. | 115 KB |

### Publicar en papel

| Documento | Qué hace | Peso |
|---|---|---:|
| [`sensor-al-papel.html`](sensor-al-papel.html) | ¿A qué tamaño puedo imprimir esto y desde dónde se va a mirar? La cadena entera —píxeles, difracción, proceso de impresión y agudeza del ojo— con el eslabón limitante siempre a la vista. | 81 KB |
| [`zine-generator.html`](zine-generator.html) | Maquetación de fanzines y fotolibros a partir de tus propias imágenes, con la imposición de cuadernillo resuelta y exportación a PDF. Las tipografías van incrustadas. | 736 KB |

### Documentación

| Documento | Qué documenta |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | Manual de uso del simulador del eclipse. Sin fórmulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Geometría del encuadre, fotometría, extinción y difracción. Modelo, derivaciones y supuestos declarados. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Manual ilustrado de la carta óptica, con capturas del propio documento y cinco recetas paso a paso. |
| [`manual-mtf.html`](manual-mtf.html) | Manual de lectura de curvas MTF, del gráfico al *rendering*: anatomía de la ficha Leica/Zeiss, protocolo de lectura en diez pasos, firmas de cada aberración con gráficas generadas en la página, de la cualidad (pop, cremosidad, glow) a la curva, puntos ciegos, ocho fichas leídas y errores comunes. | 101 KB |
| [`guia-simulador.html`](guia-simulador.html) | Guía del banco óptico de flash: qué hace cada control y en qué fórmulas se apoya. |
| [`manual-exposicion-larga.html`](manual-exposicion-larga.html) | Manual de la herramienta de exposición larga: qué significa cada control, las tres cifras que hay que entender (arrastre, trepidación y el criterio de dos píxeles), por qué el barrido se juzga por el error de seguimiento y la ciudad desierta por tiempo, la escalera de apoyos con sus tiempos a 35 mm, y qué no calcula la página. | 61 KB |
| [`manual-flash-ttl-q3.html`](manual-flash-ttl-q3.html) | Flash TTL con la Leica Q3 43: cómo mide, cómo sincroniza y por qué a potencia plena el pulso no cabe entero en la ventana de 1/2000 s. Con dos calculadoras. |
| [`manual-telemetro-m11.html`](manual-telemetro-m11.html) | Manual del simulador de telémetro, con el modelo físico, la verificación numérica y un anexo ilustrado sobre el disco de Airy. Seis figuras incrustadas. |
| [`manual-niebla.html`](manual-niebla.html) | Manual de la predicción de niebla: el índice horario, la fusión bayesiana de las fuentes disponibles en el punto, el registro de observaciones que la entrena, y dónde se guarda ese registro. |
| [`guia-niebla.html`](guia-niebla.html) | Guía rápida de la niebla, sin meteorología: dónde estás, cómo leer las tres tarjetas y la barra de horas, y los dos gestos al día con los que la página aprende tu zona. Complementa al manual, que es más técnico. |
| [`manual-astro.html`](manual-astro.html) | Manual del índice de cielo: los siete términos del índice y sus pesos por objetivo, la fusión bayesiana, el registro de observaciones y los límites declarados del modelo de seeing. |
| [`manual-stack-sensor.html`](manual-stack-sensor.html) | Manual del simulador del stack: el modelo de trazado, cómo se leen la mancha RMS y la MTF, y qué es heurístico y qué no. |
| [`manual-medidas.html`](manual-medidas.html) | Referencia de todas las medidas del análisis de centrado: qué es cada una, cómo se define, cómo se interpreta y hasta dónde llega. |

### El taller

Un itinerario guiado que encadena las herramientas: el análisis de centrado sobre tu
carpeta de fotos (y la página se abre con tus datos ya cargados), la generación e
instalación de perfiles de película, el grano por lotes, y el cierre del sensor al
papel. Las páginas web no pueden ejecutar Python; el taller corre en tu ordenador:

```bash
python3 taller.py
```

Solo biblioteca estándar; escucha únicamente en 127.0.0.1 y los resultados van a
`~/Photographers-taller/`. Los scripts necesitan `numpy` y `pillow`, y el propio
taller comprueba qué falta y te da la orden exacta.

### El código

Las herramientas de revelado y procesado son scripts de Python; sus páginas son los
manuales. El código vive en [`scripts/`](scripts/), una carpeta por herramienta.

| Carpeta | Contiene |
|---|---|
| [`scripts/peliculas/`](scripts/peliculas/) | `peliculas.py` (los cinco modelos, el lector y el escritor de perfiles ICC), `grano.py`, el `LEEME.md` original y un preset de Capture One. Solo requiere numpy. |
| [`scripts/eclipse/`](scripts/eclipse/) | `eclipse_hdr.py`, `procesar_sol.py`, `deriva_solar.py` y su `README.md`. |
| [`scripts/analitica/`](scripts/analitica/) | `subject_center.py`, el análisis que alimenta la página de centrado. |
| [`scripts/siril/`](scripts/siril/) | Dos scripts de Siril listos para este equipo: `Apilado_M11P_UHC.ssf` (cadena completa) y `Apilado_M11P_UHC_sin_darks.ssf`. Los documenta `manual-siril-apilado.html`. |
| [`scripts/sitio/`](scripts/sitio/) | Las utilidades con que se mantiene el sitio. `fusionar.py` construyó `sensor.html` con sus cuatro primeras pestañas a partir de las páginas de `fuentes/` (aísla el CSS de cada fuente, renombra los ids que chocan, encadena los conmutadores de idioma) y `ampliar.py` le añadió después las del filtro ND y el stack sin regenerarla. Las dos especificaciones (`fusion-sensor.json`, `ampliar-sensor.json`) quedan como registro de cómo se hizo: la página se ha seguido editando a mano, así que `fusionar.py` se niega a sobrescribirla salvo con `--forzar` y `ampliar.py` no actúa si las pestañas ya están. `pesos.py` recalcula los pesos que declaran la portada y este README (`python3 scripts/sitio/pesos.py`; con `--mira` solo los comprueba). `integra-ficha-paseo.py` prepara las fichas del paseo. |
| [`vendor/`](vendor/) | Las librerías de terceros que usan las páginas, servidas desde el propio sitio para no depender de un CDN: d3 7.9.0 (red de influencia, cronología y explorador de distancias), Chart.js 4.4.1 (pestaña de datos del sensor), jsPDF 2.5.1 y exifr 7.1.3 (generador de fanzines), cada una con su licencia. Las páginas recurren al CDN solo si el archivo local no carga. |
| [`perfiles-icc/`](perfiles-icc/) | Cuatro perfiles ICC reales generados con `peliculas.py` para la Leica Q3 43 (ProStandard): Kodachrome 25, Kodachrome 64, Pro 400H sobre Endura y Tri-X sobre Multigrade. Listos para instalar en Capture One; 560 KB cada uno. |

### Notas

- El explorador de distancias pesa 6,5 MB porque lleva las fotografías incrustadas en
  base64. Es lo que le permite funcionar sin conexión, pero conviene abrirlo con red
  decente y no es el mejor candidato para un móvil con datos.
- Seis nombres antiguos (`leica-sensores`, `multishot-sl3s`, `binning-m11`, `filtro-nd-infrarrojo`, `stack-sensor`, `filtro-sensor`) se conservan como redirecciones a `sensor.html`, cada uno a su pestaña; los tres últimos conservan además el ancla o el estado que traiga el enlace. No cuentan como documentos.
- El simulador del eclipse apunta al del 2 de agosto de 2027 (sur de España, Marruecos,
  Egipto). Las efemérides del evento de 2026 quedan en el histórico de git.

### Cómo abrirlo

Basta con clonar el repositorio y abrir `index.html` en el navegador; los enlaces entre
páginas son rutas relativas y funcionan en local. Para servirlo:

```bash
python3 -m http.server 8000
```

---

## English

Thirty-seven documents that settle photographic questions with the physical or statistical
model in plain sight: simulators, metrics, catalogues, processing scripts and their
documentation.

Every calculation happens in the browser. There is no server, no account and no telemetry,
and each page is **a single HTML file** that keeps working offline once loaded — with two
declared exceptions: the fog forecast and the sky index query Open-Meteo (the fog page also reads METAR reports from the Iowa Environmental Mesonet) and, without a
connection, load but cannot forecast. The few third-party libraries (d3, Chart.js, jsPDF, exifr)
are served from the repository itself (`vendor/`), not from a third-party server. The developing and processing
tools are Python scripts that run on your own machine rather than in the browser; they
require only numpy.

Every page carries an **ES / EN** switch in the top right corner. The choice is remembered
from one page to the next and can be forced by adding `?lang=en` or `?lang=es` to the
address. With no prior choice, the browser's language is followed.

### Planning the shot

| Document | What it does | Size |
|---|---|---:|
| [`simulador-eclipse.html`](simulador-eclipse.html) | Framing and exposure for the total solar eclipse of 2 August 2027 (southern Spain, northern Morocco, Egypt): whether the corona fits your frame, the phase-by-phase bracket with Espenak's photometry, nine sites from Tarifa to Luxor each in local time, and a printable field sheet. | 187 KB |
| [`simulador-flash.html`](simulador-flash.html) | Flash optical bench. The hardness of a shadow is set by the angular size of the source as seen from the subject: shadows, light falloff from the guide number, overpowering the sun, and balance with ambient light. | 97 KB |
| [`exposicion-larga.html`](exposicion-larga.html) | Long exposure: the six techniques of Pit Haupert's cheat sheet, plus a seventh (still camera, the subject leaves a trace), with the time they ask for in your scene, not the recipe's. Computes subject blur in pixels (b = f·v·t/(d·p)), whether you can hold it with the ladder of supports (elbows, tensioned strap, bracing, OIS, IBIS, tripod), which filter you need and what ISO without one. With the subject (person, cyclist, car, train) drawn at its true size in the frame together with the trace it leaves, a blur-against-shake curve and a three-body comparison. | 81 KB |
| [`programa-camara.html`](programa-camara.html) | The automatic mode is not neutral: it carries a program. Draws the line it follows — shutter, aperture and ISO at each light level — overlays the blur and depth of field your intent demanded, and marks where they collide. Born of the essay's Flusser section. | 108 KB |
| [`niebla.html`](niebla.html) | Whether fog will form at tomorrow's sunrise. A 48-hour hourly index on the convergence of temperature and dew point, plus a multi-model Bayesian fusion — now with ICON EPS, GFS ENS and ECMWF ENS ensembles of 30 to 50 members — that readjusts its weights from your own observations and recalibrates itself (Platt) from your log. Sources are resolved per site: in Galicia they include HARMONIE‑AROME at 2 km, and a table says which model lies behind each one, with what mesh and how far from the edge of its domain. The forecast is frozen automatically each night, so the morning's observation is compared against what was predicted the evening before and never against anything later. Each morning it proposes the label from the METAR of the nearby airport, and a third tab calibrates the sources against the history of that station: T − Td bias, probability curve and starting weight for each. Needs a connection: the data comes from Open-Meteo and, for METAR reports, from the Iowa Environmental Mesonet. Manual: [`manual-niebla.html`](manual-niebla.html); quick guide: [`guia-niebla.html`](guia-niebla.html). | 182 KB |
| [`astro.html`](astro.html) | Whether the night will be worth photographing the sky. An hourly index combining layered cloud, aerosol transparency (CAMS AOD), seeing from upper wind, dew and Moon, with weights that rescale for deep sky, planetary or nightscape work. Same Bayesian fusion, per-site sources and learning as the fog tool. Manual: [`manual-astro.html`](manual-astro.html). | 121 KB |
| [`luz-natural.html`](luz-natural.html) | When the light is good and where the Moon will be, for any place and date: golden and blue hours with their real durations, rise and set azimuths, the lunar phase drawn, and the alignment finder for planning the Moon over your frame. All astronomy computed locally: works offline. | 85 KB |

### The lens and the plane of focus

What character the lens has and where the plane of focus actually falls. The first is
the aberrations its designer chose not to correct; the second, whether the rangefinder
and the eye manage to put it where you think, and what the sensor's glass does to the lens.

| Document | What it does | Size |
|---|---|---:|
| [`caracter-optico-leica-m.html`](caracter-optico-leica-m.html) | 128 Leica M-mount lenses, from 1925 to 2026, with 32 descriptors each. Reconstructs the defocus disc by geometric tracing, measures the character distance between two lenses and returns their nearest neighbours. | 242 KB |
| [`caracter-optico-reducido.html`](caracter-optico-reducido.html) | Reduced rendering chart: the same lenses on the seven axes that decide the visible character (residual spherical aberration, longitudinal chromatic aberration, microcontrast, veiling glare, vignetting, pupil clipping, aspheric onion ripple), four aesthetic indices with their formula printed, head-to-head pair, neighbours and map. | 111 KB |
| [`telemetro-m11.html`](telemetro-m11.html) | What the eye sees through the M11 viewfinder and what survives of it on the sensor. Six canvases running from the rangefinder patch to the grid of photosites, with the cosine error from recomposing and a Monte Carlo hit rate. | 134 KB |
| [`sensor.html`](sensor.html) | The sensor in six tabs: measured data of the M11, Q3 and SL3-S (read noise, dual gain, PDR, SNR calculator), the SL3-S multishot (animated Bayer, √N, Nyquist, sidereal drift, stacking software, decision assistant), the M11 Triple Resolution and the diffraction and aperture tab, with the Airy disc as the physical ceiling (perfect lens): practical ceiling and hard limit in megapixels by format and aperture (≈1,865/N² and ≈11,400/N² on 24×36), and for each sensor or mode (M11 L/M/S-DNG, SL3-S 24/48/96 MP, other formats, custom pitch) how far to stop down, which mode or file suffices, when multishot pays and what the three kinds of stacking can and cannot do (focus, with the number of frames; averaging; dither); with an A/B comparator of two apertures, the Airy disc drawn on each sensor's pixel grid, a simulated resolution chart, MTF against frequency, a cameras × apertures heat map and the scene curve (detail at the extremes against aperture, with stacking as the alternative). The last two tabs are the ND filter and its infrared leakage (technologies, the sensor's own filter, cast by scene, corner drift, how to measure it) and the sensor's optical stack with ray tracing, RMS spot, MTF and corner simulation. Merges the former leica-sensores, multishot-sl3s, binning-m11, filtro-nd-infrarrojo, stack-sensor and filtro-sensor, which redirect here. Chart.js, used by the data tab, is served from `vendor/`. Stack manual: [`manual-stack-sensor.html`](manual-stack-sensor.html). | 554 KB |

### Analysing your own photographs

| Document | What it does | Size |
|---|---|---:|
| [`analisis-centrado.html`](analisis-centrado.html) | Where the subject falls inside the frame across a whole collection, with how much spread and what bias. Sets your actual practice against the rule of thirds and against strict centring, taking neither for granted. Visual output of [`subject_center.py`](scripts/analitica/subject_center.py). | 215 KB |
| [`equipo-real.html`](equipo-real.html) | Drop a folder of photographs and read their EXIF in the browser, uploading nothing: focal lengths, apertures, ISO, shutter speeds, scene EV and hours per body and lens, with a dependency-free reader of its own (JPEG, TIFF and DNG). Verdicts using the thresholds of the sibling pages —diffraction per body, 1/f camera shake, dual gain—, a focal × aperture map, coverage of one focal length or two, and a comparison between periods. The gap between what you think you use and what you use. | 101 KB |

### Developing and processing

These three work on files you have already shot. The program is a Python script and
the page is its manual; the code lives in [`scripts/`](scripts/).

| Document | What it does | Size |
|---|---|---:|
| [`peliculas-icc.html`](peliculas-icc.html) | Five classic films modelled from the physical response published by the manufacturer, not by eyeballing: the colour comes from integrating the spectrum at 1 nm between 380 and 730. Generates ICC profiles for Capture One, composed over your camera's real response. Code: [`peliculas.py`](scripts/peliculas/peliculas.py) and [`grano.py`](scripts/peliculas/grano.py). | 98 KB |
| [`manual-eclipse-hdr.html`](manual-eclipse-hdr.html) | Linear HDR merge and radial flattening of the solar corona from RAW brackets. The coronal gradient spans three orders of magnitude and does not compress with a curve: it is removed by dividing by the radial profile. Code: [`eclipse_hdr.py`](scripts/eclipse/eclipse_hdr.py). | 94 KB |
| [`manual-procesar-sol.html`](manual-procesar-sol.html) | The solar disc in white light: limb darkening, sunspots and granulation. What to do with the radial gradient before touching contrast at all. Code: [`procesar_sol.py`](scripts/eclipse/procesar_sol.py). | 86 KB |
| [`manual-siril-apilado.html`](manual-siril-apilado.html) | Siril step by step for stacking deep sky with the M11P and a front UHC filter: capture, calibration with flats taken with the filter on, registration, Winsorized-rejection stacking and postprocessing (SPCC, GHS, StarNet++), with the interface map, the click-path equivalent of every command, the no-darks variant for a modern CMOS, progress checkboxes and a red night mode. | 82 KB |

### Photographers: influence and likeness

| Document | What it does | Size |
|---|---|---:|
| [`red-influencia.html`](red-influencia.html) | 293 authors and 467 declared influence relationships. Trace lineages upstream or downstream, look up the route between two authors, and size the nodes by trophic level. It adapts to small screens and touch interaction. | 247 KB |
| [`explorador_distancias.html`](explorador_distancias.html) | 292 authors placed by the likeness between their images, with the photographs embedded. Gives the content distance for each pair and, alongside it, their distance in the influence network. | 6.5 MB |
| [`cronologia-red.html`](cronologia-red.html) | The third view of the same data: the 293 authors across two centuries, movements as lanes and influences as arcs leaping across decades, with the mean year-leap of the 467 relationships computed from the corpus itself. | 245 KB |
| [`ficha-fases-juicio-estetico.html`](ficha-fases-juicio-estetico.html) | How an image is judged across the time course of visual processing, treated as Bayesian updating; where each tool of the framework sheet lands in the three phases, and a three-tempo protocol for judging one's own work without self-deception. The companion sheet says what to do; this one, how what was done is judged. | 82 KB |
| [`ficha-marco-pensar.html`](ficha-marco-pensar.html) | Consultation sheet for the essay 'A framework for thinking photography': the four phases of practice, the technique-versus-meaning axis — the demonstration, the programme fulfilled, repeatability — with Szarkowski, Minor White, Robert and Ansel Adams, Provoke and Nakahira; nine authors and eight Japanese concepts with the field mottos and traps of *La Foto Rota*. | 115 KB |

### Publishing on paper

| Document | What it does | Size |
|---|---|---:|
| [`sensor-al-papel.html`](sensor-al-papel.html) | How large can I print this, and from where will it be seen? The whole chain — pixels, diffraction, printing process and the acuity of the eye — with the limiting link always in view. | 81 KB |
| [`zine-generator.html`](zine-generator.html) | Layout for fanzines and photobooks from your own images, with the booklet imposition already solved and PDF export. Fonts are embedded. | 736 KB |

### Documentation

| Document | What it documents |
|---|---|
| [`manual-simulador-eclipse.html`](manual-simulador-eclipse.html) | User manual for the eclipse simulator. No formulas. |
| [`manual-tecnico-eclipse.html`](manual-tecnico-eclipse.html) | Framing geometry, photometry, extinction and diffraction. Model, derivations and stated assumptions. |
| [`manual-caracter-optico.html`](manual-caracter-optico.html) | Illustrated manual for the optical chart, with screenshots from the document itself and five step-by-step recipes. |
| [`manual-mtf.html`](manual-mtf.html) | Manual for reading MTF curves, from the graph to the rendering: anatomy of the Leica/Zeiss sheet, a ten-step reading protocol, the signature of each aberration with graphs generated on the page, from quality (pop, creaminess, glow) to curve, blind spots, eight worked examples and common mistakes. | 101 KB |
| [`guia-simulador.html`](guia-simulador.html) | Guide to the flash optical bench: what each control does and which formulas it rests on. |
| [`manual-exposicion-larga.html`](manual-exposicion-larga.html) | Manual of the long-exposure tool: what each control means, the three figures to understand (blur, shake and the two-pixel criterion), why panning is judged by tracking error and the ghost town by time, the ladder of supports with its times at 35 mm, and what the page does not compute. | 61 KB |
| [`manual-flash-ttl-q3.html`](manual-flash-ttl-q3.html) | TTL flash with the Leica Q3 43: how it meters, how it syncs, and why at full power the pulse does not fit inside the 1/2000 s window. With two calculators. |
| [`manual-telemetro-m11.html`](manual-telemetro-m11.html) | Manual for the rangefinder simulator, with the physical model, the numerical verification and an illustrated annex on the Airy disc. Six embedded figures. |
| [`manual-niebla.html`](manual-niebla.html) | Manual for the fog forecast: the hourly index, the Bayesian fusion of the sources available at the point, the observation log that trains it, and where that log is kept. |
| [`guia-niebla.html`](guia-niebla.html) | Quick, meteorology-free guide to the fog tool: where you are, how to read the three cards and the hour bar, and the two daily gestures that teach the page your area. Complements the more technical manual. |
| [`manual-astro.html`](manual-astro.html) | Manual for the sky index: the seven index terms and their per-target weights, the Bayesian fusion, the observation log and the declared limits of the seeing model. |
| [`manual-stack-sensor.html`](manual-stack-sensor.html) | Manual for the stack simulator: the tracing model, how to read the RMS spot and the MTF, and what is heuristic and what is not. |
| [`manual-medidas.html`](manual-medidas.html) | Reference for every measure in the subject-placement analysis: what each one is, how it is defined, how to read it and how far it goes. |

### The workshop

A guided path that chains the tools together: the placement analysis over your folder
of photographs (with the page opening on your data, already loaded), film-profile
generation and installation, batch grain, and the sensor-to-paper close. Web pages
cannot run Python; the workshop runs on your computer:

```bash
python3 taller.py
```

Standard library only; it listens on 127.0.0.1 alone and results go to
`~/Photographers-taller/`. The scripts need `numpy` and `pillow`, and the workshop
itself checks what is missing and gives you the exact command.

### The code

The developing and processing tools are Python scripts; their pages are the manuals.
The code lives in [`scripts/`](scripts/), one folder per tool.

| Folder | Contents |
|---|---|
| [`scripts/peliculas/`](scripts/peliculas/) | `peliculas.py` (the five models, the ICC profile reader and writer), `grano.py`, the original `LEEME.md` and a Capture One preset. Requires only numpy. |
| [`scripts/eclipse/`](scripts/eclipse/) | `eclipse_hdr.py`, `procesar_sol.py`, `deriva_solar.py` and their `README.md`. |
| [`scripts/analitica/`](scripts/analitica/) | `subject_center.py`, the analysis that feeds the placement page. |
| [`scripts/siril/`](scripts/siril/) | Two Siril scripts ready for this kit: `Apilado_M11P_UHC.ssf` (full chain) and `Apilado_M11P_UHC_sin_darks.ssf`. Documented by `manual-siril-apilado.html`. |
| [`scripts/sitio/`](scripts/sitio/) | The utilities the site is maintained with. `fusionar.py` built `sensor.html` with its first four tabs from the pages in `fuentes/` (it isolates each source's CSS, renames colliding ids, chains the language switchers) and `ampliar.py` later added the ND filter and stack tabs without regenerating it. The two specs (`fusion-sensor.json`, `ampliar-sensor.json`) remain as a record of how it was done: the page has since been edited by hand, so `fusionar.py` refuses to overwrite it unless given `--forzar`, and `ampliar.py` does nothing if the tabs are already there. `pesos.py` recomputes the sizes stated by the cover page and this README (`python3 scripts/sitio/pesos.py`; with `--mira` it only checks them). `integra-ficha-paseo.py` prepares the photo-walk sheets. |
| [`vendor/`](vendor/) | The third-party libraries the pages use, served from the site itself so as not to depend on a CDN: d3 7.9.0 (influence network, timeline and distance explorer), Chart.js 4.4.1 (the sensor data tab), jsPDF 2.5.1 and exifr 7.1.3 (zine generator), each with its licence. The pages fall back to the CDN only if the local file fails to load. |
| [`perfiles-icc/`](perfiles-icc/) | Four real ICC profiles generated with `peliculas.py` for the Leica Q3 43 (ProStandard): Kodachrome 25, Kodachrome 64, Pro 400H on Endura and Tri-X on Multigrade. Ready to install in Capture One; 560 KB each. |

### Notes

- The distance explorer weighs 6.5 MB because it carries the photographs embedded as
  base64. That is what lets it run offline, but it is worth opening on a decent connection
  and it is not the best candidate for a phone on mobile data.
- Six old names (`leica-sensores`, `multishot-sl3s`, `binning-m11`, `filtro-nd-infrarrojo`, `stack-sensor`, `filtro-sensor`) are kept as redirects to `sensor.html`, each to its own tab; the last three also preserve whatever anchor or state the link carries. They do not count as documents.
- The eclipse simulator targets 2 August 2027 (southern Spain, Morocco, Egypt). The
  ephemerides of the 2026 event remain in the git history.

### Running it

Clone the repository and open `index.html` in a browser; the links between pages are
relative paths and work locally. To serve it:

```bash
python3 -m http.server 8000
```

---

Rafael Vida

---

## Paseo fotográfico · sección aparte

Fuera de «Fotografía para científicos», con su propia portada en
[`paseos/`](paseos/index.html) ([lab.rafaelvida.com/paseos/](https://lab.rafaelvida.com/paseos/)):
las fichas del paseo fotográfico de la comunidad Foto, preparadas por La Foto Rota. Un tema por salida,
con autores de referencia, la física que hay debajo y ejercicios para el día. Solo en español, sin conmutador
de idioma: tienen otro objetivo y otro diseño (negro y blanco puros, Bodoni Moda y Atkinson Hyperlegible
incrustadas, ningún recurso externo).

| Ficha | Tema | Contenido | Tamaño |
|---|---|---|---|
| [`paseos/contraste.html`](paseos/contraste.html) | 1 · Contraste | Nueve autores (Fan Ho, Metzker, Giacomelli, Moriyama, Leiter, Webb, Abbott, Titarenko, Cameron) con obra de referencia, análisis, física y ejercicio; laboratorio de luz interactivo; tres reglas para el día. | 211 KB |
| [`paseos/paseo_contraste_ruta.html`](paseos/paseo_contraste_ruta.html) | 1 · Contraste, la ruta | La ruta de ese paseo por A Coruña: mapa interactivo, hitos de reagrupamiento y un ejercicio por parada tomado de la ficha. Se abre desde la tarjeta de la ficha 1 en la portada de la sección. A diferencia de las fichas, pide las tipografías a Google Fonts. | 191 KB |
| [`paseos/medir-la-luz.html`](paseos/medir-la-luz.html) | 2 · Medir la luz | Qué mide el fotómetro, los modos de medición, medir-bloquear-recomponer en cámara y en móvil, el sistema de zonas, el histograma y las referencias de bolsillo; ocho fotógrafos por su manera de exponer (clave alta, clave baja, movimiento, tiempo largo); laboratorio para medir una calle tocando la imagen. | 229 KB |
| [`paseos/exposicion-larga.html`](paseos/exposicion-larga.html) | 3 · Exposición larga | El arrastre medido en píxeles, el temblor y la escalera de apoyos, el barrido, el tiempo para vaciar la calle, cómo llegar a él con diafragma, ISO y filtro, y el dibujo con luz; seis fotógrafos del tiempo abierto (Daguerre, Lartigue, Man Ray, Mili, Woodman, Wesely); laboratorio que pasa del arrastre al tiempo. | 230 KB |
| [`paseos/flash.html`](paseos/flash.html) | 4 · Flash | Las dos exposiciones que conviven en la foto, el número guía, la sincronización, el tamaño de la fuente, el rebote y el relleno a la luz del día; seis fotógrafos del flash (Weegee, Gilden, Parr, diCorcia, Goldin, Fink); banco de flash con sombra, histograma y reparto flash/ambiente. | 223 KB |

Para añadir una ficha: pasar el archivo del autor por
`python3 scripts/sitio/integra-ficha-paseo.py <origen> paseos/<destino>.html` —que le pone los enlaces a la
portada de la sección, el favicon, el icono táctil y las metas `og`, y reescribe los enlaces a las otras fichas
con el nombre que tienen aquí— y copiar el bloque de ficha comentado en `paseos/index.html`. El script es
idempotente: se le puede volver a pasar cada versión nueva de la misma ficha.

*A separate section, in Spanish only: the photo-walk sheets of the Foto community, prepared by La Foto Rota, with their own cover at `paseos/`.*
