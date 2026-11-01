"""Run almanac_census.script under LuaJIT 2.0 against a small made-up alife and check what it writes.

The world: artifacts lying free on two levels (one Dynamic Anomalies tracks, one a field spawned,
some the despawner saw days ago), artifacts the player, a stalker, a box and a mutant own, one
whose owner is gone, a container and a non-artifact, and m_data's levels due a roll. Checked: the
counts per level, owners, sections, sources and ages, the due list, the JSON (it parses, keys
sorted, strings escaped), the summary line, the schedule (the waits after a load and a storm,
each census once, other interactions ignored), and that an error or an unwritable log stays
inside the census.

    python test_ingame_census.py            the real script
    python test_ingame_census.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_census.script")

#: name -> (text in the script, its broken replacement); each must make this test fail
MUTANTS = {
    "free_is_owned": ("if pid == nil or pid >= 65535 then", "if pid == nil then"),
    "actor_owner": ("    if pid == AC_ID then\n", "    if false then\n"),
    "gone_owner": ('    if not p then\n        return "other"', '    if not p then\n        return nil'),
    "box_owner": ("    if IsInvbox(p) then\n", "    if false then\n"),
    "kinds": ("            if KINDS[kind] then\n", "            if true then\n"),
    "source": ('add(e.by, dao[id] and "dao" or fields[id] and "field" or "other")', 'add(e.by, "other")'),
    "age_days": ("local days = sec / 86400", "local days = sec / 3600"),
    "due_any": ("            if yes then\n", "            if true then\n"),
    "due_sorted": ("    table.sort(c.due)\n", ""),
    "no_wait": ("AFTER_LOAD_MS = 45000", "AFTER_LOAD_MS = 0"),
    "storm_wait": ('queue("emission", AFTER_STORM_MS)', 'queue("emission", 0)'),
    "psi": ('    elseif name == "psi_storm_end" then\n', '    elseif false then\n'),
    "any_interaction": ('    if typ ~= "anomalies" then\n', '    if false then\n'),
    "every_update": ("            table.remove(pending, i)\n            run(p.cause)\n",
                     "            run(p.cause)\n            i = i + 1\n"),
    "overwrite": ('io.open(path(), "a")', 'io.open(path(), "w")'),
    "unguarded": ("            run(p.cause)\n        else", "            take(p.cause)\n        else"),
    "log_failure_stops": ('        local ok2, err2 = pcall(function()\n            local f = assert(io.open(path(), "a"))\n'
                          '            f:write(to_json(c), "\\n")\n            f:close()\n        end)\n',
                          '        local f = assert(io.open(path(), "a"))\n        f:write(to_json(c), "\\n")\n'
                          '        f:close()\n        local ok2, err2 = true, nil\n'),
    "quote": ("if ch == '\"' then return '\\\\\"' end", "if ch == '\"' then return '\"' end"),
    "unsorted": ("        table.sort(keys)\n", ""),
    "no_real": ('    c.real = os.date("%Y-%m-%d %H:%M:%S")\n', ""),
}

WORLD = r"""
LOG = {}
-- the game's printf: it fills %s only, through a function
function printf(fmt, ...)
    local p, i = { ... }, 0
    fmt = string.gsub(tostring(fmt), "%%s", function() i = i + 1 return tostring(p[i]) end)
    LOG[#LOG + 1] = fmt
end

AC_ID = 0
CLS = { arty = 1, stalker = 2, box = 3, monster = 4, item = 5, actor = 6 }
function IsArtefact(o) return o:clsid() == CLS.arty end
function IsStalker(o) return o:clsid() == CLS.stalker or o:clsid() == CLS.actor end
function IsInvbox(o) return o:clsid() == CLS.box end
function IsMonster(o) return o:clsid() == CLS.monster end
KIND = { af_medusa = "i_arty", af_soul = "i_arty", af_ear = "i_arty_junk", ['af_"odd"'] = "i_arty",
         af_medusa_lead_box = "i_arty_cont", wpn_pm = "weapon" }
function SYS_GetParam(_, sec, key, def) return key == "kind" and KIND[sec] or def end

OBJ = {}
LEVELS = { [1] = "l01_escape", [2] = "l02_garbage" }
GV_LEVEL = { [10] = 1, [20] = 2 }
BROKEN = false
function alife()
    if BROKEN then error("alife broke") end
    return { object = function(_, id) return OBJ[id] end, level_name = function(_, lid) return LEVELS[lid] end }
end
function game_graph()
    return { vertex = function(_, gv) return { level_id = function() return GV_LEVEL[gv] end } end }
end
-- game time in plain seconds; CTime:diffSec is the difference
NOW_SEC = 30 * 86400
function ctime(sec) return { sec = sec, diffSec = function(self, o) return self.sec - o.sec end,
                             get = function() return 2012, 5, 14, 8, 30, 0, 0 end } end
game = { get_game_time = function() return ctime(NOW_SEC) end }
level = { name = function() return "l01_escape" end }

local function obj(id, cls, sec, gv, parent)
    OBJ[id] = { id = id, cls = cls, sec = sec, m_game_vertex_id = gv, parent_id = parent or 65535,
                clsid = function(self) return self.cls end, section_name = function(self) return self.sec end }
end
obj(0, CLS.actor, "actor", 10)
obj(2, CLS.stalker, "stalker", 10)
obj(3, CLS.box, "box", 20)
obj(4, CLS.monster, "dog", 20)
-- free on Cordon: Dynamic Anomalies' (seen 6 days ago), a field's (seen half a day ago), an
-- unseen one, and one with an odd name
obj(100, CLS.arty, "af_medusa", 10)
obj(101, CLS.arty, "af_medusa", 10)
obj(102, CLS.arty, "af_ear", 10)
obj(103, CLS.arty, 'af_"odd"', 10)
-- free on Garbage, seen 2 and 4 days ago, the second with parent_id nil
obj(110, CLS.arty, "af_soul", 20)
obj(111, CLS.arty, "af_ear", 20, nil)
OBJ[111].parent_id = nil
-- owned: the player, a stalker, a box, a mutant, an owner the alife no longer has
obj(120, CLS.arty, "af_soul", 10, 0)
obj(121, CLS.arty, "af_soul", 10, 2)
obj(122, CLS.arty, "af_medusa", 20, 3)
obj(123, CLS.arty, "af_ear", 20, 4)
obj(124, CLS.arty, "af_ear", 20, 999)
-- not counted: a container (an artifact class here, kind i_arty_cont) and a gun
obj(130, CLS.arty, "af_medusa_lead_box", 10)
obj(131, CLS.item, "wpn_pm", 10)

drx_da_main = { updated_anomaly_levels = { l01_escape = { artefacts = { [100] = "af_medusa" } }, l02_garbage = {} } }
bind_anomaly_zone = { parent_zones_by_artefact_id = { [101] = {} } }
grok_artefact_despawner = {
    artefacts_spawned_time = { [100] = { sec = NOW_SEC - 6 * 86400 }, [101] = { sec = NOW_SEC - 43200 },
                               [110] = { sec = NOW_SEC - 2 * 86400 }, [111] = { sec = NOW_SEC - 4 * 86400 } },
    t2c = function(t) return ctime(t.sec) end,
}
M_DATA = { artefact_respawn_levels = { zaton = true, l02_garbage = true, jupiter = false } }
alife_storage_manager = { get_state = function() return M_DATA end }

NOW = 0
function time_global() return NOW end
CALLBACKS = {}
function RegisterScriptCallback(name, fn) CALLBACKS[name] = fn end
function getFS() return { update_path = function(_, root, file) return OUTDIR .. "/" .. file end } end
"""


def main():
    mutant = sys.argv[1] if len(sys.argv) > 1 else None
    src = open(SCRIPT, encoding="utf-8").read()
    if mutant:
        old, new = MUTANTS[mutant]
        if src.count(old) != 1:
            print("MUTANT %s: its text occurs %d times, not once" % (mutant, src.count(old)))
            sys.exit(3)
        src = src.replace(old, new)
    tmp = tempfile.mkdtemp(prefix="almanac_ingame_")
    fails = []
    n = [0]

    def eq(what, got, want):
        n[0] += 1
        if got != want:
            fails.append("%s: got %r, want %r" % (what, got, want))

    try:
        lua = L.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.OUTDIR = tmp.replace("\\", "/")
        lua.execute(WORLD)
        lua.execute(src)
        g.on_game_start()
        cb = g.CALLBACKS
        log_file = os.path.join(tmp, "almanac_census.jsonl")

        def lines():
            if not os.path.isfile(log_file):
                return []
            with open(log_file, encoding="utf-8") as f:
                return [json.loads(x) for x in f.read().splitlines()]

        def tick(ms):
            g.NOW = g.NOW + ms
            cb.actor_on_update(0)

        # a load: nothing until 45 s have passed, then one census, once
        cb.actor_on_first_update()
        tick(44000)
        eq("before the wait", len(lines()), 0)
        tick(1000)
        eq("after the wait", len(lines()), 1)
        tick(1000)
        tick(60000)
        eq("only once", len(lines()), 1)
        c = lines()[0]
        eq("cause", c["cause"], "load")
        eq("level", c["level"], "l01_escape")
        eq("date", c["date"], "2012-05-14 08:30")
        eq("real time stamped", bool(re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$", c.get("real", ""))), True)
        esc = c["levels"]["l01_escape"]
        gar = c["levels"]["l02_garbage"]
        eq("Cordon free", esc["free"], 4)
        eq("Cordon sections", esc["sections"], {"af_medusa": 2, "af_ear": 1, 'af_"odd"': 1})
        eq("Cordon sources", esc["by"], {"dao": 1, "field": 1, "other": 2})
        eq("Cordon ages", esc["ages"], {"5 days or more": 1, "under 1 day": 1, "unseen": 2})
        eq("Cordon owned", esc["owned"], {"actor": 1, "stalker": 1})
        eq("Garbage free", gar["free"], 2)
        eq("Garbage ages", gar["ages"], {"1-3 days": 1, "3-5 days": 1})
        eq("Garbage owned", gar["owned"], {"box": 1, "monster": 1, "other": 1})
        eq("kinds", c["kinds"], {"i_arty": 7, "i_arty_junk": 4})
        eq("due", c["due"], ["l02_garbage", "zaton"])
        with open(log_file, encoding="utf-8") as f:
            raw = f.read()
        eq("keys sorted", raw.index('"cause"') < raw.index('"date"') < raw.index('"levels"'), True)
        eq("escaped", '"af_\\"odd\\"":1' in raw, True)
        summ = [x for x in g.LOG.values() if x.startswith("[almanac-census]")]
        eq("summary", summ, ["[almanac-census] 2012-05-14 08:30 (load) on l01_escape: 4 free here, "
                             "2 free elsewhere, 5 owned, 2 levels due, %s ms" % c["ms"]])

        # an interaction that isn't the anomalies' starts nothing; an emission's end waits 30 s
        cb.actor_on_interaction("trade", None, "emission_end")
        cb.actor_on_interaction("anomalies", None, "emission_end")
        tick(29000)
        eq("emission before the wait", len(lines()), 1)
        tick(1000)
        eq("emission after the wait", [x["cause"] for x in lines()], ["load", "emission"])
        cb.actor_on_interaction("anomalies", None, "psi_storm_end")
        tick(30000)
        tick(30000)
        eq("psi storm", [x["cause"] for x in lines()], ["load", "emission", "psi storm"])

        # a census that breaks logs the error and the game's update goes on
        g.BROKEN = True
        cb.actor_on_interaction("anomalies", None, "emission_end")
        try:
            tick(30000)
            eq("an error stays inside", any(x.startswith("! [almanac-census] ") and "alife broke" in x
                                            for x in g.LOG.values()), True)
        except Exception as e:
            fails.append("an error escaped the census: %s" % str(e).splitlines()[0])
        g.BROKEN = False
        eq("no line for a broken census", len(lines()), 3)

        # a log that can't be written still gives the summary line
        g.OUTDIR = os.path.join(tmp, "no", "such", "dir").replace("\\", "/")
        before = len([x for x in g.LOG.values() if x.startswith("[almanac-census]")])
        cb.actor_on_interaction("anomalies", None, "emission_end")
        try:
            tick(30000)
        except Exception as e:
            fails.append("an unwritable log broke the update: %s" % str(e).splitlines()[0])
        after = len([x for x in g.LOG.values() if x.startswith("[almanac-census]")])
        eq("summary despite the log", after - before, 1)
        eq("the log failure is logged", any(x.startswith("! [almanac-census] the log:") for x in g.LOG.values()), True)
    except Exception as e:
        fails.append("the run crashed: %s" % str(e).splitlines()[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
