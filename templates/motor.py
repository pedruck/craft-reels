"""Motor comum dos templates craft: tema, selo da comunidade, logos, visuais, legenda, cenas,
folha de conferência e validação. Cada template (templates/<nome>/build.py) só define o
layout: onde fica a pessoa, a faixa do visual e o estilo da legenda.

Tudo roda com o Python do kit (kit/.venv/bin/python), chamado pela etapa 7 do craft.
"""
import html
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
KIT = RAIZ / "kit"
sys.path.insert(0, str(KIT))
import reel  # noqa: E402
from reel import Comp, Job, bare, count_js, rich, word_caps  # noqa: E402

CAT_DIR = RAIZ / "catalogo" / "logos"
CAT = {k: v for k, v in json.loads((CAT_DIR / "logos.json").read_text()).items() if not k.startswith("_")}
LOGO_COMUNIDADE = RAIZ / "tema" / "logo-512.png"
PALETAS = json.loads((RAIZ / "tema" / "paletas.json").read_text())

# Posições fixas (quadro 1080x1920). O Instagram cobre ~220 px em cima e ~420 px embaixo:
# selo e logos ficam logo abaixo de 220; título entre eles; nada importante abaixo de 1500.
SELO = dict(left=48, top=232, size=84)
CANTO = dict(right=48, top=232, size=88, gap=104)
TITULO_TOP, TITULO_PX, TITULO_MAX = 246, 72, 780
SAFE_BOTTOM = 1500
# Legenda: SEMPRE embaixo e NUNCA sobre o rosto. Fica logo abaixo do queixo, dentro desta faixa.
LEG_MIN, LEG_MAX = 1330, 1456
PEITO_QUEIXO, PEITO_MARGEM = 1320, 56      # legenda grande no peito: queixo até 1320, texto 56 px abaixo dele


def posicao_legenda(queixo):
    """topo da legenda para um queixo em `queixo` (y no quadro); (topo, cobre_rosto?)"""
    topo = max(LEG_MIN, queixo + 24)
    return min(topo, LEG_MAX), topo > LEG_MAX + 2     # 2 px de folga: arredondamento do enquadramento


def video_cheio(enq, queixo_max=LEG_MAX - 24):  # templates com legenda grande no peito passam queixo_max=PEITO_QUEIXO
    """vídeo no quadro inteiro (bastidores, ranking, historia, destaque). Se o queixo estiver baixo demais para
    a legenda caber embaixo sem cobrir o rosto, sobe o vídeo com um zoom leve (até 1,35x), centrado no rosto.
    Devolve (estilo_css, rosto_no_quadro)."""
    r = dict(enq.get("rosto") or {"olho_y": 900, "cabelo_y": 700, "queixo_y": 1300, "centro_x": 0.5})
    s, ty = 1.0, 0.0
    if r["queixo_y"] > queixo_max:
        s = min(1.35, (1920 - queixo_max) / max(1, 1920 - r["queixo_y"]))
        ty = 1920 - 1920 * s                       # base do vídeo encostada na base do quadro
    tx = min(0.0, max(1080 - 1080 * s, 540 - r["centro_x"] * 1080 * s))
    for k in ("olho_y", "cabelo_y", "queixo_y", "y"):
        if k in r:
            r[k] = r[k] * s + ty
    return f"position:absolute;left:{tx:.0f}px;top:{ty:.0f}px;width:{1080 * s:.0f}px;height:{1920 * s:.0f}px", r


def nu(w):
    w = unicodedata.normalize("NFKD", str(w).lower())
    return "".join(c for c in w if c.isalnum() and not unicodedata.combining(c))


# ------------------------------------------------------------------ tema
def tema(paleta, fundo):
    p = PALETAS["paletas"].get(paleta or PALETAS["padrao"]) or PALETAS["paletas"][PALETAS["padrao"]]
    return p[fundo if fundo in ("claro", "escuro") else "escuro"], p


def vars_css(t):
    return "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items() if isinstance(v, str))


