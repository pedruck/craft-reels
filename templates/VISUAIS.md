# Visuais

Os templates `explainer`, `split`, `codigo` e `bastidores` mostram um visual por cena (`"visual": {...}`).
Escolha nesta ordem e pare no primeiro que deixa o ponto claro **em 2 segundos, com o som desligado**:

1. `logo` — o ponto é "o que é X" / "conheça X"
2. `fluxo` — uma relação: A vira B, A em cima de B, um coordena vários
3. `lista` — uma enumeração (até 4 itens)
4. `compare` — antes/depois, com/sem, um/vários
5. `contador` — um número que ele fala ("17× mais barato")
6. `codigo` / `terminal` — o ponto é o código ou o comando
7. `foto` — print do produto, só quando o ponto é "olha essa tela" e a imagem é livre (README, site oficial, press kit)

Regras que valem para todos:
- Tudo entra **na palavra que o nomeia** (`"at": "teclado"`), nunca antes.
- Texto em caixa: 1–3 palavras. Ícone: logo do catálogo (`"logo": "docker"`) ou emoji óbvio.
- Número na tela é sempre um número que a pessoa falou.
- `*palavra*` sai em fonte mono, na cor de destaque, entre chaves: `{palavra}`.
- O validador (`craft validar <pasta>`) mede tudo com as fontes de verdade e diz o que não cabe.

## Tempo (`at`)

| Escrita | Significa |
|---|---|
| `"teclado"` | primeira vez que a palavra é falada |
| `"teclado#2"` | segunda vez |
| `"teclado+0.3"` | 0,3 s depois |
| `"dois lados"` | a sequência de palavras |
| `36.7` | segundo 36,7 do vídeo cortado |

A comparação ignora maiúscula e pontuação, mas não acento. Para começo de cena prefira uma palavra rara.
Ache a palavra com `grep` no `frases.txt`.

## `lista`
```json
{"type": "lista", "items": [{"icone": "📦", "texto": "Tudo *pronto*", "at": "pronto"},
                            {"logo": "docker", "texto": "Docker", "at": "Docker"}]}
```
Até 4 itens. Sem `icone`/`logo`, sai o número (1, 2, 3).

## `fluxo`
```json
{"type": "fluxo", "forma": "linha", "nos": [{"logo": "archlinux", "texto": "Arch Linux", "at": "Arch"},
                                            {"logo": "omarchy", "texto": "Omarchy", "at": "constrói", "destaque": true}]}
```
`linha`: 2–3 caixas lado a lado. `hub`: a primeira em cima, até 3 embaixo. `destaque: true` deixa a caixa escura.

## `grade`
```json
{"type": "grade", "items": [{"logo": "docker", "texto": "Docker", "at": "Docker"}, {"icone": "🎨", "texto": "Temas"}]}
```
Até 6 quadrinhos. Para "vem com X, Y e Z".

## `compare`
```json
{"type": "compare", "arrow_at": "vira",
 "left":  {"label": "Antes", "big": "1 agente", "small": "faz tudo", "at": "sozinho"},
 "right": {"label": "Depois", "big": "Time", "small": "cada um uma parte", "at": "time"}}
```
Cada lado: `big` (+ `small`), `logo` em cima do texto, ou `img`. `"seta": false` para lado a lado sem antes→depois.

## `logo`
```json
{"type": "logo", "logo": "omarchy", "at": "Omarchy"}
```
A logo grande e o nome (ou a logo por extenso, se o catálogo tiver `escrito`).

## `contador`
```json
{"type": "contador", "valor": "17", "depois": "×", "texto": "mais *barato*", "legenda": "200 mensagens por 1 centavo", "at": "17"}
```
Número inteiro conta de 0 até o valor. Valor com vírgula ("0,2") aparece direto.

## `codigo`
```json
{"type": "codigo", "arquivo": "classificar.py", "linguagem": "python",
 "linhas": ["opcoes = [\"financeiro\", \"técnico\"]", "resposta = modelo.classificar(msg, opcoes)", "+ return resposta", "- print(resposta)"],
 "realces": [{"linha": 2, "at": "classificar"}], "entram": [{"linha": 3, "at": "devolve"}]}
```
Linha com `+ ` / `- ` vira diff (verde/vermelho riscado). `realces` move a barra de destaque para a linha
na palavra. `entram` faz a linha aparecer na palavra (as outras entram no começo da cena).

## `terminal`
```json
{"type": "terminal", "titulo": "bash", "comandos": [{"cmd": "craft run video.mp4", "at": "roda", "saida": ["OK  1 preparar", "OK  2 transcrever"]}]}
```
O comando é digitado; a saída aparece linha a linha.

## `foto`
```json
{"type": "foto", "img": "img/tela.jpg", "barra": "Orca · worktrees", "logo": "orca", "credito": "imagem: github.com/stablyai/orca · MIT",
 "foco": "50% 0", "ajuste": "cover", "zoom": 1.06}
```
Caminho relativo à pasta de trabalho. `barra` põe uma barra de janela em cima. Sempre com `credito`.

## Logos

Todo produto ou empresa pública do catálogo (`catalogo/logos/logos.json`) falado numa cena aparece sozinho:
pipoca grande no meio do visual e vai para o canto superior direito; nas menções seguintes o selo pulsa.
Se o visual da cena já mostra a logo, ela não pipoca de novo. Produto novo: `craft logo <chave> <slug> "Nome"`
(Simple Icons, CC0), ou baixe do repositório oficial conferindo a licença. **Nunca desenhe nem recolore uma logo**;
sem logo oficial, use `"icone"` e o nome.
