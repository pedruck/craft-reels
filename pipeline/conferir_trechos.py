#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = ["faster-whisper", "numpy"]
# ///
"""Confere o vídeo cortado trecho a trecho e acrescenta em cortes.json o que ainda tem que sair.

    conferir_trechos.py <pasta>        (lê bruto.mp4, bruto.transcript.json, cortes.json, cortado.trechos.json)

Por que existe: a transcrição do vídeo inteiro esconde defeito. Com contexto, o Whisper
"conserta" o que ouve: "tanto em taxa de aceito" + "Tanto em taxa de acertos" vira uma
frase só, e um "repaz" de meio segundo vira "O". Aqui cada trecho mantido é transcrito
SOZINHO, sem o vizinho como contexto (~2 min para 2 min de vídeo) e entram as regras:

  A  lasca      trecho com menos de 0,25 s sai; de 0,25 a 1 s só fica se o que ele diz
                bate com a fala esperada naquele ponto (senão é ruído, respiro ou pedaço)
  B  refaz      trecho com "refaz"/"repaz"/"rapaz"/"corta" escondido: sai a tomada
     repetição  trecho que termina (ou começa) dizendo o mesmo que o próximo começa: sai
                a primeira versão
     ruído      trecho curto que vira "Obrigado", "Boa noite"… (Whisper inventando em cima
                de silêncio) sai

Imprime só o que mudou. Última linha: "LIMPO" ou "N cortes novos" — rode cortar.py e
este de novo até dar LIMPO (a etapa 3 do craft faz o laço sozinha).
"""
import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

P = Path(sys.argv[1])
MARCADOR = re.compile(r"^(re[fp]a(z|s|ss|c|ca|co|ssa)|refazer|refazendo|corta|rapaz|recomeca)$")
INVENTADO = {"obrigado", "obrigada", "boa noite", "tchau", "legenda", "legendas", "e ai", "e isso ai", "valeu",
             "inscrevase", "ate a proxima", "musica", "aplausos", "risos"}
VAZIAS = {"a", "o", "e", "de", "do", "da", "que", "um", "uma", "em", "no", "na", "com", "se", "os", "as", "pra", "para"}


