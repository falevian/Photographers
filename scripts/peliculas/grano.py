#!/usr/bin/env python3
"""grano.py: grano fotografico fisicamente escalado y dependiente del tono.

El sigma base sale de la granularidad rms del datasheet (apertura de 48 um a
densidad 1.0), reescalado por la ley de Selwyn al tamano de pixel equivalente
sobre un fotograma de 24x36. La dependencia con el tono usa el perfil
sigma(densidad mostrada) calculado sobre el eje neutro del modelo espectral de
cada pelicula: en las diapositivas la fluctuacion sigue la estadistica
binomial de cobertura de colorante (crece con la densidad y decae al saturar
cerca de Dmax); en los sistemas de negativo mas papel (pro400h, trix) el grano
nace en el negativo y llega a la copia multiplicado por la pendiente local del
papel, que lo anula en los blancos y en los negros: el grano vive en los
medios, como en una copia real.

Uso:
    python3 grano.py entrada.jpg salida.jpg --pelicula trix
    python3 grano.py entrada.jpg salida.jpg --pelicula k64 --intensidad 1.3
    python3 grano.py entrada.jpg salida.jpg --rms 16          # ley generica
"""
import argparse
import base64
import io
import sys
import zlib

import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit('Falta Pillow:  pip install pillow')

