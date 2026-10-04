#!/usr/bin/env python3
"""grano.py: grano fotografico fisicamente escalado y dependiente del tono.

Modelo, en cuatro pasos:

1. Nitidez del material. Antes de nada, la imagen pasa por la MTF de la
   pelicula (gaussiana con el 50 % en --mtf50 ciclos/mm, valor tipico de la
   hoja tecnica de cada material): una diapositiva de 35 mm nunca es tan nitida
   como un sensor de 60 Mpx, y el grano añadido sobre una imagen mas nitida
   que la pelicula se lee como pegado. --mtf50 0 lo desactiva.

2. Textura. El grano es una superposicion de conglomerados de plata (o de
   nubes de colorante) colocados al azar: un modelo booleano de discos. Los
   tamaños no son todos iguales: siguen una distribucion log-normal de
   mediana --grano-um y anchura --poli (0.35 por defecto; 0 = un solo
   tamaño). Cada poblacion es independiente, asi que sus espectros de
   potencia se suman (teorema de Campbell) y el espectro resultante decae sin
   los anillos del disco unico, como el espectro de Wiener medido en pelicula.
   Las nubes de colorante llevan el borde difuminado (difusion del colorante
   al revelar); los conglomerados de plata del B/N, no. --textura gauss
   reproduce la textura de la primera version (ruido gaussiano filtrado).

3. Amplitud. La granularidad rms de la hoja tecnica esta medida con apertura
   de 48 um a densidad 1.0. La amplitud por pixel se calibra MIDIENDO sobre el
   propio campo de ruido cuanto vale su rms al promediarlo en un disco de
   48 um, y escalandolo para que coincida con la del datasheet. Esto es
   exacto para cualquier textura y resolucion. (La version anterior aplicaba
   la ley de Selwyn como si el ruido fuera blanco; con grano correlado a
   10-14 um eso sobrestimaba la amplitud entre 3.8 y 4.7 veces.)

4. Dependencia con el tono. --pelicula selecciona el perfil sigma(densidad
   mostrada) calculado sobre el eje neutro del modelo espectral de cada
   material (tabla embebida): en las diapositivas la fluctuacion sigue la
   estadistica binomial de cobertura de colorante (crece con la densidad y
   decae al saturar cerca de Dmax); en los sistemas de negativo mas papel
   (pro400h, trix) el grano nace en el negativo y llega a la copia
   multiplicado por la pendiente local del papel, que lo anula en los blancos
   y en los negros: el grano vive en los medios, como en una copia real.

El ruido se suma en el dominio de densidad, por capa, con correlacion parcial
entre capas y la componente cromatica escalada aparte (--croma), y se vuelve
a sRGB. Requiere numpy y Pillow.

Como mirarlo. El grano esta escalado a la pelicula: a la resolucion del M11
cada pixel son 3.8 um, y un pixel de 3.8 um se juzga al 100 %. Reducir la
imagen con un filtro pobre (muchos visores a "ajustar a ventana") o
recomprimirla en JPEG a calidad media convierte el grano fino en manchas.
Para una version reducida, o se aplica el grano directamente a la imagen ya
reducida (la calibracion vale para cualquier paso de pixel) o se usa
--ancho-salida, que reduce con filtro Lanczos despues de añadir el grano. El
script guarda los JPEG a calidad 95 sin submuestreo de croma.

Uso:
    python3 grano.py entrada.jpg salida.jpg --pelicula trix
    python3 grano.py entrada.jpg salida.jpg --pelicula k64 --intensidad 1.3
    python3 grano.py entrada.jpg salida.jpg --rms 16          # ley generica
    python3 grano.py recorte.jpg salida.jpg --pelicula k64 --ancho-mm 9.1
        (un recorte: se indica cuanto mide sobre el fotograma su lado largo)
    python3 grano.py entrada.jpg web.jpg --pelicula trix --ancho-salida 2000
        (grano a resolucion completa y reduccion con filtro para la web)
"""
import argparse
import base64
import io
import sys
import zlib

import numpy as np
from numpy.fft import rfft2, irfft2

try:
    from PIL import Image
except ImportError:
    sys.exit('Falta Pillow:  pip install pillow')

