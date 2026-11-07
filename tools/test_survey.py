"""Run almanac_survey.script under LuaJIT 2.0 against a made-up Zone, and check what it says.

Checked: the calendar's day count; the gate (standing steps from MCM, the network from Seasons when it
runs, else MCM's pick or the best of three); why the player can't ask (nowhere to look, locked, no
detector, a detector that doesn't list it, a question waiting, the day's questions spent) and a new
day's questions; a question's wait inside MCM's range; word held until its time and while a storm is
on, then sent in the leader's voice and portrait, or kept quiet with Messages off; where one lies
free (not owned, not a display case's copy, not one Dynamic Anomalies clears on arrival, not one the
despawner releases before the word lapses, an Artefact Hunter's kept); the levels a next roll could
make one on and how many each is expected to (Artefacts Reinvention's fields when due, Dynamic
Anomalies' list and random pick when its update is due, never the player's own level); naming a
level by standing (a poor one at the first step, the likeliest and its odds at the second); "there
is one" at the second step; nothing to say; every lead lapsing when a storm ends; the entry's
block; Seasons' time to the next storm; the save, plain values only.

    python test_survey.py            the real script
    python test_survey.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_survey.script")

#: name -> (text in the script, its broken replacement); each must make this test fail
MUTANTS = {
    "leap": ("y = m <= 2 and y - 1 or y", "y = y"),
    "tier_is": ('local tier = (st >= need_is and "is") or (st >= need and "could") or "locked"',
                'local tier = (st > need_is and "is") or (st >= need and "could") or "locked"'),
    "tier_could": ('local tier = (st >= need_is and "is") or (st >= need and "could") or "locked"',
                   'local tier = (st >= need_is and "is") or (st > need and "could") or "locked"'),
    "seasons_net": ("if ok and type(b) == \"table\" and LEADERS[b.faction] then\n        return b.faction, true",
                    "if false then\n        return b.faction, true"),
    "best_net": ("if top == nil or v > top then", "if top == nil or v < top then"),
    "nowhere": ('    if not surveyable(a) then\n        return "nowhere"\n    end\n', ""),
    "locked": ('    if g.tier == "locked" then\n        return "locked"\n    end\n', ""),
    "detector": ('    if not listed then\n        return "not_listed"\n    end\n', ""),
    "one_waiting": ('    if q then\n        return "waiting"\n    end\n', ""),
    "per_day": ('if asked >= (tonumber(mcm("survey_per_day")) or 1) then', "if false then"),
    "new_day": ("    if d ~= day_n then\n        day_n, asked = d, 0\n    end\n", ""),
    "wait_range": ("local wait = math.floor((lo + (hi - lo) * math.random()) * 60)",
                   "local wait = math.floor((lo + (hi - lo) * math.random()))"),
    "wait_due": ("if not q or game_sec() < q.due or storm_on() then", "if not q or storm_on() then"),
    "storm_hold": ("if not q or game_sec() < q.due or storm_on() then", "if not q or game_sec() < q.due then"),
    "silenced": ("    if almanac_found and not almanac_found.news() then\n", "    if false then\n"),
    "leader_icon": ("db.actor:give_game_news(T(who.name), text, who.icon, 0, 15000, 0)",
                    "db.actor:give_game_news(T(who.name), text, nil, 0, 15000, 0)"),
    "owned": ("(se.parent_id == nil or se.parent_id >= 65535)", "true"),
    "copies": ("                and not copies[id] then", "                then"),
    "dao_cleared": ("d.artefacts[id] ~= nil and dao_due(lvl)", "false"),
    "despawn_margin": ("return now - at + DESPAWN_MARGIN >= ", "return now - at >= "),
    "hunter_kept": ("if not G or (type(G.ah_af_sections) == \"table\" and G.ah_af_sections[sec]) then",
                    "if not G then"),
    "most": ("if n > most or (n == most and where and lvl < where) then", "if n > 0 then"),
    "not_here": ("if lvl and lvl ~= here and not seen[lvl] then", "if lvl and not seen[lvl] then"),
    "field_due": ("    if due[lvl] == true then\n        local p = 0.25", "    if true then\n        local p = 0.25"),
    "layer_mean": ("e = e + p * sum / #f.layers", "e = e + p * sum"),
    "dao_due": ("if D and dao_due(lvl) then", "if D then"),
    "dao_random": ("r * (D.allowed[sec] and 1 / math.max(1, n_allowed) or 0))", "0)"),
    "dao_underground": ("* (underground(lvl) and 2 or 1))) / 100", "* 1)) / 100"),
    "dao_rolls": ('local rolls = smarts_on(lvl) * dao_setting("anomaly_zone_spawn_chance") * dao_setting("max_artefacts_per_zone")',
                  'local rolls = smarts_on(lvl)'),
    "sharpen": ("ws[i] = c.w ^ (1 + 3 * s)", "ws[i] = c.w"),
    "is_likeliest": ('        local b = best(cands)\n        return { kind = "could", lvl = b.lvl, odds = odds_word(b.w) }\n', ""),
    "is_free_first": ('    if question.tier == "is" then\n        local where, most = nil, 0',
                      '    if false then\n        local where, most = nil, 0'),
    "odds": ("if p < o[1] then", "if p <= 0 then"),
    "lapse": ('if typ == "anomalies" and (name == "emission_end" or name == "psi_storm_end") then',
              'if typ == "anomalies" and name == "emission_end" then'),
    "save_q": ("local out = { day = day_n, asked = asked, q = plain_question(q), leads = {} }",
               "local out = { day = day_n, asked = asked, q = nil, leads = {} }"),
    "restore_leads": ("            leads[sec] = plain_lead(w)\n", ""),
    "plain_kind": ('if type(w) ~= "table" or (w.kind ~= "is" and w.kind ~= "could" and w.kind ~= "none") then',
                   'if type(w) ~= "table" then'),
    "block_link": ('lines[#lines + 1] = { T("st_almanac_survey_ask_" .. g.net), "body", sec, "survey" }',
                   'lines[#lines + 1] = { T("st_almanac_survey_ask_" .. g.net), "body" }'),
    "block_off": ("    if not enabled() then\n        return nil\n    end\n", ""),
    "seasons_hours": ("secs = math.min(secs or math.huge, tonumber(e.seconds))", "secs = tonumber(e.seconds)"),
    "seasons_band": ("if x and (not band or x[1] < band[1]) then", "if x and not band then"),
}

WORLD = r"""
LOG = {}
function printf(fmt, ...)
    local p, i = { ... }, 0
    fmt = string.gsub(tostring(fmt), "%%s", function() i = i + 1 return tostring(p[i]) end)
    LOG[#LOG + 1] = fmt
end
AC_ID = 0
DATE = { 2018, 11, 3, 12, 0, 0 }
function now_ct() return { get = function() return DATE[1], DATE[2], DATE[3], DATE[4], DATE[5], DATE[6], 0 end } end
STR = {
    st_almanac_survey_msg_is = "MIS %s|%s", st_almanac_survey_msg_could = "MCOULD %s|%s",
    st_almanac_survey_msg_odds = "MODDS %s|%s|%s", st_almanac_survey_msg_none = "MNONE %s",
    st_almanac_survey_is = "IS %s|%s|%s", st_almanac_survey_could = "COULD %s%s|%s|%s",
    st_almanac_survey_odds = ";%s", st_almanac_survey_none = "NONE %s|%s",
    st_almanac_survey_until_when = "UNTIL %s", st_almanac_survey_lapse_hours = "%s H",
    st_almanac_survey_asked_ecolog = "ASKED %s", st_almanac_survey_locked_ecolog = "LOCKED %s %s",
    st_almanac_survey_locked_csky = "LOCKEDC %s %s",
    st_almanac_survey_not_listed = "NOTLISTED %s", st_almanac_survey_busy = "BUSY %s",
    st_almanac_survey_standing_ecolog = "STANDING %s %s %s", st_almanac_leader_ecolog = "Sakharov",
    st_almanac_leader_csky = "Lebedev", det_echo_name = "Echo",
}
game = { get_game_time = now_ct, translate_string = function(id) return STR[id] or id end }
MCM = { ["drx_da/max_artefacts_per_zone"] = 3 }     -- Dynamic Anomalies' own MCM, read
ui_mcm = { get = function(path) return MCM[path] end }
GW = { ecolog = 0, csky = 0, isg = 0 }
relation_registry = { community_goodwill = function(net, id) return GW[net] end }
SURGE, PSI = false, false
surge_manager = { get_surge_manager = function() return { started = SURGE } end }
psi_storm_manager = { get_psi_storm_manager = function() return { started = PSI } end }
NEWS, NEWS_ON = {}, true
almanac_found = { news = function() return NEWS_ON end }
xr_sound = { set_sound_play = function() end }
DET = nil
db = { actor = {
    item_in_slot = function(self, n) return n == 9 and DET or nil end,
    give_game_news = function(self, cap, text, icon, a, ms, b) NEWS[#NEWS + 1] = { cap, text, icon } end,
} }
function detector(sec) return { section = function() return sec end } end
ini_sys = { r_string_ex = function(self, sec, key) return key == "inv_name" and sec .. "_name" or nil end }
STR.det_echo_name = "Echo"
HERE = "here"
level = { name = function() return HERE end }
-- the catalog: af_x from fields and Dynamic Anomalies, af_y fields only, af_c crafted only
CAT = {
    artifacts = {
        af_x = { sec = "af_x", name = "Ex", fields = { lA = { 0.5 } }, dao = { lD = 0.25 }, dao_random = true },
        af_y = { sec = "af_y", name = "Why", fields = { lC = { 1 } }, dao = {}, dao_random = true },
        af_c = { sec = "af_c", name = "Crafted", fields = {}, dao = {}, dao_random = false },
        af_ah_x = { sec = "af_ah_x", name = "Hunter", fields = { lG = { 1 } }, dao = {}, dao_random = false },
    },
    detectors = { det_echo = { "af_x", "af_c", "af_ah_x" }, det_bear = { "af_y" } },
    fields = {
        { level = "lA", layers = { { picks = { af_x = 0.5 } }, { picks = {} } } },
        { level = "lA", layers = { { picks = { af_x = 0.2 } } } },
        { level = "lB", layers = { { picks = { af_x = 0.1 } } } },
        { level = "here", layers = { { picks = { af_x = 0.9 } } } },
        { level = "lC", layers = { { picks = { af_y = 1 } } } },
        { level = "lG", layers = { { picks = { af_ah_x = 1 } } } },
    },
    dao = { allowed = { af_x = true, af_y = true, af_z = true, af_w = true }, chances = {},
            levels = { lD = { af_x = 1, af_y = 3 }, lB = { af_y = 2 } } },
}
almanac_data = { catalog = function() return CAT end }
MDATA = { artefact_respawn_levels = { lA = true, lB = true, here = true, lC = true } }
alife_storage_manager = { get_state = function() return MDATA end }
drx_da_main = { last_surge_time = 10, small_levels = {},
                updated_anomaly_levels = { lD = { time = 5, artefacts = { [15] = "af_x" } },
                                           lB = { time = 10, artefacts = { [16] = "af_x" } }, lE = { time = 3 } } }
game_difficulties = { get_eco_factor = function(k) return k == "arty_chance" and 0.25 or nil end }
game_achievements = { has_achievement = function() return false end }
WEATHERS = {}
function game_ini() return { r_string_ex = function(self, lvl, key) return WEATHERS[lvl] end } end
function smart(lvl) return { smrt = { lvl = lvl } } end
SIMBOARD = { smarts = { smart("lD"), smart("lD"), smart("lD"), smart("lD"), smart("lE"), smart("lE") } }
almanac_census = { level_of = function(se) return se.lvl end }
-- the alife's objects
OBJS = {}
function obj(id, sec, lvl, parent, art)
    OBJS[id] = { id = id, lvl = lvl, parent_id = parent or 65535, art = art ~= false,
                 section_name = function() return sec end }
end
function alife() return { object = function(self, id) return OBJS[id] end } end
function IsArtefact(se) return se.art end
weapon_showcase = { weapon_displays = { case1 = { [1] = 14 } } }
grok_artefact_despawner = { af_spawn_duration_limit = 432000, ah_af_sections = { af_ah_x = true },
                            artefacts_spawned_time = {} }
NOW = 0
function time_global() return NOW end
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

    def near(what, got, want):
        n[0] += 1
        if got is None or abs(got - want) > 1e-9:
            fails.append("%s: got %r, want %r" % (what, got, want))

    try:
        lua = L.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        lua.execute(WORLD)
        load = lua.eval("function(src) local e = setmetatable({}, { __index = _G }) "
                        "local f = assert(loadstring(src, 'almanac_survey')) setfenv(f, e) f() return e end")
        M = load(src)
        M.on_game_start()
        cb = g.CALLBACKS

        def tbl(t):
            return {k: (tbl(v) if L.lua_type(v) == "table" else v) for k, v in t.items()} if t is not None else None

        def lines(sec):
            b = M.block(sec)
            return None if b is None else [tuple(x.values()) for x in b.lines.values()]

        # the calendar
        epoch = datetime.date(1970, 1, 1).toordinal()
        for y, m, d in ((1970, 1, 1), (2018, 11, 3), (2016, 2, 29), (2016, 3, 1), (2000, 2, 29), (1900, 3, 1)):
            eq("days %d-%d-%d" % (y, m, d), M.days(y, m, d), datetime.date(y, m, d).toordinal() - epoch)
        eq("game_sec", M.game_sec(), (datetime.date(2018, 11, 3).toordinal() - epoch) * 86400 + 12 * 3600)

        # the gate: MCM's steps, the network
        for st, tier, s in ((100, "locked", 0), (200, "could", 0), (450, "could", 0.5), (700, "is", 1), (900, "is", 1)):
            g.GW.ecolog = st
            gt = M.gate()
            eq("tier at %d" % st, (gt.tier, gt.s, gt.net), (tier, s, "ecolog"))
        g.GW.ecolog = 400
        g.MCM["almanac/survey_could"], g.MCM["almanac/survey_is"] = 300, 500
        eq("MCM steps", (M.gate().tier, M.gate().need, M.gate().need_is), ("could", 300, 500))
        lua.execute('MCM["almanac/survey_could"], MCM["almanac/survey_is"] = nil, nil')
        g.MCM["almanac/survey_network"] = "csky"
        g.GW.csky = 250
        eq("MCM's network", (M.network(), M.gate().tier), (("csky", False), "could"))
        g.MCM["almanac/survey_network"] = "best"
        g.GW.ecolog = 100
        g.GW.isg = 800
        eq("the best of three", M.network(), ("isg", False))
        g.sotz_api = lua.eval('{ blowout = function() return { faction = "ecolog" } end }')
        eq("Seasons' network", M.network(), ("ecolog", True))
        g.sotz_api = lua.eval('{ blowout = function() return nil end }')
        eq("Seasons without a forecast", M.network(), ("isg", False))
        g.sotz_api = None
        g.MCM["almanac/survey_network"] = None
        g.GW.isg, g.GW.csky = 0, 0

        # why not
        g.GW.ecolog = 300
        eq("nowhere to look", M.why_not("af_c"), "nowhere")
        g.GW.ecolog = 100
        eq("locked", M.why_not("af_x"), "locked")
        g.GW.ecolog = 300
        eq("no detector", M.why_not("af_x"), "no_detector")
        g.DET = g.detector("det_bear")
        eq("not listed", M.why_not("af_x"), "not_listed")
        g.DET = g.detector("det_echo")
        eq("can ask", M.why_not("af_x"), None)

        # a question: its wait in MCM's range, then one at a time, then the day's
        at = lua.eval("function(x) return function() return x end end")
        t0 = M.game_sec()
        eq("asked", M.ask("af_x"), True)
        q = M.waiting()
        eq("waits 1-3 hours", t0 + 3600 <= q.due <= t0 + 3 * 3600, True)
        eq("asked at the second step", (q.tier, q.s, q.net), ("could", 0.2, "ecolog"))
        eq("one at a time", (M.why_not("af_x"), M.ask("af_x")), ("waiting", False))
        eq("no word before its time", M.deliver(), False)
        g.DATE[3], g.DATE[4] = 3, 16                     # 16:00, past any wait
        g.SURGE = True
        eq("held while a storm is on", M.deliver(), False)
        g.SURGE = False
        eq("word", M.deliver(at(0)), True)
        eq("the lead", tbl(M.lead("af_x")), {"kind": "could", "lvl": "lA", "net": "ecolog",
                                              "y": 2018, "mo": 11, "d": 3, "h": 16, "mi": 0})
        eq("in his voice", list(g.NEWS[1].values()), ["Sakharov", "MCOULD Ex|lA", "ui_inGame2_sakharov"])
        eq("the day's question spent", M.why_not("af_x"), "spent")
        g.MCM["almanac/survey_per_day"] = 2
        eq("MCM's questions a day", M.why_not("af_x"), None)
        g.MCM["almanac/survey_per_day"] = None
        g.DATE[3] = 4
        eq("a new day", M.why_not("af_x"), None)
        g.MCM["almanac/survey_wait_min"], g.MCM["almanac/survey_wait_max"] = 0, 0
        g.NEWS_ON = False
        M.ask("af_x")
        eq("silenced: no message", (M.deliver(at(0)), len(g.NEWS)), (True, 1))
        eq("silenced: still a lead", M.lead("af_x") is not None, True)
        g.NEWS_ON = True
        g.DATE[3] = 5

        # the levels a next roll could make one on: fields when due, Dynamic Anomalies when its update is
        cands = {c.lvl: c.w for c in M.could_levels(g.CAT, "af_x").values()}
        eq("could: levels", sorted(cands), ["lA", "lB", "lD", "lE"])
        near("could: lA's fields", cands.get("lA"), 0.25 * (0.25 + 0.2))
        near("could: lB's field, its Dynamic Anomalies not due", cands.get("lB"), 0.25 * 0.1)
        near("could: lD's list", cands.get("lD"), 4 * 0.5 * 3 * 0.15 * (0.75 * 0.25 + 0.25 * 0.25))
        near("could: lE's random pick", cands.get("lE"), 2 * 0.5 * 3 * 0.15 * 0.25)
        g.WEATHERS.lE = "w_indoor_ambient"
        near("could: underground twice", {c.lvl: c.w for c in M.could_levels(g.CAT, "af_x").values()}.get("lE"),
             2 * 0.5 * 3 * 0.30 * 0.25)
        g.WEATHERS.lE = None
        eq("could: af_y", sorted(c.lvl for c in M.could_levels(g.CAT, "af_y").values()), ["lC", "lD", "lE"])
        # naming one: a poor level at the first step, seldom near the second
        cl = M.could_levels(g.CAT, "af_x")
        eq("pick: first", M.pick(cl, 0, at(0)).lvl, "lA")
        eq("pick: a poor one at the first step", M.pick(cl, 0, at(0.26)).lvl, "lB")
        eq("pick: the likely one near the second", M.pick(cl, 1, at(0.26)).lvl, "lD")
        eq("best", M.best(cl).lvl, "lD")
        eq("odds", [M.odds_word(e) for e in (0.1, 0.2, 0.6)], ["slim", "fair", "good"])

        # where one lies free now
        def ago(days):
            t = datetime.datetime(2018, 11, 5, 16, 0) - datetime.timedelta(days=days)
            return lua.table_from({"Y": t.year, "M": t.month, "D": t.day, "h": t.hour, "m": t.minute, "s": 0})
        g.obj(10, "af_x", "lA")                         # unseen
        g.obj(11, "af_x", "lA")                         # seen a day ago
        g.obj(12, "af_x", "lB")                         # 4.5 days: released before the word lapses
        g.obj(13, "af_x", "lB", 500)                    # owned
        g.obj(14, "af_x", "lF")                         # a display case's copy
        g.obj(15, "af_x", "lD")                         # Dynamic Anomalies', cleared on arrival
        g.obj(16, "af_x", "lB")                         # Dynamic Anomalies', its update not due
        g.obj(17, "af_z", "lA", 500)                    # another kind, owned
        g.obj(21, "af_y", "lA")                         # another kind
        g.obj(18, "af_x", "lA", None, False)            # not an artifact
        g.obj(19, "af_ah_x", "lG")                      # an Artefact Hunter's, 10 days old
        g.obj(20, "af_x", "lH")                         # 3.5 days
        sp = g.grok_artefact_despawner.artefacts_spawned_time
        sp[11], sp[12], sp[19], sp[20] = ago(1), ago(4.5), ago(10), ago(3.5)
        eq("free ones", tbl(M.free_ones("af_x")), {"lA": 2, "lB": 1, "lH": 1})
        eq("an Artefact Hunter's kept", tbl(M.free_ones("af_ah_x")), {"lG": 1})

        # the answers
        eq("is: where most lie", tbl(M.answer(lua.table_from({"sec": "af_x", "tier": "is", "s": 1}))),
           {"kind": "is", "lvl": "lA"})
        eq("could at the second step: the likeliest, its odds",
           tbl(M.answer(lua.table_from({"sec": "af_z", "tier": "is", "s": 1}))),
           {"kind": "could", "lvl": "lE", "odds": "slim"})
        eq("could at the first step: no 'is'",
           tbl(M.answer(lua.table_from({"sec": "af_x", "tier": "could", "s": 0}), at(0.26))),
           {"kind": "could", "lvl": "lB"})
        lua.execute("MDATA.artefact_respawn_levels = {} drx_da_main.last_surge_time = -5")
        eq("nothing to say", tbl(M.answer(lua.table_from({"sec": "af_y", "tier": "could", "s": 0}))), {"kind": "none"})
        lua.execute("MDATA.artefact_respawn_levels = { lA = true, lB = true, here = true, lC = true } "
                    "drx_da_main.last_surge_time = 10")

        # the entry's block
        g.GW.ecolog = 750
        g.DATE[3] = 6
        M.ask("af_x")
        b = lines("af_x")
        eq("block: a lead, its lapse, the question, the standing", b, [
            ("COULD lA|Sakharov|16:00", "heading"), ("st_almanac_survey_until", "dim"), ("ASKED 16:00", "body"),
            ("STANDING 750 200 700", "dim")])
        eq("block: busy on another", lines("af_ah_x")[0], ("BUSY Ex", "dim"))
        g.MCM["almanac/survey_wait_min"], g.MCM["almanac/survey_wait_max"] = None, None
        M.deliver()
        g.DATE[3] = 7
        b = lines("af_x")
        eq("block: is", b[0], ("IS lA|Sakharov|16:00", "good"))
        eq("block: the link", b[2], ("st_almanac_survey_ask_ecolog", "body", "af_x", "survey"))
        g.sotz_api = lua.eval('{ blowout = function() return { emission = { seconds = 5 * 3600 }, '
                              'psi = { seconds = 9 * 3600 } } end }')
        eq("block: Seasons' hours, the nearer", lines("af_x")[1], ("UNTIL 5 H", "dim"))
        g.sotz_api = lua.eval('{ blowout = function() return { emission = { band = "8 to 16 hours" }, '
                              'psi = { band = "2 to 8 hours" } } end }')
        eq("block: Seasons' bracket, the nearer", lines("af_x")[1], ("UNTIL st_almanac_survey_lapse_band_8", "dim"))
        g.sotz_api = None
        g.DET = g.detector("det_bear")
        eq("block: the detector named", lines("af_x")[2], ("NOTLISTED det_bear_name", "dim"))
        g.DET = g.detector("det_echo")
        g.GW.ecolog = 50
        eq("block: locked", lines("af_ah_x"), [("LOCKED 200 50", "dim")])
        eq("block: nowhere", lines("af_c"), [("st_almanac_survey_nowhere", "dim")])
        g.MCM["almanac/survey"] = False
        eq("block: off", lines("af_x"), None)
        g.MCM["almanac/survey"] = None
        g.GW.ecolog = 750

        # the save: plain values; a restore takes them back, and drops what isn't
        M.ask("af_ah_x")
        st = M.state()
        eq("state: the question", (st.q.sec, st.q.tier, st.q.net), ("af_ah_x", "is", "ecolog"))
        eq("state: the leads", sorted(st.leads.keys()), ["af_x"])
        saved = lua.eval("function(t) local function copy(x) if type(x) ~= 'table' then return x end "
                         "local o = {} for k, v in pairs(x) do o[k] = copy(v) end return o end return copy(t) end")(st)
        M.lapse()
        M.restore(None)
        eq("restore nothing", (M.waiting(), M.lead("af_x")), (None, None))
        M.restore(saved)
        eq("restore: the question", M.waiting().sec, "af_ah_x")
        eq("restore: the lead", M.lead("af_x").kind, "is")
        bad = lua.eval('{ q = { sec = 5 }, leads = { af_x = { kind = "maybe" }, af_y = { kind = "could", lvl = "lB", '
                       'f = function() end } }, day = "x" }')
        M.restore(bad)
        eq("restore: junk dropped", (M.waiting(), M.lead("af_x"), M.lead("af_y").lvl, M.lead("af_y").f),
           (None, None, "lB", None))

        # every lead lapses when an emission or a psi storm ends
        M.restore(saved)
        cb.actor_on_interaction("anomalies", None, "emission_start")
        eq("not at the start", M.lead("af_x") is not None, True)
        cb.actor_on_interaction("anomalies", None, "psi_storm_end")
        eq("lapsed after a psi storm", M.lead("af_x"), None)
        M.restore(saved)
        cb.actor_on_interaction("anomalies", None, "emission_end")
        eq("lapsed after an emission", (M.lead("af_x"), len(list(M.leads_list().values()))), (None, 0))

        # the update sends word, and a failure drops the question rather than stopping the game's
        M.restore(saved)
        g.DATE[3] = 9
        cb.actor_on_first_update()
        g.NOW = 5000
        before = len(g.NEWS)
        cb.actor_on_update()
        eq("update: word sent", (len(g.NEWS), M.waiting()), (before + 1, None))
        eq("leads list", list(M.leads_list().values()), ["af_ah_x", "af_x"])
        eq("the log: %s only", [x for x in g.LOG.values() if "%" in x], [])
    except Exception as e:
        fails.append("the run crashed: %s" % str(e).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
