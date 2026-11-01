"""A read-only census of the Zone's artifacts in this install, as the game would read them: what
the Almanac can show, and what it must not count. Nothing in the install is changed.

    python census.py [OUT_DIR]      writes census.json and CENSUS.md (default: the thread folder,
                                    <ALMANAC_GAMMA>\\_baseline\\artefact-almanac-thread\\census-<date>)

What it reads (gamecfg.py names the paths and settings):
- **Artifacts:** every section of kind i_arty or i_arty_junk after DLTX, with its names (the
  string tables, top copy of each file, later file names winning), tier, af_rank, cost, weight,
  the inventory card's rows (utils_ui's stats_table.artefact, read from the winning script),
  GAMMA's caps (*_cap), the containers that hold it, its Perk-Based Artefacts hooks and perk
  names, and whether the PDA Guide lists it.
- **Detectors:** each section's af_class_1, af_class_2, ... read until the first gap.
- **Crafting:** every recipe in craft.ltx (DLTX included) whose result or ingredient is an
  artifact, read as ui_workshop's LoadRecipes does (the key's first two characters dropped;
  6, 8 or 10 fields), and each artifact's tree expanded down to uncraftable artifacts and parts.
- **Fields:** artefacts.ltx's registered groups, and each field config under
  scripts\\<level>\\anomaly with the chance that a pick names each artifact (a pick naming an
  unregistered group spawns nothing).
- **Dynamic Anomalies:** drx_da_main_artefacts.script run under LuaJIT 2.0 against these
  configs: each level's chance and list, and the artifacts its random pick allows.
- **Mentions:** every winning config and script that names an artifact, a recipe book or the
  Artefact Melter, by kind of file (trade, death drops, stash, task, loadout, script), the start
  of a source map.
"""
import collections
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # for python -I, which leaves the script's folder off the path
import gamecfg  # noqa: E402
KINDS = ("i_arty", "i_arty_junk")
CONTAINER_SUFFIXES = ("_lead_box", "_af_iam", "_af_aac", "_af_aam")
MELTER = "itm_artefactskit"
# field config folders (configs\scripts\<folder>\anomaly) and the level each belongs to
FIELD_LEVELS = {
    "agroprom": "l03_agroprom", "bar": "l05_bar", "bun": "l10u_bunker", "darkscape": "k01_darkscape",
    "darkvalley": "l04_darkvalley", "dead_city": "l09_deadcity", "escape": "l01_escape",
    "garbage": "l02_garbage", "generators": "l13_generators", "jupiter": "jupiter",
    "labx16": "l08u_brainlab", "labx18": "l04u_labx18", "limansk": "l10_limansk",
    "marsh": "k00_marsh", "military": "l07_military", "pole": "y04_pole", "pripyat": "pripyat",
    "radar": "l10_radar", "red_forest": "l10_red_forest", "rostok": "l06_rostok",
    "sarcofag": "l12u_sarcofag", "stancia_1": "l12_stancia", "stancia_2": "l12_stancia_2",
    "trucks_cemetery": "k02_trucks_cemetery", "yantar": "l08_yantar", "zaton": "zaton",
}


def num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def csv(v):
    return [gamecfg.xt(x) for x in (v or "").split(",") if gamecfg.xt(x)]


# ---------------------------------------------------------------------------------------------
# reading


def strings(vfs, lang):
    """id -> text for text\\<lang>: every visible file in name order, a later file winning"""
    out = {}
    for f in vfs.listdir("configs\\text\\" + lang, "*.xml"):
        text, _ = vfs.read("configs\\text\\" + lang + "\\" + f)
        text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
        for sid, body in re.findall(r'<string\s+id\s*=\s*"([^"]+)"\s*>(.*?)</string>', text, re.S):
            m = re.search(r"<text>(.*?)</text>", body, re.S)
            if m:
                out[sid] = gamecfg.xt(m.group(1))
    return out


def ini(vfs, rel):
    """one config file as ini_file() reads it: its #includes and its own DLTX mod files"""
    ld = gamecfg.Loader(vfs)
    ld.load(rel, 0, is_root=True)
    data = ld.finalize()
    return {s: {k: (None if it.value is gamecfg.DELETE else it.value) for k, it in v.items()}
            for s, v in data.items()}


