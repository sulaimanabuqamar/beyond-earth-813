"""
Cycle-aware irrigation priority for centre-pivot fields.

The whole point of this module is one sentence: ranking fields by NDVI decline
measures harvest, not stress.

Alfalfa in Wadi as-Sirhan is cut on a roughly 30-day cycle. Every cut drops a
field's NDVI from ~0.90 to ~0.35 within ten days. A decline ranking therefore
puts freshly mown fields at the top of the irrigation queue and sends the
scarcest input in the Gulf to crop that was simply harvested.

This module models each field's own cutting rhythm from its own history, then
asks a different question: is this field lower than *it* should be at *this*
point in *its* cycle, and has it failed to come back when it was due?

No part of this needs hyperspectral data. It runs on free Sentinel-2.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Iterable, Sequence

import numpy as np

# Thresholds. LOW/HIGH are the canopy states either side of a cut; they are the
# same values used in the validation notebook so the dashboard and the analysis
# cannot drift apart.
LOW = 0.45
HIGH = 0.70

# A peak has to clear this much above the surrounding trough to count as a
# regrowth cycle rather than sensor noise.
MIN_PROMINENCE = 0.20

# Cycle length bounds, in days. Alfalfa in this region runs 25-35 days; we allow
# a wider band so an unusual field is described rather than discarded.
MIN_CYCLE_DAYS = 18
MAX_CYCLE_DAYS = 60
DEFAULT_CYCLE_DAYS = 30

# A field is "overdue" once it has been down for this multiple of its own cycle.
OVERDUE_FACTOR = 1.30

# ...and "dormant" once it has been down for this many of its own cycles with no
# regrowth at all. Three consecutive missed cycles is not a late field; it is a
# field that is not in production. In Wadi as-Sirhan the fields are commonly
# fallowed through the hottest months, and calling that "inspect this field"
# would be the same error this tool exists to correct — mistaking a normal
# agronomic state for distress. A dormant field carries zero priority and is
# reported as out of rotation, not as a problem.
DORMANT_FACTOR = 3.0


@dataclass(frozen=True)
class FieldAssessment:
    """What the tool says about one field on one date."""

    field_id: int
    area_ha: float
    as_of: str

    ndvi: float | None
    expected_ndvi: float | None
    deficit: float | None

    cycle_days: float | None
    days_since_peak: int | None
    cycles_observed: int

    status: str          # healthy | recently_cut | overdue | dormant | off_cycle | no_data
    priority: float      # hectare-weighted deficit; 0 when nothing is wrong
    rank: int | None     # position in the ranked queue, 1 = inspect first
    reason: str          # one sentence a farm manager can act on

    def to_dict(self) -> dict:
        return asdict(self)


def _to_days(dates: Sequence[date]) -> np.ndarray:
    d0 = dates[0]
    return np.array([(d - d0).days for d in dates], dtype=float)


def find_peaks(values: np.ndarray, days: np.ndarray,
               min_prominence: float = MIN_PROMINENCE) -> list[int]:
    """Indices of regrowth peaks.

    A local maximum counts only if it stands `min_prominence` above the lowest
    point between it and the neighbouring maxima. That is what separates a real
    cut-and-regrow cycle from a cloudy pixel or a windy day.
    """
    n = len(values)
    if n < 3:
        return []

    ok = np.isfinite(values)
    idx = np.where(ok)[0]
    if len(idx) < 3:
        return []

    v = values[idx]
    cand = [i for i in range(1, len(v) - 1) if v[i] >= v[i - 1] and v[i] >= v[i + 1]]

    peaks: list[int] = []
    for i in cand:
        left = v[:i]
        right = v[i + 1:]
        if len(left) == 0 or len(right) == 0:
            continue
        prom = min(v[i] - left.min(), v[i] - right.min())
        if prom >= min_prominence:
            peaks.append(int(idx[i]))

    # Collapse peaks that sit on the same plateau: keep the highest of any group
    # closer together than the shortest plausible cycle.
    merged: list[int] = []
    for p in peaks:
        if merged and days[p] - days[merged[-1]] < MIN_CYCLE_DAYS:
            if values[p] > values[merged[-1]]:
                merged[-1] = p
        else:
            merged.append(p)
    return merged


def estimate_cycle(peaks: Sequence[int], days: np.ndarray) -> tuple[float | None, int]:
    """Median spacing between consecutive peaks, in days, and how many gaps it saw."""
    if len(peaks) < 2:
        return None, 0
    gaps = np.diff(days[list(peaks)])
    gaps = gaps[(gaps >= MIN_CYCLE_DAYS) & (gaps <= MAX_CYCLE_DAYS)]
    if len(gaps) == 0:
        return None, 0
    return float(np.median(gaps)), int(len(gaps))


def expected_at_phase(values: np.ndarray, days: np.ndarray,
                      peaks: Sequence[int], cycle: float, phase: float) -> float | None:
    """What this field usually reads this many days after a cut.

    Built only from the field's own earlier cycles, so a genuinely low-vigour
    field is not punished for being low — it is judged against itself.
    """
    if cycle is None or len(peaks) < 2:
        return None

    samples: list[float] = []
    for p in peaks[:-1]:
        t0 = days[p]
        window = (days >= t0 + phase - 3) & (days <= t0 + phase + 3)
        vals = values[window]
        vals = vals[np.isfinite(vals)]
        if len(vals):
            samples.append(float(np.median(vals)))

    if not samples:
        return None
    return float(np.median(samples))


def assess_field(field_id: int, area_ha: float, dates: Sequence[date],
                 ndvi: Sequence[float | None], as_of: date | None = None) -> FieldAssessment:
    """Assess one field from its own NDVI history."""
    values = np.array([np.nan if v is None else float(v) for v in ndvi], dtype=float)
    days = _to_days(dates)

    if as_of is None:
        as_of = dates[-1]
    cutoff = (as_of - dates[0]).days
    keep = days <= cutoff
    values, days, kept_dates = values[keep], days[keep], [d for d, k in zip(dates, keep) if k]

    finite = np.where(np.isfinite(values))[0]
    if len(finite) == 0:
        return FieldAssessment(field_id, area_ha, as_of.isoformat(), None, None, None,
                               None, None, 0, "no_data", 0.0, None,
                               "No cloud-free observation in the window.")

    last = int(finite[-1])
    now = float(values[last])

    peaks = find_peaks(values, days)
    cycle, n_cycles = estimate_cycle(peaks, days)
    cycle_used = cycle if cycle is not None else DEFAULT_CYCLE_DAYS

    if peaks:
        days_since_peak = int(days[last] - days[peaks[-1]])
    else:
        days_since_peak = None

    expected = None
    if days_since_peak is not None:
        expected = expected_at_phase(values, days, peaks, cycle_used, float(days_since_peak))
    deficit = None if expected is None else round(expected - now, 4)

    # ---- classification -------------------------------------------------
    if now >= HIGH:
        status = "healthy"
        reason = "Full canopy (NDVI %.2f). Nothing to do." % now
    elif days_since_peak is None:
        status = "off_cycle" if now < LOW else "healthy"
        reason = ("Below %.2f but no complete cycle observed yet, so this is a "
                  "watch item rather than a call." % LOW)
    elif now < LOW and days_since_peak > DORMANT_FACTOR * cycle_used:
        status = "dormant"
        reason = ("Down for %d days — more than three of its own %d-day cycles — with no "
                  "regrowth. This field is out of rotation, not late." % (days_since_peak, round(cycle_used)))
    elif now < LOW and days_since_peak > OVERDUE_FACTOR * cycle_used:
        status = "overdue"
        reason = ("Cut %d days ago on a %d-day cycle and still at NDVI %.2f. "
                  "It should have regrown by now — inspect." % (days_since_peak, round(cycle_used), now))
    elif now < LOW:
        status = "recently_cut"
        reason = ("Cut %d days ago on a %d-day cycle. The drop is on schedule — "
                  "this is harvest, not stress." % (days_since_peak, round(cycle_used)))
    elif deficit is not None and deficit > 0.15:
        status = "off_cycle"
        reason = ("NDVI %.2f against %.2f typical for day %d of its own cycle — "
                  "%.2f below where this field normally sits."
                  % (now, expected, days_since_peak, deficit))
    else:
        status = "healthy"
        reason = "Tracking its own cycle within tolerance."

    # ---- priority -------------------------------------------------------
    # Hectares of crop underperforming its own history. Zero unless the field is
    # actually behind, so a freshly cut field never enters the queue.
    #
    # An overdue field must always rank, even when its own history is too short to
    # give an expected value: falling back to the distance below LOW keeps the most
    # urgent status from disappearing out of the queue on a technicality.
    if status == "overdue":
        gap = deficit if (deficit is not None and deficit > 0) else max(0.0, LOW - now)
        priority = round(float(gap) * float(area_ha), 2)
    elif status == "off_cycle" and deficit and deficit > 0:
        priority = round(float(deficit) * float(area_ha), 2)
    else:
        priority = 0.0

    return FieldAssessment(field_id, float(area_ha), as_of.isoformat(),
                           round(now, 4), None if expected is None else round(expected, 4),
                           deficit, None if cycle is None else round(cycle_used, 1),
                           days_since_peak, n_cycles, status, priority, None, reason)


def rank(assessments: Iterable[FieldAssessment]) -> list[FieldAssessment]:
    """Sort into an inspection queue and stamp the rank."""
    items = list(assessments)
    items.sort(key=lambda a: (-a.priority, -(a.area_ha or 0)))
    out = []
    for i, a in enumerate(items):
        out.append(FieldAssessment(**{**a.to_dict(),
                                      "rank": (i + 1) if a.priority > 0 else None}))
    return out


def naive_decline_rank(field_ids: Sequence[int], dates: Sequence[date],
                       series: dict[int, Sequence[float | None]],
                       as_of: date, window_days: int = 30) -> list[int]:
    """The ranking this tool exists to replace.

    Straight NDVI change over a fixed window, steepest fall first. Included so
    the dashboard can show, on the same day and the same fields, how many of the
    fields it promotes were simply mown.
    """
    d0 = dates[0]
    day = np.array([(d - d0).days for d in dates], dtype=float)
    cutoff = (as_of - d0).days
    start = cutoff - window_days

    scored: list[tuple[float, int]] = []
    for fid in field_ids:
        v = np.array([np.nan if x is None else float(x) for x in series[fid]], dtype=float)
        a = v[(day >= start - 5) & (day <= start + 5)]
        b = v[(day >= cutoff - 5) & (day <= cutoff)]
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) == 0 or len(b) == 0:
            continue
        scored.append((float(np.median(b) - np.median(a)), int(fid)))

    scored.sort()
    return [fid for _, fid in scored]
