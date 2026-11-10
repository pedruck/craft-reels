#!/usr/bin/env python3
"""historia: o vídeo inteiro de fundo; em cada cena três cartões (imagem, logo ou emoji com rótulo),
um título e um subtítulo em cima. Legenda em pílula abaixo do queixo.
Baseado no /storytelling de Artem Novitckii (claude-editing-skills, MIT).

cena: {"at": 0, "titulo": "Um time de *agentes*", "subtitulo": "cada um cuida de uma parte",
       "cartoes": [{"img": "img/a.jpg", "texto": "front-end", "at": "front"}, {"logo": "orca", "texto": "Orca"}, {"icone": "🧪", "texto": "testes"}],
       "credito": "imagens: github.com/stablyai/orca · MIT"}
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import Motor, Validador, largura, posicao_legenda, rich, video_cheio  # noqa: E402

GIRO = (-5, 0, 5)


def faixa(r):
    """título logo acima dos olhos (nunca sobre eles); cartões acima do título"""
    titulo = min(786, r["olho_y"] - 190)
    return titulo, max(286, titulo - 436)


def validar(spec_path):
    v = Validador(spec_path)
    cenas = v.s.get("cenas", [])
    for info, c in zip(v.cenas(cenas, px=80, maxw=980), cenas):
        if not info:
            continue
        nome, t0, t1 = info
        cs = c.get("cartoes") or []
        if not 1 <= len(cs) <= 3:
            v.erros.append(f"{nome}: use de 1 a 3 cartões")
        for k, ct in enumerate(cs):
            v.dentro(ct.get("at"), f"{nome} cartão {k + 1}", t0, t1)
            v.logo(ct.get("logo"), f"{nome} cartão {k + 1}")
            if ct.get("img") and not (v.base / ct["img"]).exists():
                v.erros.append(f"{nome} cartão {k + 1}: imagem {ct['img']} não existe")
            if largura(ct.get("texto", ""), 28) > 280:
                v.erros.append(f"{nome} cartão {k + 1}: rótulo \"{ct.get('texto')}\" longo demais")
        if largura(c.get("subtitulo", ""), 38, "inter700") > 980:
            v.erros.append(f"{nome}: subtítulo longo demais")
    _, r = video_cheio(v.s.get("enquadramento") or {})
    titulo, cartoes = faixa(r)
    if cartoes + 330 > titulo - 6:
        v.erros.append(f"os olhos estão alto demais (y={r['olho_y']:.0f}): cartões e título não cabem acima deles "
                       "→ este vídeo não serve para a historia; diga à pessoa e use o explainer")
    return v.resultado()


def cartao(m, ct):
    if ct.get("img"):
        miolo = f'<img src="{m.c.asset(m.j.images(ct["img"])[0])}" style="width:300px;height:330px;object-fit:cover">'
    elif ct.get("logo"):
        miolo = (f'<div style="width:300px;height:330px;display:grid;place-items:center;background:var(--cartao)">'
                 f'{m.logo_html(ct["logo"], 170)}</div>')
    else:
        miolo = (f'<div style="width:300px;height:330px;display:grid;place-items:center;background:var(--cartao);font-size:140px;'
                 f'">{html.escape(ct.get("icone", ""))}</div>')
    rot = (f'<div style="margin:-26px auto 0;position:relative;width:max-content;background:var(--cartao);color:var(--tinta);border-radius:999px;'
           f'padding:8px 20px;font:800 28px Inter;box-shadow:0 6px 16px rgba(0,0,0,.2)">{rich(ct.get("texto", ""))}</div>') if ct.get("texto") else ""
    return f'<div style="border-radius:22px;overflow:hidden;box-shadow:0 16px 40px rgba(0,0,0,.35)">{miolo}</div>{rot}'


def main(spec):
    m = Motor(spec, "historia")
    j, c, enq = m.j, m.c, m.enq
    c.css.append('''#dim{left:0;top:0;width:1080px;height:1920px;background:linear-gradient(rgba(var(--sombra-rgb),.78),rgba(var(--sombra-rgb),.35) 45%,rgba(0,0,0,0) 62%)}
.sub{position:absolute;left:0;width:1080px;text-align:center;font:700 38px/1.2 'Inter';color:#eceff4;text-shadow:0 4px 16px rgba(0,0,0,.6)}''')
    estilo, r = video_cheio(enq)
    topo_titulo, topo_cartoes = faixa(r)
    c.body.append(c.video(j.clip, estilo, "bg"))
    c.body.append('<div id="dim" class="a"></div>')
    m.selo()

    def desenha(i, s, pid, t0, t1):
        cs = s.get("cartoes") or []
        giros = GIRO if len(cs) == 3 else (-4, 4) if len(cs) == 2 else (0,)
        for k, ct in enumerate(cs):
            x = 540 - (len(cs) * 300 + (len(cs) - 1) * 22) / 2 + k * 322
            c.body.append(f'<div class="a" id="{pid}k{k}" style="left:{x:.0f}px;top:{topo_cartoes + abs(giros[k]) * 4}px;width:300px;'
                          f'transform:rotate({giros[k]}deg)">{cartao(m, ct)}</div>')
            t = j.t(ct.get("at"), t0 + 0.15 + k * 0.18)
            c.js.append(f'tl.fromTo("#{pid}k{k}",{{y:60,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.4,ease:"back.out(1.6)"}},{t:.3f});')
        if s.get("credito"):
            c.body.append(f'<div class="a" style="right:40px;top:{topo_titulo - 44}px;font:500 17px Inter;color:#fff;background:rgba(0,0,0,.5);padding:4px 10px;'
                          f'border-radius:8px">{html.escape(s["credito"])}</div>')
        m.titulo(pid, s.get("titulo", ""), t0 + 0.3, claro=True, top=topo_titulo)
        if s.get("subtitulo"):
            c.body.append(f'<div class="sub" id="{pid}sb" style="top:{topo_titulo + 94}px">{html.escape(s["subtitulo"])}</div>')
            c.js.append(f'tl.fromTo("#{pid}sb",{{autoAlpha:0}},{{autoAlpha:1,duration:.3}},{t0 + 0.6:.3f});')
        ja = {ct["logo"] for ct in cs if ct.get("logo")}
        m.logos_da_cena(pid, t0, t1, ja, None)

    m.cenas(j.get("cenas", []), desenha)
    m.legenda_pilula(round(posicao_legenda(r["queixo_y"])[0]))
    m.fecha()


if __name__ == "__main__":
    main(sys.argv[1])
