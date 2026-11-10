"""Testes das regras puras da pipeline (sem vídeo, sem Whisper). Rode com:

    kit/.venv/bin/python -m unittest discover -s testes -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(RAIZ / "pipeline"))
sys.path.insert(0, str(RAIZ / "templates"))

import nomes  # noqa: E402
import roteiro  # noqa: E402
from estado import Estado  # noqa: E402


def palavras(texto, t0=0.0, passo=0.4):
    out, t = [], t0
    for w in texto.split():
        out.append({"word": w, "start": round(t, 3), "end": round(t + passo * 0.8, 3)})
        t += passo
    return out


class Roteiro(unittest.TestCase):
    def setUp(self):
        self.rot = roteiro.ler(FIX / "s1.roteiro.md")

    def test_le_cabecalho_e_texto(self):
        self.assertIn("Jev", self.rot["nomes"])
        self.assertTrue(self.rot["texto"].startswith("Existe um novo tipo de IA"))
        self.assertIsNone(self.rot["cenas"])

    def test_bloco_de_cenas(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text('---\nnomes: Orca\n---\nOlá mundo.\n\n```cenas\n[{"at": 0, "titulo": "Oi"}]\n```\n')
            r = roteiro.ler(p)
            self.assertEqual(r["cenas"], [{"at": 0, "titulo": "Oi"}])
            self.assertEqual(r["texto"], "Olá mundo.")

    def test_frase_dita_duas_vezes_fica_a_ultima(self):
        frase = ("Em vez de escrever um texto como o ChatGPT, eles funcionam assim: na entrada, você manda a situação "
                 "e uma lista fechada de opções.")
        ws = palavras(f"{frase} {frase} e pronto")
        novos = roteiro.tomadas(self.rot, ws, [])
        self.assertEqual(len(novos), 1)
        self.assertAlmostEqual(novos[0]["inicio"], -0.05, places=2)       # sai a primeira
        self.assertLess(novos[0]["fim"], ws[len(frase.split())]["start"] + 0.1)

    def test_frase_dita_uma_vez_nao_corta(self):
        ws = palavras("Em vez de escrever um texto como o ChatGPT, eles funcionam assim: na entrada, você manda a situação "
                      "e uma lista fechada de opções. E pronto")
        self.assertEqual(roteiro.tomadas(self.rot, ws, []), [])

    def test_tentativa_incompleta_sai(self):
        ws = palavras("Na saída, eles não escrevem eee Na saída, eles não escrevem nada, só devolvem uma dessas opções,"
                      " junto com a probabilidade de ela ser a escolha certa.")
        novos = roteiro.tomadas(self.rot, ws, [])
        self.assertTrue(any("incompleta" in c["nota"] for c in novos), novos)

    def test_legenda_corrige_nome_pelo_roteiro(self):
        ws = palavras("É aí que eles voam: o Jeb, o modelo que lançou essa categoria")
        out, trocas = roteiro.legenda(self.rot, ws)
        self.assertEqual(out[6]["word"], "Jev,")
        self.assertEqual(len(trocas), 1)

    def test_legenda_nao_troca_palavra_diferente(self):
        ws = palavras("É aí que eles correm: o Jev, o modelo")
        out, trocas = roteiro.legenda(self.rot, ws)
        self.assertEqual(out[4]["word"], "correm:")


class Nomes(unittest.TestCase):
    def test_erros_do_catalogo(self):
        ws = palavras("o walmart é bom e o cloud code também")
        out, trocas = nomes.corrigir(ws, nomes.tabela())
        texto = " ".join(w["word"] for w in out)
        self.assertIn("Omarchy", texto)
        self.assertIn("Claude Code", texto)

    def test_correcao_do_apresentador(self):
        ws = palavras("utilizando a agents de ia")
        out, _ = nomes.corrigir(ws, nomes.tabela(apresentador="pedro"))
        self.assertEqual(" ".join(w["word"] for w in out), "utilizando agentes de IA")

    def test_palavra_fantasma(self):
        ws = [{"word": "tela", "start": 1.0, "end": 1.4}, {"word": "tela", "start": 1.4, "end": 1.41}, {"word": "nova", "start": 1.5, "end": 1.8}]
        out, _ = nomes.corrigir(ws, nomes.tabela())
        self.assertEqual([w["word"] for w in out], ["tela", "nova"])


class EstadoTeste(unittest.TestCase):
    def test_refaz_quando_entrada_muda(self):
        with tempfile.TemporaryDirectory() as d:
            P = Path(d)
            (P / "a.txt").write_text("1")
            (P / "b.txt").write_text("x")
            e = Estado(P)
            self.assertEqual(e.precisa("x", ["a.txt"], ["b.txt"], []), "nunca rodou")
            e.feito("x", ["a.txt"], [], "ok")
            self.assertIsNone(Estado(P).precisa("x", ["a.txt"], ["b.txt"], []))
            (P / "a.txt").write_text("2")
            self.assertEqual(Estado(P).precisa("x", ["a.txt"], ["b.txt"], []), "a.txt mudou")

    def test_refaz_quando_opcao_muda(self):
        with tempfile.TemporaryDirectory() as d:
            P = Path(d)
            (P / "b.txt").write_text("x")
            e = Estado(P)
            e.opcoes["paleta"] = "mocha"
            e.feito("x", [], ["paleta"], "ok")
            e.opcoes["paleta"] = "nord"
            self.assertEqual(e.precisa("x", [], ["b.txt"], ["paleta"]), "opções mudaram")


class CorteManual(unittest.TestCase):
    def test_encosta_na_emenda(self):
        """regra C: ponta a menos de 0,3 s de uma emenda encosta nela (senão sobra lasca)"""
        with tempfile.TemporaryDirectory() as d:
            P = Path(d)
            (P / "cortado.trechos.json").write_text(json.dumps({"ficam": [[0.0, 5.0], [8.0, 12.0]]}))
            (P / "cortes.json").write_text(json.dumps({"cortes": []}))
            subprocess.run([sys.executable, str(RAIZ / "pipeline" / "corte_manual.py"), str(P), "4.9", "5.6", "teste"], check=True,
                           capture_output=True)
            c = json.loads((P / "cortes.json").read_text())["cortes"][0]
            self.assertAlmostEqual(c["inicio"], 4.9, places=2)
            self.assertAlmostEqual(c["fim"], 8.6, places=2)     # 5,6 no cortado = 8,6 no bruto


class Legenda(unittest.TestCase):
    def test_sempre_embaixo_e_fora_do_rosto(self):
        from motor import LEG_MAX, LEG_MIN, posicao_legenda
        self.assertEqual(posicao_legenda(1000), (LEG_MIN, False))        # queixo alto: legenda fica embaixo mesmo assim
        self.assertEqual(posicao_legenda(1400), (1424, False))
        topo, cobre = posicao_legenda(1500)
        self.assertEqual(topo, LEG_MAX)
        self.assertTrue(cobre)

    def test_video_cheio_sobe_o_rosto(self):
        from motor import LEG_MAX, video_cheio
        estilo, r = video_cheio({"rosto": {"olho_y": 996, "cabelo_y": 422, "queixo_y": 1500, "centro_x": 0.47}})
        self.assertLessEqual(r["queixo_y"], LEG_MAX - 24 + 1)
        self.assertIn("width:", estilo)

    def test_video_cheio_nao_mexe_quando_cabe(self):
        from motor import video_cheio
        estilo, r = video_cheio({"rosto": {"olho_y": 1100, "cabelo_y": 900, "queixo_y": 1380, "centro_x": 0.5}})
        self.assertIn("top:0px", estilo)
        self.assertEqual(r["queixo_y"], 1380)


class PainelExplainer(unittest.TestCase):
    def test_video_sempre_cobre_o_painel(self):
        """rosto grande encolhe o vídeo (até 0,62x): o painel encolhe junto, sem faixa vazia e sem distorcer"""
        from motor import painel_explainer
        for esc in (0.62, 0.7, 0.82, 1.0, 1.13, 1.3):
            for cx in (0.0, 0.3, 0.474, 0.5, 0.7, 1.0):
                for vy in (-300, 0, 346, 502):
                    SC, VY, VW, VH, PW, PX, VX, PT, PB = painel_explainer(
                        {"escala": esc, "video_y": vy, "olho_y": 1000, "largura": 886, "centro_x": cx})
                    caso = f"escala {esc}, centro {cx}, video_y {vy}"
                    self.assertAlmostEqual(VW / VH, 1080 / 1920, places=6, msg=caso)     # proporção intacta
                    self.assertLessEqual(VX, 0, caso)                                       # cobre a esquerda
                    self.assertGreaterEqual(VX + VW, PW - 1e-6, caso)                       # cobre a direita
                    self.assertLessEqual(VY, PT, caso)                                      # cobre o topo
                    self.assertGreaterEqual(VY + VH, PB - 1e-6, caso)                       # cobre a base
                    self.assertLessEqual(PW, 886)

    def test_caso_da_orca(self):
        from motor import painel_explainer
        SC, VY, VW, VH, PW, PX, VX, PT, PB = painel_explainer(
            {"escala": 0.62, "video_y": 502, "olho_y": 996, "largura": 886, "centro_x": 0.474})
        self.assertAlmostEqual(PW, 669.6, places=1)       # antes ficava 886, com 216 px de branco
        self.assertLessEqual(PB, VY + VH)


class Paletas(unittest.TestCase):
    def test_cada_paleta_tem_claro_e_escuro_com_as_mesmas_chaves(self):
        p = json.loads((RAIZ / "tema" / "paletas.json").read_text())
        self.assertEqual(p["padrao"], "mocha")
        chaves = set(p["paletas"]["mocha"]["escuro"])
        for nome, pal in p["paletas"].items():
            for fundo in ("claro", "escuro"):
                self.assertEqual(set(pal[fundo]), chaves, f"{nome}/{fundo}")


class Validador(unittest.TestCase):
    def test_ancora_que_nao_existe_e_titulo_largo(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("rode com kit/.venv/bin/python")
        from motor import Validador as V
        with tempfile.TemporaryDirectory() as d:
            P = Path(d)
            ws = palavras("o coordenador divide a tarefa entre agentes especializados", passo=1.0)
            (P / "legenda.json").write_text(json.dumps({"words": ws}))
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:d=10", "-f", "lavfi", "-i",
                            "anullsrc=r=48000:cl=mono", "-t", "10", "-c:v", "libx264", "-c:a", "aac", str(P / "limpo.mp4")], check=True)
            spec = {"video": "limpo.mp4", "transcript": "legenda.json", "cenas": [
                {"at": 0, "titulo": "Um título longo demais para caber *aqui*"},
                {"at": "inexistente", "titulo": "Oi"}]}
            (P / "spec.json").write_text(json.dumps(spec))
            v = V(P / "spec.json")
            v.cenas(spec["cenas"])
            erros = "\n".join(v.erros)
            self.assertIn("título largo demais", erros)
            self.assertIn("não é falado", erros)


if __name__ == "__main__":
    unittest.main()
