"""Run almanac_data.script under LuaJIT 2.0 over test_census.py's made-up install and require the
same answers census.py gives there (which test_census.py checks one by one): artifacts, names,
tiers, containers, detectors, recipes, field picks, Dynamic Anomalies' shares.

    python test_catalog.py            the real script
    python test_catalog.py MUTANT     a broken copy (see MUTANTS); the run must fail

`python -I catalog_lua.py` runs the same comparison on the install the ALMANAC_* settings name.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_census  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_data.script")

#: name -> (text in almanac_data.script, its broken replacement); each must make this test fail
MUTANTS = {
    "gap": ('            while ini_sys:line_exist(sec, "af_class_" .. i) do\n', "            while i < 9 do\n"),
    "dedupe": ('if a ~= "" and not seen[a] then', 'if a ~= "" then'),
    "container": ("            return sec:sub(1, -#suf - 1)\n", "            return sec\n"),
    "key_prefix": ("local rid = key:sub(3)", "local rid = key"),
    "field_count": ("if #t == 6 or #t == 8 or #t == 10 then", "if #t >= 4 then"),
    "takes": ("if C.artifacts[rid] or takes then", "if C.artifacts[rid] then"),
    "registered": ("        if ini:section_exist(g) then\n", "        if true then\n"),
    "members": ("                if ini_sys:section_exist(m[1]) then\n", "                if true then\n"),
    "layer_default": ('local names = csv(arts or (ini:section_exist(az) and ini:r_string_ex(az, "artefacts")))',
                      "local names = csv(arts)"),
    "pick_share": ("picks[a] = (picks[a] or 0) + 1 / #names / #members", "picks[a] = (picks[a] or 0) + 1 / #members"),
    "dao_allowed": ("            if allowed[sec] then\n                n = n + 1\n",
                    "            if true then\n                n = n + 1\n"),
    "dao_random": ("            a.dao_random = true\n", "            a.dao_random = false\n"),
    "untranslated": ('name = game.translate_string(SYS_GetParam(0, sec, "inv_name", sec))',
                     'name = SYS_GetParam(0, sec, "inv_name", sec)'),
    "zones_once": ("                if not seen[key] then\n", "                if true then\n"),
    "zone_error": ("local ok, ini = pcall(se.spawn_ini, se)", "local ok, ini = true, se:spawn_ini()"),
    "cfg_case": ('local path = string.lower(cfg):gsub("/", "\\\\")', 'local path = cfg:gsub("/", "\\\\")'),
    "zone_level": ("lvl = lok and lvl or \"?\"", "lvl = \"?\""),
}


def main():
    mutant = sys.argv[1] if len(sys.argv) > 1 else None
    tmp = tempfile.mkdtemp(prefix="almanac_catalog_")
    fails = []
    try:
        script = SCRIPT
        if mutant:
            old, new = MUTANTS[mutant]
            src = open(SCRIPT, encoding="utf-8").read()
            if src.count(old) != 1:
                print("MUTANT %s: its text occurs %d times, not once" % (mutant, src.count(old)))
                sys.exit(3)
            script = os.path.join(tmp, "almanac_data.script")
            with open(script, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
        root = os.path.join(tmp, "install")
        test_census.write_install(root)
        env = dict(os.environ, ALMANAC_GAMMA=os.path.join(root, "gamma"), ALMANAC_PROFILE="P",
                   ALMANAC_ANOMALY=os.path.join(root, "anomaly"), ALMANAC_BASE_CONFIGS=os.path.join(root, "base"),
                   ALMANAC_DATA_SCRIPT=script)
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "catalog_lua.py")], env=env,
                           capture_output=True, text=True)
        try:
            out = json.loads(r.stdout)
        except ValueError:
            print("FAIL catalog_lua.py gave no summary: " + (r.stdout + r.stderr)[-500:])
            sys.exit(1)
        for d in out["differences"]:
            fails.append("differs from the census: " + d)
        # the comparison covered the whole made-up install, so agreeing means something
        if (out["artifacts"], out["recipes"], out["fields"]) != (4, 3, 1):
            fails.append("counts: %r" % ((out["artifacts"], out["recipes"], out["fields"]),))
        if out["compared"] < 40:
            fails.append("only %d comparisons" % out["compared"])
        if not any(x.startswith("[almanac-data] 4 artifacts, 3 recipes, 1 field configs") for x in out["log"]):
            fails.append("no summary line: %r" % out["log"])
        if r.returncode != (1 if out["n_differences"] else 0):
            fails.append("exit %d with %d differences" % (r.returncode, out["n_differences"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d comparisons with the census, no difference" % out["compared"])


if __name__ == "__main__":
    main()
