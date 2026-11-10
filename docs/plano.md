# Plano v2: `craft-reels`, uma pipeline fixa de reels para a Software Craftsmanship Brasília

Status: **implementado** (novembro de 2026). Este é o plano aprovado; o que mudou na implementação está em
"Decisões tomadas", no fim. As instruções de uso estão no `AGENTS.md`.

## Em uma frase

Um repositório lido principalmente por agentes de IA. Ele pega um vídeo falado (e,
se existir, o roteiro dele) e entrega um reel de até 60 s com a identidade da
comunidade, sempre pelas mesmas etapas, na mesma ordem e com os mesmos arquivos.

Vale para **qualquer assunto e qualquer membro**. Nada no código conhece um tema
específico: Orca, Omarchy e System 1 aparecem só como filmagem de exemplo, nas
prévias e nos testes.

## Princípios

1. **Uma pipeline, um caminho.** Um comando (`craft`), um tema e um conjunto fechado de templates (abaixo), cada um com campos fixos. O template padrão é o `explainer`; outro só entra se a pessoa pedir pelo nome.
2. **A máquina decide tudo o que tem regra.** Cortes, áudio, legenda, logos, duração e conferência são scripts determinísticos. O agente só escreve as cenas (etapa 6) e olha uma imagem no fim.
3. **Contratos fixos.** Cada etapa lê e grava arquivos com nome e formato definidos. Os erros saem um por linha, no formato `ERRO <etapa>: <o que> → <como corrigir>`. A pipeline pode ser retomada de onde parou.
4. **Controle só quando pedido.** Os pontos de parada existem, mas ficam desligados. O agente só os liga se a pessoa pedir.
5. **Até 60 s, sempre.** A duração é verificada no roteiro, depois do corte e na entrega.
6. **Barato.** Tudo roda local, sem chave de API. O agente lê só o resumo e as exceções.

## Base: o repositório do Artem