def css_tema(paleta, fundo):
    t, p = tema(paleta, fundo)
    cod = t["codigo"]
    return f"""
:root{{{vars_css(t)}--cod-kw:{cod['kw']};--cod-str:{cod['str']};--cod-com:{cod['com']};--cod-fn:{cod['fn']};--cod-fg:{cod['fg']};--cod-num:{cod['num']}}}
.sobre-escuro{{{vars_css(p['escuro'])}}}
.sobre-claro{{{vars_css(p['claro'])}}}
#root{{font-family:'Inter',sans-serif;color:var(--tinta)}}
em{{font-style:normal;font-family:'JetBrains Mono',monospace;font-weight:800;color:var(--destaque);letter-spacing:-.03em}}
em::before{{content:"{{";opacity:.5;font-weight:500;margin-right:.04em}}
em::after{{content:"}}";opacity:.5;font-weight:500;margin-left:.04em}}
.claro-txt em,.pil em,.sobre-escuro em{{color:var(--destaque2)}}
.selo{{position:absolute;left:{SELO['left']}px;top:{SELO['top']}px;width:{SELO['size']}px;height:{SELO['size']}px;border-radius:50%;
  box-shadow:0 6px 18px rgba(0,0,0,.28);z-index:60}}
.lg{{display:grid;place-items:center;flex:none;box-shadow:0 10px 26px rgba(0,0,0,.22)}}
.lg img{{object-fit:contain;display:block}}
.stamp{{position:absolute;display:flex;flex-direction:column;align-items:center;gap:16px;visibility:hidden;z-index:55}}
.stamp .nm{{font:800 40px 'Inter';color:var(--tinta);background:var(--cartao);padding:6px 18px;border-radius:14px;letter-spacing:-.02em}}
.ttl{{position:absolute;left:0;width:1080px;top:{TITULO_TOP}px;text-align:center;font:800 {TITULO_PX}px/1.05 'Inter';
  letter-spacing:-.035em;white-space:nowrap;z-index:30}}
.ttl span{{display:inline-block}}
.ttl.claro-txt{{color:#fff;text-shadow:0 4px 18px rgba(0,0,0,.55)}}
.scene{{position:absolute;left:0;top:0;width:1080px;height:1920px;visibility:hidden}}
.pil{{position:absolute;left:0;right:0;margin:0 auto;width:fit-content;visibility:hidden;padding:14px 30px 18px;border-radius:22px;
  background:var(--pilula);font:800 58px/1 'Inter';color:#fff;letter-spacing:-.02em;white-space:nowrap;box-shadow:0 12px 30px rgba(0,0,0,.3);z-index:40}}
.cartao{{background:var(--cartao);color:var(--tinta);border-radius:28px;box-shadow:0 16px 40px rgba(0,0,0,.16)}}
.li{{display:flex;align-items:center;gap:28px;font:700 58px/1.05 'Inter';letter-spacing:-.02em;white-space:nowrap}}
.mk{{border-radius:24px;background:var(--destaque);color:var(--sobre-destaque);display:grid;place-items:center;font:800 44px 'JetBrains Mono';flex:none}}
.mk.ic{{background:var(--cartao);box-shadow:0 10px 24px rgba(0,0,0,.16);font-weight:400}}
.no{{position:absolute;display:grid;place-items:center}}
.nb{{width:100%;height:100%;border-radius:28px;background:var(--cartao);box-shadow:0 16px 40px rgba(0,0,0,.16);display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:14px;padding:16px;text-align:center;font:800 40px/1.05 'Inter';color:var(--tinta);letter-spacing:-.02em}}
.nb.forte{{background:var(--escuro);color:#fff}}
.nb .lg{{box-shadow:none}}
.ic2{{font-size:84px;line-height:1;font-weight:400}}
.lab{{position:absolute;font:800 24px 'Inter';letter-spacing:.12em;text-transform:uppercase;color:var(--cinza);white-space:nowrap}}
.tcard{{width:300px;height:330px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:24px;text-align:center;
  border-radius:24px;overflow:hidden;box-shadow:0 16px 40px rgba(0,0,0,.2)}}
.tcard .tb{{font:800 56px/1.02 'Inter';letter-spacing:-.03em}}
.tcard .ts{{font:600 24px/1.25 'Inter';opacity:.75}}
.shot{{position:absolute;border-radius:24px;overflow:hidden;background:#111;box-shadow:0 22px 50px rgba(0,0,0,.28)}}
.shot img{{width:100%;height:100%}}
.barra{{height:54px;display:flex;align-items:center;gap:12px;padding:0 22px;background:var(--barra);font:600 23px 'Inter';color:var(--cinza)}}
.barra b{{width:15px;height:15px;border-radius:50%;display:inline-block}}
.ed{{position:absolute;border-radius:26px;overflow:hidden;background:var(--escuro);border:2px solid rgba(255,255,255,.08);box-shadow:0 20px 50px rgba(0,0,0,.25)}}
.ed .barra{{background:var(--barra-escura);color:var(--barra-escura-txt);font-family:'JetBrains Mono'}}
.ed .lang{{margin-left:auto;font:500 19px 'JetBrains Mono';background:var(--chip-escuro);padding:4px 12px;border-radius:8px}}
.cl{{display:flex;align-items:center;height:54px;font:500 30px 'JetBrains Mono';color:var(--cod-fg);white-space:pre;position:relative}}
.cl .n{{width:64px;text-align:right;padding-right:22px;color:var(--cod-num);flex:none}}
.cl.add{{background:rgba(166,227,161,.12)}} .cl.del{{background:rgba(243,139,168,.12);text-decoration:line-through;text-decoration-color:rgba(243,139,168,.6)}}
.hl{{position:absolute;left:0;right:0;height:54px;background:rgba(var(--destaque2-rgb),.16);box-shadow:inset 6px 0 0 var(--destaque2);visibility:hidden}}
.ck{{color:var(--cod-kw)}} .cs{{color:var(--cod-str)}} .cc{{color:var(--cod-com)}} .cf{{color:var(--cod-fn)}}
.tp{{display:inline-block;overflow:hidden;vertical-align:bottom;width:0}}
.bign{{font:800 64px/1 'Inter';letter-spacing:-.03em}}
.cnt{{font:800 190px/1 'JetBrains Mono';color:var(--destaque);letter-spacing:-.05em}}
.cnt-sub{{font:800 50px/1.1 'Inter';letter-spacing:-.02em;text-align:center}}
.cnt-leg{{font:600 30px/1.2 'Inter';color:var(--cinza);text-align:center}}
"""


