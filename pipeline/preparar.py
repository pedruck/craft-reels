#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.8,<5", "numpy"]
# ///
"""Etapa 1: acha o rosto, calcula o enquadramento e escolhe o fundo claro/escuro.

    preparar.py <bruto.mp4> <pasta> [--fundo auto|claro|escuro] [--paleta mocha]

Grava <pasta>/enquadramento.json e <pasta>/quadro.jpg (um quadro com régua de 100 px,
o rosto e a linha dos olhos marcados). Todas as medidas estão no quadro 1080x1920 do
reel (o vídeo é escalado/cortado para 9:16 do mesmo jeito que o kit faz).

Rosto: detector Haar do OpenCV em ~24 quadros espalhados; vale a mediana. Se achar
rosto em menos da metade dos quadros, grava "rosto": null e sai com código 2: o
agente lê o quadro.jpg e preenche o rosto à mão (e "manual": true), e esta etapa
passa a só recalcular o resto.

Fundo: luminosidade média do cenário (terço de cima do quadro). Cenário claro pede
fundo escuro e vice-versa (regra em tema/paletas.json → regra_fundo).
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("pasta")
ap.add_argument("--fundo", default="auto", choices=["auto", "claro", "escuro"])
ap.add_argument("--paleta", default=None)
ap.add_argument("--amostras", type=int, default=24)
a = ap.parse_args()

P = Path(a.pasta)
saida = P / "enquadramento.json"
antigo = json.loads(saida.read_text()) if saida.exists() else {}
pal = json.loads((RAIZ / "tema" / "paletas.json").read_text())
paleta = a.paleta or antigo.get("paleta") or pal["padrao"]
if paleta not in pal["paletas"]:
    sys.exit(f"paleta \"{paleta}\" não existe; use uma de: {', '.join(pal['paletas'])}")

cap = cv2.VideoCapture(a.video)
w0, h0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS) or 30
nq = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
dur = nq / fps
esc = max(W / w0, H / h0)                   # igual ao FRAME_VF do kit: escala até cobrir e corta o centro
ox, oy = (w0 * esc - W) / 2, (h0 * esc - H) / 2


def quadro(i):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read()
    if not ok:
        return None
    f = cv2.resize(f, (round(w0 * esc), round(h0 * esc)), interpolation=cv2.INTER_AREA if esc < 1 else cv2.INTER_CUBIC)
    return f[int(oy):int(oy) + H, int(ox):int(ox) + W]


faces_cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
olhos_cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
idx = np.linspace(nq * 0.03, nq * 0.97, a.amostras).astype(int)
medidas, lums, meio = [], [], None
for k, i in enumerate(idx):
    f = quadro(i)
    if f is None:
        continue
    if k == len(idx) // 2:
        meio = f.copy()
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    lums.append(float(g[: H // 3].mean()) / 255)
    pq = cv2.resize(g, (W // 3, H // 3))
    pq = cv2.equalizeHist(pq)
    fs = faces_cc.detectMultiScale(pq, scaleFactor=1.1, minNeighbors=6, minSize=(W // 3 // 8, W // 3 // 8))
    if len(fs) == 0:
        continue
    x, y, fw, fh = [v * 3 for v in max(fs, key=lambda r: r[2] * r[3])]
    # olhos: só na metade de cima do rosto
    sub = g[y: y + fh // 2 + fh // 10, x: x + fw]
    os_ = olhos_cc.detectMultiScale(sub, scaleFactor=1.1, minNeighbors=8, minSize=(fw // 10, fw // 10))
    olho = float(np.median([y + oy_ + oh / 2 for (_, oy_, _, oh) in os_])) if len(os_) else y + 0.42 * fh
    medidas.append((x, y, fw, fh, olho))
cap.release()
if meio is None:
    sys.exit("não consegui ler quadros do vídeo")

lum = float(np.mean(lums)) if lums else 0.5
rf = pal["regra_fundo"]
if a.fundo != "auto":
    fundo, motivo = a.fundo, "pedido (--fundo)"
elif lum > rf["escuro_acima"]:
    fundo, motivo = "escuro", f"cenário claro ({lum:.2f} > {rf['escuro_acima']})"
elif lum < rf["claro_abaixo"]:
    fundo, motivo = "claro", f"cenário escuro ({lum:.2f} < {rf['claro_abaixo']})"
else:
    fundo, motivo = rf["entre"], f"cenário médio ({lum:.2f}), fica o padrão"

manual = bool(antigo.get("manual")) and antigo.get("rosto")
confianca = len(medidas) / max(1, len(idx))
if manual:
    rosto = antigo["rosto"]
elif confianca >= 0.5:
    x, y, fw, fh, olho = (float(np.median([m[i] for m in medidas])) for i in range(5))
    # A caixa do Haar vai do meio da testa até o queixo. Proporções medidas em vídeos de teste
    # (cabelo ≈ 0,32 da altura da caixa acima do topo; queixo ≈ 0,02 abaixo da base).
    rosto = {"x": round(x), "y": round(y), "largura": round(fw), "altura": round(fh),
             "olho_y": round(olho), "cabelo_y": round(y - 0.32 * fh), "queixo_y": round(y + 1.02 * fh),
             "centro_x": round((x + fw / 2) / W, 3)}
else:
    rosto = None

enq = {"_leia": "Medidas no quadro 1080x1920 do reel. Se o rosto não foi achado, preencha 'rosto' à mão "
                "(olho_y, cabelo_y, queixo_y, centro_x lendo o quadro.jpg) e ponha \"manual\": true.",
       "video": {"largura": w0, "altura": h0, "fps": round(fps, 3), "duracao": round(dur, 3)},
       "cenario": round(lum, 3), "fundo": fundo, "fundo_motivo": motivo, "paleta": paleta,
       "confianca_rosto": round(confianca, 2), "manual": bool(manual), "rosto": rosto}

if rosto:
    # painel do explainer: cabeça (cabelo→queixo) com ~525 px; topo do painel ~1200 (na linha dos olhos);
    # legenda logo abaixo do queixo, na faixa 1330–1456 (embaixo, fora da área que o Instagram cobre)
    cab = rosto["queixo_y"] - rosto["cabelo_y"]
    escala = min(1.3, max(0.62, 525 / max(cab, 1)))     # rosto enorme (selfie de perto) encolhe até 0,62
    video_y = 1200 - rosto["olho_y"] * escala
    legenda_y = video_y + rosto["queixo_y"] * escala + 24
    if legenda_y > 1456:          # a legenda fica SEMPRE embaixo e nunca sobre o rosto: sobe a pessoa
        video_y -= legenda_y - 1456
        legenda_y = 1456
    legenda_y = max(1330, legenda_y)
    enq["painel"] = {"escala": round(escala, 3), "video_y": round(video_y), "olho_y": rosto["olho_y"], "largura": 886,
                     "centro_x": rosto["centro_x"]}
    enq["legenda_y"] = round(legenda_y)
    enq["zoom_centro"] = [rosto["centro_x"], round(rosto["olho_y"] / H, 3)]

saida.write_text(json.dumps(enq, ensure_ascii=False, indent=1))

# quadro.jpg: régua de 100 em 100 px, rosto e olhos marcados, em meia resolução
img = meio.copy()
for v in range(100, W, 100):
    cv2.line(img, (v, 0), (v, H), (0, 200, 255), 1)
    cv2.putText(img, str(v), (v + 3, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)
for v in range(100, H, 100):
    cv2.line(img, (0, v), (W, v), (0, 200, 255), 1)
    cv2.putText(img, str(v), (5, v - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)
if rosto:
    cv2.rectangle(img, (rosto["x"], rosto["y"]), (rosto["x"] + rosto["largura"], rosto["y"] + rosto["altura"]), (0, 255, 0), 3)
    for nome, yy, cor in (("olhos", rosto["olho_y"], (255, 0, 255)), ("cabelo", rosto["cabelo_y"], (255, 255, 0)),
                          ("queixo", rosto["queixo_y"], (0, 0, 255))):
        cv2.line(img, (0, int(yy)), (W, int(yy)), cor, 3)
        cv2.putText(img, nome, (W - 200, int(yy) - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.1, cor, 3)
cv2.imwrite(str(P / "quadro.jpg"), cv2.resize(img, (W // 2, H // 2)), [cv2.IMWRITE_JPEG_QUALITY, 80])

if rosto:
    print(f"rosto em {len(medidas)}/{len(idx)} quadros{' (manual)' if manual else ''}; olhos y={rosto['olho_y']}, "
          f"cabelo {rosto['cabelo_y']}, queixo {rosto['queixo_y']}, centro x={rosto['centro_x']}; "
          f"cenário {lum:.2f} → fundo {fundo}")
else:
    print(f"rosto em só {len(medidas)}/{len(idx)} quadros; cenário {lum:.2f} → fundo {fundo}")
    sys.exit(2)
