#!/usr/bin/env python3
"""destaque: o vídeo inteiro de fundo, um cartão de post da comunidade no topo (logo, nome, @) com a
frase de cada cena, e a legenda em palavras grandes no peito. Bom para um dado ou uma frase de impacto.
Baseado no /trial-reels de Artem Novitckii (claude-editing-skills, MIT). Não tem lugar para logo de produto.

cena: {"at": 0, "texto": "Um modelo que classifica *17×* mais barato que um LLM pequeno"}
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import LEG_MIN, PEITO_MARGEM, PEITO_QUEIXO, LOGO_COMUNIDADE, Motor, Validador, largura_rica, rich, video_cheio  # noqa: E402

COMUNIDADE = {"nome": "Software Craftsmanship", "sub": "@software_craftsmanship · Brasília"}


def validar(spec_path):
    v = Validador(spec_path)
    cenas = v.s.get("cenas", [])
    v.cenas(cenas, campo_titulo=None)
    for k, c in enumerate(cenas):
        palavras = str(c.get("texto", "")).split()
        linhas, atual = 1, 0.0
        for p in palavras:
            w = largura_rica(p + " ", 50)
            if atual + w > 850:
                linhas, atual = linhas + 1, w
            else:
                atual += w
        if linhas > 3:
            v.erros.append(f"cena {k + 1}: frase longa demais para o cartão ({linhas} linhas, máximo 3)")
    return v.resultado()


def main(spec):
    m = Motor(spec, "destaque")
    j, c, enq = m.j, m.c, m.enq
    c.css.append('''#dim{left:0;top:0;width:1080px;height:1920px;background:linear-gradient(rgba(0,0,0,.25),rgba(0,0,0,0) 40%,rgba(0,0,0,.35))}
#post{left:80px;top:236px;width:920px;padding:28px 36px 34px;border-radius:28px;background:var(--cartao);color:var(--tinta);box-shadow:0 16px 40px rgba(0,0,0,.25)}
#post .cab{display:flex;align-items:center;gap:18px}
#post .cab img{width:70px;height:70px;border-radius:50%}
#post .nm{font:800 30px Inter}
#post .sb{font:500 23px Inter;color:var(--cinza)}
.fr{font:800 50px/1.12 'Inter';letter-spacing:-.02em;margin-top:20px;visibility:hidden;position:absolute;left:36px;right:36px}
#frs{position:relative;height:180px}''')
    estilo, r = video_cheio(enq, queixo_max=PEITO_QUEIXO)
    c.body.append(c.video(j.clip, estilo, "bg"))
    c.body.append(f'<div id="dim" class="a"></div><div id="post" class="a"><div class="cab"><img src="{c.asset(LOGO_COMUNIDADE)}">'
                  f'<div><div class="nm">{COMUNIDADE["nome"]}</div><div class="sb">{COMUNIDADE["sub"]}</div></div></div><div id="frs">')
    cenas = j.get("cenas", [])
    ini = [0.0] + [j.t(s["at"]) for s in cenas[1:]]
    for i, s in enumerate(cenas):
        t0 = ini[i]
        c.body.append(f'<div class="fr" id="fr{i}">{rich(s.get("texto", ""))}</div>')
        c.js.append(f'tl.set("#fr{i}",{{visibility:"visible"}},{t0:.3f});tl.fromTo("#fr{i}",{{y:16,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3}},{t0:.3f});')
        if i + 1 < len(cenas):
            c.js.append(f'tl.to("#fr{i}",{{autoAlpha:0,duration:.18}},{ini[i + 1] - 0.18:.3f});')
    c.body.append("</div></div>")
    c.js.append('tl.fromTo("#post",{y:-30,autoAlpha:0},{y:0,autoAlpha:1,duration:.4,ease:"power3.out"},0.05);')
    m.legenda_peito(round(min(1400, max(LEG_MIN, r["queixo_y"] + PEITO_MARGEM))))
    m.fecha(ini)


if __name__ == "__main__":
    main(sys.argv[1])
