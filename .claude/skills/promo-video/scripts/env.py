import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROMO = ROOT / "promo"


def api_key(name):
    key = os.environ.get(name)
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit(f"{name} missing from the environment and from {env}")
