"""Fake the network so the notebook's control flow can be executed offline.

Synthetic imagery only: circular pivots on a desert background, cut on a
~30-day cycle. This proves the notebook RUNS and writes its outputs. It proves
nothing whatever about Tabarjal.

One deliberate difference, worth knowing before you read the dry run's output:
these pivots cover well under 1% of the synthetic box, where the real fields
cover roughly 6% of the AOI. The notebook picks its detection day by the 95th
percentile of NDVI across the whole scene, which on the real data lands inside
the crop population (measured p95 0.806 on the chosen day) and here lands on
bare ground. So the day this dry run selects is meaningless, and the field
count is not comparable to the real one. Everything downstream of that choice
is still exercised, which is the point of the file.
"""
import sys, types, math, datetime as dt
import numpy as np, xarray as xr

AOI = [38.15, 29.75, 38.85, 30.30]
D0  = dt.date(2026, 2, 1)
DAYS = list(range(0, 218, 3))[:72]
DATES = [(D0 + dt.timedelta(days=d)).isoformat() for d in DAYS]

rng = np.random.default_rng(813)
N_PIVOT = 40
_c = [(rng.uniform(AOI[0]+.03, AOI[2]-.03), rng.uniform(AOI[1]+.03, AOI[3]-.03),
       rng.uniform(400, 700), rng.integers(26,35), rng.integers(0,30),
       rng.random() < 0.18) for _ in range(N_PIVOT)]

class _Item:
    def __init__(self, day):
        self.datetime = dt.datetime.fromisoformat(day + "T10:30:00")
        self.properties = {"earthsearch:boa_offset_applied": True, "eo:cloud_cover": 5.0}

def _grid(res):
    # metres per degree, roughly, at 30 N
    w = int((AOI[2]-AOI[0]) * 96000 / res)
    h = int((AOI[3]-AOI[1]) * 111000 / res)
    return max(8, min(w, 4000)), max(8, min(h, 4000))

def _scene(day_iso, res):
    W, H = _grid(res)
    t = (dt.date.fromisoformat(day_iso) - D0).days
    ys, xs = np.mgrid[0:H, 0:W]
    lon = AOI[0] + (xs + .5) * (AOI[2]-AOI[0]) / W
    lat = AOI[3] - (ys + .5) * (AOI[3]-AOI[1]) / H
    ndvi = np.full((H, W), 0.08, dtype="float32")          # bare desert
    for (clon, clat, rad, cyc, ph, stall) in _c:
        dx = (lon - clon) * 96000 * math.cos(math.radians(clat))
        dy = (lat - clat) * 111000
        inside = (dx*dx + dy*dy) <= rad*rad
        u = ((t - ph) % cyc) / cyc
        v = 0.30 + 0.60 * min(1.0, u/0.75)
        if u > 0.92: v = 0.36
        if stall and t > 130: v = min(v, 0.33)
        ndvi[inside] = v + rng.normal(0, 0.01)
    R = np.clip((1 - ndvi) * 0.22, 0.01, 1) * 10000 + 1000
    N = np.clip((1 + ndvi) * 0.22, 0.01, 1) * 10000 + 1000
    scl = np.full((H, W), 4, dtype="uint8")                # 4 = vegetation, kept
    x = 418266.0 + np.arange(W, dtype="float64") * res
    y = 3352334.0 - np.arange(H, dtype="float64") * res
    return xr.Dataset({"red": (("y","x"), R.astype("uint16")),
                       "nir": (("y","x"), N.astype("uint16")),
                       "scl": (("y","x"), scl)},
                      coords={"y": y, "x": x})

class _Search:
    def items(self): return [_Item(d) for d in DATES]
class _Client:
    @staticmethod
    def open(url, **kw): return _Client()
    def search(self, **kw): return _Search()

