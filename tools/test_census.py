"""Run census.py over a small made-up install and check what it reads.

The install: a base game with four artifacts, a detector with a gap in its list, a container, a
recipe tree two crafts deep, a recipe line the workshop skips, two field groups (one never
registered), a field config, a trader, Dynamic Anomalies' script, the inventory card's script,
Perk-Based Artefacts' tables, the PDA Guide's list, and string tables in two files. A mod
above it changes a cost by DLTX and shadows one string file. Checked: names (top copy, later
file wins), DLTX merges, the card's numbers, containers, perks, the Guide, detectors read to the
first gap, recipes read as the workshop reads them, tree totals, field pick chances, Dynamic
Anomalies' lists and random pick, trader stock against what traders buy, and the ways each
artifact turns up.

    python test_census.py            the real census.py
    python test_census.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

#: name -> (text in census.py, its broken replacement); each must make this test fail
MUTANTS = {
    "gap_ignored": ('        while ("af_class_%d" % i) in keys:\n',
                    '        while i < 99:\n            if ("af_class_%d" % i) not in keys:\n                i += 1\n                continue\n'),
    "dupes_count": ('uniq = list(dict.fromkeys(lst))', 'uniq = lst'),
    "key_prefix": ('rid = key[2:]', 'rid = key'),
    "field_count": ('if len(t) not in (6, 8, 10):', 'if len(t) < 4:'),
    "tree_flat": ('                sub = expand(item, by_result, kind, seen + (art,))',
                  '                sub = expand(item, {}, kind, seen + (art,))'),
    "unregistered_spawns": ('        if g in acfg:\n            groups[g]', '        if True:\n            groups[g]'),
    "nothing_share": ('nothing += 1.0 / len(names)', 'nothing += 0'),
    "layer_default": ('names = csv(lay.get("artefacts") or az.get("artefacts"))', 'names = csv(lay.get("artefacts"))'),
    "dao_unallowed": ('ok = [a for a in lst if a in allowed]', 'ok = lst'),
    "bought_is_sold": ('elif sec == "trade_generic_buy":', 'elif sec.startswith("trade_generic"):\n                for k in keys:\n                    if k in targets:\n                        found[k]["sold"].append(sec)\n            elif False:'),
    "string_order": ('    for f in vfs.listdir("configs\\\\text\\\\" + lang, "*.xml"):',
                     '    for f in reversed(vfs.listdir("configs\\\\text\\\\" + lang, "*.xml")):'),
    "card_magnitude": ('"shown": round(raw * row["magnitude"], 2)', '"shown": round(raw, 2)'),
    "card_section": ('raw = num((absorb if row["section"] else v).get(key), 0.0)', 'raw = num(v.get(key), 0.0)'),
    "container_fold": ('held = s[: -len(suf)]', 'held = s'),
    "guide_prefix": ('return {k[len(pre):] for k', 'return {k for k'),
    "perk_name": ('p = re.search(r"Perk:\\s*(.+?)\\s*$", comment or "")', 'p = None'),
    "drop_rules": ('k = "drop rules" if kind == "death drops" and secs <= DROP_RULES else kind', 'k = kind'),
    "ways_sold": ('SOURCE_KINDS = ("sold", "death drops", "stash", "loadout")', 'SOURCE_KINDS = ("death drops", "stash", "loadout")'),
}

FILES = {
    # ---- the base game (configs.db0, unpacked)
    "base/configs/system.ltx": '#include "items\\items\\*.ltx"\n',
    "base/configs/items/items/items_af.ltx": """
[af_base]
belt = true
inv_name = st_none
[af_a]:af_base
kind = i_arty
inv_name = st_af_a
tier = 2
cost = 1000
inv_weight = 0.5
health_restore_speed = 0.002
hit_absorbation_sect = af_a_absorbation
[af_a_absorbation]
burn_immunity = 0.01
[af_b]:af_base
kind = i_arty_junk
inv_name = st_af_b
tier = 1
[af_c]:af_base
kind = i_arty
inv_name = st_af_c
tier = 4
burn_cap = 0.3
[af_d]:af_base
kind = i_arty
inv_name = st_af_d
tier = 3
[af_a_af_aac]:af_a
kind = i_arty_cont
[part_x]
kind = i_mutant_part
[recipe_basic_4]
kind = i_book
inv_name = st_book
[ammo_x]
kind = i_ammo
[det_x]
kind = i_device
af_class_1 = af_a
af_class_2 = af_b
af_class_3 = af_a
af_class_5 = af_c
""",
    "base/configs/items/settings/craft.ltx": """