class Motor:
    """um reel: o Job/Comp do kit + tema + logos + cenas"""

    def __init__(self, spec_path, nome):
        self.j = Job(spec_path, nome)
        self.c = Comp(self.j)
        self.enq = self.j.get("enquadramento") or {}
        self.paleta, self.fundo = self.j.get("paleta"), self.j.get("fundo") or self.enq.get("fundo", "escuro")
        self.t, _ = tema(self.paleta, self.fundo)
        self.c.css.append(css_tema(self.paleta, self.fundo))
        self.avisos = []
        lg = self.j.get("logos", "auto")
        self.chaves_logo = list(CAT) if lg == "auto" else (lg or [])
        self.ditas = mencoes(self.j.words, self.chaves_logo)
        self.n_cantos = 0

    # ---------------------------------------------------------- peças fixas
    def selo(self):
        self.c.body.append(f'<img class="selo a" src="{self.c.asset(LOGO_COMUNIDADE)}">')

    def titulo(self, p, texto, t0, claro=False, top=None):
        palavras = re.findall(r"<em>.*?</em>|\S+", rich(texto))       # "*open source*" fica inteiro
        estilo = f' style="top:{top}px"' if top else ""
        self.c.body.append(f'<div class="ttl{" claro-txt" if claro else ""}" id="{p}t"{estilo}>'
                           + " ".join(f"<span>{w}</span>" for w in palavras) + "</div>")
        self.c.js.append(f'tl.fromTo("#{p}t span",{{y:36,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,stagger:.07,ease:"power3.out"}},{t0:.3f});')

    def legenda_pilula(self, top, chaves=()):
        word_caps(self.c, self.j.words, "pil", f".pil{{top:{top}px}}", maxw=3, maxc=16, keys=[bare(x) for x in self.chaves(chaves)],
                  key_tag="em", pop=(0.94, 0.16))

    def legenda_peito(self, top, px=104):
        """legenda grande no peito (bastidores, destaque): branca, palavra-chave na cor de destaque"""
        css = (f".peito{{position:absolute;left:0;width:1080px;top:{top}px;text-align:center;visibility:hidden;font:800 {px}px/1 'Inter';"
               f"color:#fff;letter-spacing:-.03em;text-shadow:0 6px 24px rgba(0,0,0,.55);z-index:40}}"
               f".peito em{{color:var(--destaque2);font-size:{px * 1.05:.0f}px}}")
        word_caps(self.c, self.j.words, "peito", css, maxw=2, maxc=11, keys=[bare(x) for x in self.chaves(())], key_tag="em",
                  pop=(0.8, 0.22))

    def chaves(self, extra):
        return list(self.j.get("chaves", [])) + list(extra) + [CAT[k]["nome"] for k in self.chaves_logo]

    # ---------------------------------------------------------- logos
    def logos_da_cena(self, p, t0, t1, ja_tem, centro):
        """primeira menção na cena: pipoca grande em `centro` e vai para o canto superior direito;
        menções seguintes: o selo do canto pulsa"""
        vistos = {}
        for t, k in self.ditas:
            if not (t0 <= t < t1) or k in ja_tem:
                continue
            if k in vistos:
                self.c.js.append(f'tl.fromTo("#{vistos[k]} .lg",{{scale:1.18}},{{scale:1,duration:.35,ease:"power2.out"}},{t:.3f});')
                continue
            sid = f"{p}lg{len(vistos)}"
            S = 240
            fx = 1080 - CANTO["right"] - CANTO["size"] / 2 - len(vistos) * CANTO["gap"]
            fy = CANTO["top"] + CANTO["size"] / 2
            cx, cy = centro or (fx, fy)          # sem centro: vai direto para o canto
            esc = CANTO["size"] / S
            self.c.body.append(f'<div class="stamp" id="{sid}" style="left:{cx - S / 2:.0f}px;top:{cy - S / 2:.0f}px;width:{S}px">'
                               f'{self.logo_html(k, S)}<div class="nm" id="{sid}n">{html.escape(CAT[k]["nome"])}</div></div>')
            dx, dy = fx - cx, fy - cy
            if t1 - t > 1.6 and centro:
                self.c.js.append(f'''tl.set("#{sid}",{{visibility:"visible"}},{t:.3f});
tl.fromTo("#{sid}",{{scale:.3,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.32,ease:"back.out(2)"}},{t:.3f});
tl.to("#{sid}n",{{autoAlpha:0,duration:.18}},{t + 1.0:.3f});
tl.to("#{sid}",{{x:{dx:.0f},y:{dy:.0f},scale:{esc:.3f},transformOrigin:"50% {S / 2:.0f}px",duration:.42,ease:"power3.inOut"}},{t + 1.05:.3f});''')
            else:
                self.c.js.append(f'''tl.set("#{sid}n",{{autoAlpha:0}},{t0:.3f});
tl.set("#{sid}",{{visibility:"visible",x:{dx:.0f},y:{dy:.0f},transformOrigin:"50% {S / 2:.0f}px"}},{t:.3f});
tl.fromTo("#{sid}",{{scale:.1,autoAlpha:0}},{{scale:{esc:.3f},autoAlpha:1,duration:.3,ease:"back.out(2)"}},{t:.3f});''')
            vistos[k] = sid
        return set(vistos)

    def logo_html(self, key, size, extra=""):
        e = CAT[key]
        fundo = e.get("fundo", "#fff")
        pad = round(size * 0.17)
        src = self.c.asset(CAT_DIR / e["icone"])
        return (f'<div class="lg" style="width:{size}px;height:{size}px;border-radius:{size * .24:.0f}px;background:{fundo};{extra}">'
                f'<img src="{src}" style="width:{size - 2 * pad}px;height:{size - 2 * pad}px"></div>')

    # ---------------------------------------------------------- cenas
    def cenas(self, cenas, desenha):
        """chama desenha(i, cena, p, t0, t1) para cada cena; cuida de mostrar e esconder"""
        if self.j.get("end"):            # teste de um trecho (--fim): só as cenas que começam dentro dele
            dentro = [cenas[0]] if cenas else []
            for s in cenas[1:]:
                try:
                    self.j.t(s["at"])
                    dentro.append(s)
                except ValueError:
                    break
            cenas = dentro
        ini = [0.0] + [self.j.t(s["at"]) for s in cenas[1:]]
        self.inicios = ini
        for i, s in enumerate(cenas):
            t0 = ini[i]
            t1 = ini[i + 1] if i + 1 < len(cenas) else self.c.dur
            p = f"s{i}"
            self.c.body.append(f'<div class="scene" id="{p}">')
            self.c.js.append(f'tl.set("#{p}",{{visibility:"visible"}},{t0:.3f});')
            desenha(i, s, p, t0, t1)
            self.c.body.append("</div>")
            if i + 1 < len(cenas):
                self.c.js.append(f'tl.to("#{p}",{{autoAlpha:0,y:-24,duration:.22,ease:"power2.in"}},{max(t0, t1 - 0.22):.3f});')
        return ini

    # ---------------------------------------------------------- fim
    def fecha(self, inicios=None):
        out = self.j.finish(self.c)
        ini = inicios or getattr(self, "inicios", [0.0])
        fins = ini[1:] + [self.c.dur]
        tempos = [max((a + b) / 2, b - 0.45) for a, b in zip(ini, fins)]
        folha = out.with_name(out.stem + ".cenas.jpg")
        folha_cenas(out, tempos, folha)
        out.with_name(out.stem + ".checagem.json").write_text(json.dumps({"avisos": self.avisos}, ensure_ascii=False, indent=1))
        print(f"cenas: {folha}")
        return out


def mencoes(words, chaves):
    formas = []
    for k in chaves:
        for f in CAT[k].get("falado", []) + [CAT[k]["nome"]]:
            formas.append((tuple(nu(x) for x in f.split()), k))
    formas.sort(key=lambda x: -len(x[0]))
    ns = [nu(w) for w, _, _ in words]
    out, i = [], 0
    while i < len(ns):
        for f, k in formas:
            if tuple(ns[i:i + len(f)]) == f:
                out.append((words[i][1], k))
                i += len(f) - 1
                break
        i += 1
    return out


def folha_cenas(video, tempos, saida):
    cols = min(8, max(1, len(tempos)))
    entradas, filtros = [], []
    for k, t in enumerate(tempos):
        entradas += ["-ss", f"{t:.2f}", "-i", str(video)]
        filtros.append(f"[{k}:v]scale=180:320,drawtext=text='{k + 1}':x=6:y=6:fontsize=22:fontcolor=red[f{k}]")
    while len(filtros) % cols:
        filtros.append(f"color=c=black:s=180x320:d=1[f{len(filtros)}]")
    grade = "".join(f"[f{k}]" for k in range(len(filtros)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex",
                    ";".join(filtros) + f";{grade}xstack=inputs={len(filtros)}:layout="
                    + "|".join(f"{(k % cols) * 180}_{(k // cols) * 320}" for k in range(len(filtros))) + ",format=yuvj420p",
                    "-frames:v", "1", str(saida)], check=True)