def install():
    pc = types.ModuleType("pystac_client"); pc.Client = _Client
    sys.modules["pystac_client"] = pc

    odc = types.ModuleType("odc"); odcs = types.ModuleType("odc.stac")
    def load(items, bands, crs, resolution, bbox, groupby, **kw):
        day = items[0].datetime.date().isoformat()
        ds = _scene(day, resolution)
        return ds.expand_dims("time")
    odcs.load = load; odc.stac = odcs
    sys.modules["odc"] = odc; sys.modules["odc.stac"] = odcs

    ea = types.ModuleType("earthaccess")
    def _login(*a, **k): raise RuntimeError("no credentials in the dry run")
    ea.login = _login
    ea.search_data = lambda **k: []
    ea.get_requests_https_session = lambda: None
    sys.modules["earthaccess"] = ea

    plc = types.ModuleType("planetary_computer"); plc.sign_inplace = lambda x: x
    sys.modules["planetary_computer"] = plc

# --- the odc-geo accessor the notebook relies on (.odc.geobox.transform) ---
from rasterio.transform import Affine

# The AOI's north-west corner in EPSG:32637, so the synthetic fields land
# where the AOI actually is. With an arbitrary origin they come out near
# 41.6 E - outside the box - and nothing intersects the EMIT swath.
UTM_X0, UTM_Y0 = 418266.0, 3352334.0

class _GeoBox:
    def __init__(self, ds):
        res = int(round(float(ds.x[1] - ds.x[0]))) if ds.sizes.get("x", 0) > 1 else 20
        self._res = res
        self.transform = Affine(res, 0.0, UTM_X0, 0.0, -res, UTM_Y0)
        self.crs = "EPSG:32637"

@xr.register_dataset_accessor("odc")
class _OdcAccessor:
    def __init__(self, ds): self._ds = ds
    @property
    def geobox(self): return _GeoBox(self._ds)


# ---------------------------------------------------------------------------
# Optional EMIT branch. Enabled with DRYRUN_EMIT=1 so the fast path stays fast.
# With it on, the notebook's hyperspectral section executes for real against
# emit_fixture.nc: download, band selection, GLT orthorectification, zonal
# reduction, the join, the prediction contest and the figures.
# ---------------------------------------------------------------------------
import os as _os

def _emit_granule(ur, day_iso, cloud):
    url = ("https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/"
           "EMITL2ARFL.001/%s/%s.nc" % (ur, ur))
    return {"umm": {
        "GranuleUR": ur,
        "TemporalExtent": {"RangeDateTime": {"BeginningDateTime": day_iso + "T10:15:00.000Z"}},
        "AdditionalAttributes": [{"Name": "CloudCover", "Values": [str(cloud)]}],
        "RelatedUrls": [
            {"Type": "GET DATA", "URL": url.replace(ur + ".nc", "EMIT_L2A_MASK_001_" + ur + ".nc")},
            {"Type": "GET DATA", "URL": url.replace(ur + ".nc", "EMIT_L2A_RFL_001_" + ur + ".nc")},
        ],
    }}

class _FakeResponse:
    def __init__(self, path):
        self._path = path
        self.headers = {"content-length": str(_os.path.getsize(path))}
    def raise_for_status(self): pass
    def iter_content(self, chunk_size=1 << 22):
        with open(self._path, "rb") as fh:
            while True:
                b = fh.read(chunk_size)
                if not b:
                    return
                yield b

class _FakeSession:
    def __init__(self, path): self._path = path
    def get(self, url, stream=False, **kw): return _FakeResponse(self._path)

def install_emit():
    """Point earthaccess at the local fixture instead of NASA."""
    import sys, emit_fixture
    here = _os.path.dirname(_os.path.abspath(__file__))
    fixture = _os.path.join(here, "emit_fixture.nc")
    if not _os.path.exists(fixture):
        emit_fixture.write(fixture)

    d1, d2 = DATES[10], DATES[50]          # exact Sentinel-2 days, so gap = 0
    grans = [_emit_granule("EMIT_L2A_RFL_001_%s_2620308_031" % d1.replace("-", ""), d1, 3),
             _emit_granule("EMIT_L2A_RFL_001_%s_2620308_047" % d2.replace("-", ""), d2, 7)]

    ea = sys.modules["earthaccess"]
    ea.login = lambda *a, **k: True
    ea.search_data = lambda **k: grans
    ea.get_requests_https_session = lambda: _FakeSession(fixture)
    _os.environ["EARTHDATA_USERNAME"] = "dryrun"
    _os.environ["EARTHDATA_PASSWORD"] = "dryrun"          # not a real credential
