# eclipse_hdr.py

Fusión HDR lineal y aplanado radial de la corona solar a partir de horquillas RAW.

El programa reconstruye la radiancia lineal de la escena a lo largo de todo el rango dinámico
de la serie, registra los fotogramas ajustando una circunferencia al limbo lunar y divide la
imagen por su propio perfil radial, de modo que la estructura azimutal de la corona queda
visible sin recurrir a ningún mapeo tonal perceptual.

Validación interna sobre escena sintética de 16 EV con 27 fotogramas: error de registro de
0,078 px, error fotométrico de 0,0100 dex de RMS a lo largo de tres décadas de intensidad, y
rechazo de un transitorio inyectado que sin recorte sesgaría la fotometría local 0,042 dex.

## Por qué no basta con Photoshop o Capture One

El fundido HDR de Capture One no expone una salida lineal utilizable. El de Photoshop sí
permite trabajar en 32 bits, pero su mapeo tonal es perceptual y su alineación es por
contenido, dos cosas incompatibles con un gradiente radial de tres órdenes de magnitud y con
una imagen cuyo único rasgo geométrico estable es un disco negro. El gradiente coronal no se
comprime con una curva: se elimina por división del perfil radial.

## Instalación

```bash
pip install numpy scipy scikit-image tifffile pillow rawpy exifread
brew install exiftool        # opcional, respaldo de metadatos
```

Python 3.9 o posterior. Probado en macOS con RAW de Canon, Nikon y Sony a través de LibRaw.

## Uso

```bash
# 1. validación interna con corona sintética, no necesita ficheros
python eclipse_hdr.py --selftest

# 2. ensayo con cualquier horquilla estática propia, a media resolución
python eclipse_hdr.py bracket/*.CR3 -o prueba --no-align --half

# 3. procesado real
python eclipse_hdr.py totalidad/IMG_2*.CR3 -o salida
```

El paso 2 conviene hacerlo antes del eclipse: confirma que LibRaw decodifica el formato de la
cámara, que los tiempos de exposición se leen del EXIF y que la memoria disponible aguanta la
resolución completa. Si falta `ExposureTime`, el programa se detiene y pide los valores con
`--times 1/8000,1/2000,...` en el mismo orden que los ficheros.

## Flujo de procesado

Dos pasadas sobre los ficheros. La primera detecta el limbo a media resolución para obtener
una estimación encadenada del centro; la segunda carga a resolución completa, refina, traslada
y acumula en flujo, de modo que el consumo de memoria no crece con el número de tomas.

**1. Decodificado RAW lineal.** LibRaw con `gamma=(1,1)`, sin brillo automático, 16 bits,
primarios sRGB. La máscara de saturación se mide sobre el mosaico de Bayer, antes del
interpolado cromático, con el criterio `M >= negro + 0,97 (blanco - negro)`, se reorienta según
el flip declarado en el RAW y se dilata dos iteraciones.

**2. Detección del limbo.** Transformada de Hough sobre la luminancia comprimida en logaritmo
para inicializar. Refinado con 720 rayos radiales: máximo de la derivada de log I a lo largo de
cada rayo, posición subpíxel por ajuste parabólico a las tres muestras centrales, y ajuste
algebraico de Kasa de la circunferencia con recorte a 2,5 sigma, todo iterado tres veces.

**3. Fusión HDR.** Con `e = t · ISO / N²` normalizado a su máximo,

```
L = sum_i w_i I_i / e_i  /  sum_i w_i
```

El peso anula la saturación con rampa entre 0,92 y 0,98, anula lo que está bajo el suelo de
ruido y es proporcional a `e_i` en el resto. Ese último factor es la ponderación de varianza
inversa cuando domina el ruido fotónico: si var(I) es proporcional a I, la varianza del
estimador `I_i / e_i` es proporcional a `L / e_i`.

**4. Registro.** Traslación al centro del fotograma de exposición mediana, con splines cúbicos
sobre cada canal y orden 1 con umbral sobre la máscara de saturación. Solo traslación, sin
rotación ni escala.

**5. Fondo de cielo.** Polinomio por canal (constante, plano o cuadrática completa) ajustado a
los píxeles con r > 4 R de la Luna, con recorte asimétrico de valores atípicos, entre -4 y +2
sigma, porque la contaminación que hay que rechazar es corona residual y estrellas, siempre
positiva. Absorbe el gradiente de extinción y el fondo crepuscular a primer orden.

**6. Aplanado radial.** Perfil en anillos de 1 px con media recortada a 3 sigma, excluyendo el
disco lunar, suavizado en logaritmo, y división `F = L / p(r)` seguida de normalización a 1
justo fuera del limbo. Con `--profile lum` los tres canales se dividen por el mismo perfil de
luminancia, lo que conserva los cocientes de color. Es la versión de simetría exacta del filtro
adaptativo de Druckmüller, y no genera halos en el limbo porque el divisor no conoce nada más
que el radio.

