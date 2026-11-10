---
name: roteiro
description: Escreve o roteiro de um reel da Software Craftsmanship Brasília (pt-BR, até 60 s, informal, texto corrido, com hook, dados e exemplos concretos) e grava o roteiro.md que a pipeline craft usa como gabarito da edição. Use sempre que pedirem roteiro, script, texto para narrar ou "o que falar" num vídeo curto sobre qualquer tema (tecnologia, IA, programação, software craftsmanship, produto), mesmo sem dizer "roteiro" — por exemplo "me escreve o que falar num vídeo de 50s sobre X". Também para reescrever ou ajustar um roteiro curto que já existe.
---

# Roteiro de reel

Roteiro para ser falado por uma pessoa da comunidade, para um público que não é especialista. O objetivo:
prender nos primeiros segundos, explicar sem perder ninguém e deixar algo concreto (um número, um exemplo,
uma regra prática). **Limite: 60 s** — reel de até 1 minuto.

## Antes de escrever

1. **Confira o tema.** Termo recente, de nicho ou ambíguo: pesquise antes. Explicar errado é pior que demorar.
2. **Junte dados.** Números que reforcem cada afirmação (velocidade, custo, adoção, "X vezes mais"), com a fonte.
   Prefira teste independente a número de fornecedor, e diga qual é qual.
3. **Duração.** Sem pedido, ~50 s. Ritmo falado informal ≈ 3 palavras/s: 30 s ≈ 90 palavras, 50 s ≈ 150,
   60 s ≈ 180. **Passou de 180 palavras, corte** — a pipeline acelera até 1,25x, mas não faz milagre.

## Estrutura (nesta ordem, invisível no texto)

1. **Hook** — uma frase que gera curiosidade sem explicar nada; quebrar expectativa funciona
   ("Existe um novo tipo de IA, e ela não foi feita pra conversar com você.").
2. **Nome** — o nome do que se explica, numa frase curta.
3. **Explicação** — uma ou duas frases: o que é e como funciona, comparando com algo conhecido.
4. **Exemplos e dados** — situação concreta, depois os números, depois o limite (quando não usar).
5. **Fechamento** — uma regra prática ("decisão frequente com opções fechadas, vai de X; problema aberto, vai de Y").

## Regras de escrita

- **Texto corrido.** Sem tópicos, títulos ou rótulos ("Hook:"). É para ler em voz alta.
- **pt-BR falado:** "tá", "pra", "vai de". Frases curtas, que caibam num fôlego.
- **Nada que exija bagagem.** Corte autor, teoria ou sigla que um leigo não pega; troque jargão por palavra
  comum ("benchmark" → "teste comparativo", "latência" → "tempo de resposta").
- **Ligue os exemplos** com conectivos falados: "então imagina que…", "vamos supor que…".
- **Exemplo concreto**, nunca abstrato. **Dado com comparação**, arredondado ("umas 70 vezes").
- **Mostre o limite** do tema: dá credibilidade.
- **Divulgue só a comunidade**, nunca a ferramenta de edição.

## Entrega

1. Uma linha: o que foi entregue e a duração estimada (palavras ÷ 3).
2. O roteiro entre linhas `---`, em texto corrido.
3. Notas curtas só se úteis: de onde vêm os números e quanto são confiáveis; que frase cortar se passar do tempo.
4. Fontes como links.
5. **Grave o `roteiro.md`** (na pasta que a pessoa indicar, ou ao lado do vídeo) no formato abaixo — é o
   gabarito que a edição usa para escolher a tomada certa e corrigir a legenda:

````markdown
---
titulo: S1 decision models
nomes: Jev, TypeSafe, System1-Arena
template: explainer
---
Existe um novo tipo de IA, e ela não foi feita pra conversar com você. São os S1 decision models. ...

```cenas
[{"at": 0, "titulo": "Uma IA *diferente*", "visual": {"type": "logo", "logo": "..."}},
 {"at": "classificar", "titulo": "Ela *classifica*", "visual": {"type": "lista", "items": [...]}}]
```
````

- `nomes`: todo produto, empresa e termo técnico falado (ajuda o Whisper e dispara as logos).
- `template`: só se a pessoa pediu um; senão omita (fica o `explainer`).
- Bloco `cenas` (opcional, recomendado): uma cena a cada 5–15 s, `at` = uma palavra **do roteiro** que abre
  o ponto, `titulo` de 1–4 palavras com UMA `*palavra*`, e o visual mais simples possível (formatos em
  `templates/VISUAIS.md` do repositório craft-reels). Com isso a etapa 6 da pipeline sai pronta.

## Ao revisar

A pessoa ajusta em rodadas. Mude só o que ela pediu e mantenha o que já aprovou (principalmente o hook).
Diga em uma linha o que mudou e atualize o `roteiro.md`.
