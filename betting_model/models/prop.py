"""A simulated player prop: a full distribution, or an explicit skip."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Prop:
    player: str
    stat: str
    draws: np.ndarray | None = None
    skipped: bool = False
    reason: str = ""
    notes: list = field(default_factory=list)

    def summary(self) -> dict:
        if self.skipped:
            return {"player": self.player, "stat": self.stat, "skipped": True, "reason": self.reason}
        d = self.draws
        return {"player": self.player, "stat": self.stat, "mean": float(d.mean()),
                "median": float(np.median(d)), "p10": float(np.quantile(d, 0.1)),
                "p90": float(np.quantile(d, 0.9)), "notes": "; ".join(self.notes)}

    def prob(self, side: str, line: float) -> dict:
        """Over/under probability from the distribution; pushes reported separately."""
        d = self.draws
        win = (d > line) if side == "over" else (d < line)
        return {"win": float(win.mean()), "push": float((d == line).mean()), "hits": win}


def _missing(**inputs):
    return [k for k, v in inputs.items() if v is None or (np.isscalar(v) and not np.isfinite(v))]