_PERFILES_B64 = (
    "eNrtenk8Vf3X9jFmDIXmkgZNopAKXRKVWUJJmiRDKmlQqdxKJYVIMxqoKNEsRJMyVIYylfEYjzPufVRo4Nnuju47533e9/c+v3/u"
    "5/k83z66Pmeda33PXuesva619t52lmLimrSfayxN48pdkR7BkqQp0zxMp2/23S1CU6R5iv7k9OFJG0drO2cR2k5agMZ6921ufhpz"
    "1TQMN8zWmKamsWGL33a/tZtXb/Fb795rX7jWZ5s7Zd/mudbXnXo9adaMaZOnqe1T+68vGcEh086f611J+Inp0NXpXS8Er/Pxk1Us"
    "sL+Hx4beVS54/wPevuld1QJevcBOF/AbBe83CfxaBDyGgNcm4LEEPLaAxxXwCIGdEPBJwft8gV+7gPdJwPsk4H0W8L4IeB0CXqeA"
    "1yngdQl4XwW8bwLedwHvu4D3Q8DrFvB6BDya8U87zfgnn2b859s6IsY//USMf9JEBTxRAU/U+Oc+YgKemIAnLuCJC3jiAp6EgCch"
    "4EkKeJICnqSAN0DAGyDgSRnb/ZafZ0V3fe3LzwFUfm6cpduXoLMlf5L68N9NUDWdfytFZWyNuwImjvFF6q2vN+e4boG8qVteZsBa"
    "aJ+db343mUrIro7xNwaU4CLLwS/rfQk+JOTPyJhYgXElOZy9ZRWYbO7YOFerEiFttp2+Q6vRrB4vzSSrYTn4XFycUg2SAqO2BYyo"
    "R9TkU4++RNej/bDJsLq79RDLMDrdU0/HO1vdmIb1DWg8Z7RQNaIBclVHEq/4NsJm1PzC0h+NmB0vPrtzZhNeRNdJfStrwhNNqUgZ"
    "n2bkj8zTs77ZjJryr1ybYS2I8v9SH5rWgsJVxWbetFYcdWaubUcrnjWMliaaWyEf3mk1fDYDi5dEP9ezZuDGmXjfXV8ZeHL1Te0p"
    "pzbcDprM9VrQBvHsmLc53DY4mBw65bWSiYKqWUW7JzKhezUsc+57Ju5G7L8YZsmCj9+47Ts7mdix5tJ+91ssKHhn51pNYqPMQ3yD"
    "WwYLS1d0PX26iw2r+cceDPjCRmZahWiHDxuvZw1L2azHQaSUgv3U+xwouk5hn1bkYHbsscqEJg5KLb5sOe3OhWLUYZWSaxwEZbRf"
    "H3mEiypG8/CXsjwUWBXk+mlx0aKi6ZM2iofb4Z53a67ykOhqW297k4t9ozM+Sybx4JRJDkgYTuDbGfsAtxE87Gkuoe9WJhBSGLym"
    "1JVAlmNxrEUgDyE351no2xLYcXr4zRUxBExTnHKvVfCQm395XUswgZ3B3V+VywmU/nDcETqIwKIjwZ7nHhDYfnasVbIsiUCtjNVd"
    "OgQSPaSwmU7gnm4ZOceIRFhXuJmuHYGehtTi3VIkHoVVqjttJFEonm0w3INAhFOrdtsUEpPdY5h1p0gkhwYp3d9FoMI70ZexmIT1"
    "dGez3Y9JJBalPGFQx5FeM5bvsI6E2hqPYdZ1JNY8Dz125xiByqbwoRv9SYyPHtst2U2ikt/0h0QYgUlyU8wdQ0gsusO/1DiUD+7o"
    "Ail2CGUv2ztYnfq8gRvvbN+vxUcI/TKxLJDAkq51t6/Fkhjq2NllbELZvxTFzfMlMLB6UHvzZRI7onUzVy/h4+iuoJpYFwKHtrKq"
    "R10h0f1FvXnvSj5sUmXfes0nkKFwZgRJ7WPmrvhj1no+rk3tkNkzloDPVg/P/dTnPg6Neknz5GP92bkDrn3hIa1BfnUddZwX9KrG"
    "rafsG8au9/aI42HukR+GQVRcG7UiUr9R+0xJYJIic3mQkI5p+LaWxNWym5cGr+JjnjXrZmceFw+WxKefXkQixD4scOlSPrxuDKtL"
    "sOAiMDSEcX4SCcPIqlsyZnzEP78Q+jKbgxEXCo8+EifxTtxQvHQmHwfCrcYmj+fgkcyPvOQq6nesmmTHGMnHq+U1Nh4BbMww7Ql9"
    "douAo/GbqBpRPqpvBOSkP2PBQa5yNms3gTRR11OdTSQiKwwC9lLnhenxEQqxxgR4p+eN2PqchMLng9uiRzLx1myt6T4RAly5cwES"
    "MSTuqR0JNNJqQ5HkYq8gfx42OQSG+fqSaLK/e2/DdAbCr27NdKzj4iM71ybYmMoX4sD+V6qtSE/cmVg5m4vPNeaG5lQergpqfxxN"
    "b0ZI9cUdPgc4cH5Mz9IoIUAUOCQFHKKEcX3pQE4mGzvzRo2MjSRwY+nQDhuyAd4fraNmNbCwXaFQ2tmawPG944zzVeiIOp/S2dPO"
    "hKpe+Dx/UQLt2xKOuR6vgeaBjI2SvDa8lqgatc2Nh7A4xx4V/w9Y/Nw4SqKEgZyZZ5w7HnB/2S1j7Id/Ot2KaSnXw4u+cX7Zpdih"
    "dxcZtiA7Z6R3se5f9jp/eu3h7CYYuUgpybmyf9krI1LHlQ5qxLGcnFG2O1j4XXCcvfw+/SY4M/X+qYLT1xGtCSvMZA3fgKIFBnU6"
    "QdrzBkx+4EfGFSOllrvPoKMYIn5RQaYfijGqUFlKzK4CFUY36srfV2DVkc+ZsccrkHnSTJy9qhphJxnOUe3VGPrm/ej0vGqkXb6b"
    "sMusHnpr+EYFp+rxbQskykProard6Zui0ICA6BXzgzY0wESrxEjcrQFXDmWfMotvhK7KAhE5WhMsjPKNzUWbcEEsO/KIXDMK6wZq"
    "NmxuRvyc85pLdjZj2rxdF8vtW3Dz05AxqpktWDlMXmTFqxaYjdi690VAK044DPGazGyFqdXYWxZdrUjLIRB4jAGDLtcpLrQ2RCYY"
    "2gcPagNL40Q2GdyGhptW4udpTMQmvblfoMJE97VzG3S9mfg46YWDP4eJRS5i9y0kWJiovTFbw4gF2aKELw/zWMj1H9St0MiCGOP2"
    "M6ceFlZe+sgSi2bjfvNQsdzbbBj4XfRovcOG9RVx22N2HMgoRkw7vIUDMw+ZlmJHDgpEyFlePRxYuWYrPVTj4nRi5I1gDgcXnA/u"
    "DrjMhf0fto3lOVw8Kkya82QXF8rEKW9LXR60IsYnvnThodz1VOjCDi6uGh67vuoRDwvD7Iy1mnmIFZu/XMmLB725N6oshhHoXqC3"
    "a9pMAupnRlhVvOFhM3NmKmcpgZIL+s9TNxIoVjEZVq5EgDkk/PTLUKqQmChtTbpIoCNgtOIefQI1qy/Hv3tMwD5qT8eNQgKWzjuK"
    "LywjYG6Y1d3RRsDg6flhyV0ElMfZ5ez0I9C2dpqNxSASRctDkgzGUoWEzx3ffIRAaLvpCaVZJFZkf7hmakbim2ZZZ8MZim8l//20"
    "I4lpQWxpZ3cSdslG7WevUIVc5ZxhAFWIRG8jsyuIKlTz7i38dp0SHNFHn/SPkPiucrho0wUSwVkREVKJBE4sMM9KpTrnzbtXm3Jv"
    "k3ht80T6NbVPe3qZ1KvrlAAaPHZ8TBXCOIMIuQlnCWyc4KHBv0PiZKHk+cklJPL8VjNUKYGam0GX3J/WW7A197+uIrHlXkSRNxWX"
    "Ztkynlo6ibKzj/Z1NZCYs/S9shH1PcitzxSb/5CExMhhVvotJHJaTHydZxG4o3Gg1iKVxPaSE0llzSRoEt4zHypQBU55zk56POXv"
    "Og3hdBI72T/oK17xEPPD86xaNCUgU7ds9vpAIqZ8mMTMtTz8IRMw+lsgCZ15qePmvSXR+IZ+7h6Xi+2BXTIaHiT2Gd70UMyihMR7"
    "SmanDxc9kz4vbDen9pVcQC9JJHEtLmjroY8cuFMZG61B4pAe6eFwggR7d3uQ7BwOtladv36ORsJ/X3OU7zYSS152JrQcZsPEIpqV"
    "VEo1HNn+WuPtSaohkvMY95QFqUMiA0/GE2gWe12vM43EkcQdK2Y2MzHZ8rpd7CYCC5R1dBjUfnrpn+LwqY363tcajqby78WKNc2R"
    "lCAsLacXaLAY6Jxh/NKXzsNY9V1eG2MJKBxM2l+a24qAj1r5y+x5aD2Ql3NrHdUADKyLlzpCnd90wuBCGhcXr5iEqVOCPvTN6YkD"
    "JzZDyjhv8mkFLuJin1WW3OGhzXlkV2lcI5qsculdyzkgW0/OXarMQ+Gix9IdbXTcNhjapXCSDfZKlt5ULy4mZurVT5aox5511QGi"
    "j1l4pnzMwSGVg6tiZhUny6og9r7jvXsJEyHHmJ3bmtlIdPJdaHX5A468iXp1qqQNxUU3wmSl/7LbP1gxUz+dgUK9Z8s2DWf9smtd"
    "adsedbAVVS70tqKhzF/2Pzy71R01WxD33YxbL9r2y/415Hnr4WRKiIqHVKiVt/YTHDe3A819giNHCc5Od5+dXmv1tP/pqqNyo/bh"
    "6I/rAHPrKDfLVTjWbbHqnOQ7bJtzZ6VJeyHMpQpWup8tRuIrxVFrrT8gl1PiqZJdhtFTvNULbCqQ5/JSfs2TWpzWnn3AacdHLF6X"
    "9dpiRTUi90UoDouhft0l6yY8XlELdthDmrZJPRw3B37WONIIk+XnwvdU1eOVfBlPUr4Ba1VVvVX1m+EYtMV88fIGNKVvNL52pRFn"
    "7vjqDH7UAveOrzu4txrxSpcMUR/YjEF31m/Yr8yAyGUGqd/chIK3nbkHl7dA9dYj9R92bVBKOW9iItoCh67DvL2HW7H6wkCFAD8m"
    "Glc3MrSkW6F3/Xnz9hgG2l32q9vtZaF4BYNd8r0VhEV4lldsG9bOWMmbuJWN+DzVexvrGNjxmhiad4waf8bLPE+zp9qpVWKBTnfb"
    "MFZNI+ODJwtBuzq2SI2j2ssBJ6yO+jMh/WYwW1SfjZsVsksMGrkIWK0y/IUWCzfy6JV51PiTaKMcWRPNw4UpnJQ91ZSK2UT21Cdx"
    "sKdnWc7UkVQ7vSvhj6/72IiydBc5Z8dF1h4fN2NqTGBoK5JDVTjoTt764T2Li5MJ9WeQTKBJ6/Cae1c48NJKXLBpLw83xvp9msui"
    "qrzy2MmdE7lQcvjxZTHVZlrVTfE9NZ6quhv8n0Zf4aKW/rTqD1BV4GKGz+HlVLVRGVjEVuEh1F0sXolqY5/Vec4xoKq7z1PHS0uD"
    "eLjVeNV/QgoBl5WKo0qoqv4q3C1dhFK595N8rMtrCazS/1i+t4xEwOI3IslqBHKk/FWWUe2o3dGRtYs/k5jpuC51tiWB/SnHY+J1"
    "qH0NVT/oK/LxZcjNrilUVdeLfsOsW0ZVSYe3l69N5CNiia106SkCFidPXTbaRaJ16lam/2w+htRWjJj0kMCmCyZTMqkq/dilTDKX"
    "aue/vTD11H9PYPbBFl/nWyROsGJbgmz4WOzxZLsuh8C1HcozllOqo/ZUNCzdno9zy5dwysRIZKU9rDv6nlKZQ7fP36Ps4zK0GDuG"
    "kFCdv8agvp5SvcX2hXRrPuSbacqK1Pig2fNIpZJJfe4HzRy2KR9zvi+5HqlHIqL7XGIGQWL+MDdXdX0+Dq+YDVWqTfcOypiwop3E"
    "meBZ16Qn8DFw6oLMK9R40r1Txr6FpMajDkcZ+YF8TNVN2yZnRWL//FZ9EQ6JFwmGmpf4JAwes52eWpNYnWbd0NNIqZJNhFjMO5Ia"
    "PxpeTqD483ZpKm6uIGHy7EtMIBW37sbJ0unU/rRLlemKuSRuR6Z5bjlIonPfrVBD6ngGaFy+n32XxIzg1qP6DiSYKWceJFDHT6xb"
    "89D+PIm0A3nFd8aQqI6bFjeRijf/dLNzyT4SGxaW8FVbCDgkXbc3oL6fq4/qZ1i6kjBXUi/Yfo2Al2TCB2/q+zRn+WasnE3FtTdS"
    "4cYaKm+H51AiRiAmeY9o/UASF+kp4+uo8fsO/+Uh2XeUCkvFhRhS47Kr5UbxmEM8PB6q52p6n0BrMq9nGZVvPjptsxa846Lg/RW2"
    "60lKnfTrva7vJKC4O9XUSpELO5GKoWWbCcRHdhozDKjuyWnr83wjDkL2yY8eQI1dByzrLy+iEUg2v1VnZ8qG+tmaOUnSBNz1zxhq"
    "b+Uhb1H0RG9tFpI3FB+7l0CN++8v5qlSY6R5/P188VG9lzUa3g1ezENtQsp9NSkufkQNnvpscBs85owZuLWSi7NliZll76jzb80f"
    "Rw6JMkDcO+9WPJ+LlcpL8kTAgaxXW+G3khasTw6JHBHOwU56kOegbWxo831MD66kVNOt54V0LRtGrUNGTQtjwZlm71Dp0ggRsUzP"
    "rElsvGTpBV+MYPZTHdVcxcF9qiNLqY6v3xZdbW3Pf6roWKpVFhWue4MohrKCok4RNqtYVB0dko3+9rOG4vZxVa+hy/Zw+3qkHNPH"
    "bTo5xKICdfmTX+5RLEPd4yELJvCqkXe0NE1TswZchVs0Kf1q+J2UbJirQKdE6Olpp+/1mOvq8uD0MjoOfXkt7aXXiOnNY1YyJRvx"
    "VmkKo2ZOE0QXqJa/lm3G5xHH1Zivm7DFntO2+3ULsl77tH2Ka8FYA+1TZrYtsL6Zm3KXGlE86awJV761UklX8EA1oRXJrXKmvKEs"
    "yFvonfk+vQ1pT/k72soZ6PhsHplYw8aJSPOI0YZMZGid+nKqug0H2WOfmCznwuvDMiPvKSxYHxDdlZLPxAlZ/zClYzwkGV+abfuN"
    "BVNOjZV1PAv0zmjXUBMCGvtehEx/yAZ9YqUC04ONodsL3hymWrTNl8MCI1ZyEFCz12jKSA5ycy4E7a0mMKX63CJbanShbTRUiszg"
    "wHKjccSSbmq0aDJ/r7SNi09Rxn6HLbgYOWpcSYQo1bKPbdpxvIWLN5lD5LZTJ1lyVOTaJiaBe4NNr0XZ8bAkmSW7w5QHnasuchce"
    "Eag6O75uRCoPFiXRG44k8mCjSw5x8SZ+XTzvj7fv6H69OY7AerKHV0Rh8FV+YshXLqrIycEd8wnIxL0+Kk+JUGGtzruMpxxMl8sY"
    "tmcFgUd+N57q2lMtr05CtocLGw8VAlttvQjM9H7glU61+mlR6ofWFTGxYpH/6jXU6NRtm3e+yJyAt+2j7DCdNjQ+Tb9psJqA//HI"
    "6RKTCEoETioXhVEjaJ1by3IzAuMGW5bQ63mIDpU286prxrLEpWKyYwhI0L48H2VLjWa1r3TfzWpC3cvAVkYlD8ED6OknznMxQu+j"
    "bObpBowZo6i5xIkHNcbq+J1ZHDhZsrdVd9Vjb94ytdgHlGhvnz2kJI0N1ptBrbUfa3EiP3Zy2XcO2r1qRG8fp0TfNZVvzazCC+Py"
    "GtnpHHy8e+ZtLpgQHRTuP1HnA44lw30SVay6B5a9WlnCwNFMrYfFt8uRxZj1uBYsuC7222uHVhTOX2vRs6EUG9aG5smpMzHc5u6l"
    "ZcHNSOA8s/V2eYeQEm8yjccAS9TnXfj9RtQ8SQt5ur0YlqMuhbNutiLlrnfol0I6YmJe769f9BZhBZZza8xbkNzjIGu2uw6Bsg8U"
    "mi7nIzmJHTTmbRPkHE7pGU2rgnTKhC71Ay/BrMDjo0aNKBxvmhOVW47QYN4rt1dPkTrCZrTYJToaw4f7y854h28iDxN94h4iT6l2"
    "v1R+HeInWdjk9xT8sov9cKxLnlENTHzwlnX2Wd/NDhqpOTMi62AlbsQ0GYwvvfPLnueZdDQ/sVTIDlUnl+U3in+97ltKysk+OvPz"
    "heyTNh3ILP3+VMgut3pJ4bUft/9l+//U9bvo7Ld7Oa1PdKQo0dnu57Xrn6o4IXeyuTPi8tAfaeWktntKsRD2DN31eZF/qRCOdVpZ"
    "M+FdhRBebPh2KVu9SgidrR5sGelXK4QlxYuur6yrF8Lx0ku1j+5vEMLg1AVrzso0CaFT+MycR4eahXC8U/MBaV6LEPLD5ceUz2YI"
    "IbLmuSS7twnhBz35hu6dTCGcfB0R2t4sIZRTy5JInckWQn3p1dsmfBRGZx+zTusgjhDeHnbCbd1CrhAeVApv0B7NE8L/THEWmTtL"
    "pHkJY8yA0bpGr4RxxQureYvkSCGcz+QujZsrjF5FEkxHc2FMrj8wZuFMYcz8PPj5wnZCCGP9NzxbdUAYd0fkZC1P5wmhGGvxqoOd"
    "HCF8bC7eqPWKJYTypU/GpEu0CeHUIfbrTl5pFkITLzt9biBdCF9dZj+RJiuFcL7XiVH6ZO6/jLT/Xf+7/r8VR4tv+qhPcWR67+as"
    "/rvmnBXw+vDf0hydf/cJFzWZNk8lHfFYKeP++HtMt5gSR/pikv8zpn7D2z8trPS0jMgWdRlj+aSjoyekyRh/iM+0VcyW7hdW6sJo"
    "j76wpP8M62/PevzTQvrP1OP/GdJfdxP/+4c08M+Q+l+v/u8Tl4ioptjvT8L1PuvW+yf5t4Lyh0jv/z+fi+vv0/t0Um/D2vs34Def"
    "S9Qugvzt79R7h/n/7KQkTeu739zfqfcuQZ+T3G9OBxRov90z6O/Ze6Wnz1P2N89OFdrfr/v0d+zt1vscpX5z3DSS9qt37+/VW3HP"
    "Cn5+md+86tRpf6u//f16q1qfn/xvfvfG0X6vcf1de3Oyz1X6N9fQ8bS/6si/7uY6gfbXufp/cxv4m5v2RFq/88HOUuLPVJKl/q2n"
    "MkJKo/fVfwDrLu/b")