_PERFILES_B64 = (
    "eNrtWmk4VW3bNocGFErTgwapPFREoVNSmZJEhUwhU4OEBiGN4kFEozRQUYZKhZRKilTmqSjjtrGntbYyVPItb7vnfWt/P77j"
    "e/+8x/F9t2M7j32t87r3Wve+7uu8rr2WpZmwiJrAj6EkoHL1ruAwb4gJyAp4GP25w3efoIC0gKfQD85PPGVhs8bSVlAgUCBI"
    "xc19t6ufylJFFb2tOirzFVW27vTz93PZ4bTTz819xL7KZdtud8q+29PF1516P2fxgvmq8xWDFf/3Q5J3ygLnz42MNPzAPGgu"
    "GhnPee9f4QergmevhsfWkVHHO/4Ob9+MjCYer4Vnb+Xx23nHO3h+nTxeF4/XzeMxeDwmj8fm8QieneDxSd5xLs+vl8f7xON9"
    "4vE+83h9PF4/jzfA4w3weIM83hce7yuP943H+8bjDfF433m8YR5PwOCHXcDgB1/A4B+HFwka/PATNPhBE+LxhHg8IYMf8wjz"
    "eMI8ngiPJ8LjifB4ojyeKI8nxuOJ8XhiPN4oHm8UjyduYPlLfJ4V2vvlZ3yOouLTZ7HmzwDVEftB+on/boAqLvq3QlRyrcFg"
    "0Ow/fJGV8eXWEoedGGvkWpIf5AKNs8tN7qZTATnYP/PmqEpcYlj7Pa6uxLuUVwsezq7HjMoi1oHaeqia2LQvVW9AePfaAd9J"
    "TaApJ0v0kE0wm3AuKUnmA9JC43YHTWlBnGpCbl98C3qPGSo0322B8EP908Mtrahaq5nY5taG9nP6q+Rj2jCm8XjqVd92WExb"
    "XlYz1A6dZBGdgYUdeB7fLP61tgNP1MRjJbfR8GpqidaaWzR8qPvCtlDoRNyevpaInE6UOVas9Bag44Rtj0sv6HjWNl2CoNEx"
    "NnrAfLJOF4zXxRdqrenCzTPJvnu/dOHJtTcfEzZ043aYKttrRTdEChLfFrG7YW14NMFrcw9KGxeX75vdA81rUflLq3twNybk"
    "UpQZA9v8ZvgHDvQgwPlyiHsGA1LeBcXmc5io9RDZ6vqQgfV2g0+f7mXCfHnk/VF9TOTn1Av1b2Pi9WKFzB1aLMSKS1nNu8eC"
    "tMNc5mlpFnQuRjakdLBQY9q387Q7G9Jxx+Qqr7MQ9rD3xtTjbDR20Sa/GM1BqXlpsZ86G51yattypnFwO9rz7odrHKQ6rG1Z"
    "e4uN4OkPP4ulcbAhnxyVMpnA1zNWQa5TONhPq2zdJ0sgvOyIc40Dgcc2FRdNQzkIv7XMVHstgYDTk2/ZJRIwytxQfL2eg+JX"
    "V7Z0HiEQeOT7F9k6AjVDNgER4wmsPn7E89x9Av5nlczTR5MIVX/oNLiIQKqHOHa0EsjWrCWX6JOIGoxeqWlJYLgtq2KfOInc"
    "qAblDT4kykQKdCd7EIjZQNfonktC1T2xpzmBRHpEmMy9vQTqvVN9u4xJrPnTduW+RyRSyzOfdFHnkfdBiWu9hYSis4fCmmYS"
    "zoURkXciCTR0RE/y2UNiZrzSd7HvJBq4HQdFowjMGTPXxCacxOo73Mvtk7hgTy8VZ4ZT9toDE5Spzxvnc8c/RJ2L8NYrxMZQ"
    "AusGt9y+fpHEJJuBQQNDyt5XnrTMl8C4pvG9tCskAuI1853WcXFib9iHi/YEju5iNE27SuJ7nzLtwGYuLLJGv/VaTuCh1Jkp"
    "JDXPSnfpocVuXFyf1y+5X4nAtl0eniHU5z6KiHsh4MmF29mlo673cZDTNtapmTrPC1qNM9wo+1YlN2+PJA6WHh/SC6Ouy0c9"
    "JusrNc/clB5ScCkHohKJbV9dSFyrvXV5giMXy9Ywbg2UsHF/XXLe6dUkwq2iQtev58LrpkJziikboRHhXefnkNCLbcyQXMlF"
    "cuGFiBcFLEy5UHYiV4RElYieSM1CLg5Fmyulz2QhV3KoJL2R+h4b51h2TeXi5aYPFh5BTCwwGo54lkHAxuBN3AchLppuBhXl"
    "PWPAekyDDmMfgRwhh4SBDhKx9bpBB6h9YfTXFKmLBgQ4p5dN2VVIQurz4d3xU3vwdqWLUbAgAfaYc0GiiSSyFY+H6qt3o1zM"
    "2CtsDwfbrUOjfH1JdFjdzd76Zxeir+3Kt2lm4z2z2OKIARUvxKGQl/J05KUGpjbosPH5g4meCRWHjmG9j+JbaQhvuhSw7RAL"
    "to9aH6tUEiBKrdOCjlLC6FYzjpXPRGDJtKkXYwncXD+p34Jsg/f7NXGL2xjwlyqTsF1D4K8DMwxeybUi7nzmwHBvD+S1opft"
    "ESLQuzsl0uGvD1A79NBHjNON16KN03a7chCVZDMst+cdjAsN4kQru1C08Ixt/33233azRKvJn07TMT/zRnT5V9bfdnFmxN3V"
    "ep0oKJrqXaH5T3vzntaPxwo6oG8vLjPGgfm3vSEma0bN+HZEFhVNWxvAwK+CY+vl9+kXwVmo9Z8qOD8rIueosnzG5K0oX6Hb"
    "vChMY9ko1ft+ZFIFMj+yg3X7KyDoFxdm9K4C08pkxYUt61Gvf7O5rroejsc/51/8qx75p1aKMB2bEHWqyzautwmT3lRPzytp"
    "Qs6Vuyl7V7ZAy5mrX5rQgq87IVoX0QJ5jQHfTKk2BMXbLQ/b2gZD9Up9Edc2XD1akLAyuR2acisExwh0wFT/lYGJUAcuCBfE"
    "Hh9DQ1nzOLW2HTQkLzmvti6QhvnL9l6qs+rErU8T/5DP78RmhbGCdi87sXLKrgPPg+g4aT3RS7WHDiNzpQzTQTpyigiERnZB"
    "d9Bhrr1AN2JT9KyOjO8GQ+VkAXmkG223zEXOC/TgYtqbe6VyPfh+/dxWTe8evJ/z3HoPqwer7YXvmYoyMFvDp0BFn4HR5Sl9"
    "D0oYKN4z/rtUOwPCXbefbRhmYPPl9wzheCbu0SYJF99mQtfvkgf9DhNrroqsjbRkQVI6Zv6xnSys9JDsrLBhoVSQXOw1zIK5"
    "Q4HMA0U2TqfG3jzCYuGC7eF9QVfYsDq4tr2uiI3csrQlT/ayIUskeJtpcqAeMzP1hT0HdQ4JEav62bimF3nDMZeDVVGWBuo0"
    "Di4KL98k48WB1tKbjaYKBL6v0No7fyEB5TNTzOvfcLCjZ2EWaz2BygvahVk+BCrkDBXqZAj0TIw+/SKCSiSGMrvSLhHoD5ou"
    "vV+bwAenK8lVjwhYxe3vv1lGwMw2oOLCRgImeo+/93cT0H16XiF9kIDsDMuiQD8C3S7zLUzHkyjfFJ6mq0QlEi57Ju04gYhe"
    "o5Myi0nYFby7brSSxFe12oG2MxTffOy30zYk5ocxJWzdSVim6/eevUolcrlzekFUIhK6jfzBMCpRLcte9fUGJThCuZ+0j5P4"
    "JnesfPsFEkcex8SIpxI4ucLkcRZVOe/Y52TEvk3itcUTidfUPL15teIvb1ACqPvI5hGVCJN0Y8bMOkvAZ5aHCvcOiVNlYudV"
    "K0mU+Dl1yVMCtfRhq1hIzkjCVgt53UhiZ3ZMuTd1XWq1GzmKeSRqz+YGD7aRWLK+WlafWocxbvnCyx+QEJ2qYK7dSaKo09DX"
    "djGBOyqHPppmkfCvPJlWSyMhIOq98IEUleBklwS2JlP+DvMR3UoikDnUaveSg8Qhz7OK8ZSAzNu5w+sdicQ6BdGFLhwclAya"
    "/jWUxKJlWTOWvSXR/qb1XDabDf/QQUkVDxLBerc8pB9TQuI9N39gGxvDcz6v6jWh5hVb0VqZSuJ6Utiuo+9ZcKciNl6FxFEt"
    "0sP6JAnmvt6w0UtY2NV4/sY5ARJ7gmlxvrtJrHsxkNJ5jAlD03hGWg1VcBTsUZ9pRVIF0RiPGU8ZED8qOO5UMgGa8OuWRfNJ"
    "HE8NsFtI64Gq2Q3Li9sJrJBdtKiLmk8r71MSPnVT6+6iN52Kv+d2zrRYShDW17WWqjC6MLDA4IVvKwdKynu9fC4SkDqcFlJT"
    "TEfQe/VXG604oB8qKcrYQhUA45qTxY9T+7uV0L2Qw8alq4ZRypSgT3pzeva42TSIG5SonpZiI+nis4bKOxx0204drElqR4d5"
    "cevgJhZI+qml62U5KFv9SKK/uxW3dScNSp1igrmZoTXPi43Z+VotqqIt2L+lKUjoEQPPZCOtrbNYuCa8sv5UbSOEq/ur3St7"
    "EB7ZM7CbxkTqBt9V5lfe4fibuJcJld2oKL8ZNVrin3ar+3YLtfO6UKb1bOP2yYy/7epXu/3jDtPRaN/aXT6p52/7Qc/vyjZq"
    "nUj6tpLdItT9t/1LeCH9WDolRBUT6xXr6L8JjqvrIdpPwRlDCU6g+7ZALxctjf901ZG7+fHB9PdbAJM1ca5mjoj8bup4TqwK"
    "u5fc2WzYWwYT8dLN7mcrkPpSeprLmncoZlV6yhXUYvpcb+VSi3qU2L8Y6/zkI05r6BzaEPAexlsevza1a0JscIy0QiL17a7b"
    "MuuR3Ucwox4IaBi2wGZH6GeV4+0w3HQuen9jC16OreWIjW2Di7y8t7w2DTZhO02MN7WhI8/H4PrVdpy547toQm4n3Pu/BLAz"
    "2vFSkwxXHkfD+DtuW0NkuyB4pYvUpnWg9O1A8eFNnZDPyFUesuyGTOZ5Q0OhTlgPHuMcOEaH04VxUkF+PWh3au9Sl6BD60Yh"
    "zT+xC732IcqWBxiosOtiVn6jgzCNfux1sRsuCzZzZu9iIrlEPtunuQsBr4lJJZFU+zNTsjDHiiqnHIVDN9zthpKiysN3ngyE"
    "7e3fKT6DKi9HnTQ/sacHEm8mMIW0mbhVP3qdbjsbQU5yk5+rM3CzpLWhhGp/Ui1kYz/Ec3BhLitzfxOlYhaxwy1pLOwf3lg0"
    "bypVTu9NOfglmIk4M3fBc5ZsPN6/zdWAahO6NKTJSXIsfE/f9a6awcaplJYzSCfQoX7MOfsqC17qqSu2H+DgppLfp6UMKsvL"
    "KqkOzGZDxnqoz5gqM82b5/omzKSy7tY9T+OvsvGx9WnjQVBZ4NLDbcc2UdlGblw5U46DCHfhZBmqjH3W7LlEl8ru257aXF4f"
    "xkFG+7U9szIJ2G+WnlZJZfWX0a55gpTKVc/ZtqbuIwFH7fd1B2pJBBm/EUxXJFAkvkduI1WOWp6Y+tH4M4mFNluydMwIhGT+"
    "lZi8iJpXT/6dtjQXfRNvDc6lsrpW/Jue5o1UlrR+e+X6bC5i1q2VqEkgYHoq4Yr+XhL0ebt69uhwMfFj/ZQ5Dwhsv2A4N5/K"
    "0o/sa8WKqXL+63MjT+1qAjqHO31tM0icZFzsDLPgwtjjib8mi8D1ANkFmyjVUXwqFJVnxcW5TetYtcIkHuc8aD5RTanM0dvn"
    "syn7jIfqXQETScgvd9ZtaaFUz9iqrHUNF2NpArLSVPugNpwr19BDfe47tSKmERdLvq27EatFIub7udSHBInlCq4OytpcHLPT"
    "gTxVpnuHPZxl10vizJHF1yVmcTFu3or8q1R78j1Q0qqTpNqjfhvJseO4mKeZs3uMOYmQ5XRtQRaJ5yl6ape5JHQfMTc8XUPC"
    "KWdN23A7pUoWMcKJVSTVfrS9mEXxl+1Vk95RT8LwWV9iKHXdmj6qEnnU/AKXG/Kki0ncjs3x3HmYxEBwRoQedT6jVK7cK7hL"
    "YsER+gltaxI9mWfup1DnT2xxfmB1nkTOoZKKO3+QaEqanzSbut5Xp2m2lcEktq6q5Mp3ErBOu2GlS63PtdyWBWYOJExklEv9"
    "rxPwEkt5502tpwnD9+FmHeq6DsRK3XSm4nZyESViBBLT9wu1jCNxqTVzZjPVft/hvjg6uopSYfGkcD2qXXYw8xFJPMrBo0la"
    "Dkb3CNDTOcMbqXjbtqh78YoqNkqrrzIdTlHqpN3idSOQgPS+LCNzaTYsBesn1e4gkBw7YNClS1VPG3YVvtJnITx47PRRVNt1"
    "yKzlymoBAukmGc2WRkwon/2wJE2CgLv2GT2NXRyUrI6f7a3BQPrWisjsFKrdr75UIk+1kSbJ916JTBv5WaOtaoIxBx9TMu8p"
    "irMxFDdh3rMJ3fBY8se4XQ1snK1Nza+tovaf88HjR4W6QGSfd61YzsZm2XUlgmBhtFd32dfKTrilh8dOiWYhsDXMc/xuJjS4"
    "24wOb6ZU03X4ucRHJvTpE6fNj2LAVsDKusG+HYLC+Z6P5zDxgqF15FJMz2+qszChKv+n6oymVMfXb6emhobnf7ro/Bz6MxeK"
    "Fzptxp92cRmtotUIDW20lLasgtOJjDXrjSuxv86/0Sm1Ds6fzc7oyNWBLLaNqQyuhUPqyeiYlY1Il1bgmri+h9bd7SW2NxqQ"
    "o3rkoGRdM5TkLvtoTG7GUMKuPw0lPyDLakOa6dtWnEygLT0e0IrKm5MbMqgW6MPcwDcta6hFHjy778ZwG6z2yU35U64NpM9g"
    "e395B1w2yo2p3tmBCU71ZjpUCeOx/Yx8yYxOvG1Z4DeligYNyeAhz4EOrF5r+yJjIh3pvTO3l5V2QkesSPKzZCe6jg0JxUt3"
    "IeP5580Lquhg1nwWe9PZiSXqiR3BFt0483JljPiXLlwqZuXZf6BDL39R7UTtHgxP/5Rty6BEaHp8WJpMN5iCqp+DrzCwSdUw"
    "JMeKgSmnxwaMlHKLa9tEmvtZ0EiOq5EvZ6GzOt8ufwMDfzhPzHkzyEHwOLXvo0o4OBUTyrl+hgXV6GVXblMlXMzO1lcCxgQs"
    "qgYXZh7mgLZnbc1TKwK1A4VaZVSpbGo9M3fjnwQKH0vfc9anSvyvz44sVyaw1d4yuPIPgtrUxWprVagka3bVoWUMleRTd9Cv"
    "Ueh//8J6X2kCk48OztvL4mBYqnz+DZIDt8vltxop7JlYtTrwCQfsB5su76DOa59Lc9n0ZxwsLZ1FL43hYIb+OV/xJA46K5Je"
    "HoumSm01r/1ujhwIGzbZE9Qm3WElJnPZjoMJQbt3r5xHzb/khF+0EQeuCgqWxTM5SF//2tm1jw2Dyg+cY5SIWS2TOWHFYkOi"
    "+lPm6SfUZp6cGTHYwUaaUdotPGAj61H5hlmRbOyfeTds+V1qE4cUG29JY8NokVOJSgobE7ke0rkhbCw5m5GgQ7DxpXDzyTRq"
    "vnzSJynXmo2wP8T3KFBJgRGndPP7IiqJ6M02atnORnnTjCOx8zn4o9PsZHMvG1uiRVd43GejIltm3vl4NtZdE3RabciG5GRO"
    "udIgG0s3TSsMf8hC9Ob+/gADFkRzZpQavGYju3zvnQeVTOQePOMvZ8pE9XrF68PL2HArFN20VpkBRbWErMGtPZi+zLkzsJQJ"
    "6SO0R3jeBcdl3ubyY7sw/rJRyPKhDsguah0scevEuhORt5X1abgtkdn/aW4NdjDEYiTlO7EjeukNpSmNsAp+/LHPpg9RTdKu"
    "kTWd+C50/eQrq0pMfVSMsxXCBk3d91Jq3ehYnCfIzptRCTVkexktFzVIjp9DZ8nT0O/91sLEsALvjY+2xDwTMog0TLLWX9gK"
    "kcdyCZPtShARRpspKChgcFbI19XWsRGRc/arZeoVoD2wzMlq3iDabzk+k/Z8j2wnlVNJUenQOO658/ILDiweqY1Pffvu580P"
    "gaqC+3/tnJuDTxFu2Qs1/mn/OVo4n6uEjjXw2R09AqYh6xmf/eHtDLm3wmV89v8fP8avomP/NK39p+iIU6Lj7+e19z9Vcdq5"
    "TLsAs3v4nyJj1fOLE98/40O32Ffr+xTL+fDpumcuhHwdH/putz9fEtLEh09q+3MOubXy4ZSM+uBDQR18mHVQ6NC0o3Q+zJ8Z"
    "OfFrWA8fJrktdazyY/Ghqn5V0VmFdj5M2XdG+g7VDvyO9hKJ98VoXD68ZVZk8bTsEz9qwT/x5DAffnas3youJGzwO76ewvmm"
    "t0qID+1lovb1GQzid3TzjflWKNfEhz9v1/6O+1Kuyy82EjD4HQvHbsy9sE6ED10zCXVja36kP+k/CrogH35o9de7OHsIv2PB"
    "utnzJ6t+5UNzvxnHQ+Z+48OTQeYCvaJDfOhofO+zzU5+LPKXWl0hw49H30nNHhj8yodBaQvydm3+wode78M5NlcH+HAw6kZw"
    "H7ePD/2gvdid/YkPtXxmuZAaXD6s1ozY8YmqHH5Hxw3DSmLyXXzYm09fXKNaxYf/n3v/ryqOoJCa8K8PuIw8wjLyEvsX3kHB"
    "kf8/Hnf53WfkoYMRHRp5jfrF5zI1C+8RhN+dRm4c/fdOMhICP28j/e408uPfT6cxvzgdkhL45afA3z1HGrifnqN/8RyQE/jX"
    "du53xxER/uko/ovj9qkCf0uypZnoP1ZLjPpbTS1Vs/LIu/8C6kzgzg==")
