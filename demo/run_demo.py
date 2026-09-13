"""Run from any working directory; no credentials or network needed."""
import subprocess
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "src.main"], cwd=root, check=True)
print("Results:", root / "runs" / "demo")