_P = np.load(io.BytesIO(zlib.decompress(base64.b64decode(_PERFILES_B64))))
GD = _P['gD']
# ganancia de copia: en los sistemas negativo+papel la rms del datasheet es la del
# NEGATIVO, y la copia la multiplica por la pendiente local del papel; k es ese factor
# en la densidad mostrada 1.0 (por canal), calculado con las curvas reparadas
K_COPIA = {k[2:]: np.asarray(_P[k], float) for k in _P.files if k.startswith('k_')}

# rms: granularidad difusa rms de la hoja tecnica (x1000, apertura 48 um, D=1.0)
# grano_um: diametro caracteristico del conglomerado
# textura: 'nube' (colorante, borde difuso) o 'disco' (plata, borde neto)
# mtf50: frecuencia (ciclos/mm) a la que la MTF del material cae al 50 %, valor
#        tipico de la hoja tecnica; se puede afinar con --mtf50
# poli: anchura (sigma del logaritmo) de la distribucion de tamaños de los
#        conglomerados; 0 = todos del mismo tamaño
PRESETS = {
    'k64':      dict(rms=10, grano_um=11.0, corr=0.35, croma=0.45, textura='nube',  mtf50=40.0, poli=0.35),
    'k25':      dict(rms=9,  grano_um=10.0, corr=0.35, croma=0.45, textura='nube',  mtf50=45.0, poli=0.35),
    'velvia50': dict(rms=9,  grano_um=10.0, corr=0.35, croma=0.45, textura='nube',  mtf50=50.0, poli=0.35),
    'pro400h':  dict(rms=4,  grano_um=12.0, corr=0.35, croma=0.45, textura='nube',  mtf50=30.0, poli=0.35),
    'trix':     dict(rms=17, grano_um=14.0, corr=1.0,  croma=1.0,  textura='disco', mtf50=40.0, poli=0.35),
}
GENERICO = dict(rms=10, grano_um=11.0, corr=0.35, croma=0.45, textura='nube', mtf50=0.0, poli=0.35)


