"""craft: a pipeline fixa de reels. Veja AGENTS.md.

    craft run <video.mp4|pasta> [opções]      roda (ou continua) as etapas 1–10
    craft estado <pasta>                      o que já foi feito
    craft validar <pasta>                     confere o cenas.json sem renderizar
    craft corte <pasta> <ini> <fim> "nota"    corte achado assistindo o cortado.mp4 (tempos do cortado)
    craft aprovar <pasta> cortes|cenas        libera um ponto de parada pedido com --parar-em
    craft templates                           lista os templates
    craft logo <chave> <slug> "<Nome>"        baixa uma logo do Simple Icons para o catálogo
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from comum import (ACELERA_MAX, KIT_PY, LIMITE, PASTA_PADRAO, PIPE, RAIZ, TEMPLATES, Falha, apresentador, duracao,
                   grava_json, kit_pronto, le_json, linha, paletas, roda)
from estado import Estado

NOMES = {1: "preparar", 2: "transcrever", 3: "cortar", 4: "audio", 5: "legenda", 6: "cenas", 7: "montar",
         8: "duracao", 9: "conferir", 10: "entregar"}


class Parada(Exception):
    """ponto em que a pipeline espera o agente (PRÓXIMO) — não é erro"""


def slug(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "reel"


def tem_roteiro(P):
    return (P / "roteiro.md").exists()


def nomes_whisper(P, op):
    """produtos e termos para o prompt do Whisper: --nomes + roteiro + apresentador"""
    nomes = [n.strip() for n in (op.get("nomes") or "").split(",") if n.strip()]
    if tem_roteiro(P):
        sys.path.insert(0, str(PIPE))
        import roteiro
        nomes += roteiro.ler(P / "roteiro.md")["nomes"]
    nomes += apresentador(op.get("apresentador")).get("nomes", [])
    vistos = []
    for n in nomes:
        if n.lower() not in [v.lower() for v in vistos]:
            vistos.append(n)
    return ", ".join(vistos)


# ------------------------------------------------------------------ etapas
def e1_preparar(P, op):
    cmd = [PIPE / "preparar.py", "bruto.mp4", ".", "--fundo", op.get("fundo") or "auto"]
    if op.get("paleta"):
        cmd += ["--paleta", op["paleta"]]
    try:
        out = roda(P, "preparar", cmd)
    except Falha as f:
        if "código 2" in f.oque:
            raise Falha("rosto não achado na maioria dos quadros",
                        "abra quadro.jpg (régua de 100 px), preencha \"rosto\" em enquadramento.json "
                        "(olho_y, cabelo_y, queixo_y, centro_x, x, y, largura, altura) e ponha \"manual\": true; rode de novo")
        raise
    return out.strip().splitlines()[-1]


def e2_transcrever(P, op):
    roda(P, "transcrever-bruto", [PIPE / "transcrever.py", "bruto.mp4", "bruto.transcript.json", "--nomes", nomes_whisper(P, op),
                                  "--quieto"] + (["--apresentador", op["apresentador"]] if op.get("apresentador") else []))
    d = le_json(P / "bruto.transcript.json")
    return f"{len(d['words'])} palavras, {d['duration']:.0f}s"


def e3_cortar(P, op):
    from comum import impressao
    plano = le_json(P / "cortes.json")
    tr = impressao(P / "bruto.transcript.json")
    if not plano or plano.get("transcricao") != tr:
        out = roda(P, "planejar", [PIPE / "planejar_cortes.py", "bruto.mp4", "bruto.transcript.json", "cortes.json", "--resumo"])
        plano = le_json(P / "cortes.json")
        plano["transcricao"] = tr
        grava_json(P / "cortes.json", plano)
        if tem_roteiro(P):
            roda(P, "tomadas", [sys.executable, PIPE / "roteiro.py", "tomadas", "roteiro.md", "bruto.transcript.json", "cortes.json"])
    enq = le_json(P / "enquadramento.json")
    centro = ",".join(str(v) for v in enq.get("zoom_centro", [0.5, 0.45]))
    zoom = str(apresentador(op.get("apresentador")).get("zoom", 1.08))
    limpo = False
    for volta in range(1, 6):
        roda(P, f"cortar-{volta}", [sys.executable, PIPE / "cortar.py", "bruto.mp4", "cortes.json", "cortado.mp4",
                                    "--centro", centro, "--zoom", zoom])
        out = roda(P, f"conferir-{volta}", [PIPE / "conferir_trechos.py", "."])
        if "LIMPO" in out:
            limpo = True
            break
    plano = le_json(P / "cortes.json")
    ficam = le_json(P / "cortado.trechos.json")["ficam"]
    tipos = {}
    for c in plano["cortes"]:
        if c.get("aplicar"):
            tipos[c["tipo"]] = tipos.get(c["tipo"], 0) + 1
    susp = [c for c in plano["cortes"] if not c.get("aplicar") and c["tipo"] not in ("pausa", "inicio", "fim")]
    for c in susp[:6]:
        linha("AVISO", 3, "cortar", f"suspeita mantida {c['inicio']:.1f}s: {c['nota'][:90]} → corte só se a pessoa pedir")
    if not limpo:
        linha("AVISO", 3, "cortar", "a conferência ainda achava algo depois de 5 voltas → veja log/conferir-5.txt")
    resumo = ", ".join(f"{v} {k}" for k, v in sorted(tipos.items(), key=lambda x: -x[1]))
    return (f"{duracao(P / 'bruto.mp4'):.0f}s → {duracao(P / 'cortado.mp4'):.1f}s, {len(ficam)} trechos "
            f"({resumo}); conferência {'limpa' if limpo else 'NÃO limpa'} na volta {volta}")


def gate_cortes(P, est):
    if "cortes" in est.d["parar_em"] and "cortes" not in est.d["aprovado"]:
        kit_pronto()
        roda(P, "aprovacao", [KIT_PY, PIPE / "aprovacao.py", "."])
        print(f"PRÓXIMO: mostre {P / 'aprovacao.jpg'} à pessoa. Aprovado: craft aprovar {P} cortes. "
              f"Para mudar: \"aplicar\" em cortes.json ou craft corte {P} <ini> <fim> \"nota\"; depois craft run {P}")
        raise Parada()


def e4_audio(P, op):
    out = roda(P, "audio", [sys.executable, PIPE / "audio.py", "cortado.mp4", "limpo.mp4"])
    d = json.loads(out.strip().splitlines()[-1])
    grava_json(P / "audio.json", d)
    return f"{d['antes_lufs']} LUFS → {d['depois_lufs']} LUFS"


def e5_legenda(P, op):
    roda(P, "transcrever-limpo", [PIPE / "transcrever.py", "limpo.mp4", "legenda.json", "--nomes", nomes_whisper(P, op), "--quieto"]
         + (["--apresentador", op["apresentador"]] if op.get("apresentador") else []))
    trocas = 0
    if tem_roteiro(P):
        out = roda(P, "legenda-roteiro", [sys.executable, PIPE / "roteiro.py", "legenda", "roteiro.md", "legenda.json"])
        trocas = sum("->" in ln for ln in out.splitlines())
    out = roda(P, "segunda-passada", [PIPE / "planejar_cortes.py", "limpo.mp4", "legenda.json", "cortes2.json", "--sem-pausas", "--resumo"])
    for ln in [ln for ln in out.splitlines() if ln.startswith("? ")][:5]:
        linha("AVISO", 5, "legenda", f"possível sobra no cortado: {ln[2:].strip()[:100]} → assista; se for, craft corte")
    (P / "frases.txt").write_text(roda(P, "frases", [sys.executable, PIPE / "frases.py", "legenda.json"]))
    n = len(le_json(P / "legenda.json")["words"])
    return f"{n} palavras na legenda" + (f", {trocas} corrigidas pelo roteiro" if trocas else "") + "; texto em frases.txt"


def e6_cenas(P, op, est):
    if not (P / "cenas.json").exists():
        if tem_roteiro(P):
            sys.path.insert(0, str(PIPE))
            import roteiro
            if roteiro.ler(P / "roteiro.md")["cenas"] is not None:
                roda(P, "cenas-roteiro", [sys.executable, PIPE / "roteiro.py", "cenas", "roteiro.md", "cenas.json"])
                linha("AVISO", 6, "cenas", "cenas.json gerado do roteiro → revise títulos e âncoras se o validador reclamar")
        if not (P / "cenas.json").exists():
            t = op.get("template") or "explainer"
            print(f"PRÓXIMO: leia {P / 'frases.txt'} e escreva {P / 'cenas.json'} para o template {t} "
                  f"(formato: templates/{t}/schema.json; exemplo: exemplos/). Depois: craft run {P}")
            raise Parada()
    cen = le_json(P / "cenas.json")
    if op.get("template") and cen.get("template") and cen["template"] != op["template"]:
        raise Falha(f"cenas.json é do template {cen['template']}, mas foi pedido {op['template']}",
                    "reescreva cenas.json no formato do template pedido (templates/<t>/schema.json)")
    erros = validar(P, op)
    if erros:
        for e in erros:
            linha("ERRO", 6, "cenas", e)
        raise Falha("cenas.json não passou no validador", f"corrija as linhas acima e rode craft run {P}")
    n = len(cen.get("cenas") or cen.get("itens") or [])
    if "cenas" in est.d["parar_em"] and "cenas" not in est.d["aprovado"]:
        for i, c in enumerate(cen.get("cenas") or cen.get("itens") or []):
            print(f"   {i + 1:2d}. {c.get('titulo') or c.get('texto', '')}  →  {(c.get('visual') or {}).get('type') or c.get('tier', '-')}")
        print(f"PRÓXIMO: mostre a lista de cenas à pessoa. Aprovado: craft aprovar {P} cenas; depois craft run {P}")
        raise Parada()
    return f"{n} cenas, template {template_de(P, op)}, validador ok"


def template_de(P, op):
    cen = le_json(P / "cenas.json", {})
    return op.get("template") or cen.get("template") or "explainer"


def validar(P, op):
    kit_pronto()
    r = subprocess.run([str(KIT_PY), str(PIPE / "montar.py"), str(P), "--template", template_de(P, op), "--so-validar"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return []
    return [ln for ln in (r.stdout + r.stderr).strip().splitlines() if ln.strip()][-15:]


def e7_montar(P, op):
    kit_pronto()
    out = roda(P, "montar", [KIT_PY, PIPE / "montar.py", P, "--template", template_de(P, op)])
    return out.strip().splitlines()[-1]


def e8_duracao(P, op):
    cmd = [sys.executable, PIPE / "duracao.py", "reel.mp4", "final.mp4", "--limite", LIMITE, "--max", ACELERA_MAX]
    if op.get("sem_limite"):
        cmd.append("--sem-limite")
    d = json.loads(roda(P, "duracao", cmd).strip().splitlines()[-1])
    grava_json(P / "duracao.json", d)
    if d.get("aviso"):
        linha("AVISO", 8, "duracao", d["aviso"])
    return d["resumo"]


def e9_conferir(P, op):
    out = roda(P, "conferir", [sys.executable, PIPE / "conferir.py", P, "--sem-limite" if op.get("sem_limite") else "--com-limite"])
    linhas = out.strip().splitlines()
    for ln in linhas[:-1]:
        if ln.startswith("AVISO"):
            linha("AVISO", 9, "conferir", ln[6:])
    return linhas[-1]


def e10_entregar(P, op):
    return roda(P, "entregar", [sys.executable, PIPE / "entregar.py", P]).strip().splitlines()[-1]


# entradas/saídas/opções de cada etapa (o estado.json usa isto para saber o que refazer)
ETAPAS = [
    (1, e1_preparar, ["bruto.mp4"], ["enquadramento.json", "quadro.jpg"], ["fundo", "paleta"]),
    (2, e2_transcrever, ["bruto.mp4", "roteiro.md"], ["bruto.transcript.json"], ["nomes", "apresentador"]),
    (3, e3_cortar, ["bruto.transcript.json", "enquadramento.json", "cortes.json", "roteiro.md"],
     ["cortes.json", "cortado.mp4", "cortado.trechos.json"], ["apresentador"]),
    (4, e4_audio, ["cortado.mp4"], ["limpo.mp4", "audio.json"], []),
    (5, e5_legenda, ["limpo.mp4", "roteiro.md"], ["legenda.json", "frases.txt"], ["nomes", "apresentador"]),
    (6, e6_cenas, ["cenas.json", "legenda.json", "enquadramento.json"], ["cenas.json"], ["template"]),
    (7, e7_montar, ["cenas.json", "limpo.mp4", "legenda.json", "enquadramento.json"], ["reel.mp4", "reel.cenas.jpg"], ["template", "_codigo"]),
    (8, e8_duracao, ["reel.mp4"], ["final.mp4", "duracao.json"], ["sem_limite"]),
    (9, e9_conferir, ["final.mp4", "duracao.json"], ["relatorio.md"], ["sem_limite"]),
    (10, e10_entregar, ["final.mp4", "relatorio.md"], ["saida"], []),
]


def versao_codigo():
    """impressão do código de render: se um template, o motor, o tema ou o kit mudar, a etapa 7 refaz o reel"""
    import hashlib
    h = hashlib.sha1()
    arquivos = sorted(TEMPLATES.glob("**/*.py")) + [RAIZ / "kit" / "reel.py", RAIZ / "tema" / "paletas.json"]
    for f in arquivos:
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


def run(a):
    alvo = Path(a.alvo).expanduser().resolve()
    if alvo.is_dir():
        P = alvo
        if not (P / "bruto.mp4").exists():
            sys.exit(f"ERRO    0 run: {P} não tem bruto.mp4 → passe o vídeo, não a pasta")
    else:
        if not alvo.exists():
            sys.exit(f"ERRO    0 run: {alvo} não existe → confira o caminho do vídeo")
        P = Path(a.pasta).expanduser().resolve() if a.pasta else PASTA_PADRAO / slug(a.nome or alvo.stem)
        P.mkdir(parents=True, exist_ok=True)
        if not (P / "bruto.mp4").exists():
            shutil.copy2(alvo, P / "bruto.mp4")
        elif (P / "bruto.mp4").stat().st_size != alvo.stat().st_size:
            sys.exit(f"ERRO    0 run: {P} já tem outro bruto.mp4 → use --nome diferente ou apague a pasta")
    est = Estado(P)
    op = est.opcoes
    for k in ("apresentador", "nomes", "template", "paleta", "fundo"):
        v = getattr(a, k)
        if v is not None:
            op[k] = v
    if a.sem_limite:
        op["sem_limite"] = True
    op["_codigo"] = versao_codigo()
    if a.roteiro:
        shutil.copy2(Path(a.roteiro).expanduser(), P / "roteiro.md")
    for g in a.parar_em or []:
        if g not in est.d["parar_em"]:
            est.d["parar_em"].append(g)
    if op.get("template") and not (TEMPLATES / op["template"] / "build.py").exists():
        sys.exit(f"ERRO    0 run: template \"{op['template']}\" não existe → craft templates")
    if op.get("paleta") and op["paleta"] not in paletas()["paletas"]:
        sys.exit(f"ERRO    0 run: paleta \"{op['paleta']}\" não existe → use {', '.join(paletas()['paletas'])}")
    est.salva()
    print(f"pasta: {P}")
    for n, fn, ent, sai, ops in ETAPAS:
        if a.ate and n > a.ate:
            print(f"PRÓXIMO: parou depois da etapa {a.ate} (--ate). Continue com craft run {P}")
            return 0
        nome = NOMES[n]
        motivo = est.precisa(nome, ent, sai, ops)
        if not motivo:
            linha("OK", n, nome, (est.d["etapas"][nome].get("resumo") or "") + "  (já feito)")
            if n == 3:
                try:
                    gate_cortes(P, est)
                except Parada:
                    return 0
            continue
        try:
            resumo = fn(P, op, est) if n == 6 else fn(P, op)
        except Parada:
            return 0
        except Falha as f:
            est.falhou(nome, f.oque)
            linha("ERRO", n, nome, f"{f.oque} → {f.como}")
            return 1
        est.feito(nome, ent, ops, resumo)
        linha("OK", n, nome, resumo)
        if n == 3:
            try:
                gate_cortes(P, est)
            except Parada:
                return 0
    saida = P / "saida"
    print(f"PRÓXIMO: olhe {P / 'reel.cenas.jpg'} (uma imagem, um quadro por cena) e entregue {saida} com o resumo de {P / 'relatorio.md'}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="craft", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("alvo", help="vídeo bruto (primeira vez) ou a pasta de trabalho (para continuar)")
    r.add_argument("--roteiro", help="roteiro.md usado na gravação (gabarito da edição)")
    r.add_argument("--nome", help="nome da pasta de trabalho (padrão: nome do arquivo)")
    r.add_argument("--pasta", help=f"pasta de trabalho (padrão: {PASTA_PADRAO}/<nome>)")
    r.add_argument("--apresentador", help="perfil em apresentadores/<nome>.json")
    r.add_argument("--nomes", help="produtos e termos falados, separados por vírgula (ajudam o Whisper)")
    r.add_argument("--template", help="só se a pessoa pedir; padrão explainer")
    r.add_argument("--paleta", help="só se a pessoa pedir: mocha (padrão), latte, nord")
    r.add_argument("--fundo", choices=["auto", "claro", "escuro"], help="só se a pessoa pedir; padrão auto (pelo cenário)")
    r.add_argument("--parar-em", action="append", choices=["cortes", "cenas"], help="só se a pessoa pedir para aprovar")
    r.add_argument("--sem-limite", action="store_true", help="só se a pessoa pedir: não acelera para caber em 60 s")
    r.add_argument("--ate", type=int, help="para depois da etapa N")
    e = sub.add_parser("estado")
    e.add_argument("pasta")
    v = sub.add_parser("validar")
    v.add_argument("pasta")
    c = sub.add_parser("corte")
    c.add_argument("pasta")
    c.add_argument("ini", type=float)
    c.add_argument("fim", type=float)
    c.add_argument("nota")
    ap_ = sub.add_parser("aprovar")
    ap_.add_argument("pasta")
    ap_.add_argument("ponto", choices=["cortes", "cenas"])
    sub.add_parser("templates")
    lg = sub.add_parser("logo")
    lg.add_argument("chave")
    lg.add_argument("slug")
    lg.add_argument("nome")
    lg.add_argument("--falado", default="")
    lg.add_argument("--erro", action="append", default=[])
    a = ap.parse_args(argv)

    if a.cmd == "run":
        return run(a)
    if a.cmd == "estado":
        est = Estado(Path(a.pasta).expanduser())
        print(f"opções: {json.dumps(est.opcoes, ensure_ascii=False)}  parar_em: {est.d['parar_em']}  aprovado: {est.d['aprovado']}")
        for n, nome in NOMES.items():
            e = est.d["etapas"].get(nome)
            print(f"{n:2d} {nome:<11} {('ok  ' + e.get('resumo', '')) if e and e['status'] == 'ok' else ('ERRO ' + e.get('motivo', '')) if e else '-'}")
        return 0
    if a.cmd == "validar":
        P = Path(a.pasta).expanduser().resolve()
        erros = validar(P, Estado(P).opcoes)
        print("\n".join(erros) if erros else "cenas ok")
        return 1 if erros else 0
    if a.cmd == "corte":
        P = Path(a.pasta).expanduser().resolve()
        print(roda(P, "corte-manual", [sys.executable, PIPE / "corte_manual.py", P, a.ini, a.fim, a.nota]).strip())
        print(f"PRÓXIMO: craft run {P}")
        return 0
    if a.cmd == "aprovar":
        est = Estado(Path(a.pasta).expanduser())
        if a.ponto not in est.d["aprovado"]:
            est.d["aprovado"].append(a.ponto)
        est.salva()
        print(f"{a.ponto} aprovado. PRÓXIMO: craft run {a.pasta}")
        return 0
    if a.cmd == "templates":
        for t in sorted(TEMPLATES.iterdir()):
            s = le_json(t / "schema.json", {})
            if (t / "build.py").exists():
                print(f"{t.name:<11} {s.get('description', '')}")
        return 0
    if a.cmd == "logo":
        cmd = [sys.executable, PIPE / "buscar_logo.py", a.chave, a.slug, a.nome, "--falado", a.falado]
        for e in a.erro:
            cmd += ["--erro", e]
        return subprocess.run([str(x) for x in cmd]).returncode
    return 0
