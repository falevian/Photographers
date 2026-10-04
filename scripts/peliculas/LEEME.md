# Emulación de películas clásicas para Capture One + Leica M11

Cuatro películas modeladas a partir de la respuesta física publicada por el
fabricante, no por ajuste visual. Toda la parte de color se calcula por
integración espectral a 1 nm entre 380 y 730 nm. Un solo fichero ejecutable,
`peliculas.py`, contiene los cuatro modelos, el lector y el escritor de
perfiles ICC. Solo requiere numpy.

| Clave | Película | Proceso | Fuente | Quién |
|---|---|---|---|---|
| `k64` | Kodachrome 64 (PKR) | K-14 | Kodak E-55 (2009) | Alex Webb |
| `k25` | Kodachrome 25 (PKM) | K-14 | Kodak E-55 (2009) | Plossu, Ghirri |
| `velvia50` | Velvia 50 (RVP 50) | E-6 | Fujifilm AF3-0221E2 | paisaje años 90 |
| `pro400h` | PRO 400H + Endura Premier | C-41 + RA-4 | Fujifilm AF3-176E y Kodak E-4070 | Rinko Kawauchi |
| `trix` | Tri-X 400 (D-76, 8 min) + Multigrade IV RC grado 2 | B/N + gelatina | Kodak F-4017 y datasheet Ilford MG IV | el B/N de reportaje |

---

## 1. Uso rápido

```
cd carpeta_donde_este_peliculas.py

# localizar el perfil de camara de Capture One
python3 peliculas.py --listar m11

# inspeccionar un candidato (clase, espacio, A2B, blanco)
python3 peliculas.py --info "/ruta/al/perfil.icm"

# componer, generar e instalar
python3 peliculas.py "/Applications/Capture One.app/Contents/Frameworks/ImageProcessing.framework/Versions/A/Resources/Profiles/Input/LeicaM11-ProStandard.icm" --pelicula k25 --n 45 --instalar
```

Las comillas dobles no son opcionales: las rutas de Capture One llevan
espacios y sin ellas la ruta llega partida al intérprete.

`--instalar` copia el ICC a `~/Library/ColorSync/Profiles/` y crea el estilo
en `~/Library/Application Support/Capture One/Styles/`. Hay que reiniciar
Capture One para que los reconozca.

**En cada imagen, imprescindible:** Base Characteristics > ICC Profile > el
perfil generado, y **Curve > Linear Response**. El modelo ya incorpora la
curva de tono del material; si se deja la curva de Capture One activa, ambas
se suman y el contraste sale duplicado. Es el error más visible que se puede
cometer con estos perfiles.

### Opciones

| Opción | Efecto |
|---|---|
| `--pelicula {k64,k25,velvia50,pro400h}` | material a emular |
| `--ev X` | exposición del material en pasos (negativo = más denso y saturado en diapositiva) |
| `--gain X` | ganancia de colorante; menor que 1 rebaja contraste y croma a la vez |
| `--copia X` | `pro400h` y `trix`: aclarado de la copia respecto al balance de laboratorio |
| `--virado {neutro,frio,calido,sepia,selenio}` | solo `trix`: virado de la copia |
| `--curvas {suaves,crudas}` | por defecto `suaves`: curvas características reparadas y suavizadas (sección 4); `crudas` usa las digitalizaciones tal cual |
| `--sala {oscura,tenue,media}` | solo diapositivas: entorno en el que se verá el resultado; `oscura` (por defecto) es la colorimetría de la proyección, `tenue` y `media` compensan la apariencia para monitor en penumbra o habitación iluminada (exponentes 0,83 y 0,67 sobre la luminancia relativa) |
| `--n {33,45}` | lado del CLUT del ICC |
| `--generico` | perfil sin cámara, supone primarios Rec.709 a la entrada |
| `--info`, `--listar [patrón]`, `--instalar`, `-o salida.icc` | utilidades |

Dos vías de trabajo:

