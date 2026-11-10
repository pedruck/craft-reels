#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Propõe os cortes de um vídeo falado: silêncio, gaguejo e tomada marcada com "refaça".

    planejar_cortes.py <video> <transcricao.json> <cortes.json> [--pausa 0.28] [--sem-pausas]

Lê a transcrição (tempo por palavra) e o áudio, e grava cortes.json com cada
trecho a remover, o motivo e o texto em volta. Cada corte vem com "aplicar":
true quando é seguro, false quando é só suspeita para você ouvir e decidir.
O relatório impresso mostra cada corte no meio da frase, que é como se revisa.

O que vira corte (regras da skill):
  refaca     "refaça"/"refaz"/"corta" no fim de uma frase: sai a frase inteira que
             ele abandonou, até o marcador, e a pausa depois dele
  gaguejo    palavra repetida ("a a gente"), trecho repetido ("a gente pode a gente
             pode"), palavra começada e recomeçada ("confi configurar"), "é," e "hã"
             soltos, e som de vogal parada ("ééé") que o Whisper engoliu dentro de
             uma palavra esticada
  pausa      buraco entre palavras acima de --pausa; sobra uma pausa curta, maior
             depois de ponto final do que no meio da frase
  inicio/fim silêncio antes da primeira palavra e depois da última
"""
import argparse
import json
import re
import subprocess
import unicodedata

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("transcricao")
ap.add_argument("saida")
ap.add_argument("--pausa", type=float, default=0.28, help="silêncio acima disso é encurtado (s)")
ap.add_argument("--sem-pausas", action="store_true", help="segunda passada, no vídeo já cortado: só refaz e gaguejo")
ap.add_argument("--resumo", action="store_true", help="só regravações, gaguejos e suspeitas (as pausas vão só para o JSON)")
a = ap.parse_args()

MARCADOR = re.compile(r"^(re[fp]a(z|s|ss|c|ca|co|ssa)|refazer|refazendo|corta|rapaz|recomeca|recomecando)$")  # Whisper escreve "Repaz", "refas"…
HESITACAO = re.compile(r"^(é{2,}|e{2,}|éh+|eh+|hã+|ã+h|ahn+|hu?m+|uh+m?)$")
SR, HOP = 16000, 320  # janelas de 20 ms
VAZIAS = {"a", "o", "e", "de", "do", "da", "que", "um", "uma", "em", "no", "na", "com", "se", "eu", "ele", "ela",
          "os", "as", "pra", "para", "por", "vai", "ja", "isso", "esse", "essa", "entao", "mas", "voce", "gente"}


def nu(w):
    """palavra comparável: minúscula, sem acento e sem pontuação"""
    w = unicodedata.normalize("NFKD", w.lower())
    return "".join(c for c in w if c.isalnum() and not unicodedata.combining(c))


def fecha_frase(w):
    """ponto final fecha frase; reticências não ("uma maneira... refaz" é a frase abandonada)"""
    w = w.rstrip()
    return w.endswith((".", "?", "!")) and not w.endswith(("...", "…"))


# ------------------------------------------------------------------ áudio
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
DUR = len(x) / SR
n = len(x) // HOP
fr = x[: n * HOP].reshape(n, HOP)
db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
# espectro por janela, para achar vogal sustentada (o "ééé" tem espectro parado)
win = np.hanning(512)
pad = np.concatenate([x, np.zeros(512)])
spec = np.array([np.abs(np.fft.rfft(pad[i * HOP: i * HOP + 512] * win))[:160] for i in range(n)])
logs = np.log(spec + 1e-6)
logs -= logs.mean(1, keepdims=True)
flux = np.r_[0, np.sqrt(((logs[1:] - logs[:-1]) ** 2).mean(1))]


def jan(t):
    return int(max(0, min(n - 1, round(t * SR / HOP))))


# ------------------------------------------------------------------ palavras
d = json.load(open(a.transcricao))
raw = d.get("words") or [w for s in d.get("segments", []) for w in s.get("words", [])]
ws, fim_ant = [], 0.0
for w in raw:  # o Whisper às vezes começa uma palavra antes da anterior terminar
    st = max(float(w["start"]), fim_ant)
    en = max(float(w["end"]), st + 0.05)
    ws.append({"w": w["word"].strip(), "n": nu(w["word"]), "s": st, "e": en, "cru": float(w["end"]) - float(w["start"])})
    fim_ant = en
ws = [w for w in ws if w["n"]]
# o Whisper repete a última palavra de um trecho no começo do seguinte, com duração zero
ws = [w for k, w in enumerate(ws) if not (w["cru"] < 0.04 and any(
    0 <= q < len(ws) and ws[q]["n"] == w["n"] and ws[q]["cru"] >= 0.04 for q in (k - 1, k + 1)))]
if not ws:
    raise SystemExit("transcrição vazia")

# piso de ruído e nível de voz, medidos no próprio vídeo
dentro = np.zeros(n, bool)
for w in ws:
    dentro[jan(w["s"]): jan(w["e"]) + 1] = True
voz_db = np.percentile(db[dentro], 50)
piso_db = np.percentile(db[~dentro], 30) if (~dentro).sum() > 20 else np.percentile(db, 5)
# acima disso tem voz. Ancorado na voz: gravação com trecho mudo digital (-78 dB) puxaria o
# limiar para baixo e a respiração/ruído da sala (~-45 dB) deixaria de contar como pausa
LIMIAR = max(piso_db + 0.45 * (voz_db - piso_db), voz_db - 9)

# ------------------------------------------------------------------ silêncio e "ééé", medidos no áudio
# O Whisper estica as palavras por cima das pausas e engole o "ééé" dentro da palavra
# vizinha, então isso não se acha pela transcrição: acha-se pelo som.
liso = np.convolve(db, np.ones(3) / 3, mode="same")
mudo = liso < LIMIAR - 1.5
trechos, k = [], 0  # [(mudo?, ini, fim)] em janelas
while k < n:
    j = k
    while j < n and mudo[j] == mudo[k]:
        j += 1
    trechos.append((bool(mudo[k]), k, j))
    k = j
# silêncio de menos de 60 ms é só consoante: funde com a voz em volta
fund = []
for t in trechos:
    if fund and (t[0] and (t[2] - t[1]) < 3 or fund[-1][0] == t[0]):
        fund[-1] = (fund[-1][0], fund[-1][1], t[2])
    else:
        fund.append(t)
trechos = fund
s_ = lambda j: j * HOP / SR  # noqa: E731
FLUX_PARADO = np.percentile(flux[~mudo], 15)
SILENCIOS = [(s_(i0), s_(i1)) for m, i0, i1 in trechos if m and s_(i1 - i0) >= 0.4]


def comeca_frase(q):
    """a palavra q abre frase: ponto antes, ou silêncio de verdade perto dela (o Whisper
    estica as palavras por cima das pausas, então o silêncio pode cair dentro da vizinha)"""
    if q == 0 or fecha_frase(ws[q - 1]["w"]):
        return True
    return any(ws[q - 1]["s"] < s1 and s0 < ws[q]["e"] + 0.8 for s0, s1 in SILENCIOS)


cortes = []


def corte(ini, fim, tipo, aplicar, nota=""):
    if fim - ini >= 0.06:
        cortes.append({"inicio": round(ini, 3), "fim": round(fim, 3), "tipo": tipo, "aplicar": aplicar, "nota": nota})


# início e fim
if ws[0]["s"] > 0.25 and not a.sem_pausas:
    corte(0, ws[0]["s"] - 0.15, "inicio", True)
if DUR - ws[-1]["e"] > 0.5 and not a.sem_pausas:
    corte(ws[-1]["e"] + 0.35, DUR, "fim", True)

# refaça: a frase abandonada vai embora inteira
refeitos = set()
for i, w in enumerate(ws):
    if not MARCADOR.match(w["n"]):
        continue
    if w["n"] in ("corta", "rapaz") and i + 1 < len(ws) and ws[i + 1]["s"] - w["e"] < 0.35 and not w["w"].endswith((".", "!")):
        continue  # "corta"/"rapaz" no meio da frase são palavras normais (o Whisper às vezes ouve "refaz" como "rapaz")
    # volta até o começo da frase: ponto final antes, ou um buraco grande
    j = i
    while (j > 0 and not fecha_frase(ws[j - 1]["w"]) and ws[j]["s"] - ws[j - 1]["e"] < 0.7
           and w["s"] - ws[j - 1]["s"] < 12):  # sem pontuação, não volta mais que 12 s
        j -= 1
    # ele costuma recomeçar de um pouco antes da frase que errou ("Isso vem com dois
    # lados… refaz. E isso tem dois lados"): procura nos 30 s anteriores o ponto cujas
    # palavras mais batem com o começo da regravação e corta desde ali
    nota_extra = ""
    depois = [w["n"] for w in ws[i + 1:i + 9] if w["n"] not in VAZIAS][:5]
    if len(depois) >= 2:
        melhor, nota_p = None, 0
        for p_ in range(i - 1, -1, -1):
            if ws[i]["s"] - ws[p_]["s"] > 30:
                break
            if p_ > 0 and not (fecha_frase(ws[p_ - 1]["w"]) or ws[p_]["s"] - ws[p_ - 1]["e"] > 0.5 or p_ == j):
                continue  # só começos de frase
            janela = {w["n"] for w in ws[p_:p_ + 7]} - VAZIAS
            pts = len(janela & set(depois))
            if pts >= 3 and pts >= nota_p:
                melhor, nota_p = p_, pts
        if melhor is not None and melhor < j:
            nota_extra = f"; recomeçou de \"{' '.join(w['w'] for w in ws[melhor:melhor + 6])}…\""
            j = melhor
    prox = ws[i + 1]["s"] - 0.12 if i + 1 < len(ws) else DUR
    texto = " ".join(x["w"] for x in ws[j: i + 1])
    # na segunda passada o vídeo já não tem pausas longas nem pontuação confiável: só avisa
    corte(ws[j]["s"] - 0.05, prox, "refaca", not a.sem_pausas, f"tomada abandonada: \"{texto}\"{nota_extra}"
          + (" — segunda passada: confira onde a tomada começa e corte à mão" if a.sem_pausas else ""))
    refeitos.update(range(j, i + 1))

# gaguejo escrito na transcrição
for i in range(len(ws) - 1):
    if i in refeitos:
        continue
    a_, b_ = ws[i], ws[i + 1]
    # palavra repetida ou começada e recomeçada
    igual = a_["w"].lower().strip(".,?!…") == b_["w"].lower().strip(".,?!…")  # com acento: "E é" não é repetição
    if igual or (len(a_["n"]) >= 3 and b_["n"].startswith(a_["n"]) and a_["w"][-1:] not in ".,?!"):
        fantasma = min(a_["cru"], b_["cru"]) < 0.04
        corte(a_["s"] - 0.02, b_["s"] - 0.03, "gaguejo", not fantasma, f"\"{a_['w']} {b_['w']}\""
              + (" — palavra de duração zero, o Whisper pode ter duplicado" if fantasma else ""))
    # trecho repetido colado: "a gente pode a gente pode"
    for k in (2, 3, 4):
        if i + 2 * k <= len(ws) and [w["n"] for w in ws[i:i + k]] == [w["n"] for w in ws[i + k:i + 2 * k]]:
            fantasma = min(w["cru"] for w in ws[i:i + 2 * k]) < 0.04
            corte(a_["s"] - 0.02, ws[i + k]["s"] - 0.03, "gaguejo", not fantasma,
                  "repetiu \"" + " ".join(w["w"] for w in ws[i:i + k]) + "\""
                  + (" — palavra de duração zero, o Whisper pode ter duplicado" if fantasma else ""))
            break
    # hesitação: "hã", "hum", "ééé" escritos, e o "é," solto entre vírgulas
    cru = a_["w"].lower().strip(".,?!…")
    solto = cru == "é" and i > 0 and ws[i - 1]["w"].endswith(",") and a_["w"].endswith(",")
    if HESITACAO.match(cru) or solto:
        prev_e = ws[i - 1]["e"] if i else a_["s"] - 0.1
        corte(prev_e + 0.02, b_["s"] - 0.03, "gaguejo", True, f"hesitação \"{a_['w']}\"")

# repetição próxima (não colada): regravação sem "refaz", ou só aviso
ate = -1
for i in range(len(ws) - 3):
    if i < ate:
        continue  # já está dentro de uma repetição achada
    for k in (4, 3, 2):
        bloco = [w["n"] for w in ws[i:i + k]]
        if all(len(t) <= 2 for t in bloco) or bloco[:2] == ["a", "gente"]:
            continue
        for j in range(i + k + 1, min(len(ws) - k + 1, i + k + 5)):
            if [w["n"] for w in ws[j:j + k]] == bloco and ws[j]["s"] - ws[i]["e"] < 6:
                # começou a frase, parou e começou de novo do mesmo jeito: é regravação
                regravou = k >= 3 and comeca_frase(i) and comeca_frase(j)
                if regravou or ws[j]["s"] - ws[i]["e"] < 2.5:
                    corte(ws[i]["s"] - 0.02, ws[j]["s"] - 0.03, "gaguejo", regravou,
                          "repetiu \"" + " ".join(w["w"] for w in ws[i:i + k]) + "\" "
                          + ("recomeçando a frase: regravação" if regravou else "logo depois; ouça se o primeiro é tropeço"))
                    ate = j
                    break
        else:
            continue
        break




def frase_antes(t):
    """a palavra que termina logo antes de t (para saber se a pausa fecha frase)"""
    ant = [w for w in ws if w["s"] < t]
    return ant[-1]["w"] if ant else ""


def resto_de(t, longo=0.0):
    """quanto de pausa sobra: mais depois de fim de frase (ponto, ou silêncio de mais de 1,2 s,
    porque o Whisper às vezes não pontua), menos depois de vírgula, quase nada no meio"""
    w = frase_antes(t)
    return 0.24 if fecha_frase(w) or longo > 1.2 else 0.16 if w.endswith(",") else 0.12


ilhas = set()
for k in range(1, len(trechos) - 1):
    eh_mudo, i0, i1 = trechos[k]
    if eh_mudo:
        continue
    a_m, b_m = trechos[k - 1], trechos[k + 1]
    dur = s_(i1 - i0)
    if not (0.15 <= dur <= 0.9 and s_(a_m[2] - a_m[1]) >= 0.06 and s_(b_m[2] - b_m[1]) >= 0.06):
        continue
    if flux[i0:i1].mean() >= FLUX_PARADO:
        continue
    # ilha de voz curta, de som parado, entre dois silêncios: é o "ééé"
    curtas = [w for w in ws if len(w["n"]) <= 2 and w["s"] >= s_(i0) - 0.05 and w["e"] <= s_(i1) + 0.05]
    meio = resto_de(s_(i0)) / 2
    corte(s_(a_m[1]) + meio, s_(b_m[2]) - meio, "gaguejo", not curtas,
          f"\"ééé\" de {dur:.2f}s entre pausas" + (f" — pode ser a palavra \"{curtas[0]['w']}\", ouça" if curtas else ""))
    ilhas.update((k - 1, k + 1))

primeira, ultima = ws[0]["s"], ws[-1]["e"]
for k, (eh_mudo, i0, i1) in enumerate(trechos):
    t0, t1 = s_(i0), s_(i1)
    if a.sem_pausas or not eh_mudo or k in ilhas or t1 - t0 <= a.pausa or t0 < primeira or t0 >= ultima:
        continue
    resto = resto_de(t0, t1 - t0)
    corte(t0 + resto / 2, t1 - resto / 2, "pausa", True, f"{t1 - t0:.2f}s → {resto:.2f}s")

# junta o que se sobrepõe (o motivo mais forte fica)
PESO = {"refaca": 4, "gaguejo": 3, "inicio": 2, "fim": 2, "pausa": 1}
cortes.sort(key=lambda c: c["inicio"])
juntos = []
for c in cortes:
    if juntos and c["inicio"] <= juntos[-1]["fim"] + 0.04 and c["aplicar"] == juntos[-1]["aplicar"]:
        u = juntos[-1]
        if PESO[c["tipo"]] > PESO[u["tipo"]]:
            u["tipo"], u["nota"] = c["tipo"], c["nota"] + (" + " + u["nota"] if u["nota"] else "")
        elif c["nota"] and c["nota"] not in u["nota"]:
            u["nota"] += " + " + c["nota"]
        u["fim"] = max(u["fim"], c["fim"])
    else:
        juntos.append(dict(c))


def contexto(c):
    antes = [w["w"] for w in ws if w["e"] <= c["inicio"] + 0.05][-5:]
    sai = [w["w"] for w in ws if c["inicio"] <= (w["s"] + w["e"]) / 2 < c["fim"]]
    depois = [w["w"] for w in ws if w["s"] >= c["fim"] - 0.05][:5]
    return " ".join(antes), " ".join(sai), " ".join(depois)


for c in juntos:
    c["antes"], c["sai"], c["depois"] = contexto(c)

json.dump({"video": a.video, "duracao": round(DUR, 3), "cortes": juntos}, open(a.saida, "w"), ensure_ascii=False, indent=1)

tira = sum(c["fim"] - c["inicio"] for c in juntos if c["aplicar"])
if not a.resumo:
    print(f"voz {voz_db:.0f} dB, piso {piso_db:.0f} dB, limiar {LIMIAR:.0f} dB\n")
for k, c in enumerate(juntos):
    if a.resumo and c["tipo"] in ("pausa", "inicio", "fim"):
        continue
    marca = "  " if c["aplicar"] else "? "
    sai = "·" if c["tipo"] in ("pausa", "inicio", "fim") else c["sai"]  # numa pausa o som cortado é silêncio
    print(f"{marca}{k:2d} {c['inicio']:7.2f}-{c['fim']:7.2f} {c['tipo']:7s} …{c['antes']} [{sai}] {c['depois']}…"
          + (f"   ({c['nota']})" if c["nota"] else "") if not a.resumo else
          f"{marca}{c['inicio']:7.2f}-{c['fim']:7.2f} {c['tipo']:7s} [{c['sai'][:90]}]")
npausas = sum(c["tipo"] == "pausa" for c in juntos)
print(f"\n{npausas} pausas encurtadas; {sum(c['aplicar'] for c in juntos)} cortes aplicados, {sum(not c['aplicar'] for c in juntos)} para ouvir (?)."
      f"\n{DUR:.1f}s → {DUR - tira:.1f}s  -> {a.saida}")
