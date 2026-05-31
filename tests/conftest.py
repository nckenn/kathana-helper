import os
import sys


# Ensure repo root is on sys.path so tests can import top-level modules like `config.py`.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