* **Perfil compuesto (recomendada).** Se pasa el ICC de la cámara y la
  transformada del film se compone sobre la respuesta real del sensor. En el
  M11 hay dos perfiles en `Profiles/Input/`: `LeicaM11.icm` y
  `LeicaM11-ProStandard.icm`. Los ProStandard aplican una preservación de
  tono propia; el estándar es más neutro. Conviene generar ambos y comparar.
* **Perfil genérico** (`--generico`). Independiente de cámara. También sirven
  las LUT `.cube` del paquete antiguo para material ya revelado y exportado.

---

## 2. Carácter de cada material

Medido sobre el ColorChecker de 24 parches frente a la reproducción
colorimétrica exacta de la misma escena. ΔC* es el exceso de croma, Δh el giro
de tono en grados, Δu′v′ la deriva de los neutros.

| | k25 | k64 | velvia50 | pro400h (copia normal) |
|---|---|---|---|---|
| Croma medio añadido | +5.0 | +10.8 | +13.5 | +16.9 |
| Verdes | +9.5 | +30.1 | +25.6 y ΔL −15.6, Δh +20° | +22.7 |
| Azul saturado | +22.7 | +26.2 | +32.3 | +41.0 |
| Amarillos | +10.6 | +18.9 | +30.8 | +6.6 |
| Piel clara | croma casi intacto, Δh +11° | Δh +16° | Δh +13° | +10 C*, Δh +12° hacia naranja |
| Sombras profundas | cálidas, Δu′ +0.036 a −5 EV | cálidas, Δu′ +0.038 | neutras, Δu′ < 0.005 | según copia |

Lectura corta: los dos Kodachrome comparten firma de familia (capa roja por
encima en toda la escala, sombras que caen a cálido; los picos de colorante
salen casi idénticos en ambas digitalizaciones, 0.76/1.05/1.25 frente a
0.77/1.06/1.28, porque el K-14 usa los mismos acopladores). El 25 es la
versión contenida, gamma ~1.5 frente a ~2.0, la paleta callada de Ghirri. El
64 es más gráfico. Velvia va aparte: tres capas apareadas por diseño, neutros
clavados hasta el fondo, y el carácter puesto entero en el croma y en unos
verdes oscurecidos y girados a esmeralda. El sistema negativo+papel es el más
saturado de todos en copia estándar, con la piel cálida típica del Endura, y
el único con dos mandos de exposición.

### El caso pro400h: dos etapas y dos mandos

La cadena es física de punta a punta: XYZ de escena → exposición de las capas
del negativo (sensibilidades del AF3-176E bajo D55) → curvas características
Status M (gamma 0.51, máscara naranja en los Dmin 0.95/0.69/0.17) → el papel
se expone a través del negativo con logE = PBAL − D_StatusM → curvas del
papel Status A (gamma ~2.9) → inversión a colorantes del papel → reflectancia
espectral → XYZ bajo D50 relativo al blanco del papel.

PBAL, el filtrado YMC de la ampliadora, se resuelve por Newton en cada
exposición para que el gris del 18% imprima neutro en L* = 47, que es lo que
hace un minilab o un escáner fotograma a fotograma. Consecuencia verificada:
con el gris reequilibrado, sobreexponer el negativo +1.5 pasos apenas mueve
la escala tonal. La latitud del C-41 no está programada, emerge del modelo.

* `--ev` expone el **negativo**. Subirlo llena las sombras sobre la recta y
  comprime las altas luces contra el hombro del papel.
* `--copia` aclara la **copia** respecto al balance de laboratorio.

El look Kawauchi es la combinación de ambos:

```
python3 peliculas.py --generico --pelicula pro400h --ev 1.5 --copia 0.55
```

Gris medio impreso en L* 76, sombras levantadas a 45 con tinte frío menta
(b* −5 en medios bajos), piel lavada (+28 L*, croma negativo), cielos girados
hacia cian. Con `--ev 0 --copia 0` se obtiene la copia RA-4 recta, un look
valioso por sí mismo. El nombre del perfil incorpora los ajustes
(`ev+1.5 c+0.55`), así que se pueden instalar varias variantes a la vez.