# ====================================================================== visuais
# Cada visual desenha dentro de uma zona {x, y, w, h} e devolve as logos que já mostra.

def marcador(m, it, i, size):
    if it.get("logo"):
        return m.logo_html(it["logo"], size)
    if it.get("icone"):
        return f'<b class="mk ic" style="width:{size}px;height:{size}px;font-size:{size * .6:.0f}px">{html.escape(it["icone"])}</b>'
    return f'<b class="mk" style="width:{size}px;height:{size}px">{i + 1}</b>'


def v_lista(m, v, p, t0, t1, z):
    items = v.get("items") or []
    rh = min(128, int(z["h"] * 0.95) // max(1, len(items)))
    top = z["y"] + (z["h"] - rh * len(items)) // 2
    rows = "".join(f'<div class="li" id="{p}li{i}" style="height:{rh}px">{marcador(m, it, i, min(88, rh - 18))}<span>{rich(it["texto"])}</span></div>'
                   for i, it in enumerate(items))
    m.c.body.append(f'<div class="a" style="left:{z["x"]}px;width:{z["w"]}px;top:{top}px;display:flex;justify-content:center"><div>{rows}</div></div>')
    for i, it in enumerate(items):
        t = m.j.t(it.get("at"), t0 + 0.4 + i * 0.7)
        m.c.js.append(f'tl.fromTo("#{p}li{i}",{{x:-40,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.32,ease:"back.out(1.6)"}},{t:.3f});')
    return {it["logo"] for it in items if it.get("logo")}


def v_fluxo(m, v, p, t0, t1, z):
    nos = v.get("nos") or []
    forma = v.get("forma", "linha")
    cor = "var(--destaque)"
    if forma == "linha":
        NW, NH = (320, 250) if len(nos) <= 2 else (260, 230)
        gap = min(110, (z["w"] - NW * len(nos)) / max(1, len(nos) - 1)) if len(nos) > 1 else 0
        x0 = z["x"] + (z["w"] - (NW * len(nos) + gap * (len(nos) - 1))) / 2
        y = z["y"] + z["h"] / 2 - NH / 2
        pos = [(x0 + k * (NW + gap), y) for k in range(len(nos))]
        ligas = [(k, k + 1) for k in range(len(nos) - 1)]
    else:  # hub: um em cima, até 3 embaixo
        NW, NH = 240, 165
        pos = [(z["x"] + (z["w"] - NW) / 2, z["y"])]
        filhos = len(nos) - 1
        x0 = z["x"] + (z["w"] - (NW * filhos + 36 * (filhos - 1))) / 2
        pos += [(x0 + k * (NW + 36), z["y"] + z["h"] - NH) for k in range(filhos)]
        ligas = [(0, k) for k in range(1, len(nos))]
    caixas, paths = [], []
    for k, (n, (x, y)) in enumerate(zip(nos, pos)):
        ic = (m.logo_html(n["logo"], 104 if forma == "linha" else 76) if n.get("logo") else
              f'<b class="ic2">{html.escape(n["icone"])}</b>' if n.get("icone") else "")
        caixas.append(f'<div class="no" id="{p}n{k}" style="left:{x:.0f}px;top:{y:.0f}px;width:{NW}px;height:{NH}px">'
                      f'<div class="nb{" forte sobre-escuro" if n.get("destaque") else ""}">{ic}<span>{rich(n["texto"])}</span></div></div>')
    for a_, b_ in ligas:
        (xa, ya), (xb, yb) = pos[a_], pos[b_]
        if forma == "linha":
            sx, sy, ex, ey = xa + NW + 8, ya + NH / 2, xb - 8, yb + NH / 2
        else:
            sx, sy, ex, ey = xa + NW / 2, ya + NH + 6, xb + NW / 2, yb - 8
        ln = ((ex - sx) ** 2 + (ey - sy) ** 2) ** .5
        paths.append(f'<path id="{p}a{b_}" d="M{sx:.0f} {sy:.0f} L{ex:.0f} {ey:.0f}" stroke="{cor}" stroke-width="7" fill="none" '
                     f'stroke-linecap="round" stroke-dasharray="{ln:.0f}" stroke-dashoffset="{ln:.0f}" opacity="0" marker-end="url(#{p}mk)"/>')
    m.c.body.append(f'<svg class="a" style="left:0;top:0;width:1080px;height:1920px;overflow:visible" viewBox="0 0 1080 1920">'
                    f'<defs><marker id="{p}mk" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto">'
                    f'<path d="M0 0 L10 5 L0 10 z" style="fill:{cor}"/></marker></defs>' + "".join(paths) + "</svg>" + "".join(caixas))
    for k, n in enumerate(nos):
        t = m.j.t(n.get("at"), t0 + 0.3 + k * 0.8)
        if k and any(b_ == k for _, b_ in ligas):
            m.c.js.append(f'tl.set("#{p}a{k}",{{opacity:1}},{max(t0, t - .25):.3f});'
                          f'tl.to("#{p}a{k}",{{strokeDashoffset:0,duration:.3,ease:"power2.inOut"}},{max(t0, t - .25):.3f});')
        m.c.js.append(f'tl.fromTo("#{p}n{k}",{{y:24,scale:.85,autoAlpha:0}},{{y:0,scale:1,autoAlpha:1,duration:.34,ease:"back.out(1.8)"}},{t:.3f});')
    return {n["logo"] for n in nos if n.get("logo")}


def v_grade(m, v, p, t0, t1, z):
    items = v.get("items") or []
    cols = 3 if len(items) > 4 else max(1, len(items)) if len(items) <= 3 else 2
    TW, TH, G = (220, 185, 28) if cols == 3 else (260, 185, 40)
    rows = (len(items) + cols - 1) // cols
    y0 = z["y"] + z["h"] / 2 - (rows * TH + (rows - 1) * 24) / 2
    for k, it in enumerate(items):
        r, col = divmod(k, cols)
        n_lin = min(cols, len(items) - r * cols)
        x0 = z["x"] + (z["w"] - (n_lin * TW + (n_lin - 1) * G)) / 2
        ic = m.logo_html(it["logo"], 92) if it.get("logo") else f'<b class="ic2">{html.escape(it.get("icone", ""))}</b>'
        m.c.body.append(f'<div class="no" id="{p}g{k}" style="left:{x0 + col * (TW + G):.0f}px;top:{y0 + r * (TH + 24):.0f}px;'
                        f'width:{TW}px;height:{TH}px"><div class="nb" style="font-size:30px">{ic}<span>{rich(it["texto"])}</span></div></div>')
        t = m.j.t(it.get("at"), t0 + 0.3 + k * 0.5)
        m.c.js.append(f'tl.fromTo("#{p}g{k}",{{y:24,scale:.8,autoAlpha:0}},{{y:0,scale:1,autoAlpha:1,duration:.3,ease:"back.out(1.8)"}},{t:.3f});')
    return {it["logo"] for it in items if it.get("logo")}


def cartao_lado(m, lado, escuro):
    if lado.get("img"):
        return f'<img src="{m.c.asset(m.j.images(lado["img"])[0])}" style="width:300px;height:330px;object-fit:cover;border-radius:24px">'
    topo = m.logo_html(lado["logo"], 92) if lado.get("logo") else ""
    cls = "sobre-escuro" if escuro else ""
    fundo = "background:var(--escuro);color:#fff" if escuro else "background:var(--cartao);color:var(--tinta)"
    return (f'<div class="tcard {cls}" style="{fundo}">{topo}<div class="tb">{rich(lado.get("big", ""))}</div>'
            f'<div class="ts">{html.escape(lado.get("small", ""))}</div></div>')


def v_compare(m, v, p, t0, t1, z):
    L, R = v.get("left") or {}, v.get("right") or {}
    xl = z["x"] + (z["w"] - 860) / 2
    xr = xl + 560
    y = z["y"] + max(0, (z["h"] - 380) / 2)
    m.c.body.append(f'''<div class="lab" id="{p}l0" style="left:{xl:.0f}px;top:{y:.0f}px">{html.escape(L.get("label", "Antes"))}</div>
<div class="lab" id="{p}l1" style="left:{xr:.0f}px;top:{y:.0f}px;color:var(--destaque)">{html.escape(R.get("label", "Depois"))}</div>
<div class="a" id="{p}lc" style="left:{xl:.0f}px;top:{y + 45:.0f}px">{cartao_lado(m, L, False)}</div>
<div class="a" id="{p}rc" style="left:{xr:.0f}px;top:{y + 45:.0f}px;clip-path:inset(0 100% 0 0)">{cartao_lado(m, R, True)}</div>
<svg class="a" style="left:{xl + 290:.0f}px;top:{y + 130:.0f}px;width:280px;height:120px;overflow:visible" viewBox="0 0 280 120">
<path id="{p}ap" d="M14 64 C 90 -12, 190 -12, 266 60" fill="none" style="stroke:var(--destaque)" stroke-width="7" stroke-linecap="round"
 stroke-dasharray="380" stroke-dashoffset="380"/><path id="{p}ah" d="M258 31 L266 60 L236.5 56.5" fill="none" style="stroke:var(--destaque)"
 stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0"/></svg>''')
    la = m.j.t(L.get("at"), t0 + 0.3)
    ra = m.j.t(R.get("at"), la + 1.2)
    aa = m.j.t(v.get("arrow_at"), max(la + 0.4, ra - 0.4)) if v.get("seta", True) else 1e6
    m.c.js.append(f'''tl.fromTo(["#{p}l0","#{p}lc"],{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.32,stagger:.05,ease:"power3.out"}},{la:.3f});
tl.to("#{p}ap",{{strokeDashoffset:0,duration:.38,ease:"power2.inOut"}},{aa:.3f});
tl.to("#{p}ah",{{opacity:1,duration:.08}},{aa + .34:.3f});
tl.fromTo("#{p}l1",{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,ease:"power3.out"}},{ra:.3f});
tl.to("#{p}rc",{{clipPath:"inset(0 0% 0 0)",duration:.34,ease:"power3.out"}},{ra:.3f});''')
    return {x["logo"] for x in (L, R) if x.get("logo")}


def v_logo(m, v, p, t0, t1, z):
    key = v["logo"]
    e = CAT[key]
    nome = (f'<img src="{m.c.asset(CAT_DIR / e["escrito"])}" style="height:70px{";filter:invert(1)" if getattr(m, "visual_escuro", m.fundo == "escuro") and e.get("escrito_claro") is None else ""}">'
            if e.get("escrito") and v.get("escrito", True) else f'<span class="bign">{html.escape(e["nome"])}</span>')
    size = min(240, int(z["h"] * 0.6))
    m.c.body.append(f'<div class="a" id="{p}bl" style="left:{z["x"]}px;width:{z["w"]}px;top:{z["y"] + (z["h"] - size - 100) / 2:.0f}px;'
                    f'display:flex;flex-direction:column;align-items:center;gap:28px">{m.logo_html(key, size)}<div id="{p}bn">{nome}</div></div>')
    t = m.j.t(v.get("at"), t0 + .05)
    m.c.js.append(f'tl.fromTo("#{p}bl .lg",{{scale:.3,autoAlpha:0,rotation:-8}},{{scale:1,autoAlpha:1,rotation:0,duration:.45,ease:"back.out(2)"}},{t:.3f});'
                  f'tl.fromTo("#{p}bn",{{y:24,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,ease:"power3.out"}},{t + .2:.3f});')
    return {key}


def v_foto(m, v, p, t0, t1, z):
    img = m.c.asset(m.j.images(v["img"])[0])
    w = min(z["w"], 860)
    barra = v.get("barra")
    h = z["h"] - (54 if barra else 0)
    x = z["x"] + (z["w"] - w) / 2
    topo = (f'<div class="barra"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b>'
            f'{m.logo_html(v["logo"], 30, "box-shadow:none;margin-left:8px") if v.get("logo") else ""}<span>{html.escape(barra)}</span></div>'
            if barra else "")
    cred = (f'<div class="a" style="right:12px;bottom:10px;font:500 17px Inter;color:#fff;background:rgba(0,0,0,.55);padding:3px 10px;border-radius:8px">'
            f'{html.escape(v["credito"])}</div>' if v.get("credito") else "")
    m.c.body.append(f'<div class="shot" id="{p}sh" style="left:{x:.0f}px;top:{z["y"]}px;width:{w}px;height:{z["h"]}px">{topo}'
                    f'<div style="width:{w}px;height:{h}px;overflow:hidden;position:relative"><img id="{p}im" src="{img}" style="width:{w}px;height:{h}px;'
                    f'object-fit:{v.get("ajuste", "cover")};object-position:{v.get("foco", "50% 0")};transform-origin:50% 30%"></div>{cred}</div>')
    m.c.js.append(f'tl.fromTo("#{p}sh",{{y:40,autoAlpha:0,scale:.96}},{{y:0,autoAlpha:1,scale:1,duration:.4,ease:"power3.out"}},{m.j.t(v.get("at"), t0) + .08:.3f});'
                  f'tl.fromTo("#{p}im",{{scale:1}},{{scale:{v.get("zoom", 1.06)},duration:{t1 - t0:.3f},ease:"none"}},{t0:.3f});')
    return {v["logo"]} if v.get("logo") else set()


def v_contador(m, v, p, t0, t1, z):
    """número falado subindo até o valor: {"valor": "17", "antes": "", "depois": "×", "texto": "mais barato", "legenda": "...", "at": "17"}"""
    alvo = str(v["valor"])
    num = re.sub(r"[^\d]", "", alvo)
    t = m.j.t(v.get("at"), t0 + 0.2)
    m.c.body.append(f'<div class="a" id="{p}ct" style="left:{z["x"]}px;width:{z["w"]}px;top:{z["y"] + z["h"] / 2 - 150:.0f}px;display:flex;'
                    f'flex-direction:column;align-items:center;gap:14px"><div class="cnt">{html.escape(v.get("antes", ""))}<span id="{p}cn">0</span>'
                    f'{html.escape(v.get("depois", ""))}</div><div class="cnt-sub">{rich(v.get("texto", ""))}</div>'
                    f'<div class="cnt-leg">{html.escape(v.get("legenda", ""))}</div></div>')
    m.c.js.append(f'tl.fromTo("#{p}ct",{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,ease:"power3.out"}},{t:.3f});')
    if num and num == alvo.replace(".", "").replace(",", "") and len(num) <= 7:
        m.c.js.append(count_js([f"{p}cn"], int(num), t, dur=0.7, fmt="plain"))
        if not alvo.isdigit():  # "0,2" e afins: no fim mostra exatamente o texto
            m.c.js.append(f'tl.call(()=>{{document.getElementById("{p}cn").textContent={json.dumps(alvo)}}},null,{t + 0.72:.3f});')
    else:
        m.c.js.append(f'tl.call(()=>{{document.getElementById("{p}cn").textContent={json.dumps(alvo)}}},null,{t:.3f});')
    return set()


# --- código: realce simples, sem dependência --------------------------------
PALAVRAS = {"def", "return", "if", "else", "elif", "for", "while", "in", "import", "from", "class", "const", "let", "var", "function",
            "async", "await", "new", "try", "except", "catch", "with", "as", "not", "and", "or", "None", "True", "False", "null", "true",
            "false", "print", "export", "interface", "type", "fn", "pub", "struct", "impl", "func", "package", "echo", "self", "this"}


def realce(linha):
    out, i = [], 0
    padrao = re.compile(r"(?P<c>#.*$|//.*$)|(?P<s>\"[^\"]*\"|'[^']*'|`[^`]*`)|(?P<w>[A-Za-z_]\w*)(?P<call>\s*\()?|(?P<o>.)", re.S)
    for mt in padrao.finditer(linha):
        if mt.group("c"):
            out.append(f'<span class="cc">{html.escape(mt.group("c"))}</span>')
        elif mt.group("s"):
            out.append(f'<span class="cs">{html.escape(mt.group("s"))}</span>')
        elif mt.group("w"):
            w = mt.group("w")
            cls = "ck" if w in PALAVRAS else "cf" if mt.group("call") else ""
            out.append(f'<span class="{cls}">{html.escape(w)}</span>' if cls else html.escape(w))
            if mt.group("call"):
                out.append(html.escape(mt.group("call")))
        else:
            out.append(html.escape(mt.group("o")))
    return "".join(out)


def v_codigo(m, v, p, t0, t1, z):
    """{"arquivo": "x.py", "linguagem": "python", "linhas": [...], "realces": [{"linha": 5, "at": "classificar"}],
        "entram": [{"linha": 3, "at": "..."}]}  — linha começando com "+ " / "- " vira diff"""
    linhas = v.get("linhas") or []
    LH = 54
    h = min(z["h"], 54 + 44 + LH * len(linhas))
    m.c.body.append(f'<div class="ed sobre-escuro" id="{p}ed" style="left:{z["x"]}px;top:{z["y"]}px;width:{z["w"]}px;height:{h}px">'
                    f'<div class="barra"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b>'
                    f'<span style="margin-left:8px">{html.escape(v.get("arquivo", ""))}</span><span class="lang">{html.escape(v.get("linguagem", ""))}</span></div>'
                    f'<div style="position:relative;padding:22px 0">')
    m.c.body.append(f'<div class="hl" id="{p}hl" style="top:22px"></div>')
    for k, ln in enumerate(linhas):
        cls = "add" if ln.startswith("+ ") else "del" if ln.startswith("- ") else ""
        m.c.body.append(f'<div class="cl {cls}" id="{p}c{k}"><span class="n">{k + 1}</span><span>{realce(ln)}</span></div>')
    m.c.body.append("</div></div>")
    m.c.js.append(f'tl.fromTo("#{p}ed",{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.35,ease:"power3.out"}},{t0 + .05:.3f});')
    entram = {e["linha"]: m.j.t(e.get("at"), t0) for e in v.get("entram", [])}
    for k in range(len(linhas)):
        t = entram.get(k + 1, t0 + 0.15 + k * 0.06)
        m.c.js.append(f'tl.fromTo("#{p}c{k}",{{x:-16,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.22,ease:"power2.out"}},{t:.3f});')
    for r in v.get("realces", []):
        t = m.j.t(r.get("at"), t0 + 0.6)
        m.c.js.append(f'tl.set("#{p}hl",{{visibility:"visible"}},{t:.3f});'
                      f'tl.to("#{p}hl",{{top:{22 + (int(r["linha"]) - 1) * LH},duration:.25,ease:"power2.out"}},{t:.3f});')
    return set()


def v_terminal(m, v, p, t0, t1, z):
    """{"titulo": "bash", "comandos": [{"cmd": "craft run video.mp4", "at": "roda", "saida": ["OK ..."]}]}"""
    cmds = v.get("comandos") or []
    nl = sum(1 + len(c.get("saida", [])) for c in cmds)
    h = min(z["h"], 54 + 44 + 54 * nl)
    m.c.body.append(f'<div class="ed sobre-escuro" id="{p}tm" style="left:{z["x"]}px;top:{z["y"]}px;width:{z["w"]}px;height:{h}px">'
                    f'<div class="barra"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b>'
                    f'<span style="margin-left:8px">{html.escape(v.get("titulo", "terminal"))}</span></div><div style="padding:22px 26px">')
    js = [f'tl.fromTo("#{p}tm",{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.35,ease:"power3.out"}},{t0 + .05:.3f});']
    t = t0 + 0.4
    for k, c in enumerate(cmds):
        t = max(t, m.j.t(c.get("at"), t))
        n = len(c["cmd"])
        m.c.body.append(f'<div class="cl"><span style="color:var(--destaque2)">$&nbsp;</span><span class="tp" id="{p}k{k}">{html.escape(c["cmd"])}</span></div>')
        dur = min(1.6, 0.045 * n)
        js.append(f'tl.to("#{p}k{k}",{{width:"{n}ch",duration:{dur:.2f},ease:"steps({n})"}},{t:.3f});')
        t += dur + 0.2
        for s_, s in enumerate(c.get("saida", [])):
            m.c.body.append(f'<div class="cl" id="{p}o{k}_{s_}" style="color:var(--cinza-claro)">{html.escape(s)}</div>')
            js.append(f'tl.fromTo("#{p}o{k}_{s_}",{{autoAlpha:0}},{{autoAlpha:1,duration:.12}},{t:.3f});')
            t += 0.25
    m.c.body.append("</div></div>")
    m.c.js += js
    return set()


VISUAIS = {"lista": v_lista, "fluxo": v_fluxo, "grade": v_grade, "compare": v_compare, "logo": v_logo, "foto": v_foto,
           "contador": v_contador, "codigo": v_codigo, "terminal": v_terminal}


def visual(m, v, p, t0, t1, z):
    if not v:
        return set()
    return VISUAIS[v.get("type", "lista")](m, v, p, t0, t1, z)


# ====================================================================== validação
FONTES = {"inter": KIT / "fonts" / "inter-800-normal.woff2", "inter700": KIT / "fonts" / "inter-700-normal.woff2",
          "mono": KIT / "fonts" / "jetbrains-mono-800-normal.woff2", "mono500": KIT / "fonts" / "jetbrains-mono-500-normal.woff2"}
_fc = {}


def largura(texto, px, fonte="inter"):
    from PIL import ImageFont
    k = (fonte, int(px))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(str(FONTES[fonte]), int(px))
    return _fc[k].getlength(texto)


def largura_rica(texto, px, fonte="inter"):
    """*palavra* sai em mono entre chaves: mede assim"""
    tot = 0.0
    for i, parte in enumerate(re.split(r"\*(.+?)\*", str(texto))):
        if parte:
            tot += largura("{" + parte + "}", px * 1.0, "mono") if i % 2 else largura(parte, px, fonte)
    return tot


class Validador:
    def __init__(self, spec_path):
        self.spec_path = Path(spec_path).resolve()
        self.s = json.loads(self.spec_path.read_text())
        self.base = self.spec_path.parent
        video = self.base / self.s["video"]
        self.fim = float(self.s.get("end") or reel.duration(video))
        self.ws = reel.load_words(video, float(self.s.get("start", 0)), self.fim,
                                  self.base / self.s["transcript"] if self.s.get("transcript") else None)
        self.bw = [bare(w) for w, _, _ in self.ws]
        self.erros, self.avisos = [], []

    def t(self, v, onde):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        mt = re.match(r"^(.+?)(?:#(\d+))?([+-]\d*\.?\d+)?$", str(v).strip())
        alvo = [bare(x) for x in mt.group(1).split()]
        nth, desl = int(mt.group(2) or 1), float(mt.group(3) or 0)
        achou = [self.ws[i][1] for i in range(len(self.bw)) if self.bw[i:i + len(alvo)] == alvo]
        if len(achou) >= nth:
            return achou[nth - 1] + desl
        perto = sorted({w for w, _, _ in self.ws if bare(w)[:3] == alvo[0][:3]})[:6]
        self.erros.append(f"{onde}: \"{v}\" não é falado{f' (falado {len(achou)}x)' if achou else ''}"
                          + (f"; parecidas: {', '.join(perto)}" if perto else "") + "; use outra palavra ou segundos (grep no frases.txt)")
        return None

    def cenas(self, cenas, campo_titulo="titulo", px=TITULO_PX, maxw=TITULO_MAX):
        ini = [0.0] + [self.t(c.get("at"), f"cena {i + 1}") for i, c in enumerate(cenas[1:], 1)]
        out = []
        for i, c in enumerate(cenas):
            nome = f"cena {i + 1} \"{c.get(campo_titulo, '')}\""
            t0 = ini[i]
            t1 = ini[i + 1] if i + 1 < len(ini) and ini[i + 1] is not None else self.fim
            if t0 is None:
                out.append(None)
                continue
            if i and ini[i - 1] is not None and t0 <= ini[i - 1]:
                self.erros.append(f"{nome}: começa em {t0:.1f}s, antes da cena anterior ({ini[i - 1]:.1f}s) — a âncora casou com a palavra errada; use \"palavra#2\" ou segundos")
            if t1 is not None and t1 - t0 < 3 and i + 1 < len(cenas):
                self.avisos.append(f"aviso: {nome} dura só {t1 - t0:.1f}s (mínimo recomendado 3 s)")
            if campo_titulo and c.get(campo_titulo) and largura_rica(c[campo_titulo], px) > maxw:
                self.erros.append(f"{nome}: título largo demais ({largura_rica(c[campo_titulo], px):.0f}px > {maxw}); encurte")
            out.append((nome, t0, t1))
        if len(cenas) and self.fim / max(1, len(cenas)) > 16:
            self.avisos.append(f"aviso: {len(cenas)} cenas para {self.fim:.0f}s — uma cena a cada 5–15 s deixa o visual vivo")
        return out

    def dentro(self, at, onde, t0, t1):
        if at is None:
            return
        x = self.t(at, onde)
        if x is not None and not (t0 - 0.1 <= x < t1):
            self.erros.append(f"{onde}: \"{at}\" cai em {x:.1f}s, fora da cena ({t0:.1f}–{t1:.1f}s)")

    def logo(self, k, onde):
        if k and k not in CAT:
            self.erros.append(f"{onde}: logo \"{k}\" não está no catálogo → craft logo {k} <slug-simpleicons> \"Nome\", ou use \"icone\"")

    def visual(self, v, nome, t0, t1, z):
        if not v:
            return
        tipo = v.get("type")
        if tipo not in VISUAIS:
            self.erros.append(f"{nome}: visual \"{tipo}\" não existe (use {', '.join(VISUAIS)})")
            return
        W = z["w"]
        if tipo == "lista":
            for k, it in enumerate(v.get("items", [])):
                self.dentro(it.get("at"), f"{nome} item {k + 1}", t0, t1)
                self.logo(it.get("logo"), f"{nome} item {k + 1}")
                if 118 + largura_rica(it["texto"], 58) > W:
                    self.erros.append(f"{nome} item {k + 1}: \"{it['texto']}\" não cabe numa linha ({118 + largura_rica(it['texto'], 58):.0f}px > {W})")
            if len(v.get("items", [])) > 4:
                self.erros.append(f"{nome}: lista com mais de 4 itens; divida em duas cenas")
        elif tipo in ("fluxo", "grade"):
            itens = v.get("nos") or v.get("items") or []
            if tipo == "fluxo" and v.get("forma") == "hub" and z["h"] < 360:
                self.erros.append(f"{nome}: fluxo \"hub\" precisa de 360px de altura e aqui tem {z['h']:.0f}px; use \"forma\": \"linha\" (até 3 caixas)")
            if tipo == "fluxo" and v.get("forma", "linha") == "linha" and len(itens) > 3:
                self.erros.append(f"{nome}: fluxo em linha tem no máximo 3 caixas")
            if tipo == "grade" and z["h"] < (185 if len(itens) <= 3 else 394):
                self.erros.append(f"{nome}: grade com {len(itens)} itens não cabe em {z['h']:.0f}px de altura; use até 3 itens")
            nw = (320 if len(itens) <= 2 else 260) if tipo == "fluxo" else (220 if len(itens) > 4 else 260)
            if v.get("forma") == "hub":
                nw = 240
            px = 40 if tipo == "fluxo" else 30
            for k, n in enumerate(itens):
                self.dentro(n.get("at"), f"{nome} caixa {k + 1}", t0, t1)
                self.logo(n.get("logo"), f"{nome} caixa {k + 1}")
                for i_, parte in enumerate(re.split(r"\*(.+?)\*", n.get("texto", ""))):
                    for palavra in parte.split():
                        w_ = largura("{" + palavra + "}", px, "mono") if i_ % 2 else largura(palavra, px)
                        if w_ > nw - 32:
                            self.erros.append(f"{nome} caixa {k + 1}: \"{palavra}\" não cabe na caixa ({w_:.0f}px > {nw - 32})")
        elif tipo == "compare":
            if z["h"] < 380:
                self.erros.append(f"{nome}: compare precisa de 380px de altura e aqui tem {z['h']:.0f}px; use lista ou fluxo em linha")
            self.dentro((v.get("left") or {}).get("at"), f"{nome} esquerda", t0, t1)
            self.dentro((v.get("right") or {}).get("at"), f"{nome} direita", t0, t1)
            for lado in ("left", "right"):
                ld = v.get(lado) or {}
                self.logo(ld.get("logo"), f"{nome} {lado}")
                for ln in str(ld.get("big", "")).split("\n"):
                    if largura_rica(ln, 56) > 252:
                        self.erros.append(f"{nome} {lado}: \"{ln}\" não cabe no cartão")
                if ld.get("img") and not (self.base / ld["img"]).exists():
                    self.erros.append(f"{nome} {lado}: imagem {ld['img']} não existe")
        elif tipo == "lista":
            pass
        elif tipo == "logo":
            self.dentro(v.get("at"), f"{nome} logo", t0, t1)
            self.logo(v.get("logo"), nome)
        elif tipo == "foto":
            if not (self.base / v.get("img", "")).exists():
                self.erros.append(f"{nome}: imagem {v.get('img')} não existe (caminho relativo à pasta do vídeo)")
        elif tipo == "contador":
            self.dentro(v.get("at"), f"{nome} contador", t0, t1)
            txt = f"{v.get('antes', '')}{v.get('valor', '')}{v.get('depois', '')}"
            if largura(txt, 190, "mono") > W:
                self.erros.append(f"{nome}: \"{txt}\" grande demais para o contador; ponha a unidade em \"texto\"")
        elif tipo == "codigo":
            for k, ln in enumerate(v.get("linhas", [])):
                if 90 + largura(ln, 30, "mono500") > W:
                    self.erros.append(f"{nome} código linha {k + 1}: longa demais ({90 + largura(ln, 30, 'mono500'):.0f}px > {W}); quebre a linha")
            if 98 + 54 * len(v.get("linhas", [])) > z["h"]:
                self.erros.append(f"{nome}: código com {len(v.get('linhas', []))} linhas não cabe (máximo {(z['h'] - 98) // 54})")
            for r in v.get("realces", []) + v.get("entram", []):
                self.dentro(r.get("at"), f"{nome} linha {r.get('linha')}", t0, t1)
        elif tipo == "terminal":
            for k, c in enumerate(v.get("comandos", [])):
                self.dentro(c.get("at"), f"{nome} comando {k + 1}", t0, t1)
                for ln in [c["cmd"]] + c.get("saida", []):
                    if 80 + largura(ln, 30, "mono500") > W:
                        self.erros.append(f"{nome} terminal: \"{ln[:30]}…\" longa demais; encurte")

    def resultado(self):
        return self.erros, self.avisos


def painel_explainer(p):
    """painel do explainer SEMPRE coberto pelo vídeo, sem distorcer: se o vídeo encolheu (rosto grande),
    o painel encolhe junto (largura e base), e o vídeo é deslocado só dentro do que ainda cobre o painel.
    Devolve (SC, VY, VW, VH, PW, PX, VX, PT, PB) — VX relativo ao painel."""
    SC, VY = float(p["escala"]), float(p["video_y"])
    VW, VH = 1080 * SC, 1920 * SC
    PW = min(float(p.get("largura", 886)), VW)
    PX = (1080 - PW) / 2
    VX = min(0.0, max(PW - VW, PW / 2 - float(p.get("centro_x", 0.5)) * VW))   # rosto no meio, sem sobrar borda
    PT = VY + float(p["olho_y"]) * SC
    PB = min(1830.0, VY + VH)                                                  # a base do painel não passa do vídeo
    return SC, VY, VW, VH, PW, PX, VX, PT, PB


def zona_explainer(enq, topo=370, base_max=800):
    """faixa do visual acima da cabeça: nunca encosta no cabelo"""
    p = enq.get("painel") or {}
    r = enq.get("rosto") or {}
    cabelo = p.get("video_y", 0) + r.get("cabelo_y", 900) * p.get("escala", 1)
    base = min(base_max, cabelo - 30)
    return {"x": 100, "y": topo, "w": 880, "h": max(260, base - topo)}
