"""Coisas que toda etapa usa: caminhos do repositório, saída padronizada e chamadas a programas.

Saída padronizada (o agente lê só isto):
    OK     <n> <etapa>: <resumo de uma linha>
    AVISO  <n> <etapa>: <o que> → <o que fazer>
    ERRO   <n> <etapa>: <o que> → <como corrigir>
    PRÓXIMO: <o que o agente faz agora>
O detalhe de cada programa vai para <pasta>/log/<nome>.txt.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PIPE = RAIZ / "pipeline"
KIT = RAIZ / "kit"
KIT_PY = KIT / ".venv" / "bin" / "python"
TEMPLATES = RAIZ / "templates"
CATALOGO = RAIZ / "catalogo"
TEMA = RAIZ / "tema"
APRESENTADORES = RAIZ / "apresentadores"
PASTA_PADRAO = Path(os.environ.get("CRAFT_PASTA", Path.home() / "Videos" / "craft-reels"))
LIMITE = 60.0          # duração máxima do reel, em segundos
ACELERA_MAX = 1.25     # quanto a etapa 8 pode acelerar para caber no limite


class Falha(Exception):
    """erro de etapa: vira uma linha ERRO e para a pipeline"""

    def __init__(self, oque, como):
        super().__init__(oque)
        self.oque, self.como = oque, como


def linha(tipo, n, etapa, texto):
    print(f"{tipo:<6} {n:>2} {etapa}: {texto}", flush=True)


def roda(pasta, nome, cmd, cwd=None, env=None):
    """roda um programa, grava stdout+stderr em log/<nome>.txt e devolve o stdout.
    Se falhar, levanta Falha com as últimas linhas do log."""
    log = Path(pasta) / "log"
    log.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd or pasta,
                       env=dict(os.environ, **(env or {})))
    (log / f"{nome}.txt").write_text(f"$ {' '.join(str(c) for c in cmd)}\n\n{r.stdout}\n{r.stderr}")
    if r.returncode:
        fim = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
        raise Falha(f"{nome} falhou (código {r.returncode})", f"veja log/{nome}.txt\n{fim}")
    return r.stdout


def duracao(video):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(video)]))


def impressao(caminho):
    """identifica um arquivo para saber se mudou: sha1 nos pequenos, tamanho+mtime nos grandes"""
    p = Path(caminho)
    if not p.exists():
        return None
    st = p.stat()
    if st.st_size > 20 * 1024 * 1024:
        return f"{st.st_size}:{st.st_mtime_ns}"
    return hashlib.sha1(p.read_bytes()).hexdigest()[:16]


def le_json(p, padrao=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else padrao


def grava_json(p, d):
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1))


def escolher_fundo(cenario, regra, pedido="auto"):
    """fundo que combina com a luz do vídeo: cenário claro → fundo claro, escuro → escuro.
    Devolve (fundo, motivo). Pedido da pessoa (--fundo) vence a regra."""
    if pedido in ("claro", "escuro"):
        return pedido, "pedido (--fundo)"
    if cenario > regra["claro_acima"]:
        return "claro", f"cenário claro ({cenario:.2f} > {regra['claro_acima']})"
    if cenario < regra["escuro_abaixo"]:
        return "escuro", f"cenário escuro ({cenario:.2f} < {regra['escuro_abaixo']})"
    return regra["entre"], f"cenário médio ({cenario:.2f}), fica o padrão"


def paletas():
    return le_json(TEMA / "paletas.json")


def apresentador(nome):
    if not nome:
        return {}
    p = APRESENTADORES / f"{nome}.json"
    if not p.exists():
        raise Falha(f"apresentador \"{nome}\" não existe", f"crie {p.relative_to(RAIZ)} (copie apresentadores/pedro.json) ou rode sem --apresentador")
    return json.loads(p.read_text())


def kit_pronto():
    if not KIT_PY.exists() or not (KIT / "vendor" / "gsap.min.js").exists():
        raise Falha("o kit de render não está instalado", "rode ./install.sh uma vez")


if __name__ == "__main__":
    sys.exit("módulo de apoio; use ./craft")
