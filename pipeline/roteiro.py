#!/usr/bin/env python3
"""O roteiro como gabarito da edição.

    roteiro.py info <roteiro.md>                         palavras, duração estimada, nomes, cenas
    roteiro.py tomadas <roteiro.md> <bruto.transcript.json> <cortes.json>
    roteiro.py legenda <roteiro.md> <legenda.json>
    roteiro.py cenas <roteiro.md> <cenas.json>

Formato do roteiro.md (o que a skill roteiro escreve):

    ---
    titulo: S1 decision models
    nomes: Jev, TypeSafe, System1-Arena
    template: explainer
    ---
    Existe um novo tipo de IA, e ela não foi feita pra conversar com você. ...

    ```cenas
    [{"at": 0, "titulo": "Uma IA *diferente*", "visual": {...}}, ...]
    ```

O texto falado é tudo fora do cabeçalho e dos blocos ```. O bloco ```cenas é opcional
e tem o formato do cenas.json (âncoras são palavras do próprio roteiro).

tomadas: frase do roteiro dita mais de uma vez → fica a melhor (a mais parecida com o
roteiro; empate, a última) e as outras viram corte "tomada". Tentativa que começa a
frase e para (sem "refaz") também sai, se a frase vem inteira logo depois.
legenda: palavra que o Whisper ouviu diferente do roteiro ("Jeb" × "Jev") é trocada
pela do roteiro quando o resto da frase bate.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path


def nu(w):
    w = unicodedata.normalize("NFKD", str(w).lower())
    return "".join(c for c in w if c.isalnum() and not unicodedata.combining(c))


def ler(caminho):
    s = Path(caminho).read_text()
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", s, re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
        s = s[m.end():]
    cenas = None
    for bloco in re.finditer(r"```cenas\s*\n(.*?)```", s, re.S):
        cenas = json.loads(bloco.group(1))
    texto = re.sub(r"```.*?```", " ", s, flags=re.S)
    texto = re.sub(r"^\s*#.*$", " ", texto, flags=re.M)          # títulos markdown não são falados
    texto = " ".join(texto.split())
    nomes = [n.strip() for n in meta.get("nomes", "").strip("[]").split(",") if n.strip()]
    return {"meta": meta, "texto": texto, "nomes": nomes, "cenas": cenas, "palavras": texto.split()}


def frases(texto):
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if f.strip()]


VAZIAS = {"a", "o", "e", "de", "do", "da", "que", "um", "uma", "em", "no", "na", "com", "se", "os", "as", "pra", "para", "é"}


def tomadas(rot, words, cortes):
    """cortes novos (tipo "tomada") para frases ditas mais de uma vez"""
    ja = [(c["inicio"], c["fim"]) for c in cortes if c.get("aplicar")]
    vivas = [w for w in words if not any(a <= (float(w["start"]) + float(w["end"])) / 2 < b for a, b in ja)]
    ns = [nu(w["word"]) for w in vivas]
    novos = []
    contagem = {}
    for f in frases(rot["texto"]):
        contagem[tuple(nu(x) for x in f.split())] = contagem.get(tuple(nu(x) for x in f.split()), 0) + 1
    for f in frases(rot["texto"]):
        alvo = [nu(x) for x in f.split() if nu(x)]
        if len(set(alvo) - VAZIAS) < 4 or contagem[tuple(nu(x) for x in f.split())] > 1:
            continue  # frase curta demais para comparar, ou que o roteiro repete de propósito
        n = len(alvo)
        achados = []
        for i in range(0, max(1, len(ns) - n // 2)):
            jan = ns[i:i + n + 2]
            sm = difflib.SequenceMatcher(None, alvo, jan, autojunk=False)
            r = sm.ratio()
            if r >= 0.75 and jan and jan[0] and difflib.SequenceMatcher(None, alvo[:2], jan[:2]).ratio() >= 0.5:
                fim = i + max(b.b + b.size for b in sm.get_matching_blocks() if b.size) - 1
                achados.append((r, i, fim))
        # junta janelas sobrepostas (a mesma ocorrência achada várias vezes)
        ocorr = []
        for r, i, fim in sorted(achados, key=lambda x: x[1]):
            if ocorr and i <= ocorr[-1][2]:
                if r > ocorr[-1][0]:
                    ocorr[-1] = (r, i, fim)
                continue
            ocorr.append((r, i, fim))
        if len(ocorr) >= 2:
            melhor = max(range(len(ocorr)), key=lambda k: (round(ocorr[k][0], 2), k))
            for k, (r, i, fim) in enumerate(ocorr):
                if k == melhor:
                    continue
                a = float(vivas[i]["start"]) - 0.05
                b = float(vivas[fim]["end"]) + 0.05
                novos.append({"inicio": round(a, 3), "fim": round(b, 3), "tipo": "tomada", "aplicar": True,
                              "nota": f"frase do roteiro dita {len(ocorr)}x, fica a {melhor + 1}ª: \"{' '.join(w['word'] for w in vivas[i:fim + 1])}\""})
        # tentativa que para no meio: começo da frase (4+ palavras) até 8 s antes da frase inteira
        for r, i, fim in ocorr:
            t_ini = float(vivas[i]["start"])
            for j in range(max(0, i - 40), i - 3):
                if float(vivas[j]["start"]) < t_ini - 20:
                    continue
                m = 0
                while m < len(alvo) and j + m < i and ns[j + m] == alvo[m]:
                    m += 1
                if m >= 4 and m < n * 0.8 and t_ini - float(vivas[j + m - 1]["end"]) < 8:
                    novos.append({"inicio": round(float(vivas[j]["start"]) - 0.05, 3), "fim": round(t_ini - 0.08, 3),
                                  "tipo": "tomada", "aplicar": True,
                                  "nota": f"tentativa incompleta: \"{' '.join(w['word'] for w in vivas[j:j + m])}…\""})
                    break
    return novos


def legenda(rot, words):
    """troca palavras da legenda pelas do roteiro quando o contexto bate; devolve (words, trocas)"""
    termos = {nu(x) for x in rot["nomes"]}
    roteiro = rot["palavras"]
    rn = [nu(x) for x in roteiro]
    wn = [nu(w["word"]) for w in words]
    sm = difflib.SequenceMatcher(None, wn, rn, autojunk=False)
    trocas = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op != "replace" or a1 - a0 != b1 - b0:
            continue
        for k in range(a1 - a0):
            w, alvo = words[a0 + k], roteiro[b0 + k]
            alvo_limpo = alvo.strip(".,!?;:…\"'()")
            if not nu(alvo_limpo) or nu(w["word"]) == nu(alvo_limpo):
                continue
            parecido = difflib.SequenceMatcher(None, nu(w["word"]), nu(alvo_limpo)).ratio()
            nome = nu(alvo_limpo) in termos or alvo_limpo[:1].isupper() or any(c.isdigit() for c in alvo_limpo)
            if parecido >= 0.5 and (nome or parecido >= 0.75):
                pont = w["word"][len(w["word"].rstrip(".,!?;:…")):]
                trocas.append(f"{w['start']:7.2f}  {w['word']} -> {alvo_limpo}{pont}")
                w["word"] = alvo_limpo + pont
    return words, trocas


def main():
    cmd = sys.argv[1]
    rot = ler(sys.argv[2])
    if cmd == "info":
        n = len(rot["palavras"])
        print(json.dumps({"palavras": n, "segundos_estimados": round(n / 3), "nomes": rot["nomes"],
                          "template": rot["meta"].get("template"), "tem_cenas": rot["cenas"] is not None}, ensure_ascii=False))
    elif cmd == "tomadas":
        d = json.loads(Path(sys.argv[3]).read_text())
        ws = d.get("words") or [w for s in d["segments"] for w in s["words"]]
        plano = json.loads(Path(sys.argv[4]).read_text())
        if any(c.get("tipo") == "tomada" for c in plano["cortes"]):
            print("tomadas já aplicadas")
            return
        novos = tomadas(rot, ws, plano["cortes"])
        plano["cortes"] += novos
        Path(sys.argv[4]).write_text(json.dumps(plano, ensure_ascii=False, indent=1))
        for c in novos:
            print(f"  {c['inicio']:7.2f}-{c['fim']:7.2f}  {c['nota']}")
        print(f"{len(novos)} cortes de tomada pelo roteiro")
    elif cmd == "legenda":
        p = Path(sys.argv[3])
        d = json.loads(p.read_text())
        ws, trocas = legenda(rot, d["words"])
        d["words"] = ws
        for s in d.get("segments", []):
            s["words"] = [w for w in ws if s["start"] - 0.01 <= w["start"] < s["end"] + 0.01]
            s["text"] = " ".join(w["word"] for w in s["words"])
        d["text"] = " ".join(w["word"] for w in ws)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print("\n".join(trocas) or "legenda já bate com o roteiro")
    elif cmd == "cenas":
        if rot["cenas"] is None:
            sys.exit("o roteiro não tem bloco ```cenas")
        saida = {"template": rot["meta"].get("template", "explainer"), "cenas": rot["cenas"]}
        Path(sys.argv[3]).write_text(json.dumps(saida, ensure_ascii=False, indent=1))
        print(f"{len(rot['cenas'])} cenas do roteiro")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
