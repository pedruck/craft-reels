# Armadilhas que já custaram tempo

Lições de vídeos reais (Orca, Omarchy e System 1). Cada uma virou regra ou código na pipeline; está aqui para
quem for mexer nela entender o porquê.

## Corte

- **Com contexto, o Whisper esconde defeito.** Na transcrição do vídeo inteiro, "tanto em taxa de aceito" +
  "Tanto em taxa de acertos" virou uma frase só, e um "repaz" de meio segundo virou "O". Por isso a etapa 3
  confere **cada trecho sozinho** (`conferir_trechos.py`), com trechos vizinhos nunca na mesma janela do Whisper.
- **Lascas.** Cortes de pausa (medidos no áudio) e de "refaz"/gaguejo (medidos na transcrição) são calculados
  separados; quando quase se encostam sobra um pedaço de 0,07–0,5 s. Regra A: nenhum trecho < 0,25 s, e os de
  0,25–1 s só ficam se, ouvidos sozinhos, dizem o que deviam.
- **Corte à mão sempre no tempo do bruto** (regra C, `craft corte`). Converter do cortado e cair exatamente na
  emenda deixou um "podem" solto no vídeo.
- **O Whisper estica palavras por cima das pausas** e engole o "ééé" dentro da palavra vizinha. Silêncio e "ééé"
  se acham pelo **áudio** (nível em dB + espectro parado), não pela transcrição.
- **Limiar de silêncio ancorado na voz.** Com trecho mudo digital (-78 dB) o limiar caía e o ruído da sala
  deixava de contar como pausa.
- **"refaz" vira "Repaz", "rapaz", "refas"**, e reticências ("maneira... refaz") são frase abandonada.
- **Palavra fantasma:** com `condition_on_previous_text=False`, o Whisper repete a última palavra de um trecho
  no começo do outro com duração zero ("tela tela"). `nomes.py` e o planejador descartam.
- **"Sim," inventado** numa emenda. Palavra estranha só na emenda: transcreva aquele trecho sozinho antes de
  mexer no corte.
- **Roteiro como gabarito só com fala próxima do roteiro.** Se a pessoa improvisou muito, nenhuma frase passa do
  limiar (0,75) e a escolha de tomada não corta nada — de propósito: abaixo disso cortaria fala boa.

## Transcrição

- **PyAV quebra o faster-whisper** (`metadata_errors`): os scripts decodificam o áudio com ffmpeg.
- **Nome de produto sai errado** sem `--nomes` ("Walmart", "Omarte", "agente de ar", "D8H", "Cloud Code").
  Erros que voltam vão em `catalogo/correcoes.json`; erros de uma voz, no perfil do apresentador.

## Render e máquina

- **`/tmp` pode ser RAM** (tmpfs). O render de 2 min precisa de ~17 GB de quadros temporários: tudo vai para a
  pasta de trabalho, no disco (`kit/reel.py` passa `TMPDIR`).
- **Muitos workers derrubam o Chrome** do HyperFrames (`Page.captureScreenshot: Target closed`): 3 workers.
- **OpenCV 5 tirou os detectores Haar** do pacote principal: a etapa 1 fixa `opencv-python-headless<5`.

## Layout

- **Legenda branca solta some na camiseta branca:** pílula escura.
- **Legenda sempre embaixo e nunca sobre o rosto** (pedido da comunidade): faixa y 1330–1456, logo abaixo do
  queixo. Rosto grande (selfie de perto): o explainer encolhe a pessoa até 0,62x; os templates de vídeo inteiro
  sobem o vídeo com zoom leve; o split, se nem assim couber, põe a legenda na emenda e avisa.
- **O Instagram cobre ~220 px em cima e ~420 px embaixo:** selo e logos ficam logo abaixo de 220; nada
  importante abaixo de 1500.
- **"17× mais barato" quebrou em duas linhas** e invadiu a cabeça: o validador mede todo texto com as fontes de
  verdade antes do render, e confere a altura que cada visual precisa (hub, comparação, grade).

## Tokens

- O que custa é ler saída longa e repetir passos à mão. Por isso: cada etapa imprime uma linha, o detalhe vai
  para `log/`, a transcrição é lida uma vez pelo `frases.txt`, e o agente olha uma imagem por vídeo
  (`reel.cenas.jpg`).
