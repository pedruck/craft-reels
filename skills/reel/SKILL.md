---
name: reel
description: Edita um vídeo falado (celular, 9:16, pessoa falando para a câmera) num reel de até 60 s com a identidade da Software Craftsmanship Brasília, pela pipeline fixa craft-reels — corta gaguejo, silêncio e as frases marcadas com "refaz"/"refaça", limpa o áudio, legenda, põe visuais simples e a logo de cada produto falado. Use quando mandarem um vídeo para editar, cortar, legendar, "fazer o reel", "deixar no formato da comunidade", "colocar visuais em cima" ou "acelerar", mesmo sem dizer "reel". Também para continuar ou corrigir um reel já começado.
---

# Reel (pipeline craft)

Esta skill só roda a pipeline. **Todas as regras estão no `AGENTS.md` do repositório** — leia-o antes do
primeiro passo; ele é curto.

Repositório: dois níveis acima da pasta real desta skill (ela é instalada como link). Chame-o de `$R`.

```bash
R="$(readlink -f "<base directory desta skill>")/../.."
"$R/craft" run <video.mp4> [--roteiro roteiro.md] [--apresentador <nome>] [--nomes "Produto A, Produto B"]
```

1. Rode `craft run`. Ele para em `PRÓXIMO:` quando precisa de você (quase sempre só na etapa 6: escrever o
   `cenas.json` a partir do `frases.txt`).
2. Faça o que o `PRÓXIMO:` diz e rode `craft run <pasta>` de novo, até a etapa 10.
3. Olhe só a `reel.cenas.jpg`. Corrija o `cenas.json` se precisar e rode de novo.
4. Entregue `saida/` com o resumo do `relatorio.md`.

Não ligue pontos de controle (`--parar-em`, `--template`, `--paleta`, `--fundo`, `--sem-limite`, `--ruido`) sem a
pessoa pedir. A tabela "pedido → opção" está no `AGENTS.md`.

Primeira vez na máquina: `"$R/install.sh"`.