### El caso trix: monocromo con positivado y virado

Misma arquitectura de dos etapas que el pro400h pero monocanal: exposición
pancromática (vector XYZ→H ajustado con la sensibilidad del F-4017, R²=0.998,
pesos [0.24, 0.31, 0.51]: la mitad del peso en Z es el sesgo azul del
pancromático clásico, que aclara cielos y oscurece rojos, la razón histórica
del filtro amarillo) → curva del negativo en D-76 a 8 minutos (velo 0.32,
gamma 0.62) → papel Multigrade IV RC a grado 2. La copia se autoexpone para
gris del 18% en densidad 0.74, y `--copia` aclara u oscurece desde ahí.

El virado es la única parte parametrizada del sistema: la densidad espectral
se modela como D(λ) = Dmin + (D − Dmin)·f(λ) con f construida sobre dos bases
suaves y coeficientes resueltos para objetivos colorimétricos declarados en
el parche de D=1.0 (sepia: a*+5, b*+18; selenio: +2.5, +1.5; cálido: +1.5,
+6; frío: −1, −3). La densidad visual se conserva por construcción y el croma
escala con la densidad, como en un virado químico real.

```
python3 peliculas.py --generico --pelicula trix --virado sepia
```

---

## 3. Grano: `grano.py`

Un perfil ICC es una transformación por píxel y no puede llevar grano, que es
un fenómeno espacial. Se aplica como paso posterior sobre la imagen exportada
de Capture One. Requiere numpy y Pillow.

```
python3 peliculas.py ...   # revelar en Capture One con el perfil
python3 grano.py exportada.jpg salida.jpg --pelicula k64
python3 grano.py exportada.jpg salida.jpg --pelicula trix --intensidad 1.2
```

### Algoritmo, paso a paso

1. **Nitidez del material.** Antes de nada, la imagen pasa por la MTF de la
   película: una gaussiana con el 50 % en `--mtf50` ciclos/mm (K64 40, K25 45,
   Velvia 50, PRO 400H 30, Tri-X 40; valores del orden de los de las hojas
   técnicas, sustituibles). `--mtf50 0` lo desactiva.

2. **Textura.** Superposición de conglomerados de plata o nubes de colorante
   colocados al azar (modelo booleano de discos) con tamaños log-normales de
   mediana `--grano-um` y anchura `--poli` (0.35 por defecto; 0 = un solo
   tamaño). Las poblaciones son independientes, así que se suman sus
   espectros de potencia (Campbell): el espectro decae sin los anillos del
   disco único, como el espectro de Wiener medido en película. Las nubes de
   colorante llevan el borde difuminado; los conglomerados de plata, no.
   `--textura gauss` recupera la textura de la primera versión.

3. **Amplitud, medida en 48 µm.** La granularidad rms del datasheet está
   medida con apertura de 48 µm a densidad 1.0. La amplitud por píxel se
   calibra midiendo sobre el propio campo de ruido su rms al promediarlo en un
   disco de 48 µm y escalándolo para que coincida; el programa imprime la
   comprobación. La primera versión aplicaba la ley de Selwyn como si el
   ruido fuera blanco y lo sobrestimaba 3.8 veces en K64 y 4.7 en Tri-X.

4. **Ganancia de copia.** En los sistemas negativo + papel la rms del
   datasheet es la del negativo (Kodak: densidad bruta 1.0; Fuji: densidad
   neta 1.0 sobre Dmin) y la copia la multiplica por la pendiente local del
   papel. Con las curvas reparadas el factor vale 3.1 en el Tri-X sobre
   Multigrade grado 2 y 3.2-3.3 por canal en el PRO 400H sobre Endura, en la
   densidad mostrada 1.0; se aplica y se imprime. `--intensidad` lo escala.

