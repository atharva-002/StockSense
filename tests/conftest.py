"""Pytest fixtures shared across tests."""
import sys
from pathlib import Path

# Ensure both repo root and backend are importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