def nu(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return "".join(c for c in w if c.isalnum() and not unicodedata.combining(c))


def parecido(a, b):
    return a == b or (len(a) > 3 and len(b) > 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.7)


ficam = json.loads((P / "cortado.trechos.json").read_text())["ficam"]
crus = json.loads((P / "bruto.transcript.json").read_text())
crus = crus.get("words") or [w for s in crus["segments"] for w in s["words"]]

pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(P / "bruto.mp4"), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0

# Cada janela de 30 s do Whisper custa o mesmo, curta ou cheia. Então os trechos são
# empacotados em janelas de até ~26 s, separados por 1 s de silêncio, e trechos VIZINHOS
# nunca dividem janela (k vai para a janela k % G): o Whisper não tem como juntar a
# repetição de um trecho com o seguinte, que é exatamente o que se quer pegar.
SR = 16000
GAP = np.zeros(SR, np.float32)
pedacos = []  # (k, ini, fim) no bruto, trechos longos quebrados em até 12 s
for k, (a, b) in enumerate(ficam):
    t = a
    while t < b - 0.01:
        pedacos.append((k, t, min(b, t + 12)))
        t += 12
total = sum(b - a for _, a, b in pedacos)
G = max(2, int(total // 24) + 1)
janelas = [[] for _ in range(G)]
for p in pedacos:
    janelas[p[0] % G].append(p)
lotes = []  # cada lote: (audio, [(k, ini_no_lote, ini_no_bruto, dur)])
for jan in janelas:
    atual, mapa, t = [], [], 0.0
    for k, a, b in jan:
        if t + (b - a) > 26 and atual:
            lotes.append((np.concatenate(atual), mapa))
            atual, mapa, t = [], [], 0.0
        atual += [audio[int(a * SR):int(b * SR)], GAP]
        mapa.append((k, t, a, b - a))
        t += (b - a) + 1.0
    if atual:
        lotes.append((np.concatenate(atual), mapa))

modelo = WhisperModel("large-v3", device="cpu", compute_type="int8")
ditas = {k: [] for k in range(len(ficam))}
for som, mapa in lotes:
    segs, _ = modelo.transcribe(som, language="pt", vad_filter=False, word_timestamps=True, beam_size=5,
                                condition_on_previous_text=False)
    for s in segs:
        for w in s.words or []:
            meio = (w.start + w.end) / 2
            for k, t0, a, dur in mapa:
                if t0 - 0.1 <= meio <= t0 + dur + 0.1:
                    ditas[k].append({"w": w.word.strip(), "n": nu(w.word), "s": max(a, a + w.start - t0),
                                     "e": min(ficam[k][1], a + w.end - t0)})
                    break
for k in ditas:
    ditas[k].sort(key=lambda w: w["s"])
for k in ditas:
    ditas[k] = [w for w in ditas[k] if w["n"]]

novos = []


def corta(a, b, regra, nota):
    novos.append({"inicio": round(a, 3), "fim": round(b, 3), "tipo": "conferencia", "aplicar": True, "nota": f"{regra}: {nota}"})


texto = lambda ws: " ".join(w["w"] for w in ws)  # noqa: E731
fora = set()
for k, (a, b) in enumerate(ficam):
    d, ws = b - a, ditas[k]
    if k == len(ficam) - 1 and d < 0.25:
        corta(a - 0.01, b + 0.01, "A lasca", f"{d:.2f}s no fim")
        fora.add(k)
        continue
    if d < 0.25:
        corta(a - 0.01, b + 0.01, "A lasca", f"{d:.2f}s, diz \"{texto(ws)}\"")
        fora.add(k)
        continue
    # B refaz escondido
    m = next((i for i, w in enumerate(ws) if MARCADOR.match(w["n"])), None)
    if m is not None and not (ws[m]["n"] in ("corta", "rapaz") and m < len(ws) - 1):
        if d < 1.5 or m == len(ws) - 1:
            ini = a
            for i in range(m - 1, -1, -1):  # volta até o começo da frase abandonada dentro do trecho
                if ws[i]["w"].endswith((".", "?", "!")) and not ws[i]["w"].endswith("..."):
                    ini = ws[i]["e"] + 0.05
                    break
            corta(ini - 0.01, b + 0.01, "B refaz", f"\"{texto(ws)}\"")
            fora.add(k) if ini <= a else None
        else:
            corta(a - 0.01, ws[m]["e"] + 0.08, "B refaz", f"\"{texto(ws[:m + 1])}\" no começo do trecho")
        continue
    # A/B ruído: trecho curto cujo texto não bate com o que devia estar ali
    if d < 1.0:
        esperado = {nu(w["word"]) for w in crus if a - 0.3 <= (float(w["start"]) + float(w["end"])) / 2 <= b + 0.3} - {""}
        frase = " ".join(w["n"] for w in ws)
        bate = any(parecido(w["n"], e) for w in ws for e in esperado)
        if not ws or frase in INVENTADO or not bate:
            corta(a - 0.01, b + 0.01, "A lasca", f"{d:.2f}s, diz \"{texto(ws) or '(nada)'}\", esperado \"{' '.join(sorted(esperado)) or '(nada)'}\"")
            fora.add(k)

# B repetição entre trechos vizinhos (pulando os que já vão sair)
ordem = [k for k in range(len(ficam)) if k not in fora and ditas[k]]
for k, k2 in zip(ordem, ordem[1:]):
    A, B_ = ditas[k], ditas[k2]
    na, nb = [w["n"] for w in A], [w["n"] for w in B_]
    feito = False
    # o fim de k repete o começo de k2: "…tanto em taxa de" | "tanto em taxa de acertos…"
    for n in range(min(len(na), len(nb), 8), 1, -1):
        # 2+ palavras de conteúdo: "para a IA. | E a IA pode" é fala normal, não regravação
        if all(parecido(x, y) for x, y in zip(na[-n:], nb[:n])) and len(set(na[-n:]) - VAZIAS) >= 2:
            ini = A[-n]["s"] - 0.05
            if ini - ficam[k][0] < 0.6:  # não deixa um pedacinho ("tanto") antes da repetição
                ini = ficam[k][0] - 0.01
            corta(max(ini, ficam[k][0] - 0.01), ficam[k][1] + 0.01, "B repetição",
                  f"\"{texto(A[-n:])}\" e logo depois \"{texto(B_[:n])}\"")
            feito = True
            break
    if feito:
        continue
    # k inteiro é uma tentativa do começo de k2: "tanto em taxa de aceito" | "Tanto em taxa de acertos e…"
    n = 0
    while n < min(len(na), len(nb)) and parecido(na[n], nb[n]):
        n += 1
    if n >= 2 and n >= len(na) - 1 and len(set(na[:n]) - VAZIAS) >= 2:
        corta(ficam[k][0] - 0.01, ficam[k][1] + 0.01, "B repetição", f"\"{texto(A)}\" refeito em \"{texto(B_[:n + 2])}…\"")

if novos:
    plano = json.loads((P / "cortes.json").read_text())
    plano["cortes"] += novos
    (P / "cortes.json").write_text(json.dumps(plano, ensure_ascii=False, indent=1))
    for c in novos:
        print(f"  {c['inicio']:7.2f}-{c['fim']:7.2f}  {c['nota']}")
    print(f"{len(novos)} cortes novos")
else:
    print("LIMPO")
(P / "trechos.conferidos.json").write_text(json.dumps(
    [{"trecho": k, "inicio": a, "fim": b, "diz": texto(ditas[k])} for k, (a, b) in enumerate(ficam)], ensure_ascii=False, indent=1))