5. **Dependencia con el tono.** `--pelicula` selecciona un perfil σ(densidad
   mostrada) calculado sobre el eje neutro del modelo de cada material y
   embebido como tabla por canal.

   * Diapositivas (k64, k25, velvia50): estadística binomial de cobertura de
     colorante, σ ∝ √(a·(1−a/a_sat)); crece con la densidad, máximo hacia
     D ≈ 1.5, decae al saturar cerca de Dmax.
   * Negativo más papel (pro400h, trix): el grano nace en el negativo, donde
     crece como √(D − Dmin), y llega a la copia multiplicado por la pendiente
     local del papel, que lo anula en blancos y negros. Estos dos perfiles se
     recalcularon con las curvas reparadas y referidos a la densidad que de
     verdad se muestra (relativa al blanco de escena). El perfil anterior del
     Tri-X, hecho con la curva del papel sin reparar, oscilaba con el tono
     (1.8× en D 0.74, 1.0× en D 1.0, 1.7× en D 1.3) y en un fondo desenfocado
     daba zonas con el doble de grano que las vecinas: nubes de grano que
     seguían la textura del bokeh. El nuevo: 0.3 en las altas luces, 1.0 en
     D 1.0, máximo 1.07 en D 1.3, cero en el negro del papel.

   Sin `--pelicula` se aplica la ley genérica σ ∝ √D (Kodachrome 200:
   `--rms 16`).

6. **Separación luminancia/croma.** La rms del datasheet es granularidad de
   densidad visual; el ruido se descompone en luminancia, que conserva la
   calibración, y croma, escalado con `--croma` (0.45 en color). Como las
   capas solo están parcialmente correladas (0.35), la σ por capa se escala
   para que la rms de luminancia sea exactamente la del datasheet (en la
   primera versión se quedaba en 0.84 veces).

7. **Aplicación.** D′ = D + n·σ(D) por canal, y vuelta a sRGB. Como la
   densidad macroscópica se define sobre la transmitancia media, se compensa
   el sesgo log-normal (sin él, las zonas granuladas se aclaran un 1-3 %).
   `--dmax-vis` fija la densidad máxima (2.6). `--ancho-mm` indica cuánto mide
   un recorte sobre la película. Los JPEG se guardan a calidad 95 sin
   submuestreo de croma.

**Cómo mirarlo.** El grano está escalado a la película: un píxel de 3.8 µm se
juzga al 100 %. Reducir con un filtro pobre (visores a «ajustar a ventana») o
recomprimir en JPEG a calidad media convierte el grano fino en manchas que no
están en el archivo. Para una versión reducida: aplicar el grano a la imagen ya
reducida (la calibración vale para cualquier paso) o usar `--ancho-salida`,
que reduce con Lanczos después de añadirlo.

### Presets

| `--pelicula` | rms | grano (µm) | textura | MTF 50 % (c/mm) | correlación | croma |
|---|---|---|---|---|---|---|
| `k64` | 10 | 11 | nube | 40 | 0.35 | 0.45 |
| `k25` | 9 | 10 | nube | 45 | 0.35 | 0.45 |
| `velvia50` | 9 | 10 | nube | 50 | 0.35 | 0.45 |
| `pro400h` | 4 | 12 | nube | 30 | 0.35 | 0.45 |
| `trix` | 17 | 14 | disco | 40 | 1.0 | 1.0 |

Todo es anulable por línea de órdenes (`--rms`, `--grano-um`, `--poli`,
`--textura`, `--mtf50`, `--ancho-mm`, `--ancho-salida`, `--correlacion`,
`--croma`, `--intensidad`, `--semilla`, `--dmax-vis`). La
alternativa rápida sin salir de Capture One es su herramienta Film Grain, que
no modela la dependencia con el tono ni la separación luminancia/croma.

---

## 4. Método y validación