def lines(sec):
    """a section's keys in the order the engine sorts them (CInifile keeps items sorted)"""
    return sorted(sec or {}, key=lambda k: k.encode("cp1251", "replace"))


def card_rows(script):
    """utils_ui's stats_table["artefact"]: key -> {magnitude, section, condition, unit, name}"""
    m = re.search(r'stats_table\["artefact"\]\s*=\s*\{(.*?)\n\s*\}', script, re.S)
    rows = {}
    if not m:
        return rows
    for key, body in re.findall(r'\["(\w+)"\]\s*=\s*\{(.*?)\}\s*,?\s*\n', m.group(1) + "\n"):
        def field(name):
            f = re.search(r"\b%s\s*=\s*(\"[^\"]*\"|[\w.\-]+)" % name, body)
            return f.group(1).strip('"') if f else None
        rows[key] = {
            "index": int(field("index") or 0),
            "magnitude": num(field("magnitude"), 1),
            "section": field("section"),
            "condition": field("condition") == "true",
            "unit": field("unit"),
            "name": field("name"),
            "functor": "value_functor" in body,
        }
    return rows


def perk_hooks(script):
    """artifact -> {"hooks": [table names], "perks": [perk names from the comments]} for every
    artifact a top-level table of perk_based_artefacts.script keys"""
    out = collections.defaultdict(lambda: {"hooks": [], "perks": []})
    for tm in re.finditer(r"^(\w+)\s*=\s*\{", script, re.M):
        name = tm.group(1)
        if name not in ("artefact_props", "speed_boosts") and not re.match(r"artefact_on_\w+_functions$", name):
            continue
        depth, i, start = 0, tm.end() - 1, tm.end()
        while i < len(script):
            c = script[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = script[start:i]
        comment = None
        for line in body.split("\n"):
            c = re.match(r"^\t--\s*(.*)$", line)
            if c:
                comment = c.group(1)
                continue
            k = re.match(r'^\t(?:\["(af_\w+)"\]|(af_\w+))\s*=', line)
            if k:
                af = k.group(1) or k.group(2)
                rec = out[af]
                if name not in rec["hooks"]:
                    rec["hooks"].append(name)
                p = re.search(r"Perk:\s*(.+?)\s*$", comment or "")
                if p and p.group(1) not in rec["perks"]:
                    rec["perks"].append(p.group(1))
                comment = None
            elif line.strip() and not line.startswith("\t\t"):
                comment = None
    return out


def encyclopedia_list(cfg):
    """the sections the PDA Guide's artifact category has an article for (encyclopedia.ltx's
    [encyclopedia_artefacts], encyclopedia_artefacts_<section>)"""
    pre = "encyclopedia_artefacts_"
    return {k[len(pre):] for k in (cfg.get("encyclopedia_artefacts") or {}) if k.startswith(pre) and k != pre + "_about"}


def detector_lists(S):
    """detector -> its artifact list: af_class_1, af_class_2, ... until the first gap; a section
    listed twice counts once"""
    out = {}
    for sec, keys in S.items():
        if "af_class_1" not in keys:
            continue
        lst, i = [], 1
        while ("af_class_%d" % i) in keys:
            lst.append(keys["af_class_%d" % i])
            i += 1
        gaps = sorted(int(k[9:]) for k in keys if re.match(r"^af_class_\d+$", k) and int(k[9:]) > i)
        uniq = list(dict.fromkeys(lst))
        out[sec] = {"list": uniq, "listed_twice": sorted({a for a in lst if lst.count(a) > 1}),
                    "ignored_after_gap": gaps}
    return out


def recipes(craft, S):
    """every workshop recipe as LoadRecipes reads it: [{section, title, key, result, tool, book,
    parts: [[item, n], ...]}], plus the lines it skips"""
    out, skipped = [], []
    ind = 1
    while str(ind) in craft:
        sec = craft[str(ind)]
        title = sec.get("title")
        for key in lines(sec):
            if key == "title":
                continue
            rid = key[2:]
            if rid not in S:
                continue
            t = [gamecfg.xt(x) for x in (sec[key] or "").split(",")]
            if len(t) not in (6, 8, 10):
                skipped.append({"section": ind, "key": key, "fields": len(t)})
                continue
            parts = []
            for j in range(2, len(t), 2):
                if t[j] in S:
                    parts.append([t[j], int(num(t[j + 1], 0))])
                else:
                    skipped.append({"section": ind, "key": key, "missing": t[j]})
            out.append({"section": ind, "title": title, "key": key, "result": rid,
                        "tool": int(num(t[0], 1)), "book": t[1], "parts": parts})
        ind += 1
    return out, skipped


def expand(art, by_result, kind, seen=()):
    """an artifact's tree down to what can't be crafted: crafts, books, leaf artifacts by kind,
    other parts; the first recipe for each result (alternatives listed with the totals)"""
    tot = {"crafts": 0, "books": set(), "artifacts": collections.Counter(), "parts": collections.Counter()}
    rs = by_result.get(art)
    if not rs or art in seen:
        tot["artifacts"][art] += 1
        return tot
    r = rs[0]
    tot["crafts"] += 1
    tot["books"].add(r["book"])
    for item, n in r["parts"]:
        if kind(item) in KINDS:
            for _ in range(n):
                sub = expand(item, by_result, kind, seen + (art,))
                tot["crafts"] += sub["crafts"]
                tot["books"] |= sub["books"]
                tot["artifacts"].update(sub["artifacts"])
                tot["parts"].update(sub["parts"])
        else:
            tot["parts"][item] += n
    return tot


def field_configs(vfs, groups, S):
    """every field config: level, layers, and per layer the chance that one pick names each
    artifact (and the chance it names nothing)"""
    out = []
    for rel in sorted(vfs.files):
        p = rel.split("\\")
        if not (len(p) == 5 and p[1] == "scripts" and p[3] == "anomaly" and p[4].endswith(".ltx")):
            continue
        cfg = ini(vfs, rel)
        az = cfg.get("anomal_zone", {})
        n_layers = int(num(az.get("layers_count"), 1))
        layers = []
        for i in range(1, n_layers + 1):
            lay = cfg.get("layer_%d" % i, {})
            names = csv(lay.get("artefacts") or az.get("artefacts"))
            start = csv(lay.get("start_artefact") or az.get("start_artefact"))
            picks = collections.Counter()
            nothing = 0.0
            for g in names:
                members = groups.get(g)
                if not members:
                    nothing += 1.0 / len(names)
                    continue
                for a in members:
                    picks[a] += 1.0 / len(names) / len(members)
            layers.append({
                "groups": names,
                "unregistered": [g for g in names if g not in groups],
                "start_artefact": start,
                "max_artefacts": num(lay.get("max_artefacts") or az.get("max_artefacts"), 1),
                "respawn_tries": num(lay.get("respawn_tries") or lay.get("artefact_count")
                                     or az.get("respawn_tries"), 1),
                "picks": dict(sorted(picks.items())),
                "nothing": nothing,
            })
        out.append({"file": rel, "folder": p[2], "level": FIELD_LEVELS.get(p[2]),
                    "layer": vfs.files[rel][0], "layers": layers})
    return out


def dao(svfs, S):
    """drx_da_main_artefacts.script run under LuaJIT 2.0 over these configs"""
    from lua_jit import L
    text, layer = svfs.read("scripts\\drx_da_main_artefacts.script")
    if text is None:
        return None
    lua = L.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    names = sorted(S)

    def section_for_each(_self, fn):
        for s in names:
            fn(s)

    def sys_get_param(typ, sec, key, default=None):
        v = (S.get(sec) or {}).get(key)
        if v is None:
            return default
        if typ == 1:
            return v.lower() in ("true", "1", "on", "yes")
        if typ == 2:
            return num(v, default)
        return v

    g.ini_sys = lua.table_from({"section_for_each": section_for_each})
    g.SYS_GetParam = sys_get_param
    lua.execute(text)

    def tolist(t):
        return [t[i] for i in range(1, len(t) + 1)] if t is not None else []

    tiers = {}
    for lvl, lst in g.artefacts_map_tiers.items():
        tiers[lvl] = tolist(lst)
    chances = dict(g.artefacts_map_chances.items()) if g.artefacts_map_chances else {}
    by_type = {}
    for k, v in (g.anomaly_type_to_artefacts or {}).items():
        by_type[k] = sorted(dict(v.items()))
    return {"layer": layer, "allowed": sorted(tolist(g.allowed_artefacts)), "chances": chances,
            "tiers": tiers, "by_anomaly_type": by_type}


def dao_settings():
    """Dynamic Anomalies' artifact settings from the player's MCM file, if it sets them"""
    path = os.path.join(os.environ.get("ALMANAC_ANOMALY", r"D:\ANOMALY"), "appdata", "axr_options.ltx")
    out = {}
    try:
        with open(path, encoding="cp1251", errors="replace") as f:
            for line in f:
                m = re.match(r"\s*(drx_da\w*/\w*artefact\w*)\s*=\s*(\S+)", line)
                if m:
                    out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def trade_stock(vfs, targets):
    """target -> [{file, layer, kind: "sold" or "bought", sections}] from every trader config
    (configs\\items\\trade\\, presets left out) as ini_file reads it: its supplies_N sections are
    the stock by supply level, trade_generic_buy what it buys"""
    out = collections.defaultdict(list)
    for rel in sorted(vfs.files):
        if not (rel.startswith("configs\\items\\trade\\") and rel.endswith(".ltx")) or "\\presets\\" in rel:
            continue
        if rel.rsplit("\\", 1)[-1].startswith("mod_"):
            continue
        cfg = ini(vfs, rel)
        found = collections.defaultdict(lambda: collections.defaultdict(list))
        for sec, keys in cfg.items():
            if re.match(r"^supplies_\d+$", sec):
                for k in keys:
                    if k in targets:
                        found[k]["sold"].append(sec)
            elif sec == "trade_generic_buy":
                for k in keys:
                    if k in targets:
                        found[k]["bought"].append(sec)
        for t, kinds in found.items():
            for kind, secs in kinds.items():
                out[t].append({"file": rel, "layer": vfs.files[rel][0], "kind": kind, "sections": sorted(secs)})
    return out


# config kinds for the mentions map, first match wins
MENTION_KINDS = [
    ("death drops", r"^configs\\items\\settings\\death_"),
    ("stash", r"treasure|stash"),
    ("task", r"^configs\\misc\\task\\|^configs\\items\\settings\\fetch_list\.ltx$"),
    ("loadout", r"loadout|new_game"),
    ("craft", r"craft|recipe|parts\.ltx$|disassembly"),
    ("story logic", r"^configs\\scripts\\"),
    ("guide", r"encyclopedia"),
]
# configs that define or tag items, or name them for other reasons, rather than hand them out
MENTION_SKIP = re.compile(
    r"^configs\\(text|ui|items\\items|items\\trade|prefetch|models|zones|mp|creatures|ai_tweaks)\\|"
    r"^configs\\scripts\\[^\\]+\\anomaly\\|^configs\\items\\settings\\(artefacts|craft|grok_items_tier|"
    r"arty_container)\.ltx$|^configs\\plugins\\(aysd|spawner_blacklist)\.ltx$|^configs\\scripts\\rf_sources\\|"
    r"dotmarks|^configs\\mod_system_|^configs\\system\.ltx$")
# scripts that name artifacts in their own tables (spawn filters, perks, detector icons, the
# despawner), so a mention there hands nothing out
SCRIPT_SKIP = re.compile(r"^scripts\\(drx_da_main_artefacts|perk_based_artefacts|grok_artefacts_bip|"
                         r"grok_artefact_despawner|debug_cmd_list|ui_debug_\w+|_g)\.script$")


# death_manager's sections that cap or keep what a body already carries, so hand nothing out
DROP_RULES = {"item_count", "keep_items", "keep_one", "weapon_drop_condition", "outfit_drop_condition"}
# mention kinds that hand an item out, and those that may give it or only want it
SOURCE_KINDS = ("sold", "death drops", "stash", "loadout")
CHECK_KINDS = ("task", "story logic", "script", "other")


def mentions(vfs, svfs, targets):
    """target -> [{file, layer, kind, sections or lines}]: the trader stock, then every other
    winning config that names it as a word (with the sections it sits in), then every script
    that names it as a quoted string"""
    out = trade_stock(vfs, targets)
    alt = "|".join(sorted(map(re.escape, targets), key=len, reverse=True))
    word = re.compile(r"(?<![\w])(%s)(?![\w])" % alt)
    quoted = re.compile(r"[\"'](%s)[\"']" % alt)
    for rel in sorted(vfs.files):
        if not rel.endswith(".ltx") or MENTION_SKIP.search(rel):
            continue
        text, layer = vfs.read(rel)
        hits = collections.defaultdict(set)
        sec = None
        for line in (text or "").splitlines():
            code = gamecfg.xt(line.split(";")[0].split("//")[0])
            h = re.match(r"^!*@?\[([^\]]+)\]", code)
            if h:
                sec = h.group(1).lower()
                code = code[h.end():]
            for m in word.finditer(code):
                hits[m.group(1)].add(sec or "")
        kind = next((k for k, pat in MENTION_KINDS if re.search(pat, rel)), "other")
        for t, secs in hits.items():
            k = "drop rules" if kind == "death drops" and secs <= DROP_RULES else kind
            out[t].append({"file": rel, "layer": layer, "kind": k, "sections": sorted(secs)})
    for rel in sorted(svfs.files):
        if not rel.endswith(".script") or SCRIPT_SKIP.search(rel):
            continue
        text, layer = svfs.read(rel)
        hits = collections.defaultdict(list)
        for n, line in enumerate((text or "").splitlines(), 1):
            for m in quoted.finditer(line.split("--")[0]):
                hits[m.group(1)].append(n)
        for t, ns in hits.items():
            out[t].append({"file": rel, "layer": layer, "kind": "script", "lines": ns})
    return out


# ---------------------------------------------------------------------------------------------
# the census


def build():
    vfs, S = gamecfg.system()
    svfs = gamecfg.VFS("scripts")
    eng, rus = strings(vfs, "eng"), strings(vfs, "rus")

    def kind(sec):
        return (S.get(sec) or {}).get("kind")

    def name(sec, table):
        key = (S.get(sec) or {}).get("inv_name")
        return table.get(key, key) if key else None

    arts = sorted(s for s, v in S.items() if v.get("kind") in KINDS)
    containers = collections.defaultdict(list)
    for s, v in S.items():
        if v.get("kind") == "i_arty_cont":
            held = s
            for suf in CONTAINER_SUFFIXES:
                if s.endswith(suf):
                    held = s[: -len(suf)]
                    break
            containers[held].append(s)

    utils_ui, utils_layer = svfs.read("scripts\\utils_ui.script")
    rows = card_rows(utils_ui or "")
    pba, pba_layer = svfs.read("scripts\\perk_based_artefacts.script")
    perks = perk_hooks(pba or "")
    enc_cfg = ini(vfs, "configs\\plugins\\encyclopedia.ltx")
    enc = encyclopedia_list(enc_cfg)
    dets = detector_lists(S)

    craft = ini(vfs, "configs\\items\\settings\\craft.ltx")
    recs, skipped = recipes(craft, S)
    art_recs = [r for r in recs if kind(r["result"]) in KINDS or any(kind(p) in KINDS for p, _ in r["parts"])]
    by_result = collections.defaultdict(list)
    for r in art_recs:
        if kind(r["result"]) in KINDS:
            by_result[r["result"]].append(r)
    used_in = collections.defaultdict(list)
    for r in art_recs:
        for p, n in r["parts"]:
            if kind(p) in KINDS:
                used_in[p].append(r["key"])

    acfg = ini(vfs, "configs\\items\\settings\\artefacts.ltx")
    groups = {}
    for g in lines(acfg.get("artefact_groups")):
        if g in acfg:
            groups[g] = [a for a in lines(acfg[g]) if a in S]
    defined_groups = sorted(s for s in acfg if s not in ("settings", "artefact_groups"))
    fields = field_configs(vfs, groups, S)
    game = ini(vfs, "configs\\game.ltx")
    outdoor = sorted(s for s, v in game.items() if v.get("weathers") and v.get("weathers") != "indoor")
    diff = ini(vfs, "configs\\plugins\\difficulty.ltx")
    arty_chance = {s: num(v["arty_chance"]) for s, v in diff.items() if "arty_chance" in v}
    d = dao(svfs, S)

    targets = set(arts) | {MELTER} | {r["book"] for r in art_recs}
    ment = mentions(vfs, svfs, targets)

    # per artifact: where the Zone makes it
    field_by_art = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in fields:
        for li, lay in enumerate(f["layers"], 1):
            for a, p in lay["picks"].items():
                field_by_art[a][f["level"] or f["folder"]].append(round(p, 4))
    dao_by_art = collections.defaultdict(dict)
    if d:
        allowed = set(d["allowed"])
        for lvl, lst in d["tiers"].items():
            ok = [a for a in lst if a in allowed]
            for a in set(ok):
                dao_by_art[a][lvl] = round(ok.count(a) / len(ok), 4)

    out_arts = {}
    for a in arts:
        v = S[a]
        absorb = S.get(v.get("hit_absorbation_sect") or "", {})
        card = {}
        for key, row in sorted(rows.items(), key=lambda kv: kv[1]["index"]):
            if row["functor"]:
                continue
            raw = num((absorb if row["section"] else v).get(key), 0.0)
            if raw:
                card[key] = {"raw": raw, "shown": round(raw * row["magnitude"], 2), "unit": row["unit"]}
        tree = expand(a, by_result, kind)
        out_arts[a] = {
            "kind": v.get("kind"),
            "name": name(a, eng), "name_rus": name(a, rus),
            "tier": num(v.get("tier")), "af_rank": num(v.get("af_rank")),
            "cost": num(v.get("cost")), "weight": num(v.get("inv_weight")),
            "belt": v.get("belt") == "true", "quest_item": v.get("quest_item") == "true",
            "story_id": v.get("story_id"),
            "card": card,
            "caps": {k: num(x) for k, x in sorted(v.items()) if k.endswith("_cap")},
            "jump_height": num(v.get("jump_height")),
            "containers": sorted(containers.get(a, [])),
            "perk": perks.get(a) and dict(perks[a]),
            "guide": a in enc,
            "detectors": sorted(dn for dn, dd in dets.items() if a in dd["list"]),
            "fields": {lvl: ps for lvl, ps in sorted(field_by_art[a].items())},
            "dao": dict(sorted(dao_by_art[a].items())),
            "dao_random": bool(d and a in d["allowed"]),
            "made_by": [r["key"] for r in by_result.get(a, [])],
            "used_in": used_in.get(a, []),
            "tree": None if not by_result.get(a) else {
                "crafts": tree["crafts"], "books": sorted(tree["books"]),
                "artifacts": dict(sorted(tree["artifacts"].items())),
                "junk": sum(n for x, n in tree["artifacts"].items() if kind(x) == "i_arty_junk"),
                "parts": dict(sorted(tree["parts"].items())),
                "part_count": sum(tree["parts"].values()),
            },
            "mentions": ment.get(a, []),
        }

    # how each turns up: the spawners and the workshop, then configs that hand it out; tasks,
    # story logic and scripts may give it or only ask for it, so they are left to the source map
    for a, rec in out_arts.items():
        ways = []
        if rec["fields"]:
            ways.append("fields")
        if rec["dao"]:
            ways.append("dao list")
        elif rec["dao_random"]:
            ways.append("dao random pick")
        if rec["made_by"]:
            ways.append("craft")
        kinds = sorted({m["kind"] for m in rec["mentions"]})
        ways += [k for k in SOURCE_KINDS if k in kinds]
        rec["ways"] = ways
        rec["to_check"] = [k for k in CHECK_KINDS if k in kinds]

    return {
        "generated": datetime.date.today().isoformat(),
        "profile": gamecfg.MODLIST,
        "files": {
            "utils_ui.script": utils_layer, "perk_based_artefacts.script": pba_layer,
            "craft.ltx": vfs.files.get("configs\\items\\settings\\craft.ltx", (None,))[0],
            "artefacts.ltx": vfs.files.get("configs\\items\\settings\\artefacts.ltx", (None,))[0],
            "drx_da_main_artefacts.script": d and d["layer"],
        },
        "settings": {
            "arty_chance": arty_chance,
            "surge_chance": num((acfg.get("settings") or {}).get("surge_chance")),
            "psi_storm_chance": num((acfg.get("settings") or {}).get("psi_storm_chance")),
            "dao_mcm": dao_settings(),
            "outdoor_levels": outdoor,
        },
        "card_rows": rows,
        "artifacts": out_arts,
        "containers": {a: c for a, c in sorted(containers.items()) if a not in out_arts},
        "detectors": {k: {"name": name(k, eng), "count": len(v["list"]), "list": v["list"],
                          "listed_twice": v["listed_twice"], "ignored_after_gap": v["ignored_after_gap"]}
                      for k, v in sorted(dets.items())},
        "recipes": art_recs,
        "recipes_skipped": skipped,
        "books": {b: {"name": name(b, eng), "mentions": ment.get(b, [])}
                  for b in sorted({r["book"] for r in art_recs})},
        "melter": {"section": MELTER, "name": name(MELTER, eng), "mentions": ment.get(MELTER, [])},
        "groups": {"registered": groups, "defined_not_registered": [g for g in defined_groups if g not in groups]},
        "fields": fields,
        "dao": d,
    }


# ---------------------------------------------------------------------------------------------
# the report


def fmt_pct(p):
    return "%g%%" % round(100 * p, 1)


def report(c):
    A = c["artifacts"]
    out = []
    w = out.append
    w("# Artefact census, %s" % c["generated"])
    w("")
    w("Read from this install's configs after DLTX by `tools/census.py`; nothing was changed. "
      "Winning files: " + ", ".join("%s from %s" % (k, v) for k, v in c["files"].items()) + ".")
    w("")
    kinds = collections.Counter(a["kind"] for a in A.values())
    w("## Counts")
    w("")
    w("- %d artifacts (`i_arty`) and %d junk artifacts (`i_arty_junk`); %d containers fold into them."
      % (kinds["i_arty"], kinds["i_arty_junk"], sum(len(a["containers"]) for a in A.values())))
    by_tier = collections.Counter((a["kind"], a["tier"]) for a in A.values())
    w("- By tier: " + ", ".join("%s %s: %d" % ("junk" if k == "i_arty_junk" else "artifact",
                                              "none" if t is None else "%g" % t, n)
                               for (k, t), n in sorted(by_tier.items(), key=lambda x: (x[0][0], x[0][1] or 0))))
    w("- Detectors (af_class lines read to the first gap): " + ", ".join(
        "%s (%s) %d" % (k, v["name"], v["count"]) for k, v in c["detectors"].items()))
    nodet = sorted(a for a, r in A.items() if not r["detectors"])
    w("- On no detector's list (%d): %s" % (len(nodet), ", ".join(nodet)))
    w("- In the PDA Guide: %d." % sum(1 for a in A.values() if a["guide"]))
    w("- With a Perk-Based Artefacts hook: %d." % sum(1 for a in A.values() if a["perk"]))
    w("")
    w("## How the Zone makes them")
    w("")
    s = c["settings"]
    w("- Fields: arty_chance per economy setting %s, x%s after an emission, x%s after a psi storm."
      % (", ".join("%s %g" % kv for kv in sorted(s["arty_chance"].items())), s["surge_chance"], s["psi_storm_chance"]))
    reg = c["groups"]["registered"]
    w("- Registered groups (%d): %s." % (len(reg), ", ".join("%s (%d)" % (g, len(m)) for g, m in reg.items())))
    w("- Groups defined but not registered: %s." % ", ".join(c["groups"]["defined_not_registered"]))
    picks = sum(len(l["groups"]) for f in c["fields"] for l in f["layers"])
    dead = sum(len(l["unregistered"]) for f in c["fields"] for l in f["layers"])
    w("- %d field configs, %d group entries, %d of them unregistered (a pick that spawns nothing)."
      % (len(c["fields"]), picks, dead))
    if c["dao"]:
        w("- Dynamic Anomalies: %d levels with a list, %d artifacts its random pick allows; MCM: %s."
          % (len(c["dao"]["tiers"]), len(c["dao"]["allowed"]), s["dao_mcm"] or "not set (defaults)"))
    w("")
    w("### By level")
    w("")
    w("| Level | Fields | Field artifacts | Picks that spawn nothing | DAO chance | DAO list |")
    w("|---|---|---|---|---|---|")
    levels = collections.OrderedDict()
    for f in c["fields"]:
        levels.setdefault(f["level"] or f["folder"], []).append(f)
    for lvl in sorted(set(levels) | set((c["dao"] or {}).get("tiers", {}))):
        fs = levels.get(lvl, [])
        fa = sorted({a for f in fs for l in f["layers"] for a in l["picks"]})
        nothing = [l["nothing"] for f in fs for l in f["layers"]]
        dl = (c["dao"] or {}).get("tiers", {}).get(lvl, [])
        w("| %s | %d | %s | %s | %s | %s |" % (
            lvl, len(fs), ", ".join(fa) or "-",
            ("%s on average" % fmt_pct(sum(nothing) / len(nothing))) if nothing else "-",
            (c["dao"] or {}).get("chances", {}).get(lvl, "-"),
            ("%d entries, %d kinds" % (len(dl), len(set(dl)))) if dl else "-"))
    w("")
    w("## Crafting")
    w("")
    books = collections.Counter(r["book"] for r in c["recipes"] if c["artifacts"].get(r["result"]))
    w("- %d recipes make an artifact (%s); %d more use one as an ingredient; %d lines skipped."
      % (sum(books.values()), ", ".join("%s %d" % kv for kv in sorted(books.items())),
         sum(1 for r in c["recipes"] if not c["artifacts"].get(r["result"])), len(c["recipes_skipped"])))
    w("")
    w("| Artifact | Tier | Book | Crafts | Junk | Artifacts at the bottom | Mutant parts |")
    w("|---|---|---|---|---|---|---|")
    for a, r in sorted(A.items(), key=lambda kv: (-(kv[1]["tree"] or {}).get("crafts", 0), kv[0])):
        t = r["tree"]
        if not t:
            continue
        w("| %s (%s) | %s | %s | %d | %d | %d | %d |" % (
            r["name"], a, "%g" % r["tier"] if r["tier"] is not None else "-",
            next(rr["book"] for rr in c["recipes"] if rr["result"] == a), t["crafts"], t["junk"],
            sum(t["artifacts"].values()), t["part_count"]))
    w("")
    w("## Books and the Melter")
    w("")
    for b, rec in list(c["books"].items()) + [(c["melter"]["section"], c["melter"])]:
        w("- **%s** (%s): %s" % (rec["name"], b, "; ".join(
            "%s `%s` (%s)" % (m["kind"], m["file"], m["layer"]) for m in rec["mentions"]) or "no mention"))
    w("")
    w("## Turning up")
    w("")
    w("Ways: fields, Dynamic Anomalies (its level lists or its random pick), the workshop, a "
      "trader's stock, death drops, stashes, new-game loadouts. Tasks, story logic and scripts "
      "may give an artifact or only ask for one, so they are listed to check.")
    w("")
    w("| Artifact | Kind | Tier | Ways | To check | Detectors |")
    w("|---|---|---|---|---|---|")
    for a, r in sorted(A.items(), key=lambda kv: (bool(kv[1]["ways"]), kv[0])):
        w("| %s (%s) | %s | %s | %s | %s | %d |" % (
            r["name"], a, "junk" if r["kind"] == "i_arty_junk" else "artifact",
            "%g" % r["tier"] if r["tier"] is not None else "-", ", ".join(r["ways"]) or "**none**",
            ", ".join(r["to_check"]) or "-", len(r["detectors"])))
    w("")
    w("### Source map for those with no way")
    w("")
    for a, r in sorted(A.items()):
        if r["ways"]:
            continue
        ms = [m for m in r["mentions"] if m["kind"] in CHECK_KINDS]
        w("- **%s** (%s): %s" % (r["name"], a, "; ".join(
            "%s `%s`%s" % (m["kind"], m["file"].split("\\", 1)[1],
                           (" [%s]" % ", ".join(m["sections"])) if m.get("sections") else
                           (" :%s" % ",".join(map(str, m["lines"][:5]))) if m.get("lines") else "")
            for m in ms) or "no mention outside the files that define it"))
    w("")
    return "\n".join(out) + "\n"


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        gamecfg.GAMMA, "_baseline", "artefact-almanac-thread", "census-" + datetime.date.today().isoformat())
    c = build()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "census.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(c, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(out_dir, "CENSUS.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report(c))
    print("census: %d artifacts, %d recipes, %d field configs -> %s"
          % (len(c["artifacts"]), len(c["recipes"]), len(c["fields"]), out_dir))


if __name__ == "__main__":
    main()
