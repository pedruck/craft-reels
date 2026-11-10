#!/usr/bin/env python3
"""codigo: fundo do tema, título + editor de código (ou terminal, ou qualquer visual) ocupando o
alto do quadro, a pessoa recortada (sem o cenário) embaixo, legenda em pílula abaixo do queixo.
Template próprio da comunidade, no mesmo motor dos outros.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import Motor, Validador, posicao_legenda, visual  # noqa: E402

CABELO = 1030          # topo da cabeça recortada


def geometria(enq):
    r = enq.get("rosto") or {"cabelo_y": 900, "queixo_y": 1400, "centro_x": 0.5}
    esc = min(1.1, max(0.3, 400 / max(1, r["queixo_y"] - r["cabelo_y"])))   # cabeça com ~400 px, qualquer rosto
    vy = CABELO - r["cabelo_y"] * esc
    vx = 540 - r["centro_x"] * 1080 * esc
    leg, _ = posicao_legenda(vy + r["queixo_y"] * esc)   # sempre embaixo, nunca no rosto
    return esc, vx, vy, leg


def zona(enq):
    return {"x": 60, "y": 370, "w": 960, "h": CABELO - 30 - 370}


def validar(spec_path):
    v = Validador(spec_path)
    z = zona(v.s.get("enquadramento", {}))
    cenas = v.s.get("cenas", [])
    for info, c in zip(v.cenas(cenas), cenas):
        if info:
            v.visual(c.get("visual"), info[0], info[1], info[2], z)
    return v.resultado()


def main(spec):
    m = Motor(spec, "codigo")
    j, c, enq = m.j, m.c, m.enq
    esc, vx, vy, leg = geometria(enq)
    c.css.append('#bk{left:0;top:0;width:1080px;height:1920px;background:radial-gradient(ellipse at 50% 28%,var(--papel2) 0%,var(--papel) 70%)}')
    c.body.append('<div id="bk" class="a"></div>')
    m.selo()
    z = zona(enq)

    def desenha(i, s, pid, t0, t1):
        m.titulo(pid, s.get("titulo", ""), t0)
        ja = visual(m, s.get("visual"), pid, t0, t1, z)
        m.logos_da_cena(pid, t0, t1, ja, (540, z["y"] + z["h"] / 2))

    m.cenas(j.get("cenas", []), desenha)
    corte = j.cutout()
    base = vy + 1920 * esc
    mascara = ""
    if base < 1915:          # o corpo recortado não chega na base do quadro: some num degradê, sem corte seco
        mascara = ";-webkit-mask-image:linear-gradient(#000 78%,transparent);mask-image:linear-gradient(#000 78%,transparent)"
    c.body.append(c.video(corte, f"position:absolute;left:{vx:.0f}px;top:{vy:.0f}px;width:{1080 * esc:.0f}px;height:{1920 * esc:.0f}px;z-index:20{mascara}", "cut"))
    m.legenda_pilula(round(leg))
    m.fecha()


if __name__ == "__main__":
    main(sys.argv[1])
