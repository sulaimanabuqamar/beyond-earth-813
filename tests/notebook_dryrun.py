"""Execute the notebook's code cells in order, offline, against the stubs."""
import sys, json, io, traceback, contextlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import offline_stubs as stubs; stubs.install()
if os.environ.get("DRYRUN_EMIT") == "1":
    stubs.install_emit()
    print("EMIT branch ENABLED - the hyperspectral section will execute\n")
import matplotlib; matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(HERE, "_dryrun"), exist_ok=True)
os.chdir(os.path.join(HERE, "_dryrun"))
NB = os.path.join(ROOT, "notebook", "beyond_earth_tabarjal.ipynb")
nb = json.load(open(NB))
cells = [ (i, "".join(c["source"])) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code" ]

g = {"__name__": "__main__"}
n = 0
for i, srcs in cells:
    n += 1
    if srcs.lstrip().startswith("import subprocess"):        # never pip-install in the dry run
        print("cell %2d  [skipped: pip install]" % n); continue
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(srcs, "<cell %d>" % n, "exec"), g)
    except Exception:
        print("cell %2d  FAILED" % n)
        print(buf.getvalue()[-1500:])
        traceback.print_exc()
        sys.exit(1)
    out = buf.getvalue().strip()
    head = " | ".join(out.split("\n")[-3:])[:150] if out else ""
    print("cell %2d  ok   %s" % (n, head))

print("\n--- files written ---")
for f in sorted(os.listdir(".")):
    if f.startswith("tabarjal"):
        print("  %-34s %9.1f KB" % (f, os.path.getsize(f) / 1024))