**Digitalización.** Cada gráfica del datasheet se rasteriza a 400 ppp y se
digitaliza por etiquetado de componentes conexas, enmascarado de texto por
cajas medidas, y seguimiento conjunto de curvas con memoria de pendiente y
asignación excluyente, con permutación de colas en los cruces detectada por
identidad física. Controles de cierre donde el documento los permite: en K64,
|N − (Y+M+C)| máximo 0.016 y densidad visual del neutro 1.001 frente al 1.000
nominal; en K25, cierre con error máximo 0.036.

**Reparación de las curvas digitalizadas.** Las curvas D(logE) así
obtenidas arrastraban tres defectos que una curva H&D real no tiene, y que se
veían en el tono: rizado periódico de la cuadrícula de píxeles (±0.1 en gamma
con periodo ~0.05 logE); tramos rellenados con una recta entre puntos escasos,
con gamma exactamente constante y un escalón al final (K64: gamma 0.82 durante
0.5 logE y salto a 1.39 justo por encima del gris medio; K25: 0.98 durante
0.7 logE y salto a 2.0, que dejaba la gamma del gris en 0.98 y hacía al K25
falsamente «contenido»); y saltos y bultos donde el trazador se confundió de
curva (Multigrade grado 2: picos de gamma local 4.4 y 5.6 con un valle de 0.95
en medio). Desde esta versión las curvas se reparan al cargarlas, con el mismo
tratamiento para todas y solo numpy: los rellenos lineales se sustituyen por un
puente de gamma lineal entre las gammas medidas a cada lado, escalado para
cerrar en los dos extremos reales; un primer ajuste fino rebaja el peso de los
puntos aberrantes (biweight de Tukey, 4.5 MAD); se ajusta un B-spline cúbico en
el dominio logístico u = ln((D − Dmin)/(Dmax − D)), asintótico en talón y
hombro, con el paso de nudos más fino (0.12 a 0.40 logE) que deja la curva
monótona y su gamma localmente suave; y se recorta al rango de los datos
forzando la monotonía. Dmin, Dmax y la colocación de la exposición no cambian.
Resultado: en el K64 desaparece el escalón de contraste entre gris y blanco
(pendiente en L*: de 24 → 20 → 17 → 19 → 21 L*/EV a 24 → 22 → 20 → 19 → 17);
en el K25 la gamma del gris sube de 0.98 a 1.27 (15.5 → 19.8 L*/EV); en el
MG2 la gamma máxima baja de 5.6 a 4.0 con la ISO(R) intacta (108).
`--curvas crudas` recupera las digitalizaciones originales.

**Cadena de diapositiva** (k64, k25, velvia50): matriz 3×3 XYZ→exposición de
capa ajustada sobre 924 reflectancias (24 ColorChecker con peso 12 más 900
sintéticas) → curvas características → inversión densitométrica Status A
(responsividades gaussianas en 640/540/438 nm, Jacobiano con términos
cruzados) → balance de grises resuelto para el neutro de D = 1.0 → colorantes
→ transmitancia → proyector de 3200 K → adaptación Bradford. El blanco difuso
se coloca donde la curva verde está 0.105 por encima de Dmin.

**Validación real en Capture One** (K64 sobre M11, carta Calibrite): la
predicción del modelo frente al render real del ICC da ΔE medio 2.9 en 23
parches, 18 de ellos por debajo de 2.5. La escala neutra confirma que no hay
desajuste de exposición dependiente del tono (rango de 0.08 EV entre blanco y
gris oscuro, ruido de medida).

**Limitaciones conocidas, en orden de importancia.**

1. Amarillos, naranjas y cianes muy saturados en los Kodachrome se desvían
   más (ΔE 7 a 11 en los cuatro parches monocolorante del ColorChecker). La
   inversión lineal Status A se estira lejos del punto de linealización. Se
   evaluó un solver Newton exacto y se descartó: mejora esos cuatro parches
   pero degrada la media global de 2.9 a 4.9, porque fuerza consistencia
   exacta con unas responsividades Status A que son aproximadas.
