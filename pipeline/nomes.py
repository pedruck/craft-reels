#!/usr/bin/env python3
"""Troca na transcrição os nomes que o Whisper erra, usando catalogo/logos/logos.json ("erros"),
catalogo/correcoes.json e as "correcoes" do apresentador.

    nomes.py <transcricao.json> [--troca "agente de ar=agente de IA" ...] [--apresentador pedro]

Edita o arquivo no lugar e imprime cada troca. Rode depois de transcrever e
sempre que achar um erro novo (e aí acrescente em catalogo/correcoes.json, para
os próximos vídeos já saírem certos).
"""
import argparse
import json
import unicodedata
from pathlib import Path

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo"
APRESENTADORES = Path(__file__).resolve().parent.parent / "apresentadores"


def nu(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return "".join(c for c in w if c.isalnum() and not unicodedata.combining(c))


def tabela(extra=(), apresentador=None):
    t = {}
    cat = json.loads((CATALOGO / "logos" / "logos.json").read_text())
    for k, v in cat.items():
        if not k.startswith("_"):
            t.update(v.get("erros", {}))
    for k, v in json.loads((CATALOGO / "correcoes.json").read_text()).items():
        if not k.startswith("_"):
            t[k] = v
    if apresentador:  # erros que o Whisper comete com a voz desta pessoa
        ap = APRESENTADORES / f"{apresentador}.json"
        if ap.exists():
            t.update(json.loads(ap.read_text()).get("correcoes", {}))
    for e in extra:
        k, v = e.split("=", 1)
        t[k] = v
    return {tuple(nu(p) for p in k.split()): v for k, v in t.items()}


def sem_fantasmas(words):
    """o Whisper repete a última palavra de um trecho no começo do seguinte, com duração ~0"""
    dur = lambda w: float(w["end"]) - float(w["start"])  # noqa: E731
    return [w for k, w in enumerate(words) if not (dur(w) < 0.04 and any(
        0 <= q < len(words) and nu(words[q]["word"]) == nu(w["word"]) and dur(words[q]) >= 0.04 for q in (k - 1, k + 1)))]


def corrigir(words, tab):
    """words: lista de {word,start,end}; devolve a lista nova e as trocas feitas"""
    words = sem_fantasmas(words)
    out, trocas, i = [], [], 0
    chaves = sorted(tab, key=len, reverse=True)
    while i < len(words):
        for k in chaves:
            if [nu(w["word"]) for w in words[i:i + len(k)]] == list(k):
                velho = " ".join(w["word"] for w in words[i:i + len(k)])
                fim = words[i + len(k) - 1]["word"]
                pont = fim[len(fim.rstrip(".,?!…:;")):]
                novo = tab[k] + pont
                # uma palavra por item, para a legenda quebrar normal; o tempo é repartido
                partes = novo.split(" ") if " " in tab[k] and len(k) > 1 else [novo]
                t0, t1 = float(words[i]["start"]), float(words[i + len(k) - 1]["end"])
                passo = (t1 - t0) / len(partes)
                for n_, pt in enumerate(partes):
                    out.append({"word": pt, "start": round(t0 + n_ * passo, 3), "end": round(t0 + (n_ + 1) * passo, 3)})
                trocas.append(f"{words[i]['start']:7.2f}  {velho} -> {novo}")
                i += len(k)
                break
        else:
            out.append(words[i])
            i += 1
    return out, trocas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("transcricao")
    ap.add_argument("--troca", action="append", default=[])
    ap.add_argument("--apresentador")
    a = ap.parse_args()
    d = json.loads(Path(a.transcricao).read_text())
    tab = tabela(a.troca, a.apresentador)
    ws, trocas = corrigir(d.get("words") or [w for s in d["segments"] for w in s["words"]], tab)
    d["words"] = ws
    for s in d.get("segments", []):
        s["words"] = [w for w in ws if s["start"] - 0.01 <= w["start"] < s["end"] + 0.01]
        s["text"] = " ".join(w["word"] for w in s["words"])
    d["text"] = " ".join(w["word"] for w in ws)
    Path(a.transcricao).write_text(json.dumps(d, ensure_ascii=False, indent=1))
    print("\n".join(trocas) or "nada para trocar")
