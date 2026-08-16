"""Minimal Pmf / Suite helpers for Think Bayes–style notebooks (Python 3).

Problem ideas follow Allen B. Downey, Think Bayes (中译《贝叶斯思维》).
This is an original, abbreviated API — not a copy of the original thinkbayes.py.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Optional, Sequence, Tuple


def Odds(p: float) -> float:
    """Convert probability p to odds p / (1 - p)."""
    if p == 1:
        return float("inf")
    return p / (1 - p)


def Probability(o: float) -> float:
    """Convert odds o to probability o / (o + 1)."""
    return o / (o + 1)


class Cdf:
    """Discrete cumulative distribution built from a Pmf."""

    def __init__(self, xs: Sequence[Any], ps: Sequence[float]):
        self.xs = list(xs)
        self.ps = list(ps)

    def Prob(self, x: Any) -> float:
        """P(X <= x) for comparable xs."""
        if not self.xs:
            return 0.0
        if x < self.xs[0]:
            return 0.0
        lo, hi = 0, len(self.xs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.xs[mid] <= x:
                lo = mid
            else:
                hi = mid - 1
        return self.ps[lo]

    def Value(self, p: float) -> Any:
        """Smallest x with CDF(x) >= p."""
        if not self.xs:
            raise ValueError("empty Cdf")
        if p <= 0:
            return self.xs[0]
        if p >= 1:
            return self.xs[-1]
        lo, hi = 0, len(self.xs) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.ps[mid] >= p:
                hi = mid
            else:
                lo = mid + 1
        return self.xs[lo]

    def Percentile(self, percentage: float) -> Any:
        return self.Value(percentage / 100.0)

    def CredibleInterval(self, percentage: float = 90) -> Tuple[Any, Any]:
        tail = (100 - percentage) / 2
        return self.Percentile(tail), self.Percentile(100 - tail)


class Pmf(MutableMapping):
    """Probability mass function: map from hypothesis -> probability (or unnormalized mass)."""

    def __init__(self, values: Optional[Iterable[Any] | Mapping[Any, float]] = None):
        self.d: dict[Any, float] = {}
        if values is None:
            return
        if isinstance(values, Mapping):
            for k, v in values.items():
                self.d[k] = float(v)
        else:
            for v in values:
                self.Incr(v)

    # --- MutableMapping ---
    def __getitem__(self, key: Any) -> float:
        return self.d[key]

    def __setitem__(self, key: Any, value: float) -> None:
        self.d[key] = float(value)

    def __delitem__(self, key: Any) -> None:
        del self.d[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.d)

    def __len__(self) -> int:
        return len(self.d)

    def __repr__(self) -> str:
        return f"Pmf({self.d!r})"

    # --- Think Bayes–style API ---
    def Set(self, hypo: Any, prob: float = 1.0) -> None:
        self.d[hypo] = float(prob)

    def Incr(self, hypo: Any, amount: float = 1.0) -> None:
        self.d[hypo] = self.d.get(hypo, 0.0) + amount

    def Mult(self, hypo: Any, factor: float) -> None:
        self.d[hypo] = self.d.get(hypo, 0.0) * factor

    def Prob(self, hypo: Any, default: float = 0.0) -> float:
        return self.d.get(hypo, default)

    def Items(self) -> list[Tuple[Any, float]]:
        return list(self.d.items())

    def Values(self) -> list[Any]:
        return list(self.d.keys())

    def Total(self) -> float:
        return sum(self.d.values())

    def Normalize(self, fraction: float = 1.0) -> float:
        total = self.Total()
        if total == 0:
            raise ValueError("Normalize: total probability is zero")
        factor = fraction / total
        for hypo in self.d:
            self.d[hypo] *= factor
        return total

    def Mean(self) -> float:
        return sum(hypo * p for hypo, p in self.d.items())

    def MaximumLikelihood(self) -> Any:
        return max(self.d, key=self.d.get)

    def MakeCdf(self, name: str = "") -> Cdf:  # noqa: ARG002 — name kept for familiarity
        xs = sorted(self.d)
        total = 0.0
        ps = []
        for x in xs:
            total += self.d[x]
            ps.append(total)
        if total and abs(total - 1.0) > 1e-9:
            ps = [p / total for p in ps]
        return Cdf(xs, ps)

    def CredibleInterval(self, percentage: float = 90) -> Tuple[Any, Any]:
        return self.MakeCdf().CredibleInterval(percentage)

    def Copy(self, name: str = "") -> "Pmf":  # noqa: ARG002
        return Pmf(self.d)

    def Max(self, n: int) -> "Pmf":
        """Distribution of the maximum of n i.i.d. draws from this Pmf."""
        cdf = self.MakeCdf()
        xs = cdf.xs
        # P(max <= x) = F(x)^n → pmf via differencing
        pmf = Pmf()
        prev = 0.0
        for x, p in zip(xs, cdf.ps):
            p_max = p**n
            pmf.Set(x, p_max - prev)
            prev = p_max
        pmf.Normalize()
        return pmf


class Suite(Pmf):
    """Bayesian suite: prior over hypotheses with Update via Likelihood."""

    def Likelihood(self, data: Any, hypo: Any) -> float:
        raise NotImplementedError

    def Update(self, data: Any) -> float:
        for hypo in list(self.d):
            self.Mult(hypo, self.Likelihood(data, hypo))
        return self.Normalize()

    def UpdateSet(self, dataset: Iterable[Any]) -> None:
        for data in dataset:
            self.Update(data)

    def LogUpdate(self, data: Any) -> None:
        """Multiply by likelihood in log-space friendly form (still uses Mult)."""
        self.Update(data)


def MakeMixture(components: Pmf | Iterable[Tuple[Pmf, float]]) -> Pmf:
    """Mixture of discrete Pmfs.

    `components` is either an iterable of (pmf, weight) pairs, or a Pmf whose
    values are weights and whose keys are hashable labels (prefer pairs —
    Pmf objects themselves are not hashable).
    """
    mix = Pmf()
    if isinstance(components, Pmf):
        pairs: Iterable[Tuple[Any, float]] = components.Items()
    else:
        pairs = components
    for pmf, weight in pairs:
        for hypo, p in pmf.Items():
            mix.Incr(hypo, weight * p)
    mix.Normalize()
    return mix


def PmfAdd(pmf1: Pmf, pmf2: Pmf) -> Pmf:
    """Distribution of the sum of independent draws from pmf1 and pmf2."""
    out = Pmf()
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            out.Incr(v1 + v2, p1 * p2)
    out.Normalize()
    return out


def MakeDice(sides: int) -> Pmf:
    pmf = Pmf()
    for face in range(1, sides + 1):
        pmf.Set(face, 1.0 / sides)
    return pmf


def HistFromList(data: Iterable[Any]) -> Counter:
    return Counter(data)
