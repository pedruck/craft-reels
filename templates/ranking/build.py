#!/usr/bin/env python3
"""ranking: o vídeo inteiro de fundo, um título e uma tier list (S, A, B…) que vai se preenchendo:
cada item entra na sua faixa quando é falado. Legenda em pílula abaixo do queixo.
Baseado no /ranking-list de Artem Novitckii (claude-editing-skills, MIT).

cenas.json: {"template": "ranking", "titulo": "Quem *classifica* melhor", "tiers": ["S", "A", "C"],
             "itens": [{"texto": "Jev", "icone": "⚡", "tier": "S", "at": "Jev"}, ...]}
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motor import TITULO_MAX, TITULO_PX, Motor, Validador, largura, largura_rica, posicao_legenda, rich, video_cheio  # noqa: E402

TOPO, LINHA, PAINEL_W = 380, 118, 860


def validar(spec_path):
    v = Validador(spec_path)
    s = v.s
    tiers = s.get("tiers") or ["S", "A", "B", "C"]
    if largura_rica(s.get("titulo", ""), TITULO_PX) > TITULO_MAX:
        v.erros.append(f"título largo demais ({largura_rica(s.get('titulo', ''), TITULO_PX):.0f}px > {TITULO_MAX})")
    por_tier, ultimo = {}, -1
    for k, it in enumerate(s.get("itens", [])):
        nome = f"item {k + 1} \"{it.get('texto', '')}\""
        if it.get("tier") not in tiers:
            v.erros.append(f"{nome}: tier \"{it.get('tier')}\" não está em {tiers}")
        v.logo(it.get("logo"), nome)
        t = v.t(it.get("at"), nome)
        if t is not None and t < ultimo:
            v.avisos.append(f"aviso: {nome} entra antes do item anterior")
        ultimo = t if t is not None else ultimo
        por_tier[it.get("tier")] = por_tier.get(it.get("tier"), 0) + 48 + largura(it.get("texto", ""), 34) + 70
    for t, w in por_tier.items():
        if w > PAINEL_W - 150:
            v.erros.append(f"tier {t}: itens demais para uma linha ({w:.0f}px > {PAINEL_W - 150}); textos mais curtos")
    _, r = video_cheio(s.get("enquadramento") or {})
    if r and TOPO + LINHA * len(tiers) > r.get("olho_y", 2000) - 60:
        v.erros.append(f"a tier list ({len(tiers)} faixas) desceria até {TOPO + LINHA * len(tiers)}px, sobre os olhos (y={r['olho_y']:.0f}) "
                       "→ use menos tiers; se nem 2 couberem, este vídeo não serve para o ranking (use o explainer)")
    elif r and TOPO + LINHA * len(tiers) > r.get("cabelo_y", 2000) - 10:
        v.avisos.append(f"aviso: a tier list desce até {TOPO + LINHA * len(tiers)}px e a cabeça começa em {r['cabelo_y']}px — use menos tiers")
    return v.resultado()


def main(spec):
    m = Motor(spec, "ranking")
    j, c, enq = m.j, m.c, m.enq
    tiers = j.get("tiers") or ["S", "A", "B", "C"]
    cores = m.t["tiers"]
    c.css.append(f'''
#dim{{left:0;top:0;width:1080px;height:1920px;background:linear-gradient(rgba(var(--sombra-rgb),.62),rgba(var(--sombra-rgb),.08) 55%)}}
#tl{{left:{(1080 - PAINEL_W) // 2}px;top:{TOPO}px;width:{PAINEL_W}px;border-radius:26px;overflow:hidden;background:rgba(var(--escuro-rgb),.93);
  box-shadow:0 20px 50px rgba(0,0,0,.4)}}
.tr{{display:flex;height:{LINHA}px;border-bottom:2px solid rgba(255,255,255,.07)}}
.tl{{width:{LINHA}px;display:grid;place-items:center;font:800 56px 'JetBrains Mono';color:var(--sobre-tier);flex:none}}
.ti{{flex:1;display:flex;align-items:center;gap:14px;padding-left:22px}}
.it{{display:flex;align-items:center;gap:10px;background:#fff;border-radius:16px;padding:10px 18px;font:800 34px 'Inter';color:#1e1e2e;white-space:nowrap}}''')
    estilo, r = video_cheio(enq)
    c.body.append(c.video(j.clip, estilo, "bg"))
    c.body.append('<div id="dim" class="a"></div>')
    m.selo()
    m.titulo("rk", j.get("titulo", ""), 0.1, claro=True)
    linhas = []
    for k, t in enumerate(tiers):
        itens = "".join(
            f'<div class="it" id="it{n}">{m.logo_html(it["logo"], 44, "box-shadow:none") if it.get("logo") else html.escape(it.get("icone", ""))}'
            f'<span>{rich(it["texto"])}</span></div>' for n, it in enumerate(j.get("itens", [])) if it["tier"] == t)
        linhas.append(f'<div class="tr"><div class="tl" style="background:{cores[min(k, len(cores) - 1)]}">{html.escape(t)}</div>'
                      f'<div class="ti">{itens}</div></div>')
    c.body.append(f'<div id="tl" class="a">{"".join(linhas)}</div>')
    c.js.append('tl.fromTo("#tl",{y:30,autoAlpha:0},{y:0,autoAlpha:1,duration:.4,ease:"power3.out"},0.3);')
    tempos = [0.0]
    for n, it in enumerate(j.get("itens", [])):
        t = j.t(it.get("at"), 1 + n)
        tempos.append(t)
        c.js.append(f'tl.fromTo("#it{n}",{{scale:.2,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.38,ease:"back.out(2.2)"}},{t:.3f});')
    falados = {it.get("logo") for it in j.get("itens", [])}
    m.logos_da_cena("rk", 0, c.dur, falados, None)
    m.legenda_pilula(round(posicao_legenda(r["queixo_y"])[0]))
    m.fecha(sorted(set(round(t, 2) for t in tempos)))


if __name__ == "__main__":
    main(sys.argv[1])
