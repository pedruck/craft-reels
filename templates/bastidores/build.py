#!/usr/bin/env python3
"""bastidores: o vídeo inteiro de fundo, um cartão do tema ATRÁS da pessoa (recorte de fundo) com
título e visual de cada cena, e a legenda em palavras grandes no peito.
Baseado no /behind-the-person de Artem Novitckii (claude-editing-skills, MIT).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import LEG_MIN, PEITO_MARGEM, PEITO_QUEIXO, Motor, Validador, video_cheio, visual  # noqa: E402

TOPO = 300


def geometria(enq):
    estilo, r = video_cheio(enq, queixo_max=PEITO_QUEIXO)             # legenda grande no peito cabe abaixo do queixo
    base = min(1150, max(TOPO + 420, r["cabelo_y"] + 140))        # a cabeça entra um pouco na frente do cartão
    zona = {"x": 130, "y": TOPO + 120, "w": 820, "h": max(200, min(base - 30, r["cabelo_y"] - 24) - (TOPO + 120))}
    peito = min(1400, max(LEG_MIN, r["queixo_y"] + PEITO_MARGEM))
    return base, zona, peito, estilo


def validar(spec_path):
    v = Validador(spec_path)
    _, z, _, _ = geometria(v.s.get("enquadramento", {}))
    cenas = v.s.get("cenas", [])
    for info, c in zip(v.cenas(cenas, px=60, maxw=780), cenas):
        if info:
            v.visual(c.get("visual"), info[0], info[1], info[2], z)
    if z["h"] < 260:
        v.erros.append(f"o rosto ocupa quase o quadro: o cartão atrás da pessoa ficaria escondido (só {z['h']:.0f}px livres) "
                       "→ este vídeo não serve para o bastidores; diga à pessoa e use o explainer")
    return v.resultado()


def main(spec):
    m = Motor(spec, "bastidores")
    j, c, enq = m.j, m.c, m.enq
    base, z, peito, estilo = geometria(enq)
    m.visual_escuro = True          # o visual fica num cartão escuro, qualquer que seja o fundo
    c.css.append(f'''
#dim{{left:0;top:0;width:1080px;height:1920px;background:linear-gradient(rgba(var(--sombra-rgb),.55),rgba(var(--sombra-rgb),.2) 60%,rgba(var(--sombra-rgb),.5));z-index:2}}
.atras{{position:absolute;left:90px;top:{TOPO}px;width:900px;height:{base - TOPO}px;border-radius:36px;background:var(--escuro);
  border:2px solid rgba(255,255,255,.1);box-shadow:0 20px 60px rgba(0,0,0,.4)}}
#sc{{position:absolute;left:0;top:0;width:1080px;height:1920px;z-index:5}}''')
    c.body.append(c.video(j.clip, estilo, "bg"))
    c.body.append('<div id="dim" class="a"></div><div id="sc">')
    if z["h"] < 260:
        m.avisos.append(f"rosto grande: só {z['h']:.0f}px para o visual no cartão")

    def desenha(i, s, pid, t0, t1):
        c.body.append(f'<div class="atras sobre-escuro" id="{pid}cd"></div><div class="sobre-escuro">')
        c.js.append(f'tl.fromTo("#{pid}cd",{{scale:.94,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.32,ease:"power3.out"}},{t0:.3f});')
        m.titulo(pid, s.get("titulo", ""), t0, claro=True, top=TOPO + 34)
        ja = visual(m, s.get("visual"), pid, t0, t1, z)
        c.body.append("</div>")
        m.logos_da_cena(pid, t0, t1, ja, (540, z["y"] + z["h"] / 2))

    m.cenas(j.get("cenas", []), desenha)
    c.body.append("</div>")
    corte = j.cutout()
    c.body.append(c.video(corte, estilo + ";z-index:20", "cut"))
    m.selo()
    m.legenda_peito(peito)
    m.fecha()


if __name__ == "__main__":
    main(sys.argv[1])
