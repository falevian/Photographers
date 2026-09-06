# -*- coding: utf-8 -*-
"""Fusiona varias páginas del repositorio en una sola con pestañas.
Cada fuente conserva su CSS (aislado bajo .part-<clave>), su HTML y su JS;
solo se renombran los ids que colisionan entre partes y se encadenan los
manejadores de idioma. Uso: merge.py <spec.json>"""
import io,re,os,sys,json,collections,urllib.parse

def scope_css(css, cls):
    """Prefija cada selector con .cls; :root/html/body pasan a ser .cls; quita reglas de langbar y de idioma global."""
    css=re.sub(r"/\*.*?\*/","",css,flags=re.S)
    out=[]; i=0; n=len(css)
    def scope_sel(sel):
        sel=sel.strip()
        if not sel: return None
        if sel in (":root","html","body","html,body","body,html"): return "."+cls
        if sel.startswith(".langbar"): return None
        if sel.startswith("html[lang"): return None
        if re.match(r'^(html|body)\s*[ >]',sel): return "."+cls+" "+re.sub(r'^(html|body)\s*','',sel,count=1)
        return "."+cls+" "+sel
    while i<n:
        m=re.compile(r'[^{}]*?\{').match(css,i)
        if not m:
            break
        head=m.group(0)[:-1]; j=m.end()
        if head.strip().startswith("@"):
            # bloque anidado (media, keyframes, font-face)
            depth=1; k=j
            while k<n and depth>0:
                if css[k]=="{": depth+=1
                elif css[k]=="}": depth-=1
                k+=1
            inner=css[j:k-1]
            name=head.strip()
            if name.startswith("@media") or name.startswith("@supports"):
                out.append(name+"{"+scope_css(inner,cls)+"}")
            else:
                out.append(name+"{"+inner+"}")
            i=k
        else:
            k=css.find("}",j)
            body=css[j:k]
            sels=[scope_sel(s) for s in head.split(",")]
            sels=[s for s in sels if s]
            if sels: out.append(",".join(sels)+"{"+body+"}")
            i=k+1
    return "\n".join(out)

