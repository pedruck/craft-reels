# Exemplos

- `s1/roteiro.md` — roteiro completo no formato da skill `roteiro` (150 palavras, ~50 s), com o bloco
  ```` ```cenas ```` que a etapa 6 transforma no `cenas.json` sozinha.
- `orca/cenas.json` — cenas escritas por um agente na etapa 6 para um vídeo real (template `explainer`), e
  `orca/frases.txt`, o texto de onde elas saíram. Mostra lista, fluxo (linha e hub), logo e foto.
- `orca/testes-cenas/*.json` — um `cenas.json` curto para cada um dos outros 6 templates, usados para testar
  cada template com 14 s de vídeo (`kit/.venv/bin/python pipeline/montar.py <pasta> --template X --cenas Y --fim 14`).
- `orca/reel.cenas.jpg` — a folha de conferência (um quadro por cena) que o agente olha no fim.

Os vídeos brutos e a imagem `img/diffs.jpg` usada pela cena 7 não estão no repositório (são pessoais ou de terceiros, e pesados).
