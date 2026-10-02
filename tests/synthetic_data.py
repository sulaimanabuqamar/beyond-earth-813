"""Synthetic Tabarjal-shaped data. NOT a deliverable - it exists only to
exercise the JSON -> priority-model -> dashboard path before real data lands."""
import json, math, random
random.seed(813)

N_FIELDS = 60
# 85 acquisition days across a season, irregular like real Sentinel-2 revisit
from datetime import date, timedelta
D0 = date(2026, 2, 1)
days, d = [], 0
while d < 218 and len(days) < 85:
    days.append(d); d += random.choice([2, 3, 3, 5, 2, 5, 3])
DATES = [(D0 + timedelta(days=x)).isoformat() for x in days]

def sawtooth(cycle, amp_hi, amp_lo, phase, noise, stall_after=None):
    out = []
    for t in days:
        u = ((t - phase) % cycle) / cycle
        val = amp_lo + (amp_hi - amp_lo) * min(1.0, u / 0.75)
        if u > 0.92:
            val = amp_lo + (amp_hi - amp_lo) * 0.15
        if stall_after is not None and t > stall_after:
            val = min(val, amp_lo + 0.04)          # cut, never came back
        val += random.gauss(0, noise)
        out.append(None if random.random() < 0.10 else max(0.05, min(0.95, val)))
    return out

fields, ndvi = [], {}
for i in range(1, N_FIELDS + 1):
    ha = round(random.uniform(12, 90), 1)
    lon0, lat0 = 38.2 + (i % 10) * 0.06, 29.8 + (i // 10) * 0.05
    r = math.sqrt(ha * 1e4 / math.pi) / 111320.0
    poly = [[round(lon0 + r * math.cos(a) / math.cos(math.radians(lat0)), 5),
             round(lat0 + r * math.sin(a), 5)]
            for a in [k * 2 * math.pi / 24 for k in range(25)]]
    fields.append({"id": i, "ha": ha, "c": [round(lon0, 5), round(lat0, 5)], "p": poly})
    stall = random.choice([None] * 8 + [120, 140])       # ~20% go overdue late in the season
    ndvi[str(i)] = [None if v is None else int(round(v * 1000))
                    for v in sawtooth(random.choice([26, 30, 34]), random.uniform(0.80, 0.92),
                                      random.uniform(0.25, 0.38), random.randint(0, 25),
                                      0.025, stall)]

payload = {"meta": {"aoi": [38.15, 29.75, 38.85, 30.30], "crs": "EPSG:32637",
                    "res_field_m": 20, "res_series_m": 60,
                    "season": [DATES[0], DATES[-1]], "n_fields": len(fields),
                    "n_days": len(DATES), "n_obs": sum(1 for k in ndvi for v in ndvi[k] if v is not None),
                    "ha_total": round(sum(f["ha"] for f in fields), 1), "ha_median": 40.0,
                    "low": 0.45, "high": 0.70, "emit_scenes": [], "emit_granules": [],
                    "SYNTHETIC": True},
           "dates": DATES, "fields": fields, "ndvi": ndvi, "emit": []}
import os
json.dump(payload, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic.json"), "w"), separators=(",", ":"))
print("synthetic.json: %d fields, %d dates" % (len(fields), len(DATES)))