[1]
title = st_tools
x_ammo_x = 1, recipe_basic_0, ammo_x,1, part_x,1
[2]
title = st_ammo
a_ammo_x = 5, recipe_basic_0, af_b,1, part_x,2
[3]
title = encyclopedia_artefacts
x_af_c = 6, recipe_basic_4, af_a,2, af_b,1, part_x,5
y_af_a = 6, recipe_basic_0, af_b,1, part_x,1
z_af_d = 6, recipe_basic_4, af_c,1, part_x
""",
    "base/configs/items/settings/artefacts.ltx": """
[settings]
psi_storm_chance = 0.6
surge_chance = 1.2
[artefact_groups]
g1
g_missing
[g1]
af_a
af_zzz
[g2]
af_b
""",
    "base/configs/scripts/escape/anomaly/f1.ltx": """
[anomal_zone]
artefacts = g1, g2
layers_count = 2
[layer_1]
[layer_2]
artefacts = g1
""",
    "base/configs/items/trade/trade_x.ltx": """
[trader]
[trade_generic_buy]
af_a = 1, 1
[supplies_1]
recipe_basic_4 = 1, 1
af_d = 1, 1
""",
    "base/configs/items/settings/death_generic.ltx": "[item_count]\naf_c = 1, 2\n[keep_items]\naf_d\n",
    "base/configs/items/settings/death_items.ltx": "[stalker_master]\naf_b = 1\n",
    "base/configs/game.ltx": "[l01_escape]\nweathers = default\n[l03u_agr_underground]\nweathers = indoor\n",
    "base/configs/plugins/difficulty.ltx": "[econ_1]\narty_chance = 0.3\n",
    "base/configs/plugins/encyclopedia.ltx": "[encyclopedia_artefacts]\nencyclopedia_artefacts__about\nencyclopedia_artefacts_af_a\n",
    "base/configs/text/eng/st_a.xml": '<string_table><string id="st_af_a"><text>Alpha</text></string>'
                                      '<string id="st_af_b"><text>Beta (a)</text></string>'
                                      '<string id="st_af_d"><text>Delta (a)</text></string></string_table>',
    "base/configs/text/eng/st_b.xml": '<string_table><string id="st_af_b"><text>Beta</text></string>'
                                      '<string id="st_af_c"><text>Gamma (base)</text></string></string_table>',
    "base/configs/text/eng/st_c.xml": '<string_table><string id="st_af_d"><text>Delta</text></string>'
                                      '<string id="st_book"><text>Book</text></string></string_table>',
    "base/configs/text/rus/st_a.xml": '<string_table><string id="st_af_a"><text>Альфа</text></string></string_table>',
    "base/scripts/utils_ui.script": """
	stats_table["artefact"] = {
		["condition"]                  = { index= 1,  typ= "float",   name= "ui_inv_af_condition", magnitude= 100, unit= "st_perc", show_always= true , value_functor= {"utils_ui","prop_condition"} },
		["health_restore_speed"]       = { index= 2,  typ= "float",   name= "ui_inv_health", magnitude= 6600,  unit= "", condition= true, show_always= false },
		["burn_immunity"]              = { index= 7,  typ= "float",   name= "ui_inv_outfit_burn_protection", magnitude= 84800, unit= "st_perc", condition= true, show_always= false ,section= "hit_absorbation_sect" },
	}
""",
    "base/scripts/perk_based_artefacts.script": """
artefact_props = {
	af_c = {
		boost = 1,
	},
}
artefact_on_update_functions = {

	-- Alpha, Perk: Glow
	af_a = function(actor)
		local x = 1
	end,
	af_b = function() end,
}
""",
    "base/scripts/drx_da_main_artefacts.script": """