def srgb_eotf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_oetf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


# ---------- nucleos de convolucion (por FFT, con envoltura circular) ----------

def _nucleo_fft(shape, k):
    h, w = shape
    K = np.zeros((h, w))
    kh, kw = k.shape
    K[:kh, :kw] = k
    K = np.roll(K, (-(kh // 2), -(kw // 2)), (0, 1))
    return rfft2(K)


def _disco(r_px):
    """disco de radio r_px con bordes antialias (supermuestreo 4x4)"""
    n = int(np.ceil(r_px)) * 2 + 3
    c = n // 2
    yy, xx = np.mgrid[:n, :n] - c
    acc = np.zeros((n, n))
    for dy in (-.375, -.125, .125, .375):
        for dx in (-.375, -.125, .125, .375):
            acc += ((xx + dx) ** 2 + (yy + dy) ** 2 <= r_px ** 2)
    return acc / 16.0


def _gauss(sigma_px):
    n = int(np.ceil(3 * sigma_px)) * 2 + 1
    c = n // 2
    yy, xx = np.mgrid[:n, :n] - c
    g = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma_px ** 2))
    return g / g.sum()


def _filtro_textura(shape, textura, grano_um, pitch_um, poli=0.35):
    """respuesta en frecuencia del filtro que da la correlacion espacial del grano.
    Con poli > 0 los conglomerados tienen tamaños log-normales (mediana grano_um,
    sigma del logaritmo poli); como las poblaciones son independientes, se suman
    sus espectros de potencia (Campbell) y se devuelve la raiz, un filtro de fase
    cero con el espectro de la mezcla."""
    if textura == 'gauss':
        return _nucleo_fft(shape, _gauss(max(0.35, (grano_um / pitch_um) / 2.355)))
    if poli > 0:
        s = np.linspace(-2.5 * poli, 2.5 * poli, 9)
        w = np.exp(-0.5 * (s / poli) ** 2)
        w /= w.sum()
    else:
        s, w = np.array([0.0]), np.array([1.0])
    P = 0.0
    for sk, wk in zip(s, w):
        r = max(0.6, 0.5 * grano_um * np.exp(sk) / pitch_um)
        Hk = _nucleo_fft(shape, _disco(r))
        if textura == 'nube':        # nube de colorante: disco con el borde difundido
            Hk = Hk * _nucleo_fft(shape, _gauss(max(0.35, r / 3.0)))
        P = P + wk * np.abs(Hk) ** 2
    return np.sqrt(P)


def campo(shape, H, rng):
    """campo de ruido de varianza unidad por pixel con la correlacion de H"""
    h, w = shape
    f = irfft2(rfft2(rng.standard_normal((h, w))) * H, s=(h, w))
    return f / max(f.std(), 1e-12)


def rms_en_apertura(f, pitch_um, diametro_um=48.0):
    """desviacion tipica del campo promediado en un disco de `diametro_um`"""
    r = 0.5 * diametro_um / pitch_um
    if r < 0.5:
        return float(f.std()) * (2 * r)  # apertura menor que el pixel: Selwyn
    K = _disco(r)
    K /= K.sum()
    return float(irfft2(rfft2(f) * _nucleo_fft(f.shape, K), s=f.shape).std())


def escala_por_pixel(textura, grano_um, pitch_um, rms, poli=0.35):
    """sigma de densidad por pixel a D=1 que deja la rms de la hoja tecnica en 48 um.
    Se mide sobre un campo de referencia con la misma textura y el mismo paso."""
    shape = (768, 768)
    H = _filtro_textura(shape, textura, grano_um, pitch_um, poli)
    f = campo(shape, H, np.random.default_rng(20240912))
    s48 = rms_en_apertura(f, pitch_um)
    return (rms / 1000.0) / max(s48, 1e-9), s48


def desenfoque_mtf(lin, mtf50, pitch_um):
    """MTF gaussiana con el 50 % en mtf50 ciclos/mm, aplicada en luz lineal"""
    if not mtf50 or mtf50 <= 0:
        return lin, 0.0
    sigma_um = 1000.0 * np.sqrt(np.log(2) / 2.0) / (np.pi * mtf50)
    sigma_px = sigma_um / pitch_um
    if sigma_px < 0.25:
        return lin, sigma_px
    h, w, _ = lin.shape
    H = _nucleo_fft((h, w), _gauss(sigma_px))
    out = np.empty_like(lin)
    for c in range(3):
        out[..., c] = irfft2(rfft2(lin[..., c]) * H, s=(h, w))
    return np.clip(out, 0, 1), sigma_px


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('entrada')
    ap.add_argument('salida')
    ap.add_argument('--pelicula', choices=list(PRESETS) + ['generico'],
                    default='generico',
                    help='usa el perfil sigma(D) y los valores del material')
    ap.add_argument('--rms', type=float, default=None,
                    help='granularidad rms del datasheet (anula el preset)')
    ap.add_argument('--grano-um', type=float, default=None,
                    help='diametro caracteristico del conglomerado en micras')
    ap.add_argument('--textura', choices=['nube', 'disco', 'gauss'], default=None,
                    help='nube = colorante (borde difuso), disco = plata, '
                         'gauss = textura de la version anterior')
    ap.add_argument('--mtf50', type=float, default=None,
                    help='MTF del material: ciclos/mm al 50 %%; 0 la desactiva')
    ap.add_argument('--poli', type=float, default=None,
                    help='anchura de la distribucion de tamaños de conglomerado '
                         '(sigma del logaritmo); 0 = un solo tamaño; 0.35 por defecto')
    ap.add_argument('--ancho-salida', type=int, default=0,
                    help='si se indica, reduce el resultado a este ancho en px con '
                         'filtro Lanczos (para la web); 0 = tamaño original')
    ap.add_argument('--ancho-mm', type=float, default=36.0,
                    help='cuanto mide sobre la pelicula el lado largo de la '
                         'imagen (36 = fotograma entero de 24x36)')
    ap.add_argument('--intensidad', type=float, default=1.0)
    ap.add_argument('--correlacion', type=float, default=None,
                    help='correlacion entre capas; 1.0 = monocroma')
    ap.add_argument('--croma', type=float, default=None,
                    help='ganancia de la componente cromatica del grano '
                         '(0 = grano acromatico, 1 = capas plenamente '
                         'independientes); por defecto 0.45 en color')
    ap.add_argument('--semilla', type=int, default=None)
    ap.add_argument('--dmax-vis', type=float, default=2.6)
    a = ap.parse_args()

    pre = PRESETS.get(a.pelicula, GENERICO)
    rms = a.rms if a.rms is not None else pre['rms']
    gum = a.grano_um if a.grano_um is not None else pre['grano_um']
    corr = a.correlacion if a.correlacion is not None else pre['corr']
    croma = a.croma if a.croma is not None else pre['croma']
    textura = a.textura or pre['textura']
    mtf50 = a.mtf50 if a.mtf50 is not None else pre['mtf50']
    poli = a.poli if a.poli is not None else pre.get('poli', 0.35)

    im = Image.open(a.entrada)
    arr = np.asarray(im.convert('RGB')).astype(np.float64)
    escala = 65535.0 if arr.max() > 255 else 255.0
    rgb = arr / escala
    h, w, _ = rgb.shape
    pitch_um = 1000.0 * a.ancho_mm / max(h, w)

    # 1. nitidez del material
    lin, sigma_mtf = desenfoque_mtf(srgb_eotf(rgb), mtf50, pitch_um)
    D = -np.log10(np.clip(lin, 10 ** (-a.dmax_vis), 1.0))

    # 2. textura y 3. amplitud calibrada en 48 um
    sigma_D1, s48 = escala_por_pixel(textura, gum, pitch_um, rms, poli)
    k_copia = K_COPIA.get(a.pelicula, np.ones(3))
    # la rms de la hoja tecnica es granularidad de densidad VISUAL (luminancia); con
    # capas solo parcialmente correladas, la luminancia de tres capas de sigma s vale
    # s*f_lum (0.845 para corr 0.35), asi que la sigma por capa se escala con 1/f_lum
    WV = np.array([0.2126, 0.7152, 0.0722])
    f_lum = np.sqrt((WV ** 2).sum() + 2 * corr * (WV[0] * WV[1] + WV[0] * WV[2] + WV[1] * WV[2]))
    sigma_D1 = sigma_D1 / f_lum
    rng = np.random.default_rng(a.semilla)
    H = _filtro_textura((h, w), textura, gum, pitch_um, poli)
    comun = campo((h, w), H, rng)
    campos = []
    for _ in range(3):
        propio = campo((h, w), H, rng)
        n = np.sqrt(corr) * comun + np.sqrt(max(0.0, 1 - corr)) * propio
        campos.append(n / max(n.std(), 1e-9))
    ruido = np.stack(campos, -1)

    # 4. dependencia con el tono
    if a.pelicula != 'generico':
        T = _P[a.pelicula]
        rel = np.stack([np.interp(D[..., c], GD, T[:, c]) for c in range(3)], -1)
    else:
        rel = np.sqrt(np.clip(D, 0.0, None))
    sig = sigma_D1 * k_copia[None, None, :] * rel * a.intensidad

    # descomponer el ruido de densidad en luminancia y croma: la calibracion
    # rms del datasheet es de densidad visual, asi que se conserva integra en
    # la componente de luminancia y el croma se escala aparte
    dn = ruido * sig
    lum = (dn * WV).sum(-1, keepdims=True)
    dn = lum + croma * (dn - lum)
    # la densidad macroscopica de la hoja tecnica esta definida sobre la
    # transmitancia MEDIA: un ruido de media cero en densidad aclararia la zona
    # granulada en exp((sigma ln10)^2/2) (1-3 %); se compensa con el sesgo
    # log-normal, calculado con la sigma efectiva de cada canal tras el reparto
    var_lum = ((WV * sig) ** 2).sum(-1, keepdims=True) + 2 * corr * (
        WV[0] * WV[1] * sig[..., 0:1] * sig[..., 1:2] + WV[0] * WV[2] * sig[..., 0:1] * sig[..., 2:3]
        + WV[1] * WV[2] * sig[..., 1:2] * sig[..., 2:3])
    var_ef = np.clip(var_lum + croma ** 2 * (sig ** 2 - var_lum), 0, None)
    sesgo = 0.5 * np.log(10.0) * var_ef
    Dg = np.clip(D + dn + sesgo, 0.0, a.dmax_vis)
    out = srgb_oetf(10.0 ** (-Dg))
    res = np.clip(out * escala + 0.5, 0, escala).astype(
        np.uint16 if escala > 255 else np.uint8)
    im_out = Image.fromarray(res)
    if a.ancho_salida and a.ancho_salida < w:
        im_out = im_out.resize((a.ancho_salida, max(1, round(h * a.ancho_salida / w))),
                               Image.LANCZOS)
    if a.salida.lower().endswith(('.jpg', '.jpeg')):
        im_out.save(a.salida, quality=95, subsampling=0)
    else:
        im_out.save(a.salida)
    kv = float(np.dot(WV, k_copia))
    print('grano %s: rms=%g  pitch=%.2f um  textura=%s  grano=%g um (poli %g)  '
          'sigma por pixel (D=1)=%.4f%s  [rms medida a 48 um: %.1f]  '
          'MTF50=%g c/mm (sigma %.2f px)  croma=%g%s'
          % (a.pelicula, rms, pitch_um, textura, gum, poli,
             sigma_D1 * kv * a.intensidad,
             '' if abs(kv - 1) < 1e-6 else '  (ganancia de copia x%.2f)' % kv,
             1000 * sigma_D1 * s48 * a.intensidad,
             mtf50, sigma_mtf, croma,
             '  salida reducida a %d px' % im_out.width if a.ancho_salida else ''))


if __name__ == '__main__':
    main()
