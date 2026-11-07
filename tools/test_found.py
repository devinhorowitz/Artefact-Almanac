"""Run almanac_found.script under LuaJIT 2.0 against a made-up actor and check the finds it keeps.

The world: a pack holding an artifact, a lead box with another inside and a gun; then artifacts
taken from the ground, a trader, a dead stalker, a living one, a stash, the Melter's window and a
talk. Checked: the quiet scan at the first update (and a take before it), one find per artifact,
a container counting as what it holds, how each find came and its words, the PDA message and MCM's
switch for it, the date, the counts, a save and a load into a fresh copy of the script, and a load
of a broken record.

    python test_found.py            the real script
    python test_found.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_found.script")

#: name -> (text in the script, its broken replacement); each must make this test fail
MUTANTS = {
    "container": ('    if kind == "i_arty_cont" then\n', "    if false then\n"),
    "once": ("    if not a or found[a] then\n", "    if not a then\n"),
    "quiet_scan": ("mark(obj:section(), true, carried)", "mark(obj:section(), false, carried)"),
    "before_scan": ("mark(obj:section(), not scanned, scanned and take_source or carried)",
                    "mark(obj:section(), false, take_source)"),
    "trade": ('            if gui.mode == "trade" then\n', "            if false then\n"),
    "living": ("            elseif IsStalker(partner) and living(gui, partner) then\n", "            elseif false then\n"),
    "craft": ("    if ws and ws:IsShown() then\n", "    if false then\n"),
    "news_off": ("    return not (ok and v == false)\n", "    return true\n"),
    "load_plain": ("                out[sec] = plain(at)\n", "                out[sec] = at\n"),
    "learn_found": ("    if not a or found[a] or learned[a] then\n", "    if not a or learned[a] then\n"),
    "learn_once": ("    if not a or found[a] or learned[a] then\n", "    if not a or found[a] then\n"),
    "learn_saved": (", learned = plain_all(learned),", ","),
    "learn_quiet": ("    learned[a] = at\n    if not quiet then\n", "    learned[a] = at\n    if true then\n"),
    "strip_comma": ('s = ok and type(s) == "string" and s:gsub("[,%s]+$", "") or nil',
                    's = ok and type(s) == "string" and s or nil'),
    "vertex_check": ("    if gg and gg:valid_vertex_id(place.gv) then\n", "    if gg then\n"),
    "schema": ("m_data.almanac = { v = SCHEMA, found = plain_all(found)", "m_data.almanac = { found = plain_all(found)"),
    "survey_saved": ("                       survey = ok and survey or nil }", "                       survey = nil }"),
    "survey_restored": ("        pcall(almanac_survey.restore, type(d) == \"table\" and d.survey or nil)\n", ""),
    "who": ('s = string.format(s, (how.who and how.who ~= "") and how.who or T("st_almanac_by_someone"))',
            's = string.format(s, T("st_almanac_by_someone"))'),
}

WORLD = r"""
LOG, NEWS = {}, {}
function printf(fmt, ...)
    local p, i = { ... }, 0
    fmt = string.gsub(tostring(fmt), "%%s", function() i = i + 1 return tostring(p[i]) end)
    LOG[#LOG + 1] = fmt
end
STR = { st_almanac_new_entry = "New: %s", st_almanac_in = "in %s", l01_escape = "Cordon",
        st_almanac_got_ground = "picked up", st_almanac_got_trade = "bought from %s",
        st_almanac_got_body = "taken from %s", st_almanac_got_gift = "given by %s",
        st_almanac_got_stash = "from a stash", st_almanac_got_craft = "made", st_almanac_got_carried = "carried",
        st_almanac_by_someone = "someone", st_almanac_title = "Almanac",
        st_almanac_got_news = "radio, %s found one", st_almanac_got_task = "%s asked" }
game = {
    translate_string = function(id) return STR[id] or id end,
    get_game_time = function() return { get = function() return 2012, 5, 14, 8, 30, 0, 0 end } end,
}
level = { name = function() return "l01_escape" end }
KIND = { af_k = "i_arty", af_l = "i_arty", af_m = "i_arty",
         af_a = "i_arty", af_b = "i_arty_junk", af_c = "i_arty", af_d = "i_arty", af_e = "i_arty",
         af_f = "i_arty", af_g = "i_arty", af_h = "i_arty", af_i = "i_arty", af_j = "i_arty",
         af_b_lead_box = "i_arty_cont", wpn_pm = "w_pistol" }
function SYS_GetParam(_, sec, key, def) return key == "kind" and KIND[sec] or def end
NAMES = { af_a = "Ay", af_b = "Bee", af_c = "Cee", af_d = "Dee" }
ini_sys = { r_string_ex = function(_, s, k) return k == "inv_name" and NAMES[s] or nil end }
almanac_data = { held_by = function(sec) return (sec:gsub("_lead_box$", "")) end }
MCM = {}
ui_mcm = { get = function(k) return MCM[k] end }
function vector() return { set = function(self, x, y, z) self.x, self.y, self.z = x, y, z return self end } end
function game_graph()
    return { valid_vertex_id = function(_, gv) return gv < 100 end,
             vertex = function(_, gv)
                 if gv >= 100 then error("no such vertex") end
                 return { level_id = function() return 1 end }
             end }
end
function alife() return { level_name = function(_, id) return "l01_escape" end } end
dynamic_news_helper = { GetPointDescription = function(t) return "in Cordon, near the village, " end }
function obj_at(gv, extra)
    local o = extra or {}
    o.game_vertex_id = function() return gv end
    o.position = function() return { x = 1.23, y = 2, z = 3 } end
    return o
end
TALK = false
INV = { "af_a", "af_b_lead_box", "wpn_pm" }
db = { actor = obj_at(5, {
    give_game_news = function(_, title, text) NEWS[#NEWS + 1] = title .. "|" .. text end,
    iterate_inventory = function(self, fn)
        for _, s in ipairs(INV) do fn(self, { section = function() return s end }) end
    end,
    is_talking = function() return TALK end,
}) }
function item(sec) return { section = function() return sec end } end
function IsStalker(o) return o.stalker == true end
SPEAKER = { character_name = function() return "Barman" end, game_vertex_id = function() return 7 end,
            position = function() return { x = 0, y = 0, z = 0 } end }
function get_speaker() return SPEAKER end
GUI = nil
ui_inventory = setmetatable({}, { __index = function(_, k) if k == "GUI" then return GUI end end })
WS = { IsShown = function() return false end }
ui_workshop = { GUI = WS }
function window(mode, partner, extra)
    local g = extra or {}
    g.mode = mode
    g.IsShown = function() return true end
    g.GetPartner = function() return partner end
    return g
end
function npc(name, alive)
    return obj_at(8, { stalker = true, character_name = function() return name end, alive = function() return alive end })
end
CALLBACKS = {}
function RegisterScriptCallback(name, fn) CALLBACKS[name] = fn end
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
    fails = []
    n = [0]

    def eq(what, got, want):
        n[0] += 1
        if got != want:
            fails.append("%s: got %r, want %r" % (what, got, want))

    try:
        lua = L.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        lua.execute(WORLD)
        load = lua.eval("function(src) local e = setmetatable({}, { __index = _G }) "
                        "local f = assert(loadstring(src, 'almanac_found')) setfenv(f, e) f() return e end")
        F = load(src)
        F.on_game_start()
        cb = g.CALLBACKS
        eq("callbacks", sorted(cb.keys()), ["actor_on_first_update", "actor_on_item_take", "load_state", "save_state"])

        def kind(sec):
            at = F.found_at(sec)
            return at and at.how and at.how.kind

        def news():
            return list(g.NEWS.values())

        cb.load_state(lua.table_from({}))
        # a take before the first update (the engine's own, at load) counts as carried, quietly
        cb.actor_on_item_take(g.item("af_e"))
        eq("before the scan", (kind("af_e"), news()), ("carried", []))
        cb.actor_on_first_update()
        eq("scan", (kind("af_a"), kind("af_b"), F.is_found("wpn_pm"), F.is_found("af_b_lead_box")),
           ("carried", "carried", False, False))
        eq("scan is quiet", news(), [])
        # from the ground: a find and a message; the same again: nothing
        cb.actor_on_item_take(g.item("af_c"))
        eq("ground", kind("af_c"), "ground")
        eq("message", news(), ["Almanac|New: Cee"])
        cb.actor_on_item_take(g.item("af_c"))
        cb.actor_on_item_take(g.item("af_a"))
        eq("once each", (len(news()), kind("af_a")), (1, "carried"))
        # bought, from a body, given by a living stalker, from a stash
        g.GUI = g.window("trade", g.npc("Sakharov", True))
        cb.actor_on_item_take(g.item("af_d"))
        eq("trade", (kind("af_d"), F.found_at("af_d").how.who), ("trade", "Sakharov"))
        eq("trade words", F.describe(F.found_at("af_d")), "bought from Sakharov in Cordon, near the village")
        g.GUI = g.window("loot", g.npc("Vasya", False))
        cb.actor_on_item_take(g.item("af_f"))
        eq("body", (kind("af_f"), F.describe(F.found_at("af_f"))), ("body", "taken from Vasya in Cordon, near the village"))
        g.GUI = g.window("loot", g.npc("Petya", True))
        cb.actor_on_item_take(g.item("af_g"))
        eq("living", kind("af_g"), "gift")
        g.GUI = g.window("loot", g.obj_at(9, {}), lua.table_from({"npc_is_box": True}))
        cb.actor_on_item_take(g.item("af_h"))
        eq("stash", kind("af_h"), "stash")
        g.GUI = None
        g.WS.IsShown = lua.eval("function() return true end")
        cb.actor_on_item_take(g.item("af_i"))
        eq("craft", kind("af_i"), "craft")
        g.WS.IsShown = lua.eval("function() return false end")
        g.TALK = True
        g.MCM["almanac/news"] = False
        cb.actor_on_item_take(g.item("af_j"))
        eq("talk", (kind("af_j"), F.found_at("af_j").how.who), ("gift", "Barman"))
        # six messages before the switch (ground, trade, body, gift, stash, craft), none after it
        eq("silenced", (len(news()), any("(silenced)" in x for x in g.LOG.values())), (6, True))
        g.TALK = False
        g.MCM["almanac/news"] = None
        # heard of: once, never for what's found, quietly when asked, in words like a find
        place = lua.table_from({"gv": 5, "x": 1, "y": 2, "z": 3})
        eq("learn", F.learn("af_k", lua.table_from({"kind": "news", "who": "Vasya", "place": place})), "af_k")
        eq("learn message", news()[-1], "Almanac|New: af_k")
        eq("learn words", F.describe(F.learned_at("af_k")), "radio, Vasya found one in Cordon, near the village")
        eq("learn once", F.learn("af_k", lua.table_from({"kind": "task", "who": "X"})), None)
        eq("learn what's found", (F.learn("af_a", lua.table_from({"kind": "task"})), F.is_learned("af_a")), (None, False))
        before = len(news())
        eq("learn quietly", (F.learn("af_l", lua.table_from({"kind": "task", "who": "Sid"}), True), len(news()) - before), ("af_l", 0))
        eq("learned isn't found", (F.is_learned("af_l"), F.is_found("af_l")), (True, False))
        g.MCM["almanac/news"] = False
        eq("date", F.date_of(F.found_at("af_c")), "14.05.2012")
        eq("count", (F.count_found(), F.count_found(lua.table_from(["af_a", "af_x"]))), (10, 1))
        # a place whose vertex isn't on this mod list: the level alone; a find with no how: the level
        eq("no vertex", F.place_text(lua.table_from({"gv": 500, "x": 0, "y": 0, "z": 0}), "l01_escape"), "in Cordon")
        eq("no how", F.describe(lua.table_from({"lvl": "l01_escape"})), "Cordon")
        # save, and load into a fresh copy
        m = lua.table_from({})
        lua.execute("SURVEY_IN = nil almanac_survey = { state = function() return { asked = 1 } end, "
                    "restore = function(t) SURVEY_IN = t end }")
        cb.save_state(m)
        eq("schema", m.almanac.v, 1)
        eq("the survey saved beside the finds", m.almanac.survey.asked, 1)
        saved = m.almanac.found
        eq("saved", sorted(saved.keys()), ["af_a", "af_b", "af_c", "af_d", "af_e", "af_f", "af_g", "af_h", "af_i", "af_j"])
        F2 = load(src)
        F2.on_game_start()
        g.CALLBACKS.load_state(m)
        eq("the survey restored", g.SURVEY_IN.asked, 1)
        g.almanac_survey = None
        eq("loaded", (F2.count_found(), F2.describe(F2.found_at("af_d")), F2.found_at("af_d").how.place.x),
           (10, "bought from Sakharov in Cordon, near the village", 1.2))
        eq("learned loaded", (F2.is_learned("af_k"), F2.is_learned("af_l"), F2.describe(F2.learned_at("af_l"))),
           (True, True, "Sid asked in Cordon"))
        # a broken record: a string where a find should be, a number for a section
        bad = lua.eval("function() return { almanac = { v = 1, found = { af_a = 'x', [3] = {}, af_c = { y = 2012 } } } } end")()
        F3 = load(src)
        F3.on_game_start()
        g.CALLBACKS.load_state(bad)
        eq("broken record", (F3.is_found("af_a"), F3.is_found("af_c"), F3.count_found()), (False, True, 1))
        F4 = load(src)
        F4.on_game_start()
        g.CALLBACKS.load_state(lua.table_from({"almanac": "garbage"}))
        eq("broken key", F4.count_found(), 0)
    except Exception as e:
        fails.append("the run crashed: %s" % str(e).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
