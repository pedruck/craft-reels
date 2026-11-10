"""estado.json: o que cada etapa já fez, com que entradas e opções.

Uma etapa roda de novo só se: nunca rodou, falta uma saída, uma entrada mudou
(impressão do arquivo diferente) ou uma opção dela mudou. Rodar de novo uma etapa
muda as saídas dela, que são entradas da seguinte, então a cadeia se refaz sozinha.
"""
import time
from pathlib import Path

from comum import grava_json, impressao, le_json


class Estado:
    def __init__(self, pasta):
        self.pasta = Path(pasta)
        self.arq = self.pasta / "estado.json"
        self.d = le_json(self.arq, {"opcoes": {}, "etapas": {}, "parar_em": [], "aprovado": []})

    def salva(self):
        grava_json(self.arq, self.d)

    @property
    def opcoes(self):
        return self.d["opcoes"]

    def _impressoes(self, entradas):
        return {e: impressao(self.pasta / e) for e in entradas}

    def precisa(self, etapa, entradas, saidas, opcoes):
        e = self.d["etapas"].get(etapa)
        if not e or e.get("status") != "ok":
            return "nunca rodou" if not e else "não terminou"
        falta = [s for s in saidas if not (self.pasta / s).exists()]
        if falta:
            return f"falta {falta[0]}"
        mudou = [k for k, v in self._impressoes(entradas).items() if e["entradas"].get(k) != v]
        if mudou:
            return f"{mudou[0]} mudou"
        op = {k: self.opcoes.get(k) for k in opcoes}
        if e.get("opcoes") != op:
            return "opções mudaram"
        return None

    def feito(self, etapa, entradas, opcoes, resumo):
        self.d["etapas"][etapa] = {"status": "ok", "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
                                   "entradas": self._impressoes(entradas),
                                   "opcoes": {k: self.opcoes.get(k) for k in opcoes}, "resumo": resumo}
        self.salva()

    def falhou(self, etapa, motivo):
        self.d["etapas"][etapa] = {"status": "erro", "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "motivo": motivo,
                                   "entradas": {}, "opcoes": {}}
        self.salva()

    def esquece(self, etapa):
        self.d["etapas"].pop(etapa, None)
        self.salva()
