"""Run almanac_learn.script under LuaJIT 2.0 against a made-up news manager, news helper and task
manager, and check what it learns.

Checked: the wrappers are put in place at the first update and stand aside when what they wrap is
missing; every argument and result passes through both; a stalker's "found an artifact" news is
learned only once it's sent to the player, from him, where he stood, whether the queue names him by
his object or his id (dEmergence's news fixes), and never when the news wasn't queued, was another
stalker's, wasn't about an artifact, or failed to send; the pending messages are capped; a task asking
for an artifact is learned from its giver, quietly at the read after a load, and a task asking for
anything else isn't. What a PDA or an Ecologist tells of: artifacts unknown and turning up, this
level's first; a PDA as many as its size, once per owner, an encrypted one once decrypted (the
decryption wrapped, its results passed through); an Ecologist (alive, not hostile) one a day, from
him, picking again what the player has come to know.

    python test_learn.py            the real script
    python test_learn.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_learn.script")

#: name -> (text in the script, its broken replacement); each must make this test fail
MUTANTS = {
    "forward_args": ("local res = { orig(self, sender, itm, ...) }", "local res = { orig(self, sender, itm) }"),
    "forward_results": ("        end\n        return unpack(res)\n    end\n    wrapped_news = true",
                        "        end\n        return res[1]\n    end\n    wrapped_news = true"),
    "tip_args": ("local res = { orig(msg, ...) }", "local res = { orig(msg) }"),
    "learn_on_send": ("        if p then\n            pending[msg] = nil", "        if p and false then\n            pending[msg] = nil"),
    "failed_send": ("            if res[1] ~= false then\n", "            if true then\n"),
    "queued_only": ("        if res[1] == true then\n", "        if true then\n"),
    "artifact_news": ('e.Ty == "artifact" and (e.Id == sender or e.Id == sender:id()) and ', ""),
    "id_queued": ("(e.Id == sender or e.Id == sender:id())", "e.Id == sender"),
    "any_sender": ("(e.Id == sender or e.Id == sender:id())", "true"),
    "cap": ("    if n_pending >= MAX_PENDING then\n", "    if false then\n"),
    "task_quiet": ("pcall(read_tasks, first_read)", "pcall(read_tasks, false)"),
    "task_artifact": ('local a = type(sec) == "string" and almanac_found.artifact_of(sec)', "local a = sec"),
    "giver": ("who = giver_name(type(t) == \"table\" and t.task_giver_id)", "who = nil"),
    "here_first": ("for _, t in ipairs({ here, elsewhere }) do", "for _, t in ipairs({ elsewhere, here }) do"),
    "word_unknown": ("if not almanac_page.known(sec) and almanac_page.turns_up(a) then", "if almanac_page.turns_up(a) then"),
    "word_turns_up": ("if not almanac_page.known(sec) and almanac_page.turns_up(a) then", "if not almanac_page.known(sec) then"),
    "pda_once": ("    if se_load_var(id, obj:name(), READ) == who then\n        return 0\n    end\n", ""),
    "pda_encrypted": ('    if info.state == "encrypted" then\n        return 0\n    end\n', ""),
    "pda_size": ("for _, sec in ipairs(word_of(size, level.name())) do", "for _, sec in ipairs(word_of(1, level.name())) do"),
    "decrypt_scan": ("        pcall(scan_pdas, false)\n", ""),
    "talk_ecolog": ('npc:character_community() == "ecolog"', "true"),
    "talk_daily": ("if not willing(npc) or se_load_var(npc:id(), npc:name(), TALKED) == day() then", "if not willing(npc) then"),
    "talk_hostile": ("and not (npc.relation and npc:relation(db.actor) == game_object.enemy)", ""),
    "talk_repick": ("if t and (t.who ~= whose(npc) or almanac_page.known(t.sec)) then", "if t and t.who ~= whose(npc) then"),
    "talk_who": ('{ kind = "talk", who = npc:character_name(), place', '{ kind = "talk", who = nil, place'),
    "asking_artifact": ('if type(want) == "string" and almanac_found.artifact_of(want) == sec then',
                        'if type(want) == "string" then'),
}

WORLD = r"""
LOG = {}
function printf(fmt, ...)
    local p, i = { ... }, 0
    fmt = string.gsub(tostring(fmt), "%%s", function() i = i + 1 return tostring(p[i]) end)
    LOG[#LOG + 1] = fmt
end
KIND = { af_a = "i_arty", af_b = "i_arty", af_c = "i_arty", af_d = "i_arty" }
LEARNED, CALLS = {}, {}
almanac_found = {
    artifact_of = function(sec) return KIND[sec] and sec or nil end,
    place_of = function(o) return "place of " .. (type(o.name) == "function" and o:name() or o.name) end,
    learn = function(sec, how, quiet)
        CALLS[#CALLS + 1] = { sec = sec, kind = how.kind, who = how.who, place = how.place, quiet = quiet }
        if LEARNED[sec] then return nil end
        LEARNED[sec] = true
        return sec
    end,
}
-- the news manager: FoundArtefact queues the news on the sender's channel (newest first) and says
-- whether it did; it gives back a second value, and records the arguments it got. PUSH_ID: the
-- sender as queued, his object (nil), his id (true, as dEmergence's news fixes do) or another id
C = {}
PUSH, PUSH_TY, PUSH_ID, ARGS, N = true, "artifact", nil, {}, 0
function C:FoundArtefact(sender, itm, extra)
    N = N + 1
    ARGS[N] = extra or false
    if not PUSH then return false, "no" end
    local id = PUSH_ID == true and sender:id() or PUSH_ID or sender
    table.insert(self.queue[sender:character_community()], 1, { Mg = "news " .. itm:section() .. " " .. N, Ty = PUSH_TY, Id = id })
    return true, "pushed"
end
dynamic_news_manager = { DynamicNewsManager = C }
DNM = setmetatable({ queue = { dolg = {} } }, { __index = C })
SENT, TIP_RESULT = {}, nil
dynamic_news_helper = { send_tip = function(msg, header, a, b)
    SENT[#SENT + 1] = { msg, header, a, b }
    return TIP_RESULT, "tip"
end }
function stalker(name, id) return { name = name, character_name = function() return name end,
                                    character_community = function() return "dolg" end,
                                    id = function() return id or 0 end } end
function item(sec) return { section = function() return sec end } end
TASKS, VARS = {}, {}
task_manager = { get_task_manager = function() return { task_info = TASKS } end }
function load_var(obj, key) return VARS[key] end
GIVERS = { [7] = { character_name = function() return "Sidorovich" end } }
level = { object_by_id = function(id) return GIVERS[id] end }
function alife() return { object = function() return nil end } end
db = { actor = {} }
NOW = 0
function time_global() return NOW end
CALLBACKS = {}
function RegisterScriptCallback(name, fn) CALLBACKS[name] = fn end
-- what a PDA or an Ecologist can tell of: h1 and h2 the Zone makes on this level (a field, Dynamic
-- Anomalies), e1 elsewhere, k1 known already, n1 turning up nowhere
CAT = { order = { "e1", "h1", "h2", "k1", "n1" }, artifacts = {
    h1 = { sec = "h1", name = "Aitch One", fields = { here = { 0.1 } }, dao = {} },
    h2 = { sec = "h2", name = "Aitch Two", fields = {}, dao = { here = 0.5 } },
    e1 = { sec = "e1", name = "Ee One", fields = { there = { 0.1 } }, dao = {} },
    k1 = { sec = "k1", name = "Kay One", fields = { here = { 0.1 } }, dao = {} },
    n1 = { sec = "n1", name = "En One", fields = {}, dao = {}, nowhere = true },
} }
almanac_data = { catalog = function() return CAT end }
KNOWN = { k1 = true }
almanac_page = { known = function(sec) return KNOWN[sec] == true or LEARNED[sec] == true end,
                 turns_up = function(a) return not a.nowhere end }
level.name = function() return "here" end
SE = {}
function se_load_var(id, name, key) return SE[id] and SE[id][key] end
function se_save_var(id, name, key, v) SE[id] = SE[id] or {}; SE[id][key] = v end
-- a PDA's owner as ui_pda_npc_tab registers it (none: nil), and its state
function set_pda(id, owner, state)
    SE[id] = SE[id] or {}
    SE[id].info = owner and { contact = { name = owner, comm = "stalker", rank = "novice" }, state = state } or {}
end
function pda(id, sec) return { id = function() return id end, name = function() return "pda" .. id end,
                               section = function() return sec end } end
DATE = { 2012, 5, 14 }
STR = { st_almanac_talk = "Studying %s", st_almanac_talk_none = "Nothing" }
game = { get_game_time = function() return { get = function() return DATE[1], DATE[2], DATE[3] end } end,
         translate_string = function(id) return STR[id] or id end }
game_object = { enemy = 2 }
AC_ID = 0
db.actor.name = "actor"
db.actor.id = function() return 0 end
INV = {}
db.actor.iterate_inventory = function(self, fn, actor) for i = 1, #INV do fn(actor, INV[i]) end end
function npc(id, name, comm)
    local o = { alive_v = true, rel = 1 }
    o.id = function() return id end
    o.name = function() return "npc" .. id end
    o.character_name = function() return name end
    o.character_community = function() return comm end
    o.alive = function() return o.alive_v end
    o.relation = function() return o.rel end
    return o
end
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
                        "local f = assert(loadstring(src, 'almanac_learn')) setfenv(f, e) f() return e end")
        M = load(src)
        M.on_game_start()
        cb = g.CALLBACKS
        dnm, vasya = g.DNM, g.stalker("Vasya")

        def calls():
            return [(c.sec, c.kind, c.who, c.place, c.quiet) for c in g.CALLS.values()]

        def tip(msg, *rest):
            return g.dynamic_news_helper.send_tip(msg, *rest)

        cb.actor_on_first_update()
        # the news, queued: nothing learned; every argument in and result out passes through
        eq("found news", dnm.FoundArtefact(dnm, vasya, g.item("af_a"), "extra"), (True, "pushed"))
        eq("its arguments", g.ARGS[1], "extra")
        eq("queued, not learned", calls(), [])
        # sent: learned, from him, where he stood; the helper's arguments and results pass through
        eq("sent", tip("news af_a 1", "hdr", 3, 4), (None, "tip"))
        eq("helper's arguments", list(g.SENT[1].values()), ["news af_a 1", "hdr", 3, 4])
        eq("learned", calls(), [("af_a", "news", "Vasya", "place of Vasya", None)])
        tip("news af_a 1")
        eq("once", len(calls()), 1)
        # not queued (the news is off): nothing, even when the same text goes out
        g.PUSH = False
        eq("not queued", dnm.FoundArtefact(dnm, vasya, g.item("af_b"), None), (False, "no"))
        g.PUSH = True
        tip("news af_b 2")
        # the queue's top is still the old, sent news: it mustn't be taken for this one
        tip("news af_a 1")
        eq("not queued, not learned", len(calls()), 1)
        # not an artifact, or news of another kind at the top of the queue: nothing
        dnm.FoundArtefact(dnm, vasya, g.item("wpn_pm"), None)
        tip("news wpn_pm 3")
        g.PUSH_TY = "death"
        dnm.FoundArtefact(dnm, vasya, g.item("af_b"), None)
        tip("news af_b 4")
        g.PUSH_TY = "artifact"
        eq("not an artifact's news", len(calls()), 1)
        # sent but failed (no actor): nothing
        dnm.FoundArtefact(dnm, vasya, g.item("af_c"), None)
        g.TIP_RESULT = False
        tip("news af_c 5")
        g.TIP_RESULT = None
        eq("failed to send", len(calls()), 1)
        # the cap: past 64 queued, the oldest are forgotten
        dnm.FoundArtefact(dnm, vasya, g.item("af_b"), None)   # "news af_b 6"
        for i in range(70):
            dnm.FoundArtefact(dnm, g.stalker("S%d" % i), g.item("af_c"), None)
        tip("news af_b 6")
        eq("capped", [c for c in calls() if c[0] == "af_b"], [])
        tip("news af_c 76")
        eq("still working", calls()[-1][:3], ("af_c", "news", "S69"))
        # queued by his id (dEmergence's news fixes): learned all the same; another's id: not his
        petya = g.stalker("Petya", 12)
        g.PUSH_ID = 99
        dnm.FoundArtefact(dnm, petya, g.item("af_d"), None)   # "news af_d 77"
        tip("news af_d 77")
        eq("another's news", [c for c in calls() if c[0] == "af_d"], [])
        g.PUSH_ID = True
        dnm.FoundArtefact(dnm, petya, g.item("af_d"), None)   # "news af_d 78"
        g.PUSH_ID = None
        tip("news af_d 78")
        eq("queued by id", calls()[-1], ("af_d", "news", "Petya", "place of Petya", None))
        # tasks: the first read after a load is quiet, then not; only artifacts; from the giver
        g.TASKS["t1"] = lua.table_from({"task_giver_id": 7})
        g.TASKS["t2"] = lua.table_from({"task_giver_id": 8})
        g.VARS["t1_fetch"], g.VARS["t2_fetch"] = "af_b", "wpn_pm"
        before = len(calls())
        g.NOW = 2000
        cb.actor_on_update()
        eq("task", calls()[before:], [("af_b", "task", "Sidorovich", None, True)])
        g.TASKS["t3"] = lua.table_from({"task_giver_id": 7})
        g.VARS["t3_fetch"] = "af_c"
        g.NOW = 4000
        cb.actor_on_update()
        eq("not before the next read", len(calls()), before + 1)
        g.NOW = 8000
        cb.actor_on_update()
        eq("next read", [c for c in calls()[before + 1:] if c[0] == "af_c"], [("af_c", "task", "Sidorovich", None, False)])
        # the page asks which of the player's tasks want an artifact now, and from whom
        eq("asking", [list(M.asking(s).values()) for s in ("af_b", "af_c", "af_a")], [["Sidorovich"], ["Sidorovich"], []])
        # what a PDA or an Ecologist tells of: unknown, turning up, this level's first
        w = list(M.word_of(10, "here").values())
        eq("word: this level's first", (sorted(w[:2]), w[2:]), (["h1", "h2"], ["e1"]))
        eq("word: one, this level's", list(M.word_of(1, "here").values())[0] in ("h1", "h2"), True)
        eq("word: no level", sorted(M.word_of(10, None).values()), ["e1", "h1", "h2"])
        # a PDA: its owner's notes on as many as its size, once; another owner's anew
        before = len(calls())
        g.set_pda(900, "Vasya", None)
        p = g.pda(900, "itm_pda_uncommon")
        eq("pda: its size", M.on_pda(p, False), 2)
        new = calls()[before:]
        eq("pda: from its owner, here first", (sorted(c[0] for c in new), {c[1:4] for c in new}),
           (["h1", "h2"], {("pda", "Vasya", "place of actor")}))
        eq("pda: once", M.on_pda(p, False), 0)
        g.set_pda(900, "Petya", None)
        eq("pda: another owner's", M.on_pda(p, False), 1)
        # an encrypted one waits for the decryption, then is read; the decryption passes through
        lua.execute("LEARNED = {}")
        g.set_pda(901, "Ivan", "encrypted")
        p2 = g.pda(901, "itm_pda_rare")
        eq("pda: encrypted", M.on_pda(p2, False), 0)
        g.INV[1] = p2
        g.set_pda(901, "Ivan", None)
        g.ui_pda_npc_tab = lua.eval("{ unlock_encrypted_pda = function(x) UNLOCKED = x return 'r1', 'r2' end }")
        eq("decryption wrapped", M.wrap_decrypt(), True)
        before = len(calls())
        eq("decryption passes through", (g.ui_pda_npc_tab.unlock_encrypted_pda("v"), g.UNLOCKED), (("r1", "r2"), "v"))
        eq("decrypted, read", sorted(c[0] for c in calls()[before:]), ["e1", "h1", "h2"])
        g.set_pda(902, None, None)
        eq("pda: no owner", M.on_pda(g.pda(902, "itm_pda_common"), False), 0)
        eq("not a pda", M.on_pda(g.pda(903, "wpn_pm"), False), 0)
        # an Ecologist: one a day, from him, this level's first
        lua.execute("LEARNED = {}")
        actor, eco = g.db.actor, g.npc(50, "Kruglov", "ecolog")
        eq("talk: an Ecologist", M.talk_ok(actor, eco), True)
        eq("talk: names one, this level's", M.talk_text(actor, eco) in ("Studying Aitch One", "Studying Aitch Two"), True)
        before = len(calls())
        M.talk_told(actor, eco)
        eq("talk: learned from him", [c[1:4] for c in calls()[before:]], [("talk", "Kruglov", "place of npc50")])
        eq("talk: once a day", M.talk_ok(actor, eco), False)
        g.DATE[3] = 15
        eq("talk: the next day", M.talk_ok(actor, eco), True)
        # what he'd tell, come to know since, he picks again
        first = M.talk_text(actor, eco)
        names = {"Studying Aitch One": "h1", "Studying Aitch Two": "h2", "Studying Ee One": "e1"}
        g.LEARNED[names[first]] = True
        M.talk_ok(actor, eco)
        eq("talk: picks again", M.talk_text(actor, eco) != first, True)
        eq("talk: not a Loner", M.talk_ok(actor, g.npc(51, "Vasya", "stalker")), False)
        hostile = g.npc(52, "Nikolai", "ecolog")
        hostile.rel = 2
        eq("talk: not when hostile", M.talk_ok(actor, hostile), False)
        dead = g.npc(53, "Semen", "ecolog")
        dead.alive_v = False
        eq("talk: not dead", M.talk_ok(actor, dead), False)
        lua.execute("LEARNED = { h1 = true, h2 = true, e1 = true }")
        other = g.npc(54, "Ozersky", "ecolog")
        eq("talk: nothing new", (M.talk_ok(actor, other), M.talk_text(actor, other)), (False, "Nothing"))
        # nothing to wrap: the wrappers stand aside
        g.dynamic_news_manager = None
        M2 = load(src)
        eq("no news manager", M2.wrap_news(), False)
    except Exception as e:
        fails.append("the run crashed: %s" % str(e).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
