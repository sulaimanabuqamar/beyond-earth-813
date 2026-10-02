"""Every endpoint answers, and none of them 500s - including the error paths.

Runs against a synthetic dataset pointed at through BEYOND_EARTH_DATA, so it never
touches, moves or needs the real one in results/.
"""
import os, sys, gzip, shutil, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

SRC = os.path.join(HERE, "synthetic.json")
tmp = tempfile.mkdtemp(prefix="beyond-earth-api-smoke-")
DST = os.path.join(tmp, "tabarjal.json.gz")
with open(SRC, "rb") as fi, gzip.open(DST, "wb") as fo:
    shutil.copyfileobj(fi, fo)
os.environ["BEYOND_EARTH_DATA"] = DST

bad = 0
try:
    from fastapi.testclient import TestClient
    import importlib
    import api.service as svc
    importlib.reload(svc)
    assert str(svc.DATA) == DST, "BEYOND_EARTH_DATA was not honoured: %s" % svc.DATA
    c = TestClient(svc.app)

    cases = [
        ("/health", 200), ("/meta", 200), ("/fields", 200), ("/fields/1", 200),
        ("/priority", 200), ("/priority?as_of=2026-06-01", 200),
        ("/comparison", 200), ("/comparison?as_of=2026-06-01", 200),
        ("/fields/999999", 404), ("/hyperspectral/1", 404),
        ("/priority?as_of=not-a-date", 422),
    ]
    for path, want in cases:
        r = c.get(path)
        ok = r.status_code == want
        bad += 0 if ok else 1
        print("  %-32s %s expected %s  %s" % (path, r.status_code, want, "ok" if ok else "MISMATCH"))

    pr = c.get("/priority").json()
    assert "queue" in pr and "counts" in pr, "/priority payload shape changed"
    cm = c.get("/comparison").json()
    for k in ("naive_decline_top", "cycle_aware_top", "naive_that_were_only_mown", "headline"):
        assert k in cm, "/comparison missing " + k
    print("\npayload shapes ok |", "FAILURES: %d" % bad if bad else "all status codes as expected")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("BEYOND_EARTH_DATA", None)

sys.exit(1 if bad else 0)
