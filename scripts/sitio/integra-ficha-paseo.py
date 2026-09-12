#!/usr/bin/env python3
"""Integra una ficha del paseo tal cual la exporta el autor: enlaces a la portada de la
sección, favicon e icono táctil, metas og/twitter y el nombre que las otras fichas tienen
dentro de paseos/. Reaplicable sobre cada versión nueva; avisa de lo que ya estaba puesto."""
import io,os,re,sys
FAV=('<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2F'
     'www.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2064%2064%27%3E%3Crect%20width%3D%2764%27%20height%3D%2764%27%20'
     'fill%3D%27%23000%27%2F%3E%3Ccircle%20cx%3D%2732%27%20cy%3D%2732%27%20r%3D%2726%27%20fill%3D%27none%27%20'
     'stroke%3D%27%23767676%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M32%206A26%2026%200%200%201%2032%2058'
     'A12.2%2026%200%200%201%2032%206Z%27%20fill%3D%27%23fff%27%2F%3E%3Cpath%20d%3D%27M32%2058A12.2%2026%200%200%201%20'
     '32%206%27%20fill%3D%27none%27%20stroke%3D%27%23d9574e%27%20stroke-width%3D%272%27%2F%3E%3C%2Fsvg%3E">\n'
     '<link rel="apple-touch-icon" href="../icons/paseos-180.png">')
def nombre_en_la_seccion(href):
    """El autor exporta «tema_ficha_N.html»; dentro de paseos/ la ficha se llama «tema-con-guiones.html»."""
    m=re.match(r"^(.+?)_ficha_\d+\.html$",href)
    return m.group(1).replace("_","-")+".html" if m else None

def integra(src,dest):
    s=io.open(src,encoding="utf-8").read(); hechos=[]; ya=[]
    base=os.path.basename(dest)
    if 'rel="icon"' not in s:
        s=s.replace('<meta name="referrer" content="no-referrer">','<meta name="referrer" content="no-referrer">\n'+FAV,1); hechos.append("favicon + icono táctil")
    else: ya.append("favicon")
    if "og:url" not in s:
        m=re.search(r'<meta property="og:description"[^>]*>',s); assert m,"falta og:description"
        s=s[:m.end()]+('\n<meta property="og:url" content="https://falevian.github.io/Photographers/paseos/%s">'%base)+\
          '\n<meta property="og:image" content="https://falevian.github.io/Photographers/og/paseos.png">'+\
          '\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">'+\
          '\n<meta name="twitter:card" content="summary_large_image">'+s[m.end():]; hechos.append("og:url/og:image/twitter")
    else: ya.append("og")
    m=re.search(r'<p class="hero-top"><span>([^<]*)</span>',s)
    if m: s=s[:m.start()]+'<p class="hero-top"><a href="./">%s</a>'%m.group(1)+s[m.end():]; hechos.append("cabecera enlaza a la portada")
    else: ya.append("cabecera")
    for viejo in sorted(set(re.findall(r'href="([^"/:#][^"]*_ficha_\d+\.html)"',s))):
        nuevo=nombre_en_la_seccion(viejo)
        if not nuevo or nuevo==base: continue
        s=s.replace('href="%s"'%viejo,'href="%s"'%nuevo)
        falta="" if os.path.exists(os.path.join(os.path.dirname(dest) or ".",nuevo)) else "  (¡ojo! esa ficha aún no está en la sección)"
        hechos.append("%s → %s%s"%(viejo,nuevo,falta))
    if "Todas las fichas del paseo" not in s:
        a='<div class="share-row">'; assert s.count(a)==1,"no encuentro share-row"
        s=s.replace(a,'<p><a href="./">Todas las fichas del paseo</a></p>\n'+a); hechos.append("pie enlaza a la portada")
    else: ya.append("enlace del pie")
    io.open(dest,"w",encoding="utf-8").write(s)
    print("%s · %d KB\n  aplicado: %s%s"%(dest,len(s.encode())//1024,"; ".join(hechos) or "nada",
          "\n  ya venía: "+"; ".join(ya) if ya else ""))
    return len(s.encode())//1024

if __name__=="__main__": integra(sys.argv[1],sys.argv[2])
