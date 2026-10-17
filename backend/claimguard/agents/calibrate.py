"""Confidence calibration from reviewer outcomes. < calibration_min_labels: Beta prior by claim type
(confidence x reliability / 0.5, clipped). >= min labels: isotonic regression of (predicted, accepted)."""
from __future__ import annotations

from ..config import settings
from ..learning.stats import counts, reliability


class Calibrator:
    def __init__(self, db_url: str | None = None):
        c = counts(db_url)
        self.types = {t: reliability(a, d) for t, (a, d) in c["type"].items()}
        self.n = len(c["pairs"])
        self.iso = None
        if self.n >= settings()["thresholds"]["calibration_min_labels"]:
            from sklearn.isotonic import IsotonicRegression
            xs, ys = zip(*c["pairs"])
            self.iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(xs, ys)

    def __call__(self, conf: float | None, claim_type: str) -> float | None:
        if conf is None:
            return None
        if self.iso is not None:
            return round(float(self.iso.predict([conf])[0]), 3)
        r = self.types.get(claim_type, 0.5)
        return round(max(0.0, min(1.0, conf * r / 0.5)), 3)


def bins(pairs: list[tuple[float, int]], n: int = 5) -> list[dict]:
    """Reliability diagram: mean predicted vs observed accept rate per confidence bin."""
    out = []
    for i in range(n):
        lo, hi = i / n, (i + 1) / n
        sel = [(p, y) for p, y in pairs if lo <= p < hi or (i == n - 1 and p == 1.0)]
        if sel:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "predicted": round(sum(p for p, _ in sel) / len(sel), 3),
                        "observed": round(sum(y for _, y in sel) / len(sel), 3), "n": len(sel)})
    return out
