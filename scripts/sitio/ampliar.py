# -*- coding: utf-8 -*-
"""Añade pestañas a una página ya fusionada, sin regenerarla.

fusionar.py construye una página con pestañas a partir de sus fuentes. Cuando
la página publicada se ha seguido editando a mano, regenerarla perdería esos
cambios. Este script hace lo contrario: toma la página tal como está y le
incorpora partes nuevas con las mismas reglas de fusionar.py (CSS aislado bajo
.part-<clave>, ids que chocan renombrados con el prefijo de la parte, JS
envuelto y manejador de idioma encadenado). Lo ya publicado no se toca salvo
la cáscara: título, descripción, cabecera, pie y barra de pestañas.

Uso, desde la raíz del repositorio:  python3 scripts/sitio/ampliar.py <spec.json>
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusionar as F  # noqa: E402


def build(spec):
    path = spec["into"]
    page = io.open(path, encoding="utf-8").read()
    assert 'id="tab-%s"' % spec["tabs"][0]["id"] not in page, "la página ya tiene esas pestañas"

    def rep(old, new, count=1):
        nonlocal page
        n = page.count(old)
        assert n == count, "%d apariciones (esperaba %d) de %r" % (n, count, old[:80])
        page = page.replace(old, new)

    def sub(pattern, new, count=1):
        nonlocal page
        page, n = re.subn(pattern, lambda m: new, page, flags=re.S)
        assert n == count, "%d coincidencias (esperaba %d) de %r" % (n, count, pattern[:80])

    # ---- partes nuevas, con las reglas de fusionar.py ----
    taken = set(F.ids_of(page))
    parts = []
    for p in spec["parts"]:
        e = F.extract(p["file"])
        e.update(p)
        coll = {x for x in F.ids_of(e["body"]) if x in taken} | set(e.get("forceprefix", []))
        if coll:
            F.prefix_ids(e, coll, e["key"] + "-")
            print("  %s: ids renombrados con %s- → %s" % (e["key"], e["key"], ", ".join(sorted(coll))))
        taken |= set(F.ids_of(e["body"]))
        e["css_scoped"] = F.scope_css(e["css"], "part-" + e["key"])
        for a, b in spec.get("linkmap", {}).items():
            e["body"] = e["body"].replace('href="' + a + '"', 'href="' + b + '"')
        e["js"] = [j.replace("window.onLangChange", "window.onLangChange_" + e["key"]) for j in e["js"]]
        e["js"] = [j if re.match(r"\s*\(function\(\)", j) else "(function(){\n" + j + "\n})();" for j in e["js"]]
        for a, b in e.get("jsfix", []):
            assert sum(j.count(a) for j in e["js"]) >= 1, (e["key"], a[:60])
            e["js"] = [j.replace(a, b) for j in e["js"]]
        for a, b in e.get("htmlfix", []):
            assert e["body"].count(a) >= 1, (e["key"], a[:60])
            e["body"] = e["body"].replace(a, b)
        assert not e["ext"] and not e["fonts"], "la parte trae recursos externos: añádelos a mano a la cabecera"
        parts.append(e)

    # ---- enlaces de la página hacia lo que ahora es interno ----
    for a, b in spec.get("linkmap_page", {}).items():
        rep('href="' + a + '"', 'href="' + b + '"', page.count('href="' + a + '"'))

    # ---- cáscara: título, descripción, cabecera, pie ----
    esc = lambda s: s.replace("&", "&amp;").replace('"', "&quot;")
    sub(r"<title>.*?</title>", "<title>" + spec["title_es"] + "</title>")
    sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + esc(spec["desc_es"]) + '">')
    sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="' + esc(spec["title_es"]) + '">')
    sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="' + esc(spec["desc_es"]) + '">')
    for l in ("es", "en"):
        sub(r"    " + l + r":\{ title:\"(?:[^\"\\]|\\.)*\", desc:\"(?:[^\"\\]|\\.)*\" \}",
            "    %s:{ title:%s, desc:%s }" % (l, json.dumps(spec["title_" + l], ensure_ascii=False), json.dumps(spec["desc_" + l], ensure_ascii=False)))
    sub(r'<div class="shell-head">.*?</div>',
        '<div class="shell-head">\n  <h1 data-lang="es">%s</h1>\n  <h1 data-lang="en">%s</h1>\n  <p data-lang="es">%s</p>\n  <p data-lang="en">%s</p>\n</div>'
        % (spec["h1_es"], spec["h1_en"], spec["lead_es"], spec["lead_en"]))
    sub(r'<div class="shell-foot">.*?</div>',
        '<div class="shell-foot">\n  <span data-lang="es">%s</span>\n  <span data-lang="en">%s</span>\n</div>' % (spec["foot_es"], spec["foot_en"]))

    # ---- barra de pestañas: rótulos nuevos de las existentes y botones de las añadidas ----
    for tid, lab in spec.get("relabel", {}).items():
        sub(r'(<button type="button" role="tab" data-tab="%s" aria-selected="false">)<span data-lang="es">[^<]*</span><span data-lang="en">[^<]*</span>' % re.escape(tid),
            '<button type="button" role="tab" data-tab="%s" aria-selected="false"><span data-lang="es">%s</span><span data-lang="en">%s</span>' % (tid, lab["es"], lab["en"]))
    btns = "".join('<button type="button" role="tab" data-tab="%s" aria-selected="false"><span data-lang="es">%s</span><span data-lang="en">%s</span></button>'
                   % (t["id"], t["es"], t["en"]) for t in spec["tabs"])
    rep("</button></div></nav>", "</button>" + btns + "</div></nav>")

    # ---- secciones, CSS y JS ----
    secs = ""
    for t in spec["tabs"]:
        e = next(p for p in parts if p["key"] == t["part"])
        secs += '<section class="tab" id="tab-%s" role="tabpanel" hidden>\n<div class="part-%s">%s</div>\n</section>\n' % (t["id"], e["key"], e["body"])
    rep('<div class="shell-foot">', secs + '<div class="shell-foot">')
    i = page.index("</style>")
    extra = ("\n" + spec["css_shell"]) if spec.get("css_shell") else ""
    page = page[:i] + "\n".join(e["css_scoped"] for e in parts) + extra + "\n" + page[i:]
    rep("<script>\n/* ---------- pestañas ---------- */",
        "<script>\n" + "\n".join("\n".join(e["js"]) for e in parts) + "\n</script>\n<script>\n/* ---------- pestañas ---------- */")
    hooks = " ".join("if(window.onLangChange_%s) window.onLangChange_%s(l);" % (e["key"], e["key"]) for e in parts)
    m = re.search(r"(?:if\(window\.onLangChange_\w+\) window\.onLangChange_\w+\(l\); ?)+", page)
    assert m, "no encuentro los manejadores de idioma"
    seq = m.group(0).rstrip()
    page = page[:m.start()] + seq + " " + hooks + page[m.start() + len(seq):]

    # ---- un hash con estado de una parte (no es nombre de pestaña) abre la pestaña de esa parte ----
    sh = spec.get("statehash")
    if sh:
        rep("if(alias[h]) h=alias[h]; show(h||ids[0],false);",
            "if(alias[h]) h=alias[h]; else if(h && ids.indexOf(h)<0 && /%s/.test(h)) h=%s; show(h||ids[0],false);" % (sh["re"], json.dumps(sh["tab"])))

    io.open(path, "w", encoding="utf-8").write(page)
    dup = sorted({x for x in re.findall(r'\sid="([^"\$]+)"', page) if page.count(' id="%s"' % x) > 1})
    print(path, "·", round(len(page.encode()) / 1024), "KB · es/en", page.count('data-lang="es"'), page.count('data-lang="en"'), "· ids dup:", dup)
    assert not dup


if __name__ == "__main__":
    build(json.load(io.open(sys.argv[1], encoding="utf-8")))
