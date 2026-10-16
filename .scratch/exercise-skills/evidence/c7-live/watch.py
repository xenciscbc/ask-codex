"""Copy every ask-codex run directory that appears under R:\\Temp (and D:\\tmp) to a capture directory while the
live session runs, so its events survive the skill's cleanup. Read-only towards the run directories.

    python -I watch.py <capture dir> <stop file>
"""
import os
import shutil
import sys
import time
from pathlib import Path

ROOTS = [Path(r"R:\Temp"), Path(r"D:\tmp\ui-exercise-targets")]
capture, stop = Path(sys.argv[1]), Path(sys.argv[2])
capture.mkdir(parents=True, exist_ok=True)
seen = {}


def runs():
    for root in ROOTS:
        for dirpath, dirnames, _ in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > 7:
                dirnames[:] = []
                continue
            for name in list(dirnames):
                if name.startswith("run.") and Path(dirpath).name == "ask-codex":
                    yield Path(dirpath) / name
                    dirnames.remove(name)


while not stop.exists():
    try:
        for run in runs():
            key = str(run)
            out = capture / (run.parent.parent.name + "__" + run.name)
            for path in run.rglob("*"):
                try:
                    if not path.is_file():
                        continue
                    stat = path.stat()
                    mark = (stat.st_size, stat.st_mtime_ns)
                    if seen.get(str(path)) == mark:
                        continue
                    seen[str(path)] = mark
                    target = out / path.relative_to(run)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
                except OSError:
                    pass
            if key not in seen:
                seen[key] = time.time()
                with open(capture / "runs.log", "a", encoding="utf-8") as log:
                    log.write(f"{time.strftime('%H:%M:%S')} {key}\n")
    except OSError:
        pass
    time.sleep(1)