O repositório começa como um clone de
[artemnovitckii/claude-editing-skills](https://github.com/artemnovitckii/claude-editing-skills)
no commit `beff6b8` (MIT). O histórico e o crédito são mantidos, e um `upstream` fica
configurado para puxar correções dele.

| Do Artem | Destino |
|---|---|
| `kit/reel.py` (Job, Comp, âncoras de palavra, legenda, render, folha de conferência) | **fica**, é o motor |
| `kit/cutout.py` (recorte com RobustVideoMatting) e `kit/setup.sh` | **ficam** |
| `kit/transcribe.py` (Groq, com chave de API) | **trocado** pela transcrição local com faster-whisper |
| os 6 formatos com pessoa falando (`explainer`, `split-screen`, `behind-the-person`, `ranking-list`, `storytelling`, `trial-reels`) | **viram a base** dos nossos templates, um a um, com o tema `craft` |
| `install.sh` e `.claude-plugin/` | **ficam**, com nome e descrição nossos |
| as 5 skills fotográficas (`shape-shift`, `picture-stack`…) e o `style_template.py` | **saem** (continuam no repositório do Artem): não são de pessoa falando |

## O que entra no lugar de quê

| Fonte | O que entra na pipeline |
|---|---|
| nossa skill `reel-explainer` | regras de corte ("refaz", gaguejo, silêncio), regras A/B/C (sem lascas, conferência trecho a trecho, corte manual no tempo do bruto), catálogo de logos, correções do Whisper, validador de spec, aceleração sem mudar o tom, armadilhas conhecidas |
| nossa skill `roteiro-video-curto` | etapa 0, com saída num formato fixo (`roteiro.md`) que a pipeline lê |
| [video-use](https://github.com/browser-use/video-use) (MIT) | fade de 30 ms em toda emenda; transcrição como interface do agente, imagem só no fim |
| [video-editing-skill](https://github.com/social-media-skills/video-editing-skill) (MIT) | etapa de áudio: passa-alta 80 Hz, compressor e -14 LUFS (redução de ruído opcional); relatório por vídeo |
| [ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT) | checagens automáticas (rosto coberto, tamanho de legenda, volume) e a página de aprovação de cortes, usada só sob pedido |
| [open-edits](https://github.com/kevinbadi/open-edits) (MIT) | visual `contador` para número falado; regra de que o visual entra no máximo 0,1 s antes da palavra |
| ideia nossa | roteiro como gabarito: escolhe a tomada, corrige a legenda e já traz as cenas |

Ficaram de fora, por tirarem previsibilidade:
- template escolhido pelo agente (só a pessoa escolhe; sem pedido, é o `explainer`);
- skill de criar template;
- copiar o estilo de um reel de referência;
- desenho livre em HTML;
- WhisperX;
- Remotion.

## A pipeline

Entrada: `bruto.mp4` e, opcionalmente, `roteiro.md`. Pasta de trabalho fixa:
`~/Videos/craft-reels/<slug>/`, sempre no disco, nunca em `/tmp`.

```
craft run bruto.mp4 [--roteiro roteiro.md] [--apresentador pedro]
```

| # | Etapa | Quem | Entrada → saída | Regra fixa |
|---|---|---|---|---|
| 0 | roteiro *(opcional, antes de gravar)* | agente, skill `roteiro` | tema → `roteiro.md` | 150–180 palavras; hook → nome → explicação → exemplos e dados → limite e fechamento; uma sugestão de visual por frase |
| 1 | preparar | máquina | `bruto.mp4` → `enquadramento.json`, `quadro.jpg` | o rosto é achado automaticamente (olhos, queixo, centro) e o painel é calculado; se falhar, o agente lê o `quadro.jpg` com régua; o fundo claro ou escuro é escolhido pela luminosidade do cenário |
| 2 | transcrever | máquina | → `bruto.transcript.json` | faster-whisper large-v3 local, parâmetros fixos; correções do catálogo e do apresentador |
| 3 | cortar | máquina | → `cortes.json`, `cortado.mp4` | "refaz", gaguejo e silêncio; com roteiro, fica a tomada que bate com ele; laço A/B/C até `LIMPO`; fade de 30 ms nas emendas; suspeitas (`?`) **não** são cortadas, só relatadas |
| 4 | áudio | máquina | `cortado.mp4` (áudio tratado) | passa-alta 80 Hz, compressor, -14 LUFS; redução de ruído só se a pessoa pedir (`--ruido`) |
| 5 | legenda | máquina | → `legenda.json`, `frases.txt` | transcreve o cortado; o roteiro corrige palavras divergentes; palavras duvidosas sem roteiro viram exceção |
| 6 | cenas | **agente** | `frases.txt` → `cenas.json` | com roteiro, é gerado das sugestões e o agente só revisa; sem roteiro, o agente escreve; uma cena a cada 5–15 s; só os tipos de visual fixos; `craft validar` precisa passar |
| 7 | montar | máquina | → `reel.mp4`, `cenas.jpg` | logos detectadas pelas menções; recorte de fundo; render HyperFrames com o tema `craft` |
| 8 | duração | máquina | `reel.mp4` | se passar de 60 s, acelera até 1,25x sem mudar o tom; se ainda passar, `AVISO` com as cenas candidatas a sair (nada é cortado sozinho) |
| 9 | conferir | máquina + agente olha 1 imagem | → `relatorio.md` | duração ≤ 60 s, -14 LUFS ±1, nenhum trecho < 0,25 s, texto dentro da largura, nada nas zonas do Instagram, rosto não coberto; o agente olha só o `cenas.jpg` |
| 10 | entregar | máquina | → `saida/<slug>.mp4`, `saida/<slug>-leve.mp4`, `relatorio.md` | a versão leve tem 720 px, para WhatsApp |

**Como o agente roda:** `craft run` executa as etapas 1–5 e para na 6 com
`PRÓXIMO: escreva cenas.json (ver schemas/cenas.schema.json)`. Com roteiro, essa
parada é pulada. Rodar `craft run` de novo continua da 7 à 10. O `estado.json` guarda
o que já foi feito; uma etapa só roda de novo se a entrada dela mudou.

**Pontos de controle (desligados por padrão):**

| A pessoa pede | Opção |
|---|---|
| "quero aprovar os cortes" | `--parar-em cortes` gera `aprovacao.jpg`, com um quadro em cada corte |
| "quero ver as cenas antes" | `--parar-em cenas` mostra a lista título → visual antes de renderizar |
| "não acelera" / "pode passar de 60 s" | `--sem-limite` |
| "usa a paleta Nord" / "usa o fundo claro" | `--paleta latte\|nord`, `--fundo claro\|escuro` |
| "tira o ruído" | `--ruido` (liga a redução de ruído na etapa 4) |
| "esse corte está errado" | `craft corte <ini> <fim>` (tempo do cortado, regra C) |

## Contratos para agentes

- **`AGENTS.md` na raiz** (com `CLAUDE.md` apontando para ele) é a porta de entrada.
  Em uma página, ele traz:
  - a pipeline e os comandos;
  - os arquivos de cada etapa;
  - a tabela de erros e o que fazer em cada um;
  - o que nunca fazer: cortar fora das regras, inventar logo, trabalhar em `/tmp`, ligar ponto de controle sem pedido.
- **Duas skills, finas:** `roteiro` (etapa 0) e `reel` (roda a pipeline). Cada `SKILL.md` aponta para o `AGENTS.md`, sem repetir regra.
- **Schemas** em `schemas/`: `roteiro`, `cenas`, `enquadramento` e `relatorio`. O `craft validar` usa os mesmos schemas.
- **Saída curta:** cada etapa imprime uma linha `OK`, `AVISO` ou `ERRO`; o detalhe vai para `log/`.
- **Exemplo completo** em `exemplos/system1/`: `roteiro.md`, `cenas.json`, `cenas.jpg` e `relatorio.md`.

## Identidade visual: tema `craft`

Tudo vem de `tema/paletas.json`. O template não tem cor nem fonte fixa no código.

- **Cores:** paletas frias e suaves, de temas de editor de código abertos (MIT). Cada paleta define a cor de destaque e tem duas versões de fundo. Pares renderizados em `docs/previas/par-*.jpg`.

  | Paleta | Fundo claro | Fundo escuro |
  |---|---|---|
  | **`mocha` (padrão)**, malva | base Latte `#EFF1F5`, tinta `#4C4F69`, destaque `#8839EF` | base Mocha `#1E1E2E`, tinta `#CDD6F4`, destaque `#CBA6F7` |
  | `latte`, lavanda | base Latte `#EFF1F5`, destaque `#7287FD` | base Mocha `#1E1E2E`, destaque `#B4BEFE` |
  | `nord`, azul | Snow Storm `#ECEFF4`, tinta `#2E3440`, destaque `#5E81AC` | Polar Night `#2E3440`, tinta `#ECEFF4`, destaque `#88C0D0` |

  Fontes: [Catppuccin](https://github.com/catppuccin/catppuccin) e [Nord](https://www.nordtheme.com/docs/colors-and-palettes). A paleta só muda se a pessoa pedir (`--paleta latte|nord`).
- **Fundo claro ou escuro: escolhido pela máquina, na etapa 1.** A regra mede a luminosidade média do cenário (o terço de cima do quadro, em amostras do vídeo bruto) e escolhe o fundo que combina com ele, para o vídeo parecer parte do quadro:
  - cenário claro (> 0,55) → fundo claro;
  - cenário escuro (< 0,45) → fundo escuro;
  - entre os dois → escuro, o padrão do Mocha.

  Nos três vídeos de teste, o carro (Orca, 0,27) cai no fundo escuro e o quarto (Omarchy 0,61, System 1 0,60) no claro. O valor e a decisão ficam no `enquadramento.json`. A pessoa pode forçar com `--fundo claro|escuro`.
- **Cor de destaque sobre fundo escuro:** na pílula da legenda, sobre o vídeo e no editor, usa-se a versão clara do destaque, para manter o contraste.
- **Templates com o vídeo inteiro** (`bastidores`, `ranking`, `historia`, `destaque`): o fundo muda só os cartões e as chaves, porque o fundo é o próprio vídeo.
- **Fontes:**
  - Inter nos títulos e na legenda;
  - JetBrains Mono (OFL) nos visuais de código e terminal e nas palavras-chave.
- **Palavra-chave:** em fonte mono, na cor de destaque, entre chaves, como na logo: `{teclado}`. Vale no título e na legenda.
- **Selo:** a logo da comunidade pequena no canto superior esquerdo, o vídeo todo. As logos de produto ficam no canto direito. Não há cartão final, porque contaria nos 60 s.
- **Só a comunidade aparece:** o reel divulga a Software Craftsmanship Brasília (selo, nome e `@software_craftsmanship`) e nunca a ferramenta. O nome do repositório não aparece em nenhum vídeo, legenda ou crédito.
- **Legenda:** pílula escura abaixo do queixo em todos os templates (menos o `destaque`, que usa palavra grande no peito).
- **Visuais, só estes 8:**
  - `logo`;
  - `fluxo` (2–4 caixas);
  - `lista` (até 4 itens);
  - `compare`;
  - `contador`;
  - `codigo` (com modo diff para antes/depois de refatoração);
  - `terminal`;
  - `foto` (só imagem livre, com crédito).

## Templates

Um conjunto fechado, como no repositório do Artem. Cada template tem um
`schema.json` com campos fixos (título, visual, legenda, logos…), então qualquer
assunto entra pelos mesmos campos. Prévias de 1 quadro, com filmagem dos vídeos brutos
de exemplo, estão em `previas/` (`previas/templates.png` mostra todos).

| Template | Base no Artem | Como é | Serve para |
|---|---|---|---|
| `explainer` **(padrão)** | explainer | fundo claro, título + visual em cima, pessoa num painel com a cabeça saindo | explicar um conceito |
| `split` | split-screen | selo de passo + título + janela com print/código em cima, pessoa embaixo, legenda na emenda | mostrar uma ferramenta ou um passo a passo |
| `bastidores` | behind-the-person | cartão atrás da pessoa (recorte de fundo), palavra grande no peito | apresentar um produto ou uma ideia de impacto |
| `ranking` | ranking-list | tier list (S, A, B…) que vai se preenchendo conforme a fala | comparar opções |
| `historia` | storytelling | três cartões de imagem + título + subtítulo sobre o vídeo inteiro | contar algo em partes |
| `destaque` | trial-reels | cartão de post da comunidade no topo + número ou palavra grande no peito | um dado ou frase de impacto |
| `codigo` | novo | editor com destaque de sintaxe e a linha da fala realçada, pessoa recortada embaixo | mostrar código, refatoração ou terminal |

As prévias são quadros estáticos que definem layout, tema e posições. Os templates de
verdade são composições HyperFrames animadas, derivadas do `build.py` de cada
original do Artem.

## Regra das logos

Sempre que a fala citar um **produto ou uma empresa pública**, a logo dele aparece, desde que o template tenha lugar para logo:

| Template | Onde a logo aparece |
|---|---|
| `explainer`, `split`, `historia`, `codigo` | pipoca grande na palavra e vai para o canto superior direito; nas menções seguintes, o selo do canto pulsa |
| `bastidores` | no cartão atrás da pessoa |
| `ranking` | no item da tier list |
| `destaque` | sem lugar para logo de produto (o cartão é da comunidade) |

- **Detecção:** é automática, pela legenda e pelo catálogo (`catalogo/logos.json`, com as formas faladas e os erros comuns do Whisper).
- **Repetição:** se o visual da cena já mostra a logo, ela não pipoca de novo.
- **Ordem de busca:**
  1. catálogo;
  2. Simple Icons (CC0);
  3. kit de imprensa ou repositório oficial, conferindo a licença.
- **Sem logo oficial** (ex.: o Jev na prévia do `ranking`): aparece um cartão com o nome. A logo nunca é desenhada nem recolorida.

## Estrutura do repositório

```
craft-reels/
├── AGENTS.md  CLAUDE.md     porta de entrada dos agentes
├── README.md                curto, para humanos
├── LICENSE  NOTICE.md       MIT; copyright do Artem mantido; terceiros listados
├── install.sh  .claude-plugin/
├── craft                    CLI única
├── kit/                     motor do Artem (reel.py, cutout.py, setup.sh) + transcrição local
├── pipeline/                etapas 1–10 + estado.json
├── templates/               explainer split bastidores ranking historia destaque codigo
│                            (cada um: build.py, schema.json, previa.png)
├── visuais/                 os 8 tipos de visual
├── tema/                    paletas.json (mocha, latte, nord × claro, escuro), logo.svg, fontes
├── catalogo/                logos/ + correcoes.json
├── apresentadores/          pedro.json
├── skills/                  roteiro/  reel/
├── schemas/
├── exemplos/system1/
└── testes/                  regras de corte e validador, com transcrições reais (sem vídeo bruto)
```

## Fases

1. **Base:**
   - clone do Artem em `beff6b8` e remoção do que sai;
   - CLI `craft` com `estado.json`;
   - `AGENTS.md` inicial.
2. **Etapas 1–5:**
   - extraídas da `reel-explainer`, mais a etapa de áudio e o roteiro como gabarito;
   - testes com as transcrições da Orca, do Omarchy e do System 1.
3. **Tema e templates:**
   - tema `craft`, os 7 templates (a partir das prévias aprovadas) e os 8 visuais;
   - regra das logos;
   - `craft validar`.
4. **Etapas 7–10:** montar, duração, conferir e entregar.
5. **Skills e exemplo:** `roteiro` e `reel`; `exemplos/system1/`.
6. **Prova:**
   - rodar os 3 vídeos brutos de ponta a ponta, só pelo `AGENTS.md`;
   - comparar com as versões que você aprovou;
   - instalar do zero numa pasta limpa.
7. **Publicação:** só com o seu OK.

## Decisões tomadas

1. **Publicação:** repositório público em `github.com/pedruck/craft-reels`.
2. **Tema:** paleta padrão Catppuccin Mocha; Latte e Nord sob pedido; cada uma com fundo claro e escuro,
   escolhido pela luminosidade do cenário. Palavra-chave em mono entre chaves `{palavra}`.
3. **Logo da comunidade:** a imagem de 150 px foi vetorizada (Potrace) em `tema/logo.svg`.
4. **Skills antigas:** `reel-explainer` e `roteiro-video-curto` foram substituídas por `reel` e `roteiro`.
5. **Templates:** 7, seis a partir dos formatos do Artem e um novo (`codigo`), todos no mesmo motor
   (`templates/motor.py`). O agente não escolhe template: sem pedido é o `explainer`.
6. **Legenda:** sempre embaixo e nunca sobre o rosto (faixa y 1330–1456, logo abaixo do queixo).
7. **Divulgação:** o reel mostra só a comunidade; o nome da ferramenta não aparece em vídeo nenhum.