**7. Realce multiescala y salida.** Máscaras de enfoque gaussianas a varias escalas con el
disco lunar rellenado durante el filtrado y recompuesto con degradado, para evitar los anillos
de Gibbs. El estirado final mide los percentiles dentro del anillo estructural, no en todo el
fotograma.

## Opciones

| Opción | Omisión | Efecto |
| --- | --- | --- |
| `-o, --out` | `salida` | Directorio de salida |
| `--selftest` | | Validación con corona sintética y salida inmediata |
| `--half` | | Media resolución, sin interpolado cromático |
| `--wb {camera,daylight}` | `camera` | Origen de los multiplicadores de balance de blancos |
| `--times` | | Tiempos manuales si falta el EXIF |
| `--moon-radius` | auto | Radio lunar aproximado en píxeles, restringe el barrido de Hough |
| `--center x,y` | auto | Centro manual, para usar con `--no-align` |
| `--no-align` | | Omite el registro |
| `--floor` | `1.5e-3` | Suelo de ruido en fracción de saturación |
| `--trim {auto,off}` | `auto` | Recorte de extremos por píxel dentro de cada grupo de igual exposición |
| `--bg {plane,poly2,const,none}` | `plane` | Modelo de fondo de cielo |
| `--bg-k` | `4.0` | Radio interior de la zona de cielo, en radios lunares |
| `--profile {lum,rgb}` | `lum` | Perfil por luminancia o por canal |
| `--no-enhance` | | Omite el realce multiescala |
| `--sigmas` | `3,10,30,90` | Escalas del realce en píxeles |
| `--gains` | `1.0,0.8,0.6,0.4` | Ganancias por escala |

## Salidas

| Fichero | Tipo | Contenido |
| --- | --- | --- |
| `01_hdr_lineal_f32.tif` | float32 RGB | Radiancia relativa lineal. El único fichero fotométrico |
| `02_hdr_aplanado_f32.tif` | float32 RGB | Fondo restado y perfil radial dividido. Estructura azimutal visible |
| `03_final_16bit.tif` | uint16 RGB | Con realce, estirado por percentiles y gamma 2,2 |
| `perfil_radial.csv` | texto | `r_px` y el perfil usado como divisor |
| `preview.jpg` | jpeg | Control rápido, submuestreado a 2000 px |

Los TIFF float32 se abren en Photoshop en modo 32 bits por canal. Al convertir a 16 bits hay
que elegir exposición y gamma, no ninguno de los métodos adaptativos: el gradiente radial ya
está eliminado y cualquier compresión local volvería a introducir halos en el limbo.

## Validación

`--selftest` genera nueve escalones de exposición separados 2 EV, 16 EV en total, con tres
tomas por escalón, 27 fotogramas, de una corona sintética con modulación azimutal
cos(5 theta) que gira con el radio, disco lunar oscuro, fondo con gradiente, ruido gaussiano
más ruido fotónico, saturación del núcleo en las tomas largas, deriva del centro de 4,7 px por
fotograma y una traza de satélite inyectada en un único fotograma. Después procesa la serie sin
conocer la verdad y comprueba cuatro criterios:

| Criterio | Umbral | Obtenido |
| --- | --- | --- |
| Error de centro | < 0,6 px | 0,078 px |
| RMS fotométrico entre 1,05 y 3,0 R | < 0,04 dex | 0,0100 dex |
| Residuo sobre la traza del transitorio | < 0,05 dex | 0,0047 dex (0,0422 sin recorte) |
| Radio detectado | ± 2 px | 138,13 frente a 140 |

Es una verificación de la implementación matemática, no del sistema completo. No demuestra que
LibRaw lea una cámara concreta, ni que el EXIF esté completo, ni que la corona real se comporte
como el modelo.

## Limitaciones

Cifras para 400 mm, sensor de fotograma completo con píxel de 4,3 micras (2,22 segundos de arco
por píxel) y una totalidad de 76 s con el Sol a 12 grados de altura.

1. **La imagen aplanada no es fotométrica.** Dividir por p(r) elimina toda la estructura
   radial real, incluida la caída de brillo de un penacho a lo largo de su eje. Cualquier
   medida sale de `01_hdr_lineal_f32.tif`.
2. **Movimiento relativo de la Luna respecto al Sol.** El registro fija la Luna, así que la
   corona se mueve. El corrimiento acumulado en toda la totalidad es del orden de la diferencia
   de diámetros aparentes, unos 60 segundos de arco, es decir 27 px. En una ráfaga de 5 s baja
   a 1,8 px. Conviene procesar por grupos temporales de menos de unos 10 s y combinar después.
3. **Rotación de campo sin montura ecuatorial.** Con `omega = 15,04 cos(phi) cos(A) / cos(h)`
   en grados por hora, para 43,4 grados de latitud, 12 de altura y azimut 295, sale 4,7 grados
   por hora, o 0,10 grados en 76 s. A 3 radios lunares del centro son 4,9 segundos de arco,
   2,2 px que la traslación no corrige.
