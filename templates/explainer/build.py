#!/usr/bin/env python3
"""explainer (padrão): fundo do tema, título + visual em cima, a pessoa num painel arredondado com a
cabeça saindo por cima, legenda em pílula logo abaixo do queixo.
Baseado no /explainer de Artem Novitckii (claude-editing-skills, MIT).

    kit/.venv/bin/python templates/explainer/build.py spec.json      (a etapa 7 do craft chama isto)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import Motor, Validador, painel_explainer, posicao_legenda, visual, zona_explainer  # noqa: E402


def zona(s):
    return zona_explainer(s.get("enquadramento", {}))


def validar(spec_path):
    v = Validador(spec_path)
    z = zona(v.s)
    cenas = v.s.get("cenas", [])
    for info, c in zip(v.cenas(cenas), cenas):
        if info:
            v.visual(c.get("visual"), info[0], info[1], info[2], z)
    if z["h"] < 330:
        v.avisos.append(f"aviso: a cabeça sobe até y={z['y'] + z['h'] + 30:.0f}; sobram só {z['h']:.0f}px para o visual — prefira lista curta, logo ou contador")
    return v.resultado()


def main(spec):
    m = Motor(spec, "explainer")
    j, c, enq = m.j, m.c, m.enq
    p = enq["painel"]
    SC, VY, VW, VH, PW, PX, VX, PT, PB = painel_explainer(p)   # o vídeo sempre cobre o painel inteiro
    c.css.append(f'''
#bk{{left:0;top:0;width:1080px;height:1920px;background:radial-gradient(ellipse at 50% 28%,var(--papel2) 0%,var(--papel) 70%)}}
#pan{{left:{PX:.1f}px;top:{PT:.1f}px;width:{PW:.1f}px;height:{PB - PT:.1f}px;border-radius:56px;overflow:hidden;box-shadow:0 30px 70px rgba(0,0,0,.28)}}
#pop{{left:{PX:.1f}px;top:{VY:.1f}px;width:{PW:.1f}px;height:{PT - VY + 2:.1f}px;overflow:hidden;z-index:20}}''')
    c.body.append('<div id="bk" class="a"></div>')
    m.selo()
    z = zona(j.s)
    if z["h"] < 330:
        m.avisos.append(f"rosto grande: só {z['h']:.0f}px para o visual acima da cabeça")

    def desenha(i, s, pid, t0, t1):
        m.titulo(pid, s.get("titulo", ""), t0)
        ja = visual(m, s.get("visual"), pid, t0, t1, z)
        m.logos_da_cena(pid, t0, t1, ja, (540, z["y"] + z["h"] / 2))

    m.cenas(j.get("cenas", []), desenha)
    corte = j.cutout()
    c.body.append('<div id="pan" class="a">' + c.video(j.clip, f"position:absolute;left:{VX:.1f}px;top:{VY - PT:.1f}px;width:{VW:.1f}px;height:{VH:.1f}px", "bg") + "</div>")
    c.body.append('<div id="pop" class="a">' + c.video(corte, f"position:absolute;left:{VX:.1f}px;top:0;width:{VW:.1f}px;height:{VH:.1f}px", "cut") + "</div>")
    topo, cobre = posicao_legenda(VY + float((enq.get("rosto") or {}).get("queixo_y", 1300)) * SC)
    if cobre:
        m.avisos.append("a legenda encosta no queixo: o rosto desce demais no painel")
    m.legenda_pilula(round(topo))
    m.fecha()


if __name__ == "__main__":
    main(sys.argv[1])
