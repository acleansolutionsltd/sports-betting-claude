"""Load config.yaml and resolve package paths."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
AUDIT_REPORTS = DATA / "audit_reports"
OUTPUTS = ROOT / "outputs"
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def config_hash(path: Path = CONFIG_PATH) -> str:
    """Short hash logged with every run so results can be tied to exact settings."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