_P = np.load(io.BytesIO(zlib.decompress(base64.b64decode(_PERFILES_B64))))
GD = _P['gD']

PRESETS = {
    'k64':      dict(rms=10, grano_um=11.0, corr=0.35, croma=0.45),
    'k25':      dict(rms=9,  grano_um=10.0, corr=0.35, croma=0.45),
    'velvia50': dict(rms=9,  grano_um=10.0, corr=0.35, croma=0.45),
    'pro400h':  dict(rms=4,  grano_um=12.0, corr=0.35, croma=0.45),
    'trix':     dict(rms=17, grano_um=14.0, corr=1.0, croma=1.0),
}


def srgb_eotf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_oetf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def gauss_blur(x, sigma):
    if sigma <= 0.01:
        return x
    h, w = x.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    H = np.exp(-2 * (np.pi * sigma) ** 2 * (fy ** 2 + fx ** 2))
    return np.fft.irfft2(np.fft.rfft2(x) * H, s=(h, w))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada')
    ap.add_argument('salida')
    ap.add_argument('--pelicula', choices=list(PRESETS) + ['generico'],
                    default='generico',
                    help='usa el perfil sigma(D) y los valores del material')
    ap.add_argument('--rms', type=float, default=None,
                    help='granularidad rms del datasheet (anula el preset)')
    ap.add_argument('--grano-um', type=float, default=None,
                    help='diametro caracteristico del grano en micras')
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

    pre = PRESETS.get(a.pelicula, dict(rms=10, grano_um=11.0, corr=0.35, croma=0.45))
    rms = a.rms if a.rms is not None else pre['rms']
    gum = a.grano_um if a.grano_um is not None else pre['grano_um']
    corr = a.correlacion if a.correlacion is not None else pre['corr']
    croma = a.croma if a.croma is not None else pre['croma']

    im = Image.open(a.entrada)
    arr = np.asarray(im.convert('RGB')).astype(np.float64)
    escala = 65535.0 if arr.max() > 255 else 255.0
    rgb = arr / escala
    h, w, _ = rgb.shape

    pitch_um = 36000.0 / max(h, w)
    A48 = np.pi * 24.0 ** 2
    sigma_D1 = (rms / 1000.0) * np.sqrt(A48 / pitch_um ** 2)

    lin = srgb_eotf(rgb)
    D = -np.log10(np.clip(lin, 10 ** (-a.dmax_vis), 1.0))

    rng = np.random.default_rng(a.semilla)
    comun = rng.standard_normal((h, w))
    sigma_px = max(0.35, (gum / pitch_um) / 2.355)
    campos = []
    for _ in range(3):
        propio = rng.standard_normal((h, w))
        n = np.sqrt(corr) * comun + np.sqrt(max(0.0, 1 - corr)) * propio
        n = gauss_blur(n, sigma_px)
        campos.append(n / max(n.std(), 1e-9))
    ruido = np.stack(campos, -1)

    if a.pelicula != 'generico':
        T = _P[a.pelicula]
        rel = np.stack([np.interp(D[..., c], GD, T[:, c]) for c in range(3)], -1)
    else:
        rel = np.sqrt(np.clip(D, 0.0, None))
    sig = sigma_D1 * rel * a.intensidad

    # descomponer el ruido de densidad en luminancia y croma: la calibracion
    # rms del datasheet es de densidad visual, asi que se conserva integra en
    # la componente de luminancia y el croma se escala aparte
    dn = ruido * sig
    WV = np.array([0.2126, 0.7152, 0.0722])
    lum = (dn * WV).sum(-1, keepdims=True)
    dn = lum + croma * (dn - lum)
    Dg = np.clip(D + dn, 0.0, a.dmax_vis)
    out = srgb_oetf(10.0 ** (-Dg))
    res = np.clip(out * escala + 0.5, 0, escala).astype(
        np.uint16 if escala > 255 else np.uint8)
    Image.fromarray(res).save(
        a.salida, quality=95 if a.salida.lower().endswith(('.jpg', '.jpeg')) else None)
    print('grano ' + a.pelicula + ': rms=' + str(rms) + '  pitch=' +
          str(round(pitch_um, 2)) + ' um  sigma(D=1)=' +
          str(round(sigma_D1 * a.intensidad, 4)) + '  grano=' + str(gum) + ' um  croma=' + str(croma))


if __name__ == '__main__':
    main()
