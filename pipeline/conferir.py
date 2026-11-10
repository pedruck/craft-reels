#!/usr/bin/env python3
"""Etapa 9: checagens automáticas do reel final e o relatorio.md.

    conferir.py <pasta> [--sem-limite|--com-limite]

Checa: duração ≤ 60 s; volume -14 LUFS ±1; nenhum trecho mantido < 0,25 s;
avisos de geometria que o template gravou (texto largo, visual encostando no rosto,
algo na faixa que o Instagram cobre); folha de cenas existe. Imprime uma linha AVISO
por problema e, na última linha, o resumo. O relatorio.md tem o que o agente conta à
pessoa (antes → depois, cortes agrupados, suspeitas mantidas, cenas, correções).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

P = Path(sys.argv[1])
SEM_LIMITE = "--sem-limite" in sys.argv


def j(nome, padrao=None):
    p = P / nome
    return json.loads(p.read_text()) if p.exists() else padrao


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def lufs(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else float("nan")


avisos = []
final = P / "final.mp4"
d_final, d_bruto = dur(final), dur(P / "bruto.mp4")
if d_final > 60.05 and not SEM_LIMITE:
    avisos.append(f"duração {d_final:.1f}s passa de 60 s → a pessoa escolhe uma cena para sair (lista no relatorio.md)")
L = lufs(final)
if not (-15.0 <= L <= -13.0):
    avisos.append(f"volume {L:.1f} LUFS fora de -14 ±1 → rode de novo a etapa 4 (apague audio.json)")
ficam = j("cortado.trechos.json", {"ficam": []})["ficam"]
lascas = [f"{a:.2f}s" for a, b in ficam if b - a < 0.25]
if lascas:
    avisos.append(f"{len(lascas)} trecho(s) com menos de 0,25 s ({', '.join(lascas[:4])}) → craft corte em cada um")
geo = j("reel.checagem.json", {"avisos": []})
avisos += geo.get("avisos", [])
if not (P / "reel.cenas.jpg").exists():
    avisos.append("reel.cenas.jpg não foi gerada → rode a etapa 7 de novo")

# ------------------------------------------------------------------ relatório
plano = j("cortes.json", {"cortes": []})
ap = [c for c in plano["cortes"] if c.get("aplicar")]
grupo = {}
for c in ap:
    grupo.setdefault(c["tipo"], []).append(c)
susp = [c for c in plano["cortes"] if not c.get("aplicar") and c["tipo"] not in ("pausa", "inicio", "fim")]
spec = j("spec.json", {})
cen = spec.get("cenas") or spec.get("itens") or []
dur_j = j("duracao.json", {})
audio = j("audio.json", {})
enq = j("enquadramento.json", {})
nomes_tipo = {"refaca": "regravações marcadas com \"refaz\"", "gaguejo": "gaguejos e hesitações", "pausa": "pausas encurtadas",
              "tomada": "tomadas repetidas (pelo roteiro)", "conferencia": "sobras achadas na conferência trecho a trecho",
              "manual": "cortes manuais", "inicio": "silêncio do começo", "fim": "silêncio do fim"}
R = [f"# Relatório — {P.name}", "",
     f"- **Duração:** {d_bruto:.0f}s bruto → {dur(P / 'cortado.mp4'):.1f}s cortado → **{d_final:.1f}s final**"
     + (f" (acelerado {dur_j.get('fator')}x, tom da voz igual)" if dur_j.get("fator", 1) > 1 else ""),
     f"- **Volume:** {audio.get('antes_lufs', '?')} → {L:.1f} LUFS (alvo -14)",
     f"- **Template:** {spec.get('template', '?')} · paleta {enq.get('paleta')} · fundo {enq.get('fundo')} ({enq.get('fundo_motivo', '')})",
     "", "## Cortes", ""]
for t, cs in sorted(grupo.items(), key=lambda x: -len(x[1])):
    R.append(f"- {len(cs)} {nomes_tipo.get(t, t)}")
    if t not in ("pausa", "inicio", "fim"):
        for c in cs[:8]:
            R.append(f"  - {c['inicio']:.1f}s: {c.get('nota', '')[:110]}")
if susp:
    R += ["", "## Suspeitas mantidas (não cortadas)", ""]
    R += [f"- {c['inicio']:.1f}s: {c.get('nota', '')[:120]}" for c in susp]
R += ["", "## Cenas", ""]
for i, c in enumerate(cen):
    R.append(f"{i + 1}. {re.sub(r'[*]', '', str(c.get('titulo') or c.get('texto', '')))} → {(c.get('visual') or {}).get('type') or c.get('tier') or (str(len(c.get('cartoes', []))) + ' cartões' if c.get('cartoes') else 'frase')}")
trocas = []
for nome in ("transcrever-limpo.txt", "legenda-roteiro.txt"):
    lp = P / "log" / nome
    if lp.exists():
        trocas += [ln.strip() for ln in lp.read_text().splitlines() if "->" in ln and not ln.strip().startswith("$")]
if trocas:
    R += ["", "## Palavras da legenda corrigidas", ""] + [f"- {t}" for t in trocas[:20]]
R += ["", "## Checagens", ""] + ([f"- ⚠ {a}" for a in avisos] or ["- tudo dentro das regras"])
R += ["", "## Para a pessoa conferir", "",
      "- assistir inteiro antes de postar, principalmente as emendas com zoom",
      "- a legenda nos nomes próprios"] + (["- as suspeitas mantidas acima"] if susp else [])
(P / "relatorio.md").write_text("\n".join(R) + "\n")
for a in avisos:
    print(f"AVISO {a}")
print(f"{d_final:.1f}s, {L:.1f} LUFS, {len(ficam)} trechos; {len(avisos)} aviso(s); relatorio.md")
