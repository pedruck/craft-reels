"""Teste a seco dos templates: monta a composição HTML de verdade, sem recorte nem render.

    kit/.venv/bin/python testes/seco.py <pasta> <template> <cenas.json>
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "templates"))
import motor  # noqa: E402
import reel  # noqa: E402

P, t, cen = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
reel.Comp.render = lambda self, out: shutil.copy(self.job.clip, out)
reel.Job.cutout = lambda self, model=None: self.clip
reel.sheet = lambda *a, **k: None
motor.folha_cenas = lambda *a, **k: None
enq = json.loads((P / "enquadramento.json").read_text())
spec = json.loads((P / cen).read_text())
spec.update({"video": "limpo.mp4", "transcript": "legenda.json", "out": f"seco-{t}.mp4", "end": 14, "template": t,
             "paleta": enq["paleta"], "fundo": enq["fundo"], "enquadramento": enq})
sp = P / f"seco-{t}.spec.json"
sp.write_text(json.dumps(spec, ensure_ascii=False))
m = importlib.util.spec_from_file_location("t", RAIZ / "templates" / t / "build.py")
mod = importlib.util.module_from_spec(m)
m.loader.exec_module(mod)
mod.main(str(sp))
html = (P / ".work" / f"seco-{t}" / "comp_main" / "index.html").read_text()
print(f"{t}: ok, {len(html) // 1024} KB de HTML")
