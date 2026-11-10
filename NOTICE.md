# Avisos de terceiros

O código deste repositório é MIT (veja `LICENSE`). Ele parte de outro projeto e usa ferramentas, modelos,
fontes, paletas e marcas de terceiros, listados aqui com a licença de cada um.

## Base do projeto

- **[claude-editing-skills](https://github.com/artemnovitckii/claude-editing-skills)**, de Artem Novitckii
  (MIT). O motor de render (`kit/reel.py`, `kit/cutout.py`, `kit/setup.sh`), a forma de ancorar visuais na
  palavra falada e os seis formatos que viraram os templates `explainer`, `split`, `bastidores`, `ranking`,
  `historia` e `destaque` vêm de lá. O histórico original está preservado neste repositório (commit
  `beff6b8`). As instruções originais de cada formato estão em `templates/<nome>/referencia-artem.md`.

## Executados ou baixados na instalação (não incluídos aqui)

| Projeto | Uso | Licença |
|---|---|---|
| [HyperFrames](https://github.com/heygen-com/hyperframes), HeyGen | render HTML → MP4 | Apache-2.0 |
| [GSAP](https://gsap.com) | animações (baixado no setup) | licença GreenSock (uso gratuito) |
| [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting), Shanchuan Lin et al. | recorte da pessoa (modelo baixado no setup) | GPL-3.0 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper), SYSTRAN | transcrição local | MIT |
| [Whisper large-v3](https://github.com/openai/whisper), OpenAI | modelo de transcrição | MIT |
| [OpenCV](https://opencv.org) | detecção de rosto (etapa 1) | Apache-2.0 |
| [NumPy](https://numpy.org), [Pillow](https://python-pillow.org), [ONNX Runtime](https://onnxruntime.ai) | apoio | BSD / MIT-CMU / MIT |
| [FFmpeg](https://ffmpeg.org) | corte, áudio, codificação | LGPL/GPL |
| [uv](https://github.com/astral-sh/uv), Astral | ambientes dos scripts | MIT / Apache-2.0 |
| [Potrace](https://potrace.sourceforge.net), Peter Selinger | vetorização da logo da comunidade (feita uma vez) | GPL-2.0 |

## Incluídos aqui

- **Fontes** em `kit/fonts`: Inter, Archivo Black, DM Serif Display, Instrument Serif, Pixelify Sans, TikTok
  Sans (vindas do kit original) e [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) — todas SIL
  Open Font License 1.1 (arquivos `OFL-*.txt`).
- **Paletas** em `tema/paletas.json`: [Catppuccin](https://github.com/catppuccin/catppuccin) (Latte, Mocha;
  MIT) e [Nord](https://www.nordtheme.com) (MIT), com os valores oficiais.
- **Logos de produto** em `catalogo/logos`: ícones do [Simple Icons](https://simpleicons.org) (CC0) e logos
  oficiais de projetos open source (Orca: [stablyai/orca](https://github.com/stablyai/orca), MIT; Omarchy:
  [omarchy.org](https://omarchy.org)). Cada entrada de `logos.json` tem o campo `fonte`. **As marcas são de
  quem é dono delas**; aparecem só para identificar o produto citado no vídeo.
- **Logo da Software Craftsmanship Brasília** em `tema/`: da comunidade
  ([@software_craftsmanship](https://www.instagram.com/software_craftsmanship/)), vetorizada a partir da
  imagem original. Não é coberta pela licença MIT.
- **Prévias** em `docs/previas`: quadros de vídeos de teste gravados por Pedro ([@pedruck](https://github.com/pedruck)), e capturas do
  repositório [stablyai/orca](https://github.com/stablyai/orca) (MIT), com crédito na própria imagem.

## Ideias de outros projetos open source

Nenhum código foi copiado destes; as ideias foram reescritas na pipeline:

- [video-use](https://github.com/browser-use/video-use) (MIT): fade curto em toda emenda; transcrição como
  interface do agente.
- [video-editing-skill](https://github.com/social-media-skills/video-editing-skill) (MIT): cadeia de áudio e
  -14 LUFS; relatório por vídeo.
- [ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT): checagens automáticas e página de
  aprovação de cortes.
- [open-edits](https://github.com/kevinbadi/open-edits) (MIT): número falado vira contador; o visual entra na
  palavra, nunca antes.
