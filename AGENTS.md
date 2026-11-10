# AGENTS.md — craft-reels

Você é um agente editando um reel da **Software Craftsmanship Brasília**. Este repositório é uma pipeline
**fixa**: as mesmas etapas, na mesma ordem, com os mesmos arquivos. Não invente passos. Siga isto.

## Em uma frase

Vídeo falado (celular, pessoa falando para a câmera) → `craft run` → reel 1080x1920 de **até 60 s** com a
identidade da comunidade. Só a etapa 6 (cenas) é sua; o resto é a máquina.

## Comandos

```bash
./craft run <video.mp4> [--roteiro roteiro.md] [--apresentador pedro] [--nomes "Orca, Claude Code"]
./craft run <pasta>                     # continua de onde parou (refaz só o que mudou)
./craft validar <pasta>                 # confere o cenas.json sem renderizar (rápido)
./craft corte <pasta> <ini> <fim> "nota"   # corte achado assistindo o cortado.mp4 (tempos do cortado)
./craft estado <pasta>                  # o que já foi feito
./craft templates                       # os 7 templates
./craft logo <chave> <slug> "Nome"      # logo nova do Simple Icons para o catálogo
```

Pasta de trabalho: `~/Videos/craft-reels/<nome>/` (ou `--pasta`). Nunca em `/tmp` (pode ser RAM; o render
precisa de ~17 GB por 2 min de vídeo).

`--nomes`: todo produto e termo técnico que a pessoa fala (o Whisper erra nome próprio sem isso). Com
`--roteiro`, os `nomes` do roteiro já entram.

## As etapas

| # | Etapa | Quem | Gera | Regra fixa |
|---|---|---|---|---|
| 1 | preparar | máquina | `enquadramento.json`, `quadro.jpg` | acha o rosto; cenário claro → fundo escuro, cenário escuro → fundo claro |
| 2 | transcrever | máquina | `bruto.transcript.json` | faster-whisper large-v3 local; correções do catálogo e do apresentador |
| 3 | cortar | máquina | `cortes.json`, `cortado.mp4` | "refaz"/"refaça", gaguejo, silêncio; tomada repetida (com roteiro); laço A/B/C até `LIMPO`; suspeitas (`?`) **não** são cortadas |
| 4 | audio | máquina | `limpo.mp4`, `audio.json` | passa-alta, redução de ruído, compressor, -14 LUFS |
| 5 | legenda | máquina | `legenda.json`, `frases.txt` | transcreve o cortado; o roteiro corrige palavras |
| 6 | cenas | **você** | `cenas.json` | ver abaixo |
| 7 | montar | máquina | `reel.mp4`, `reel.cenas.jpg` | template + paleta + logos automáticas |
| 8 | duracao | máquina | `final.mp4` | > 60 s → acelera até 1,25x sem mudar o tom; nada é cortado sozinho |
| 9 | conferir | máquina | `relatorio.md` | duração, volume, lascas, geometria |
| 10 | entregar | máquina | `saida/<nome>.mp4`, `-leve.mp4` | |

Saída: cada etapa imprime **uma linha** `OK`, `AVISO` ou `ERRO <n> <etapa>: <o que> → <como corrigir>`.
`PRÓXIMO:` diz o que você faz agora. O detalhe fica em `<pasta>/log/` — abra só se uma linha mandar.

## Etapa 6: escrever o `cenas.json`

1. Leia **uma vez** o `frases.txt` (o texto cortado, uma frase por linha com o segundo em que começa).
2. Template: **`explainer`**, a menos que a pessoa tenha pedido outro pelo nome. Formato de cada um em
   `templates/<t>/schema.json` (tem exemplo); visuais em `templates/VISUAIS.md`.
3. Divida em pontos: uma cena a cada 5–15 s (nunca menos de 3 s). Por cena: `at`, `titulo` (1–4 palavras,
   UMA entre `*asteriscos*`) e `visual` — o mais simples que deixa o ponto claro em 2 s sem som.
4. `chaves`: 3–8 palavras que carregam o sentido (destacadas na legenda).
5. `./craft validar <pasta>` até dar `cenas ok`, depois `./craft run <pasta>`.

Com `--roteiro` que tem um bloco ```` ```cenas ````, o `cenas.json` sai pronto do roteiro; você só corrige o
que o validador apontar.

Ao final, olhe **uma** imagem: `reel.cenas.jpg` (um quadro por cena). Confira título e visual inteiros, nada
sobre o rosto, legenda legível. A legenda fica **sempre embaixo e nunca sobre o rosto** (logo abaixo do queixo,
entre y 1330 e 1456); os templates calculam isso sozinhos a partir do `enquadramento.json`. Se algo estiver errado, ajuste o `cenas.json` e rode de novo (só as etapas
7–10 refazem).

## Rosto muito grande no quadro (selfie de perto)

O `explainer` e o `codigo` se ajustam sozinhos (a pessoa encolhe; o painel acompanha o vídeo, sem faixa vazia).
Os templates de vídeo inteiro precisam de espaço acima da cabeça: se não houver, o validador dá **ERRO**
dizendo que o vídeo não serve para aquele template (`bastidores`, `historia`, `ranking`). Não force: conte à
pessoa e sugira o `explainer`.

## Logos

Produto ou empresa pública falado → a logo aparece sozinha, se o template tiver lugar (todos menos o
`destaque`). Logo que falta no catálogo: `./craft logo <chave> <slug-do-simpleicons> "Nome" --falado "forma falada"`.
Sem logo oficial: cartão com o nome (`"icone"`). **Nunca desenhe, invente ou recolore uma logo.**

## Controle: só quando a pessoa pedir

Por padrão tudo roda direto. Ligue estes **apenas** se a pessoa pedir com essas palavras (ou equivalentes):

| A pessoa diz | Você usa |
|---|---|
| "quero aprovar os cortes" | `--parar-em cortes` → mostre `aprovacao.jpg`; ela aprova → `craft aprovar <pasta> cortes` |
| "quero ver as cenas antes" | `--parar-em cenas` → mostre a lista; ela aprova → `craft aprovar <pasta> cenas` |
| "usa o template X" | `--template X` |
| "usa a paleta Nord/Latte" / "usa o fundo claro" | `--paleta nord\|latte`, `--fundo claro\|escuro` |
| "não acelera" / "pode passar de 60 s" | `--sem-limite` |
| "esse pedaço está errado" | `craft corte <pasta> <ini> <fim> "nota"` (tempos do cortado.mp4) |

## Nunca

- cortar fora das regras (suspeita `?` só sai se a pessoa pedir);
- trocar template, paleta ou fundo sem pedido;
- inventar logo, número ou palavra que a pessoa não falou;
- trabalhar em `/tmp`; imprimir transcrições inteiras com tempo (use `frases.txt` e `grep`);
- divulgar a ferramenta no vídeo: o reel mostra só a comunidade (selo e `@software_craftsmanship`).

## Ao entregar, conte à pessoa (do `relatorio.md`)

Duração antes → depois; cortes agrupados; suspeitas mantidas; cada cena em uma linha (título → visual);
palavras corrigidas na legenda; o que vale ela assistir antes de postar. Arquivos em `<pasta>/saida/`.

## Mais

- `skills/roteiro/SKILL.md` — escrever o roteiro (até 60 s) antes de gravar
- `skills/reel/SKILL.md` — a skill que roda esta pipeline
- `docs/armadilhas.md` — o que já deu errado e por quê
- `docs/plano.md` — por que a pipeline é assim