def extract(path):
    s=io.open(path,encoding="utf-8").read()
    css="\n".join(re.findall(r'<style[^>]*>(.*?)</style>',s,re.S))
    scripts=[m.group(1) for m in re.finditer(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',s,re.S)]
    ext=[m.group(0) for m in re.finditer(r'<script[^>]*src="[^"]+"[^>]*></script>',s)]
    pre=[x for x in scripts if "Fija el idioma" in x]
    sw=[x for x in scripts if "conmutador de idioma" in x]
    main=[x for x in scripts if x not in pre and x not in sw]
    body=re.search(r'<body[^>]*>(.*)</body>',s,re.S).group(1)
    body=re.sub(r'<script.*?</script>','',body,flags=re.S)
    body=re.sub(r'<div class="langbar".*?data-setlang="en"[^>]*>EN</button>\s*</div>','',body,flags=re.S)
    fonts=re.findall(r'<link href="(https://fonts\.googleapis\.com/css2\?[^"]+)"',s)
    return dict(css=css,body=body,js=main,ext=ext,fonts=fonts,raw=s)

def ids_of(html): return set(re.findall(r'\sid="([^"\$]+)"',html))

def prefix_ids(part, ids, pfx):
    """Renombra los ids dados en HTML, CSS y JS de la parte."""
    b,c,js=part["body"],part["css"],part["js"]
    for x in sorted(ids,key=len,reverse=True):
        nx=pfx+x
        b=re.sub(r'(\sid=")'+re.escape(x)+r'(")',r'\g<1>'+nx+r'\2',b)
        b=re.sub(r'(\sfor=")'+re.escape(x)+r'(")',r'\g<1>'+nx+r'\2',b)
        b=re.sub(r'(href="#)'+re.escape(x)+r'(")',r'\g<1>'+nx+r'\2',b)
        c=re.sub(r'#'+re.escape(x)+r'(?![\w-])','#'+nx,c)
        js=[re.sub(r'(["\'])'+re.escape(x)+r'\1',r'\g<1>'+nx+r'\1',j) for j in js]
        js=[re.sub(r'(["\']#)'+re.escape(x)+r'(["\' ])',r'\g<1>'+nx+r'\2',j) for j in js]
        js=[j.replace('id="'+x+'"','id="'+nx+'"') for j in js]
    part["body"],part["css"],part["js"]=b,c,js

def build(spec):
    parts=[]
    for p in spec["parts"]:
        e=extract(p["file"]); e.update(p); parts.append(e)
    # colisiones de ids entre partes
    seen=collections.Counter()
    for e in parts:
        for x in ids_of(e["body"]): seen[x]+=1
    for e in parts:
        coll={x for x in ids_of(e["body"]) if seen[x]>1}|set(e.get("forceprefix",[]))
        if e.get("base"): coll-= set(e.get("keep",[]))  # la base conserva los suyos salvo que se pida
        if e.get("base"): coll=set(e.get("forceprefix",[]))
        if coll: prefix_ids(e,coll,e["key"]+"-")
        e["css_scoped"]=scope_css(e["css"],"part-"+e["key"])
        # enlaces internos a otras partes / páginas fusionadas
        for a,b in spec.get("linkmap",{}).items(): e["body"]=e["body"].replace('href="'+a+'"','href="'+b+'"')
        # manejador de idioma propio
        e["js"]=[j.replace("window.onLangChange","window.onLangChange_"+e["key"]) for j in e["js"]]
        # el JS de ámbito global se envuelve para no chocar con otras partes
        e["js"]=[j if re.match(r'\s*\(function\(\)',j) else "(function(){\n"+j+"\n})();" for j in e["js"]]
        for a,b in e.get("jsfix",[]):
            n=sum(j.count(a) for j in e["js"]); assert n>=1,(e["key"],a[:60])
            e["js"]=[j.replace(a,b) for j in e["js"]]
        for a,b in e.get("htmlfix",[]):
            assert e["body"].count(a)>=1,(e["key"],a[:60]); e["body"]=e["body"].replace(a,b)
    fonts=[];
    for e in parts:
        for f in e["fonts"]:
            if f not in fonts: fonts.append(f)
    ext=[]
    for e in parts:
        for x in e["ext"]:
            if x not in ext: ext.append(x)
    BASE="https://falevian.github.io/Photographers/"
    svg=io.open(spec["icon_svg"],encoding="utf-8").read().strip()
    fav='<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,'+urllib.parse.quote(svg)+'">'
    tabs_btn="".join(f'<button type="button" role="tab" data-tab="{t["id"]}" aria-selected="false"><span data-lang="es">{t["es"]}</span><span data-lang="en">{t["en"]}</span></button>' for t in spec["tabs"])
    sections=""
    for t in spec["tabs"]:
        inner=""
        for blk in t["blocks"]:
            e=next(p for p in parts if p["key"]==blk["part"])
            html=e["body"]
            if blk.get("section"):
                m=re.search(r'<section id="'+blk["section"]+r'".*?</section>',html,re.S); assert m,(blk,)
                html=m.group(0)
                if blk.get("remove_from_part"):
                    e["body"]=e["body"].replace(m.group(0),"")
            if blk.get("strip_sections"):
                for sid in blk["strip_sections"]:
                    html=re.sub(r'<section id="'+sid+r'".*?</section>\s*','',html,flags=re.S)
            inner+=f'<div class="part-{e["key"]}">{html}</div>\n'
        sections+=f'<section class="tab" id="tab-{t["id"]}" role="tabpanel" hidden>\n{inner}</section>\n'
    # las secciones se rellenan en orden de pestaña; si una pestaña extrae una sección de una parte
    # que también se muestra entera en otra pestaña, hay que extraer primero: se resuelve construyendo dos veces
    css_all="\n".join(e["css_scoped"] for e in parts)
    js_all="\n".join("\n".join(e["js"]) for e in parts)
    hooks=" ".join(f'if(window.onLangChange_{e["key"]}) window.onLangChange_{e["key"]}(l);' for e in parts)
    out=f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{spec["title_es"]}</title>
<meta name="author" content="Rafael Vida">
<meta name="description" content="{spec["desc_es"]}">
{fav}
<link rel="apple-touch-icon" href="{spec["touch"]}">
<meta name="theme-color" content="{spec["theme"]}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{spec["apptitle"]}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Photographers">
<meta property="og:title" content="{spec["title_es"]}">
<meta property="og:description" content="{spec["desc_es"]}">
<meta property="og:url" content="{BASE}{spec["out"]}">
<meta property="og:image" content="{BASE}{spec["og"]}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="es_ES">
<meta property="og:locale:alternate" content="en_GB">
<meta name="twitter:card" content="summary_large_image">
<script>
/* Fija el idioma antes de pintar, para que no parpadeen los dos a la vez. */
(function(){{
  var K="pn-lang", u=null;
  try{{ u=new URLSearchParams(location.search).get("lang"); }}catch(e){{}}
  if(u!=="es"&&u!=="en"){{ try{{ u=localStorage.getItem(K); }}catch(e){{ u=null; }} }}
  if(u!=="es"&&u!=="en"){{ u=/^es/i.test(navigator.language||"") ? "es" : "en"; }}
  document.documentElement.lang=u;
}})();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
{"".join('<link href="'+f+'" rel="stylesheet">' for f in fonts)}
{"".join(ext)}
<style>
/* ---------- cáscara de pestañas ---------- */
:root{{--sh-bg:{spec["theme"]};--sh-ink:#1B1D1B;--sh-muted:#5F6662;--sh-rule:#D3D8D2;--sh-acc:{spec["accent"]};}}
*{{box-sizing:border-box}}
html{{background:var(--sh-bg)}}
body{{margin:0;background:var(--sh-bg);color:var(--sh-ink);font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif}}
.shell-head{{max-width:1080px;margin:0 auto;padding:52px 20px 10px}}
.shell-head h1{{font-family:"Fraunces","Iowan Old Style",Georgia,serif;font-weight:600;font-size:clamp(28px,4.6vw,44px);line-height:1.1;margin:0 0 10px;letter-spacing:-.01em}}
.shell-head p{{max-width:68ch;margin:0;color:var(--sh-muted);font-size:16px;line-height:1.5}}
.tabs{{position:sticky;top:0;z-index:20;background:var(--sh-bg);border-bottom:1px solid var(--sh-rule)}}
.tabs .in{{max-width:1080px;margin:0 auto;padding:0 20px;display:flex;gap:4px;overflow-x:auto;-webkit-overflow-scrolling:touch}}
.tabs button{{font:inherit;font-size:14px;background:transparent;border:0;border-bottom:3px solid transparent;padding:12px 12px 10px;color:var(--sh-muted);cursor:pointer;white-space:nowrap}}
.tabs button:hover{{color:var(--sh-ink)}}
.tabs button[aria-selected="true"]{{color:var(--sh-ink);border-bottom-color:var(--sh-acc);font-weight:600}}
.tabs button:focus-visible{{outline:2px solid var(--sh-acc);outline-offset:-2px}}
.tab[hidden]{{display:block!important;position:absolute;left:0;right:0;visibility:hidden;height:0;overflow:hidden;pointer-events:none}}
.tab{{position:relative}}
[class^="part-"]{{padding-top:1px}}
[class^="part-"] header{{padding-top:20px}}
.shell-foot{{max-width:1080px;margin:0 auto;padding:20px 20px 60px;font-size:13px;color:var(--sh-muted)}}
.shell-foot a{{color:inherit}}
/* ---------- convenio bilingüe ---------- */
html[lang="es"] [data-lang="en"]{{display:none!important}}
html[lang="en"] [data-lang="es"]{{display:none!important}}
.langbar{{position:fixed;top:12px;right:14px;z-index:50;display:flex;background:rgba(255,255,255,.94);border:1px solid var(--sh-rule);border-radius:6px;overflow:hidden;backdrop-filter:blur(6px)}}
.langbar button{{font:inherit;font-size:12px;letter-spacing:.08em;background:transparent;border:0;color:var(--sh-muted);padding:7px 11px;cursor:pointer}}
.langbar button+button{{border-left:1px solid var(--sh-rule)}}
.langbar button:hover{{color:var(--sh-ink)}}
.langbar button.on{{background:var(--sh-ink);color:#fff}}
.langbar a.home{{display:flex;align-items:center;padding:0 9px;color:var(--sh-muted);border-right:1px solid var(--sh-rule)}}
.langbar a.home:hover{{color:var(--sh-ink)}}
.langbar a.home svg{{width:12px;height:12px;display:block}}
@media print{{.langbar,.tabs{{display:none!important}} .tab[hidden]{{position:static;visibility:visible;height:auto}}}}
/* ---------- estilos de cada parte, aislados ---------- */
{css_all}
</style>
</head>
<body>
<div class="langbar" role="group" aria-label="Idioma / Language">
  <a class="home" href="index.html" title="Portada / Home" aria-label="Portada / Home"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 7.5 8 2.5l5.5 5v6h-4v-4h-3v4h-4z"/></svg></a>
  <button type="button" data-setlang="es" aria-pressed="true">ES</button>
  <button type="button" data-setlang="en" aria-pressed="false">EN</button>
</div>
<div class="shell-head">
  <h1 data-lang="es">{spec["h1_es"]}</h1>
  <h1 data-lang="en">{spec["h1_en"]}</h1>
  <p data-lang="es">{spec["lead_es"]}</p>
  <p data-lang="en">{spec["lead_en"]}</p>
</div>
<nav class="tabs" aria-label="Pestañas" data-aria-es="Pestañas" data-aria-en="Tabs"><div class="in" role="tablist">{tabs_btn}</div></nav>
{sections}
<div class="shell-foot">
  <span data-lang="es">{spec["foot_es"]}</span>
  <span data-lang="en">{spec["foot_en"]}</span>
</div>
<script>
{js_all}
</script>
<script>
/* ---------- pestañas ---------- */
(function(){{
  var btns=[].slice.call(document.querySelectorAll('.tabs button[data-tab]'));
  var ids=btns.map(function(b){{return b.getAttribute('data-tab');}});
  var alias={json.dumps(spec.get("alias",{}))};
  function show(id,push){{
    if(ids.indexOf(id)<0) id=ids[0];
    btns.forEach(function(b){{ b.setAttribute('aria-selected', b.getAttribute('data-tab')===id ? 'true':'false'); }});
    ids.forEach(function(x){{ var s=document.getElementById('tab-'+x); if(s) s.hidden = (x!==id); }});
    if(push){{ try{{ history.replaceState(null,'','#'+id); }}catch(e){{}} }}
    try{{ (window.__sensCharts||[]).forEach(function(c){{ c.resize(); }}); }}catch(e){{}}
    setTimeout(function(){{ window.dispatchEvent(new Event('resize')); }},30);
  }}
  btns.forEach(function(b){{ b.addEventListener('click',function(){{ show(b.getAttribute('data-tab'),true); window.scrollTo({{top:0}}); }}); }});
  function fromHash(){{ var h=(location.hash||'').replace('#',''); if(alias[h]) h=alias[h]; show(h||ids[0],false);
    if(h && !ids.includes(h)) {{ var el=document.getElementById(h); if(el){{ var sec=el.closest('.tab'); if(sec){{ show(sec.id.replace('tab-',''),false); setTimeout(function(){{ el.scrollIntoView(); }},50); }} }} }} }}
  window.addEventListener('hashchange',fromHash);
  // enlaces internos entre pestañas
  document.addEventListener('click',function(ev){{ var a=ev.target.closest('a[href^="#"]'); if(!a) return; var h=a.getAttribute('href').slice(1); if(ids.indexOf(h)>=0){{ ev.preventDefault(); show(h,true); window.scrollTo({{top:0}}); }} else if(alias[h]){{ ev.preventDefault(); show(alias[h],true); window.scrollTo({{top:0}}); }} }});
  fromHash();
}})();
/* ---------- conmutador de idioma / language switch ---------- */
(function(){{
  var KEY="pn-lang";
  var META={{
    es:{{ title:{json.dumps(spec["title_es"],ensure_ascii=False)}, desc:{json.dumps(spec["desc_es"],ensure_ascii=False)} }},
    en:{{ title:{json.dumps(spec["title_en"],ensure_ascii=False)}, desc:{json.dumps(spec["desc_en"],ensure_ascii=False)} }}
  }};
  function apply(l){{
    document.documentElement.lang=l;
    document.title=META[l].title;
    var d=document.querySelector('meta[name="description"]');
    if(d) d.setAttribute("content",META[l].desc);
    [].forEach.call(document.querySelectorAll("[data-aria-"+l+"]"),function(e){{ e.setAttribute("aria-label",e.getAttribute("data-aria-"+l)); }});
    [].forEach.call(document.querySelectorAll("[data-setlang]"),function(b){{
      var on=b.getAttribute("data-setlang")===l;
      b.classList.toggle("on",on);
      b.setAttribute("aria-pressed",on?"true":"false");
    }});
    {hooks}
  }}
  [].forEach.call(document.querySelectorAll("[data-setlang]"),function(b){{
    b.addEventListener("click",function(){{
      var l=b.getAttribute("data-setlang");
      try{{ localStorage.setItem(KEY,l); }}catch(e){{}}
      apply(l);
    }});
  }});
  apply(document.documentElement.lang==="en"?"en":"es");
}})();
</script>
</body>
</html>
'''
    io.open(spec["out"],"w",encoding="utf-8").write(out)
    ids=[i for i,c in collections.Counter(re.findall(r'\sid="([^"\$]+)"',out)).items() if c>1]
    print(spec["out"],"·",round(len(out.encode())/1024),"KB · es/en",out.count('data-lang="es"'),out.count('data-lang="en"'),"· ids dup:",ids)

if __name__=="__main__":
    build(json.load(io.open(sys.argv[1],encoding="utf-8")))
