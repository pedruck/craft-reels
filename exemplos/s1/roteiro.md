---
titulo: S1 decision models
nomes: Jev, TypeSafe, S1, LLM
---
Existe um novo tipo de IA, e ela não foi feita pra conversar com você. São os S1 decision models. Em vez de escrever um texto, eles recebem a situação e uma lista fechada de opções, e devolvem só uma delas, com a probabilidade de ser a certa. Então imagina um suporte que recebe milhares de mensagens por dia: você pede pra ele classificar cada uma entre financeiro, técnico ou cancelamento, e ele responde só "técnico, 92%". É aí que eles voam: o Jev, o modelo que lançou essa categoria, responde em menos de dois décimos de segundo, e num teste independente classificou 200 mensagens por menos de um centavo, umas 17 vezes mais barato que um LLM pequeno. Mas tem limite: se a resposta certa não tá na lista, ele erra com toda a convicção. Resumindo: decisão frequente com opções fechadas, vai de S1; problema aberto, vai de LLM.

```cenas
[
 {"at": 0, "titulo": "Uma IA *diferente*", "visual": {"type": "lista", "items": [{"icone": "💬", "texto": "Não *conversa*", "at": "conversar"}]}},
 {"at": "São", "titulo": "*S1* decision models", "visual": {"type": "fluxo", "forma": "linha", "nos": [
   {"icone": "📋", "texto": "Opções", "at": "lista"}, {"icone": "🧠", "texto": "Modelo", "at": "devolvem"}, {"icone": "✅", "texto": "Uma *só*", "at": "probabilidade"}]}},
 {"at": "suporte", "titulo": "Ele *classifica*", "visual": {"type": "grade", "items": [
   {"icone": "💰", "texto": "Financeiro", "at": "financeiro"}, {"icone": "🔧", "texto": "Técnico", "at": "técnico"}, {"icone": "❌", "texto": "Cancela", "at": "cancelamento"}]}},
 {"at": "voam", "titulo": "Onde ele *voa*", "visual": {"type": "contador", "valor": "17", "depois": "×", "texto": "mais *barato*", "legenda": "200 mensagens por menos de 1 centavo", "at": "17"}},
 {"at": "limite", "titulo": "Tem *limite*", "visual": {"type": "lista", "items": [{"icone": "📋", "texto": "Fora da *lista*", "at": "lista#2"}, {"icone": "❌", "texto": "Erra *convicto*", "at": "convicção"}]}},
 {"at": "Resumindo", "titulo": "*Resumindo*", "visual": {"type": "compare", "seta": false,
   "left": {"label": "Opções fechadas", "big": "S1", "small": "decisão frequente", "at": "fechadas"},
   "right": {"label": "Problema aberto", "big": "LLM", "small": "precisa raciocinar", "at": "aberto"}}}
]
```
