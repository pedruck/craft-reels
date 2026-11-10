#!/usr/bin/env python3
"""Aplica cortes.json ao vídeo e devolve o vídeo cortado com a transcrição já ajustada.

    cortar.py <video> <cortes.json> <saida.mp4> [--zoom 1.08] [--centro 0.5,0.45] [--sem-zoom]

Usa só os cortes com "aplicar": true. Cada emenda cai em quadro inteiro (30 fps),
com 30 ms de fade no áudio para não estalar. Para o pulo de imagem do corte no
meio da frase não ficar seco, alterna um zoom leve entre um trecho e o outro
(punch-in), centrado em --centro (fração da largura e da altura: ponha nos olhos).

Grava também <saida>.transcript.json: as palavras que sobraram, com o tempo novo.
Não precisa transcrever de novo, mas transcrever o resultado é a melhor conferência.
"""
import argparse
import json
import subprocess
from pathlib import Path

FPS = 30
ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("cortes")
ap.add_argument("saida")
ap.add_argument("--zoom", type=float, default=1.08)
ap.add_argument("--centro", default="0.5,0.45")
ap.add_argument("--sem-zoom", action="store_true")
ap.add_argument("--transcricao", help="padrão: <video sem extensão>.transcript.json")
a = ap.parse_args()

info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height:format=duration", "-of", "json", a.video]))
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
DUR = float(info["format"]["duration"])

plano = json.load(open(a.cortes))
cs = sorted((c["inicio"], c["fim"]) for c in plano["cortes"] if c.get("aplicar"))
fora = []
for i0, i1 in cs:
    if fora and i0 <= fora[-1][1]:
        fora[-1][1] = max(fora[-1][1], i1)
    else:
        fora.append([i0, i1])


def q(t):  # quadro inteiro
    return round(round(t * FPS) / FPS, 4)


# regra A: nenhum trecho mantido com menos de 0,25 s — não cabe uma palavra, é sempre
# respiro, ruído ou pedaço de tomada (sobra entre dois cortes calculados separados)
MINIMO = 0.25
ficam, t = [], 0.0
for i0, i1 in fora:
    if q(i0) - q(t) >= MINIMO:
        ficam.append((q(t), q(i0)))
    t = i1
if DUR - q(t) >= MINIMO:
    ficam.append((q(t), q(DUR) - 1 / FPS))

cx, cy = (float(v) for v in a.centro.split(","))
zw, zh = int(W / a.zoom) // 2 * 2, int(H / a.zoom) // 2 * 2
zx = int(min(max(cx * W - zw / 2, 0), W - zw))
zy = int(min(max(cy * H - zh / 2, 0), H - zh))
ZOOM = f"crop={zw}:{zh}:{zx}:{zy},scale={W}:{H},setsar=1"

partes, rot = [], []
for k, (i0, i1) in enumerate(ficam):
    vf = f"[0:v]trim={i0}:{i1},setpts=PTS-STARTPTS"
    if k % 2 == 1 and not a.sem_zoom:
        vf += "," + ZOOM
    d = i1 - i0
    af = (f"[0:a]atrim={i0}:{i1},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
          f"afade=t=out:st={max(0, d - 0.03):.4f}:d=0.03")
    partes += [f"{vf}[v{k}]", f"{af}[a{k}]"]
    rot.append(f"[v{k}][a{k}]")
grafo = ";".join(partes) + f";{''.join(rot)}concat=n={len(ficam)}:v=1:a=1[v][a]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-filter_complex", grafo, "-map", "[v]", "-map", "[a]",
                "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.saida], check=True)

# transcrição no tempo novo
tp = Path(a.transcricao) if a.transcricao else Path(a.video).with_suffix(".transcript.json")
saida = Path(a.saida)
if tp.exists():
    d = json.load(open(tp))
    ws = d.get("words") or [w for s in d.get("segments", []) for w in s.get("words", [])]
    # O Whisper estica as palavras por cima das pausas, então o tempo dele não diz sozinho se a
    # palavra saiu. Palavra no meio de um corte de refaça/gaguejo saiu. Palavra que caiu num corte
    # de pausa não saiu (ali só tem silêncio medido): vai para o começo do trecho seguinte.
    removidos = [(c["inicio"], c["fim"]) for c in plano["cortes"] if c.get("aplicar") and c["tipo"] not in ("pausa", "inicio", "fim")]
    bases, base = [], 0.0
    for i0, i1 in ficam:
        bases.append(base)
        base += i1 - i0
    novos = []
    for w in ws:
        s0, s1 = float(w["start"]), float(w["end"])
        meio = (s0 + s1) / 2
        if any(r0 <= meio < r1 for r0, r1 in removidos):
            continue
        sobra = [(min(s1, i1) - max(s0, i0), k) for k, (i0, i1) in enumerate(ficam)]
        dentro, k = max(sobra)
        if dentro < 0.03:  # caiu inteira numa pausa cortada
            k = next((k for k, (i0, _) in enumerate(ficam) if i0 >= s1 - 0.01), None)
            if k is None:
                continue
            i0 = ficam[k][0]
            s0, s1 = i0, i0 + 0.05
        i0, i1 = ficam[k]
        novos.append({"word": w["word"], "start": round(max(i0, s0) - i0 + bases[k], 3),
                      "end": round(min(i1, s1) - i0 + bases[k], 3)})
    texto = " ".join(w["word"] for w in novos)
    json.dump({"text": texto, "segments": [{"start": 0, "end": base, "text": texto, "words": novos}],
               "words": novos, "duration": base},
              open(saida.with_suffix(".transcript.json"), "w"), ensure_ascii=False, indent=1)
    print(f"transcrição ajustada -> {saida.with_suffix('.transcript.json')}")
json.dump({"ficam": ficam}, open(saida.with_suffix(".trechos.json"), "w"), indent=1)
total = sum(i1 - i0 for i0, i1 in ficam)
print(f"{len(ficam)} trechos, {DUR:.1f}s → {total:.1f}s -> {saida}")
