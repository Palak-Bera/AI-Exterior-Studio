#!/usr/bin/env python3
"""Download Grounded SAM weights into storage/models (run once, not at server startup).

Saves locally (outside application code):
  storage/models/IDEA-Research--grounding-dino-tiny/
  storage/models/facebook--sam-vit-base/

Usage:
  cd backend
  python scripts/download_models.py

Requires: pip install -r requirements.txt (huggingface_hub is enough to download).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging_config import setup_logging
from app.services.model_download import download_all_models

setup_logging()


def main() -> int:
    manifest = download_all_models()
    models = manifest.get("models", {})
    failed = [k for k, v in models.items() if not str(v.get("status", "")).startswith("ok")]
    print("\n=== Download summary ===")
    for key, info in models.items():
        mark = "OK" if info.get("status") == "ok" else "FAIL"
        print(f"  [{mark}] {key}: {info.get('path')}"
              + (" (skipped — already present)" if info.get("skipped") else ""))
    if failed:
        print(f"\nFailed: {failed}", file=sys.stderr)
        return 1
    print(f"\nAll models saved under storage/models/ ({manifest.get('duration_sec')}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
