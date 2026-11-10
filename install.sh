#!/usr/bin/env bash
# craft-reels: liga as skills (reel, roteiro) em ~/.claude/skills e prepara o kit de render uma vez.
# Precisa de ffmpeg (com libvpx-vp9), Node 22+ (npx), Python 3.10+ e uv. Pode rodar de novo depois de um git pull.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
for d in "$ROOT"/skills/*/; do
  [ -f "$d/SKILL.md" ] || continue
  name=$(basename "$d")
  if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    echo "pulei $name: $DEST/$name já existe e não é um link (renomeie ou apague para instalar)"
    continue
  fi
  ln -sfn "${d%/}" "$DEST/$name"
  echo "skill /$name ligada"
done
bash "$ROOT/kit/setup.sh" --cutout
echo "aquecendo os ambientes uv (Whisper, OpenCV) — a primeira transcrição baixa o modelo large-v3 (~3 GB)"
uv run --quiet --script "$ROOT/pipeline/preparar.py" --help >/dev/null 2>&1 || true
uv run --quiet --script "$ROOT/pipeline/transcrever.py" --help >/dev/null 2>&1 || true
echo "pronto. Leia AGENTS.md; comece com: $ROOT/craft run <video.mp4>"
