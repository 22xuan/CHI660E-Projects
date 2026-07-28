#!/usr/bin/env python3
"""RDE 动力学参数测定 — 公共函数模块"""

import yaml
import numpy as np
from pathlib import Path
from typing import Dict, Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def load_params() -> Dict[str, Any]:
    with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def angular_velocity(rpm: float) -> float:
    return rpm * 2 * np.pi / 60
