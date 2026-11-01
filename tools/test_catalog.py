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
    "cfg_case": ('return (string.lower(path):gsub("/", "\\\\"))', 'return (path:gsub("/", "\\\\"))'),
    "zone_level": ("lvl = lok and lvl or \"?\"", "lvl = \"?\""),
    "supplies_only": ('if s:match("^supplies_%d+$") then', "if true then"),
    "item_count": ('if death:line_exist("item_count", item) then', "if true then"),
    "chance_positive": ("if chance > 0 then", "if true then"),
    "private_sections": ('for _, private in ipairs({ "", "_private" }) do', 'for _, private in ipairs({ "" }) do'),
    "seller_names": ("names[#names + 1] = game.translate_string(n)", "names[#names + 1] = n"),
    "fetch_args": ('local what = args and args:match("^[^:]*:([^:]+)")', 'local what = args and args:match("^([^:]+)")'),
    "sim_comms": ('if comms and comms ~= "" then', "if false then"),
    "sim_trader": ('local trader = id:match("^sim_default_(.-)_trader_task_%d+$")', "local trader = nil"),
    "drx_prefix": ('local sid = id:gsub("^drx_sl_", ""):match("^(.-)_task_%d+$")', 'local sid = id:match("^(.-)_task_%d+$")'),
}

# on top of test_census's install: the book carried by legend-rank loners (privately) and master
# Duty, the Melter in one death list but with no [item_count] entry (so never dropped) and only
# bought by the trader; a fetch list and the tasks that use it (a faction's squads, a faction's
# traders, a storyline NPC, and a task fetching something else); the trader map naming trade_x's
# trader and a config nobody uses
EXTRA = {
    "base/configs/items/settings/death_generic.ltx":
        "#include \"death_items.ltx\"\n[item_count]\naf_c = 1, 2\nrecipe_basic_4 = 1, 1\n[keep_items]\naf_d\n",
    "base/configs/items/settings/death_items.ltx":
        "[stalker_master]\naf_b = 1\n[stalker_private_legend]\nrecipe_basic_4 = 0.04\n[dolg_master]\nrecipe_basic_4 = 0.02\n"
        "[stalker_legend]\nitm_artefactskit = 0.5\n",
    "base/configs/items/trade/trade_x.ltx":
        "[trader]\n[trade_generic_buy]\naf_a = 1, 1\nitm_artefactskit = 1, 1\n[supplies_1]\nrecipe_basic_4 = 1, 1\naf_d = 1, 1\n",
    "base/configs/items/settings/fetch_list.ltx":
        "[fetch_list]\nartefacts\nsupplies\n[artefacts]\naf_a = true\n[supplies]\nammo_x = true\n",
    "base/configs/misc/task/task_manager.ltx":
        "[x_task_1]\nfetch_func = %=setup_fetch_task(x_task_1_fetch:artefacts:1:1)%\nsim_communities = stalker\n"
        "[sim_default_ecolog_trader_task_2]\nfetch_func = %=setup_fetch_task(sim_default_ecolog_trader_task_2_fetch:artefacts:1:1)%\n"
        "[drx_sl_yan_x_task_3]\nfetch_func = %=setup_fetch_task(drx_sl_yan_x_task_3_fetch:artefacts:1:1)%\n"
        "[w_task_1]\nfetch_func = %=setup_fetch_task(w_task_1_fetch:supplies:1:1)%\n[v_task_1]\ntitle = no fetch\n",
    "base/configs/text/eng/st_d.xml": '<string_table><string id="st_trader_x"><text>Trader X</text></string></string_table>',
    "traders.ltx": "[almanac_trade]\ntrade_x = st_trader_x\ntrade_nobody = -\n",
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
        for rel, text in EXTRA.items():
            p = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="cp1251", newline="\n") as f:
                f.write(text)
        env = dict(os.environ, ALMANAC_GAMMA=os.path.join(root, "gamma"), ALMANAC_PROFILE="P",
                   ALMANAC_ANOMALY=os.path.join(root, "anomaly"), ALMANAC_BASE_CONFIGS=os.path.join(root, "base"),
                   ALMANAC_DATA_SCRIPT=script, ALMANAC_TRADERS=os.path.join(root, "traders.ltx"))
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
        # where the book and the Melter come from, and what fetch tasks can ask for, by whom
        want = {"recipe_basic_4": {"sellers": ["Trader X"], "drops": [["stalker", "legend", 0.04], ["dolg", "master", 0.02]]},
                "itm_artefactskit": {"sellers": [], "drops": []}}
        if out["sources"] != want:
            fails.append("sources: %r" % out["sources"])
        got = (out["wanted"], out["wanted_tasks"], out["wanted_factions"], out["wanted_givers"])
        if got != (["af_a"], 3, ["ecolog", "stalker"], ["yan_x"]):
            fails.append("wanted: %r" % (got,))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d comparisons with the census, no difference" % out["compared"])


if __name__ == "__main__":
    main()