4. **Viñeteado y aplanado radial.** El perfil está centrado en la Luna y el viñeteado en el eje
   óptico. Si la Luna está descentrada, el aplanado convierte el viñeteado en una modulación
   azimutal espuria, indistinguible de una asimetría real.
5. **Sesgo del radio.** El máximo del gradiente cae dentro del borde geométrico por efecto de
   la PSF, unos 1,9 px sobre 140 en la validación. Inocuo para el registro, porque el sesgo es
   común a todos los fotogramas, pero desplaza en torno al 1 % los umbrales que dependen del
   radio lunar.
6. **Sin calibración.** No hay resta de dark, ni flat, ni mapa de píxeles calientes. Solo se
   resta el nivel de negro declarado en el RAW. Un píxel caliente sobrevive a la media
   ponderada y el realce multiescala lo amplifica.
7. **Umbral de saturación y balance de blancos.** El criterio de respaldo marca como saturado
   todo píxel cuyo canal máximo supera 0,96 en la imagen ya balanceada, y los multiplicadores
   del balance son mayores que 1 en rojo y azul. Un píxel brillante pero no saturado en el
   sensor puede quedar excluido. Incluir en la horquilla una exposición claramente más corta de
   lo necesario resuelve el problema.
8. **Modelo de fondo de primer orden.** Un plano no describe luz parásita interna, reflejos
   entre lentes ni bruma localizada. Comparar `--bg plane` con `--bg poly2`: lo que cambie de
   sitio no es corona.
9. **Requisitos geométricos.** El limbo completo debe estar en el encuadre y el radio ha de
   caer entre 0,04 y 0,35 de la dimensión menor del fotograma. A partir de unos 1200 mm sobre
   fotograma completo hay que dar `--moon-radius`.
10. **Rechazo limitado a eventos de un solo fotograma.** El recorte por grupos elimina lo que
    afecta a una única toma de un grupo de 3 o más. Una nube que cubre varias tomas seguidas,
    un desenfoque sostenido o un píxel caliente, que es idéntico en todos los fotogramas, pasan
    el recorte. La inspección previa sigue siendo necesaria.

## Cómo disparar

- Abertura e ISO fijos durante toda la totalidad. La escala fotométrica se reconstruye con
  `t · ISO / N²`, pero cambiar de abertura cambia también el viñeteado y la PSF.
- Horquilla de 16 EV en pasos de 2 EV, por ejemplo de 1/4000 a 1/2 s a f/8 e ISO 200. El paso
  de 2 EV es suficiente porque la ponderación por `e_i` hace que los solapes contribuyan de
  forma óptima.
- Ráfagas repetidas de la misma escalera, con al menos 3 tomas por escalón dentro de cada
  bloque temporal para que el recorte de transitorios esté activo. Las tomas de igual
  exposición se combinan y la relación señal a ruido crece como raíz de N.
- Dejar cielo en el encuadre. A 400 mm el campo es de 5,15 por 3,44 grados y el radio lunar
  mide 420 px, de modo que la región con r > 4 R cubre el 81 % del fotograma. A 800 mm esa
  fracción cae al 25 % y conviene `--bg-k 3`. A focales mayores, `--bg const`.
- Enfoque manual fijado antes de la totalidad y bloqueado. RAW sin compresión con pérdida y sin
  reducción de ruido en cámara.

## Leer el registro de ejecución

```
rango dinamico del bracket: 16.0 EV
pase A: deteccion del limbo a media resolucion...
  IMG_4471.CR3   centro=(2612.4, 1740.8) r=210.3  sigma=0.31 px  n=698
pase B: fusion (referencia: IMG_4475.CR3)...
  IMG_4471.CR3   desplazamiento=(+27.44, -19.02) px  sigma=0.29
```

- `sigma`: desviación típica del residuo radial del ajuste. Por debajo de 0,5 px el limbo está
  bien determinado. Por encima de 1,5 px sospechar desenfoque, movimiento o enganche a la
  cromosfera.
- `n`: rayos supervivientes de 720. Menos de 300 indica limbo parcialmente fuera del encuadre.
- `desplazamiento`: sin seguimiento debe crecer de forma monótona y casi lineal con el tiempo.
  Un salto no monótono señala una detección errónea.
- `rango dinamico`: si sale muy por debajo de lo disparado, los metadatos están mal leídos y la
  fotometría posterior es falsa.

Dos comprobaciones sobre las salidas: en `perfil_radial.csv` el perfil debe decrecer de forma
monótona desde el limbo hacia fuera, y en `preview.jpg` el disco lunar debe aparecer oscuro. Un
disco claro indica fondo sobrerrestado y valores negativos amplificados por la división.

## Contenido del repositorio

```
eclipse_hdr.py     programa, sin dependencias más allá de las indicadas
docs/manual.html   manual técnico con los algoritmos y las limitaciones detalladas
README.md
```

## Licencia

MIT.