2. La capa roja ajusta peor que las demás en todos los materiales (R² 0.96 a
   0.98 frente a 0.998 y mejores). No es un defecto del método sino la
   colorimetría real de estas películas: sus sensibilidades rojas en 640 a
   650 nm no son combinación lineal de las funciones del observador. Esperar
   desviaciones mayores en rojos profundos, sobre todo en Velvia.
3. En `pro400h`, la cuarta capa sensible al cian del negativo no se modela;
   su función es corregir fluorescentes y bajo luz día su aporte es menor. El
   puente negativo→papel usa la equivalencia Status M ≈ densidad de
   impresión, que es la finalidad de diseño de Status M, en lugar de los
   espectros de colorante del negativo, que Fuji no publica.
4. Las sensibilidades espectrales de los datasheet empiezan dibujadas en su
   pico o cerca de él (sin flanco izquierdo en el azul); el tratamiento es
   idéntico en todos los materiales.
5. En `trix`, el pie del papel por debajo de D=0.55 no es separable en la
   gráfica (las cinco curvas emparejadas se funden) y se completa con la
   aproximación exponencial clásica hacia Dmin=0.06, con la constante
   resuelta para reproducir exactamente el ISO(R)=110 que publica Ilford
   para el grado 2. La curva del negativo y el resto del papel son
   digitalización directa. El virado es una parametrización colorimétrica
   declarada, no un dato de fabricante.
6. El canal amarillo del papel Endura tiene en la digitalización un salto de
   0.2 D cerca de Dmax; la reparación lo puentea, pero la forma del hombro
   amarillo entre D 2.0 y 2.4 es una estimación (afecta a los negros más
   profundos de la copia).
7. Las MTF de `grano.py` son valores típicos, no digitalizaciones; los efectos
   de adyacencia del D-76 (MTF por encima del 100 % a baja frecuencia) no se
   modelan. La ganancia de copia del grano depende de la gamma máxima del
   papel (4.0 en el Multigrade reparado; en un grado 2 real quizá 3): el 3.1
   del Tri-X puede estar algo alto; `--intensidad` lo corrige.
8. El perfil genérico supone primarios Rec.709 a la entrada. Para máxima
   fidelidad, componer sobre el perfil de cámara.

---

## 5. Ficheros

| Fichero | Contenido |
|---|---|
| `peliculas.py` | **el entregable principal**: 4 modelos, lector y escritor ICC, CLI completa |
| `grano.py` | grano físico standalone (numpy + Pillow) |
| `curvas_k25_digitalizadas.png`, `curvas_velvia_digitalizadas.png`, `curvas_pro400h_endura.png` | verificación visual de las digitalizaciones |
| `tri_pareja.jpg` | original, K64, Velvia sobre la misma toma |
| `duo_k64_k25.jpg` | K64 frente a K25 |
| `tri_400h.jpg` | original, copia RA-4 normal, ajuste Kawauchi |
| `duo_trix.jpg` | Tri-X neutro frente a virado sepia |
| `curvas_trix_mg2.png` | curvas digitalizadas del Tri-X y del grado 2 |
| `crop_grano.png` | recorte 1:1 sin y con grano |
| `crop_grano_tonal.png` | luces frente a medios oscuros, sin y con grano trix |
| `crop_grano_croma.png` | croma 1.0 frente a 0.45 sobre cielo y mar oscuros |
| `Kodachrome64/`, `Kodachrome64.zip` | paquete modular antiguo solo K64 (LUT `.cube` incluidas, LEEME propio con el detalle numérico completo del E-55) |
| `kodachrome64.py` | versión de un solo material, sustituida por `peliculas.py` |

Los ICC generados son v2, clase entrada (`scnr`), CLUT de 33³ o 45³ con
indexado gamma 1.8 y PCS Lab, verificados con Little CMS (`transicc`): la
diferencia entre la tabla y el modelo directo es ΔE2000 medio 0.022, máximo
0.31 con rejilla de 33.