allowed_artefacts = (function()
	local t = {}
	ini_sys:section_for_each(function(sec)
		local k = SYS_GetParam(0, sec, "kind", "")
		if (k == "i_arty" or k == "i_arty_junk") and sec ~= "af_c" then
			t[#t + 1] = sec
		end
	end)
	return t
end)()
artefacts_map_chances = { ["l01_escape"] = 20 }
artefacts_map_tiers = { ["l01_escape"] = { "af_a", "af_a", "af_b", "af_c" } }
anomaly_type_to_artefacts = {}
""",
    # ---- a mod above the base
    "gamma/mods/m1/gamedata/configs/items/items/mod_system_m1.ltx": "",
    "gamma/mods/m1/gamedata/configs/mod_system_m1.ltx": "![af_a]\ncost = 2000\n",
    "gamma/mods/m1/gamedata/configs/text/eng/st_b.xml": '<string_table><string id="st_af_c"><text>Gamma</text></string></string_table>',
    "gamma/profiles/P/modlist.txt": "# order\n+m1\n-m_off\n",
    "anomaly/appdata/axr_options.ltx": "[mcm]\n",
}


def write_install(root):
    for rel, text in FILES.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="cp1251" if "/text/" in rel else "utf-8", newline="\n") as f:
            f.write(text)
    os.makedirs(os.path.join(root, "gamma", "overwrite", "gamedata"), exist_ok=True)
    os.makedirs(os.path.join(root, "anomaly", "gamedata"), exist_ok=True)


def run_census(tools, root):
    env = dict(os.environ, ALMANAC_GAMMA=os.path.join(root, "gamma"), ALMANAC_PROFILE="P",
               ALMANAC_ANOMALY=os.path.join(root, "anomaly"), ALMANAC_BASE_CONFIGS=os.path.join(root, "base"))
    out = os.path.join(root, "out")
    r = subprocess.run([sys.executable, "-I", os.path.join(tools, "census.py"), out], env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("census.py failed:\n" + r.stdout + r.stderr)
    with open(os.path.join(out, "census.json"), encoding="utf-8") as f:
        c = json.load(f)
    with open(os.path.join(out, "CENSUS.md"), encoding="utf-8") as f:
        return c, f.read()


def check(c, md):
    fails = []
    n = [0]

    def eq(what, got, want):
        n[0] += 1
        if got != want:
            fails.append("%s: got %r, want %r" % (what, got, want))

    A = c["artifacts"]
    eq("artifacts", sorted(A), ["af_a", "af_b", "af_c", "af_d"])
    eq("kinds", [A[a]["kind"] for a in sorted(A)], ["i_arty", "i_arty_junk", "i_arty", "i_arty"])
    # names: st_b.xml from the mod shadows the base's; files load in name order, later wins
    eq("name af_a", A["af_a"]["name"], "Alpha")
    eq("name af_b (st_b.xml shadowed, so st_a's)", A["af_b"]["name"], "Beta (a)")
    eq("name af_c (the mod's st_b.xml)", A["af_c"]["name"], "Gamma")
    eq("name af_d (st_c.xml loads after st_a.xml)", A["af_d"]["name"], "Delta")
    eq("name rus", A["af_a"]["name_rus"], "Альфа")
    eq("cost by DLTX", A["af_a"]["cost"], 2000.0)
    eq("card", A["af_a"]["card"], {"health_restore_speed": {"raw": 0.002, "shown": 13.2, "unit": ""},
                                   "burn_immunity": {"raw": 0.01, "shown": 848.0, "unit": "st_perc"}})
    eq("caps", A["af_c"]["caps"], {"burn_cap": 0.3})
    eq("containers", A["af_a"]["containers"], ["af_a_af_aac"])
    eq("perk af_a", A["af_a"]["perk"], {"hooks": ["artefact_on_update_functions"], "perks": ["Glow"]})
    eq("perk af_b (no comment)", A["af_b"]["perk"], {"hooks": ["artefact_on_update_functions"], "perks": []})
    eq("perk af_c", A["af_c"]["perk"], {"hooks": ["artefact_props"], "perks": []})
    eq("guide", [a for a in sorted(A) if A[a]["guide"]], ["af_a"])
    # the detector stops at the gap at af_class_4 and counts af_a once
    eq("detector list", c["detectors"]["det_x"]["list"], ["af_a", "af_b"])
    eq("detector count", c["detectors"]["det_x"]["count"], 2)
    eq("detector twice", c["detectors"]["det_x"]["listed_twice"], ["af_a"])
    eq("detector gap", c["detectors"]["det_x"]["ignored_after_gap"], [5])
    eq("af_c detectors", A["af_c"]["detectors"], [])
    # recipes: key[2:], 6/8/10 fields; z_af_d has 5 and is skipped; x_ammo_x has no artifact
    eq("recipes", sorted(r["key"] for r in c["recipes"]), ["a_ammo_x", "x_af_c", "y_af_a"])
    eq("skipped", c["recipes_skipped"], [{"section": 3, "key": "z_af_d", "fields": 5}])
    eq("made_by af_a", A["af_a"]["made_by"], ["y_af_a"])
    eq("used_in af_b", sorted(A["af_b"]["used_in"]), ["a_ammo_x", "x_af_c", "y_af_a"])
    # af_c = 2 af_a (each 1 af_b + 1 part) + 1 af_b + 5 parts: 3 crafts, 3 junk, 7 parts
    eq("tree af_c", A["af_c"]["tree"], {"crafts": 3, "books": ["recipe_basic_0", "recipe_basic_4"],
                                        "artifacts": {"af_b": 3}, "junk": 3,
                                        "parts": {"part_x": 7}, "part_count": 7})
    eq("tree af_b", A["af_b"]["tree"], None)
    # groups: g1 registered (af_zzz isn't a section), g_missing has no section, g2 not registered
    eq("registered", c["groups"]["registered"], {"g1": ["af_a"]})
    eq("not registered", c["groups"]["defined_not_registered"], ["g2"])
    f = c["fields"][0]
    eq("field level", f["level"], "l01_escape")
    eq("layer 1 (the default list)", (f["layers"][0]["picks"], f["layers"][0]["nothing"]), ({"af_a": 0.5}, 0.5))
    eq("layer 1 unregistered", f["layers"][0]["unregistered"], ["g2"])
    eq("layer 2", (f["layers"][1]["picks"], f["layers"][1]["nothing"]), ({"af_a": 1.0}, 0.0))
    eq("fields af_a", A["af_a"]["fields"], {"l01_escape": [0.5, 1.0]})
    eq("fields af_b", A["af_b"]["fields"], {})
    # DAO: af_c isn't allowed, so the list is af_a 2 of 3, af_b 1 of 3
    eq("dao allowed", c["dao"]["allowed"], ["af_a", "af_b", "af_d"])
    eq("dao af_a", A["af_a"]["dao"], {"l01_escape": 0.6667})
    eq("dao af_b", A["af_b"]["dao"], {"l01_escape": 0.3333})
    eq("dao af_c", (A["af_c"]["dao"], A["af_c"]["dao_random"]), ({}, False))
    eq("settings", (c["settings"]["arty_chance"], c["settings"]["surge_chance"], c["settings"]["outdoor_levels"]),
       ({"econ_1": 0.3}, 1.2, ["l01_escape"]))
    # the trader sells the book and only buys af_a
    eq("book sold", [(m["kind"], m["sections"]) for m in c["books"]["recipe_basic_4"]["mentions"]],
       [("sold", ["supplies_1"])])
    eq("book name", c["books"]["recipe_basic_4"]["name"], "Book")
    eq("af_a trade", [m["kind"] for m in A["af_a"]["mentions"] if m["file"].startswith("configs\\items\\trade")],
       ["bought"])
    eq("ways af_a", A["af_a"]["ways"], ["fields", "dao list", "craft"])
    # death_generic's item_count caps what a body carries; death_items hands af_b out
    eq("ways af_c", A["af_c"]["ways"], ["craft"])
    eq("ways af_b", A["af_b"]["ways"], ["dao list", "death drops"])
    eq("drop rules af_c", [(m["kind"], m["sections"]) for m in A["af_c"]["mentions"]], [("drop rules", ["item_count"])])
    eq("ways af_d", A["af_d"]["ways"], ["dao random pick", "sold"])
    eq("report source map", "### Source map" in md, True)
    eq("report counts", "- 3 artifacts (`i_arty`) and 1 junk artifacts (`i_arty_junk`); 1 containers fold into them." in md, True)
    return fails, n[0]


def main():
    mutant = sys.argv[1] if len(sys.argv) > 1 else None
    tmp = tempfile.mkdtemp(prefix="almanac_census_")
    try:
        tools = HERE
        if mutant:
            old, new = MUTANTS[mutant]
            tools = os.path.join(tmp, "tools")
            os.makedirs(tools)
            for f in ("census.py", "gamecfg.py", "lua_jit.py"):
                shutil.copy(os.path.join(HERE, f), tools)
            p = os.path.join(tools, "census.py")
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            if src.count(old) != 1:
                print("MUTANT %s: its text occurs %d times, not once" % (mutant, src.count(old)))
                sys.exit(3)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(src.replace(old, new))
        root = os.path.join(tmp, "install")
        write_install(root)
        try:
            c, md = run_census(tools, root)
        except AssertionError as e:
            print("FAIL " + str(e).splitlines()[0])
            print(str(e)[-600:])
            sys.exit(1)
        try:
            fails, n = check(c, md)
        except Exception as e:  # a broken census can leave out what a check reads
            fails, n = ["the checks crashed: %r" % e], 0
        for f in fails:
            print("FAIL " + f)
        if fails:
            sys.exit(1)
        print("ok: %d checks" % n)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
