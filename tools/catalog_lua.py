"""Run almanac_data.script and almanac_trees.script under LuaJIT 2.0 over an install's configs, as
the game would hand them to them, and compare the catalog and every artifact's tree totals with
census.py's reading of the same install.

The game's calls the scripts make are served from gamecfg's reading of the install: ini_sys and
SYS_GetParam from system.ltx, ini_file from each file with its DLTX, the string tables for
game.translate_string, an alife with a zone per field config on its folder's level, and the
install's own Dynamic Anomalies script run as its module. Paths come from the ALMANAC_* settings
(see gamecfg.py).

    python -I catalog_lua.py              compare on the install the settings name; prints a JSON
                                          summary, exit 1 on any difference
    ALMANAC_DATA_SCRIPT=<path>            run another copy of almanac_data.script (the tests' mutants)
    ALMANAC_TREES_SCRIPT=<path>           the same for almanac_trees.script
    ALMANAC_TRADERS=<path>                another trader map than the repo's almanac_traders.ltx
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census  # noqa: E402
import gamecfg  # noqa: E402
from lua_jit import L  # noqa: E402

SCRIPT = os.environ.get("ALMANAC_DATA_SCRIPT",
                        os.path.join(HERE, "..", "gamedata", "scripts", "almanac_data.script"))
TREES = os.environ.get("ALMANAC_TREES_SCRIPT",
                       os.path.join(HERE, "..", "gamedata", "scripts", "almanac_trees.script"))
TRADERS = os.environ.get("ALMANAC_TRADERS",
                         os.path.join(HERE, "..", "gamedata", "configs", "plugins", "almanac_traders.ltx"))

STUBS = r"""
LOG = {}
function printf(fmt, ...)
    local p, i = { ... }, 0
    fmt = string.gsub(tostring(fmt), "%%s", function() i = i + 1 return tostring(p[i]) end)
    LOG[#LOG + 1] = fmt
end
function wrap_ini(h)
    return {
        section_exist = function(_, s) return h.section_exist(s) end,
        line_exist = function(_, s, k) return h.line_exist(s, k) end,
        line_count = function(_, s) return h.line_count(s) end,
        r_line_ex = function(_, s, i) return h.r_line_ex(s, i) end,
        r_string_ex = function(_, s, k) return h.r_string_ex(s, k) end,
        r_float_ex = function(_, s, k) return tonumber(h.r_string_ex(s, k)) end,
        section_for_each = function(_, fn) local names = h.sections() for i = 1, #names do fn(names[i]) end end,
    }
end
-- the alife as the catalog sees it: every field config on a zone of its own, on its level, plus a
-- second zone sharing the first one's config (counted once), an object with no [anomal_zone] and
-- one whose spawn_ini throws
function make_world(zones)
    local objects, levels, vertex = {}, {}, {}
    local function zone_ini(cfg)
        return { section_exist = function(_, s) return s == "anomal_zone" end,
                 r_string_ex = function(_, s, k) return (s == "anomal_zone" and k == "cfg") and cfg or nil end }
    end
    for i = 1, #zones do
        local path, lvl = zones[i][1], zones[i][2]
        if not levels[lvl] then
            levels[lvl] = #vertex + 1
            vertex[#vertex + 1] = lvl
        end
        local gv = levels[lvl]
        objects[100 + i] = { m_game_vertex_id = gv, spawn_ini = function() return zone_ini(path) end }
    end
    if #zones > 0 then
        objects[99] = { m_game_vertex_id = levels[zones[1][2]], spawn_ini = function() return zone_ini(string.upper(zones[1][1])) end }
    end
    objects[5] = { m_game_vertex_id = 1, spawn_ini = function() return { section_exist = function() return false end } end }
    objects[6] = { m_game_vertex_id = 1, spawn_ini = function() error("no spawn ini here") end }
    alife = function()
        return { object = function(_, id) return objects[id] end, level_name = function(_, l) return vertex[l] end }
    end
    game_graph = function()
        return { vertex = function(_, gv) return { level_id = function() return gv end } end }
    end
end
function run_module(text, name)
    local env = setmetatable({}, { __index = _G })
    local f = assert(loadstring(text, name))
    setfenv(f, env)
    f()
    return env
end
"""


class Ini:
    """one config as ini_file hands it to a script: sections, keys in the engine's sorted order"""

    def __init__(self, data):
        self.data = data
        self.order = {s: census.lines(v) for s, v in data.items()}

    def section_exist(self, s):
        return s in self.data

    def line_exist(self, s, k):
        return k in self.data.get(s, {})

    def line_count(self, s):
        return len(self.order.get(s, []))

    def r_line_ex(self, s, i):
        k = self.order[s][i]
        v = self.data[s][k]
        return True, k, "" if v is None else v

    def r_string_ex(self, s, k):
        return self.data.get(s, {}).get(k)

    def sections(self):
        return self._names

    def with_names(self, lua):
        self._names = lua.table_from(sorted(self.data))
        return self


def plain_ini(path):
    """a plain config file (no includes, no DLTX): section -> key -> value"""
    data, sec = {}, None
    for line in open(path, encoding="cp1251").read().splitlines():
        line = line.split(";")[0].strip()
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            sec = data.setdefault(m.group(1).lower(), {})
        elif sec is not None and "=" in line:
            k, v = line.split("=", 1)
            sec[k.strip()] = v.strip()
    return data


def named_traders():
    """the trade config stems the trader map gives a named trader"""
    return {k for k, v in plain_ini(TRADERS).get("almanac_trade", {}).items() if v and v != "-"}


def lua_catalog():
    vfs, S = gamecfg.system()
    svfs = gamecfg.VFS("scripts")
    eng = census.strings(vfs, "eng")
    lua = L.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    lua.execute(STUBS)
    sysini = Ini(S).with_names(lua)
    g.ini_sys = g.wrap_ini(sysini)
    cache = {}

    def ini_file(path):
        rel = "configs\\" + path.replace("/", "\\").lower()
        if rel not in cache:
            # the trader map is the Almanac's own: the repo's copy, not the install's
            data = plain_ini(TRADERS) if rel == "configs\\plugins\\almanac_traders.ltx" else census.ini(vfs, rel)
            cache[rel] = g.wrap_ini(Ini(data).with_names(lua))
        return cache[rel]

    def sys_get_param(typ, sec, key, default=None):
        v = (S.get(sec) or {}).get(key)
        if v is None:
            return default
        if typ == 1:
            return v.lower() in ("true", "1", "on", "yes")
        if typ == 2:
            return census.num(v, default)
        return v

    g.ini_file = ini_file
    g.SYS_GetParam = sys_get_param
    g.game = lua.table_from({"translate_string": lambda s: eng.get(s, s)})
    zones = []
    for rel in sorted(vfs.files):
        p = rel.split("\\")
        if len(p) == 5 and p[1] == "scripts" and p[3] == "anomaly" and p[4].endswith(".ltx"):
            zones.append(lua.table_from(["\\".join(p[1:]), census.FIELD_LEVELS.get(p[2], p[2])]))
    g.make_world(lua.table_from(zones))
    g.itms_manager = lua.table_from({"ini_craft": ini_file("items\\settings\\craft.ltx"),
                                     "ini_death": ini_file("items\\settings\\death_generic.ltx")})
    g.task_manager = lua.table_from({"task_ini": ini_file("misc\\task\\task_manager.ltx")})
    text, _ = svfs.read("scripts\\drx_da_main_artefacts.script")
    if text is not None:
        g.drx_da_main_artefacts = g.run_module(text, "drx_da_main_artefacts")
    src = open(SCRIPT, encoding="utf-8").read()
    mod = g.run_module(src, "almanac_data")
    g.almanac_data = mod
    trees = g.run_module(open(TREES, encoding="utf-8").read(), "almanac_trees")
    C = mod.catalog()
    return C, list(g.LOG.values()), trees


def tree_plain(t):
    """almanac_trees.totals' table in census.py's terms (None when nothing makes the artifact)"""
    if t is None:
        return None
    return {"crafts": t.crafts, "books": sorted(t.books.keys()),
            "artifacts": dict(sorted(t.artifacts.items())), "junk": t.junk,
            "parts": dict(sorted(t.parts.items())), "part_count": t.part_count}


def plain(C, trees):
    """the Lua catalog in the census's terms, for comparing"""
    def lst(t):
        return [t[i] for i in range(1, len(t) + 1)] if t is not None else []

    arts = {}
    for sec, a in C.artifacts.items():
        arts[sec] = {
            "tree": tree_plain(trees.totals(sec, False, C)),
            "kind": a.kind, "name": a.name, "tier": a.tier,
            "containers": sorted(lst(a.containers)),
            "detectors": sorted(lst(a.detectors)),
            "made_by": sorted(lst(a.made_by)), "used_in": sorted(lst(a.used_in)),
            "fields": {lvl: sorted(round(p, 4) for p in lst(ps)) for lvl, ps in a.fields.items()},
            "dao": {lvl: round(s, 4) for lvl, s in a.dao.items()},
            "dao_random": bool(a.dao_random),
        }
    groups = {gname: lst(m) for gname, m in C.groups.items()}
    recipes = sorted(r.key for r in C.recipes.values())
    sources = {item: {"sold": sorted("configs\\" + f for f in lst(s.files)), "carried": len(lst(s.drops)) > 0}
               for item, s in C.sources.items()}
    return {"artifacts": arts, "groups": groups, "recipes": recipes, "fields": len(lst(C.fields)),
            "detectors": {d: lst(v) for d, v in C.detectors.items()}, "failed": lst(C.failed),
            "sources": sources, "wanted": sorted(C.wanted.arts.keys())}


def expected(c):
    """census.py's answers in the same terms"""
    arts = {}
    for sec, a in c["artifacts"].items():
        arts[sec] = {
            "kind": a["kind"], "name": a["name"], "tier": a["tier"],
            "containers": sorted(a["containers"]), "detectors": sorted(a["detectors"]),
            "made_by": sorted(a["made_by"]), "used_in": sorted(a["used_in"]),
            "fields": {lvl: sorted(ps) for lvl, ps in a["fields"].items()},
            "dao": a["dao"], "dao_random": a["dao_random"],
            "tree": a["tree"],
        }
    # the books that are items, and the Melter: the trade configs that stock one, and whether a
    # death list (not just its [item_count]) hands one out
    books = {b: r for b, r in c["books"].items() if r["name"] is not None}
    books[c["melter"]["section"]] = c["melter"]
    used = named_traders()
    sources = {b: {"sold": sorted(m["file"] for m in r["mentions"] if m["kind"] == "sold"
                                  and m["file"].rsplit("\\", 1)[1][:-4] in used),
                   "carried": any(m["kind"] == "death drops" for m in r["mentions"])
                   and any("item_count" in (m.get("sections") or []) for m in r["mentions"])}
               for b, r in books.items()}
    wanted = sorted(sec for sec, a in c["artifacts"].items()
                    if any(m["kind"] == "task" and m["file"] == "configs\\items\\settings\\fetch_list.ltx"
                           for m in a["mentions"]))
    return {"artifacts": arts, "groups": c["groups"]["registered"],
            "recipes": sorted(r["key"] for r in c["recipes"]), "fields": len(c["fields"]),
            "detectors": {d: v["list"] for d, v in c["detectors"].items()}, "failed": [],
            "sources": sources, "wanted": wanted}


def compare(got, want):
    diffs, n = [], 0
    for key in ("groups", "recipes", "fields", "detectors", "failed", "sources", "wanted"):
        n += 1
        if got[key] != want[key]:
            diffs.append("%s: lua %r, census %r" % (key, got[key], want[key]))
    ga, wa = got["artifacts"], want["artifacts"]
    n += 1
    if sorted(ga) != sorted(wa):
        diffs.append("artifacts: only lua %s, only census %s" % (sorted(set(ga) - set(wa)), sorted(set(wa) - set(ga))))
    for sec in sorted(set(ga) & set(wa)):
        for field in wa[sec]:
            n += 1
            if ga[sec].get(field) != wa[sec][field]:
                diffs.append("%s.%s: lua %r, census %r" % (sec, field, ga[sec].get(field), wa[sec][field]))
    return diffs, n


def stale_traders():
    """the repo's trader map against traders.py's reading of this install: the stems that differ"""
    import traders
    vfs, S = gamecfg.system()
    fresh = {k: ", ".join(v) or "-" for k, v in traders.trade_map(vfs, S).items()}
    kept = plain_ini(TRADERS).get("almanac_trade", {})
    return sorted(k for k in set(fresh) | set(kept) if fresh.get(k) != kept.get(k))


def main():
    C, log, trees = lua_catalog()
    got = plain(C, trees)
    want = expected(census.build())
    diffs, n = compare(got, want)
    # the repo's trader map, unless a test hands its own, is the one traders.py writes today
    if "ALMANAC_TRADERS" not in os.environ:
        n += 1
        stale = stale_traders()
        if stale:
            diffs.append("almanac_traders.ltx is stale (rerun tools/traders.py): %s" % ", ".join(stale))
    W = C.wanted
    sources = {item: {"sellers": sorted(s.sellers.keys()),
                      "drops": [[d.comm, d.rank, d.chance] for d in (s.drops[i] for i in range(1, len(s.drops) + 1))]}
               for item, s in C.sources.items()}
    print(json.dumps({"compared": n, "differences": diffs[:40], "n_differences": len(diffs),
                      "artifacts": len(got["artifacts"]), "recipes": len(got["recipes"]),
                      "fields": got["fields"], "log": [x for x in log if "almanac-data" in x],
                      "sources": sources, "wanted": got["wanted"], "wanted_tasks": W.tasks,
                      "wanted_factions": sorted(W.factions.keys()), "wanted_givers": sorted(W.givers.keys())},
                     indent=1))
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
