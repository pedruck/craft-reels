#!/usr/bin/env python3
"""split: metade de cima no fundo do tema (selo de passo opcional, título, visual — print numa janela,
código, lista…), a pessoa na metade de baixo, legenda em pílula embaixo, abaixo do queixo (na emenda só
quando o rosto é grande demais para caber a legenda sem cobri-lo).
Baseado no /split-screen de Artem Novitckii (claude-editing-skills, MIT).
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import LEG_MAX, Motor, Validador, posicao_legenda, visual  # noqa: E402

EM = 960                                   # a emenda entre as metades
ZONA = {"x": 100, "y": 396, "w": 880, "h": EM - 396 - 56}


def validar(spec_path):
    v = Validador(spec_path)
    cenas = v.s.get("cenas", [])
    for info, c in zip(v.cenas(cenas), cenas):
        if info:
            v.visual(c.get("visual"), info[0], info[1], info[2], ZONA)
    return v.resultado()


def main(spec):
    m = Motor(spec, "split")
    j, c, enq = m.j, m.c, m.enq
    r = enq.get("rosto") or {}
    alvo = EM + 0.36 * (1920 - EM)             # olhos a ~1/3 da metade de baixo
    rel = min(0, max(-EM, alvo - EM - r.get("olho_y", 900)))
    # legenda sempre embaixo, sem cobrir o rosto: sobe o vídeo o quanto der sem esconder os olhos na emenda
    queixo = EM + rel + r.get("queixo_y", 1300)
    if queixo > LEG_MAX - 24:
        sobe = min(queixo - (LEG_MAX - 24), EM + rel + r.get("olho_y", 900) - (EM + 110), rel + EM)
        rel -= max(0, sobe)
        queixo = EM + rel + r.get("queixo_y", 1300)
    leg, cobre = posicao_legenda(queixo)
    if cobre:                                  # rosto grande demais: a legenda vai para a emenda, acima da cabeça
        leg = EM - 44
        m.avisos.append("rosto grande na metade de baixo: legenda na emenda (acima da cabeça) para não cobrir o rosto")
    c.css.append(f'''
#bk{{left:0;top:0;width:1080px;height:{EM}px;background:radial-gradient(ellipse at 50% 30%,var(--papel2) 0%,var(--papel) 75%)}}
#vd{{left:0;top:{EM}px;width:1080px;height:{1920 - EM}px;overflow:hidden}}
.passo{{position:absolute;left:0;right:0;margin:0 auto;width:fit-content;top:338px;font:800 28px 'JetBrains Mono';color:var(--sobre-destaque);
  background:var(--destaque);padding:7px 22px;border-radius:999px}}''')
    c.body.append('<div id="bk" class="a"></div>')
    c.body.append('<div id="vd" class="a">' + c.video(j.clip, f"position:absolute;left:0;top:{rel:.0f}px;width:1080px;height:1920px", "bg") + "</div>")
    m.selo()

    def desenha(i, s, pid, t0, t1):
        m.titulo(pid, s.get("titulo", ""), t0)
        if s.get("passo"):
            c.body.append(f'<div class="passo" id="{pid}ps">{{ {html.escape(str(s["passo"]))} }}</div>')
            c.js.append(f'tl.fromTo("#{pid}ps",{{scale:.6,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.3,ease:"back.out(2)"}},{t0:.3f});')
        ja = visual(m, s.get("visual"), pid, t0, t1, ZONA)
        m.logos_da_cena(pid, t0, t1, ja, (540, ZONA["y"] + ZONA["h"] / 2))

    m.cenas(j.get("cenas", []), desenha)
    m.legenda_pilula(round(leg))
    m.fecha()


if __name__ == "__main__":
    main(sys.argv[1])
