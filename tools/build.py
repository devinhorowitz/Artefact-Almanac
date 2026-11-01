"""Check the Artefact Almanac and install it as an MO2 mod.

Checks: every script compiles under LuaJIT 2.0, every script's VERSION matches this build's, and
the tests pass. Only then mirrors gamedata/ into <mods>\\Artefact Almanac\\gamedata (files no
longer in the source are removed there) and writes its meta.ini.

Installing into the live MO2 folder counts as a launch for the shared game lock: it refuses
unless MO2 and the game are closed and the lock (ALMANAC_LOCK, default
<ALMANAC_GAMMA>\\_baseline\\state\\game-lock.txt) is held by the Almanac ("almanac ...").

    build.py                      check and install into <ALMANAC_GAMMA>\\mods
    build.py --check              check only
    build.py --mods <folder>      install into another MO2 mods folder (no lock needed)
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

ROOT = os.path.dirname(HERE)
GD = os.path.join(ROOT, "gamedata")
NAME = "Artefact Almanac"
VERSION = "0.1.0"
TESTS = ["test_census.py", "test_ingame_census.py"]
GAMMA = os.environ.get("ALMANAC_GAMMA", r"D:\GAMMA")
LOCK = os.environ.get("ALMANAC_LOCK", os.path.join(GAMMA, "_baseline", "state", "game-lock.txt"))

META = """[General]
modid=0
version={version}
newestVersion=
category=
installationFile=
repository=
gameName=stalkeranomaly
comments=Artefact Almanac {version}: a guide to the Zone's artifacts.
notes="Built from the Artefact-Almanac repo by tools/build.py. Do not edit here: rebuild."
url=https://github.com/devinhorowitz/Artefact-Almanac
hasCustomURL=true
"""


def check():
    bad = []
    lua = L.LuaRuntime()
    compiles = lua.eval("function(s, n) local f, e = loadstring(s, n) return e end")
    n_lua = 0
    for root, _, files in os.walk(GD):
        for f in files:
            if not f.endswith(".script"):
                continue
            p = os.path.join(root, f)
            text = open(p, encoding="latin-1").read()
            n_lua += 1
            err = compiles(text, f)
            if err:
                bad.append("%s: %s" % (p, err))
            m = re.search(r'(?m)^VERSION = "([^"]+)"', text)
            if m and m.group(1) != VERSION:
                bad.append("%s's VERSION is %s, this build's is %s" % (f, m.group(1), VERSION))
    print("scripts compile: %d, version %s" % (n_lua, VERSION))
    if n_lua == 0:
        bad.append("no scripts under " + GD)
    for t in TESTS:
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, t)], capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-200:]
        print("%-24s %s" % (t, last))
        if r.returncode != 0:
            bad.append(t + ": " + last)
    return bad


def lock_is_ours():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout
    busy = [e for e in ("ModOrganizer.exe", "AnomalyDX11AVX.exe") if e in out]
    held = open(LOCK, encoding="utf-8").read().strip() if os.path.isfile(LOCK) else "(no lock file)"
    if busy or not held.startswith("almanac "):
        return "refused: lock=%r running=%s (take the lock first)" % (held, busy)
    return None


def install(mods):
    dest = os.path.join(mods, NAME)
    dest_gd = os.path.join(dest, "gamedata")
    os.makedirs(dest_gd, exist_ok=True)
    want = set()
    for root, _, files in os.walk(GD):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), GD)
            want.add(rel.lower())
            out = os.path.join(dest_gd, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(os.path.join(root, f), out)
    removed = 0
    for root, _, files in os.walk(dest_gd):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), dest_gd)
            if rel.lower() not in want:
                os.remove(os.path.join(root, f))
                removed += 1
    with open(os.path.join(dest, "meta.ini"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(META.format(version=VERSION))
    print("installed %d files into %s (%d stale removed)" % (len(want), dest, removed))


def main():
    args = sys.argv[1:]
    bad = check()
    if bad:
        for b in bad:
            print("FAIL " + b)
        sys.exit(1)
    if "--check" in args:
        return
    if "--mods" in args:
        install(args[args.index("--mods") + 1])
        return
    refused = lock_is_ours()
    if refused:
        sys.exit(refused)
    install(os.path.join(GAMMA, "mods"))


if __name__ == "__main__":
    main()
