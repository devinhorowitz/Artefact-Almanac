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
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

ROOT = os.path.dirname(HERE)
GD = os.path.join(ROOT, "gamedata")
NAME = "Artefact Almanac"
VERSION = "0.1.0"
TESTS = ["test_census.py", "test_ingame_census.py", "test_catalog.py", "test_trees.py", "test_page.py", "test_found.py", "test_learn.py"]
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
    # every XML parses (string tables as windows-1251); a UI file's first element is <w>, since the
    # engine's UI parser gives up on anything before it and every widget is then nil
    defined, n_xml = set(), 0
    for root, _, files in os.walk(GD):
        for f in files:
            if not f.endswith(".xml"):
                continue
            p = os.path.join(root, f)
            text = open(p, "rb").read().decode("cp1251")
            body = text.split("?>", 1)[1] if text.startswith("<?xml") else text
            try:
                tree = ET.fromstring(body)
                n_xml += 1
            except ET.ParseError as e:
                bad.append("%s: %s" % (p, e))
                continue
            if os.path.basename(root) == "ui" and tree.tag != "w":
                bad.append("%s: the root element is <%s>, not <w>" % (p, tree.tag))
            if "\\text\\" in p or "/text/" in p:
                defined |= {s.get("id") for s in tree.iter("string")}
    # every string id the scripts and UI files name is in the string table
    used = set()
    for root, _, files in os.walk(GD):
        for f in files:
            if f.endswith((".script", ".xml")) and "\\text\\" not in os.path.join(root, f):
                used |= set(re.findall(r"\b((?:st|ui_mcm)_almanac_[a-z0-9_]+)", open(os.path.join(root, f), encoding="latin-1").read()))
    for sid in sorted(used - defined):
        # MCM builds an option's ids itself (ui_mcm_almanac_<id>, _desc); prefixes used to build
        # ids in code end in "_"
        if not sid.endswith("_"):
            bad.append("string id %s is used but not defined" % sid)
    print("xml parse: %d, string ids used: %d, defined: %d" % (n_xml, len(used), len(defined)))
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
