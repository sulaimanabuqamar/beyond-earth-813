#!/usr/bin/env python3
"""Run every check in one command:  python3 tests/verify.py

  1  notebook dry run     - the whole notebook, offline, on synthetic imagery.
                            Proves it runs to completion and writes its outputs
                            with no Earthdata credentials present.
  2  model parity         - the Python model in api/priority.py and the
                            JavaScript model inside dashboard/index.html must
                            return the same answer for every field on every
                            date. They are two implementations of one model;
                            if they disagree, the dashboard is lying.
  3  dashboard render     - the page is rendered headlessly against eight
                            datasets, including the degenerate ones a real run
                            can produce, and must throw nothing.
  1b notebook + EMIT      - the same, with the hyperspectral branch executing
                            against a miniature but structurally faithful EMIT
                            granule: download, band selection, GLT
                            orthorectification, zonal reduction, the join and
                            the prediction contest.
  4  API smoke            - every endpoint answers, error paths included.

Needs: pip install -r requirements.txt, and `npm install` inside tests/ for
jsdom. Checks needing node are skipped, not failed, when node is absent.
"""
import os, subprocess, sys, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def have(cmd):
    return shutil.which(cmd) is not None

def step(title, args, cwd=HERE, optional=False):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    t0 = time.time()
    try:
        r = subprocess.run(args, cwd=cwd)
        code = r.returncode
    except FileNotFoundError as e:
        if optional:
            print("  SKIPPED -", e)
            return None
        raise
    print("  -> %s in %.1fs" % ("PASS" if code == 0 else "FAIL", time.time() - t0))
    return code

results = {}
subprocess.run([sys.executable, os.path.join(HERE, "synthetic_data.py")], cwd=HERE)

results["notebook dry run"] = step(
    "1  NOTEBOOK DRY RUN (offline, synthetic imagery, no credentials)",
    [sys.executable, os.path.join(HERE, "notebook_dryrun.py")])

env_emit = dict(os.environ, DRYRUN_EMIT="1")
print("\n" + "=" * 72)
print("1b  NOTEBOOK DRY RUN WITH THE HYPERSPECTRAL BRANCH ACTIVE")
print("=" * 72)
_r = subprocess.run([sys.executable, os.path.join(HERE, "notebook_dryrun.py")],
                    cwd=HERE, env=env_emit)
results["notebook dry run (EMIT)"] = _r.returncode
print("  -> %s" % ("PASS" if _r.returncode == 0 else "FAIL"))

results["model parity (python)"] = step(
    "2  MODEL PARITY (api/priority.py  vs  dashboard/index.html)",
    [sys.executable, os.path.join(HERE, "parity_python.py")])
results["model parity (python vs js)"] = step(
    "   ... the same model as implemented in the dashboard's JavaScript",
    ["node", os.path.join(HERE, "parity_js.js")], optional=not have("node"))

results["dashboard render"] = step(
    "3  DASHBOARD RENDER (8 datasets, headless)",
    ["node", os.path.join(HERE, "dashboard_render.js")], optional=not have("node"))

results["api smoke"] = step(
    "4  API SMOKE (every endpoint, error paths included)",
    [sys.executable, os.path.join(HERE, "api_smoke.py")])

print("\n" + "=" * 72)
print("SUMMARY")
print("=" * 72)
worst = 0
for k, v in results.items():
    label = "SKIP" if v is None else ("PASS" if v == 0 else "FAIL")
    if v not in (0, None):
        worst = 1
    print("  %-28s %s" % (k, label))
print()
sys.exit(worst)
