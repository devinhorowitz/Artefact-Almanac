"""Run almanac_page.script under LuaJIT 2.0, with the real almanac_trees.script, against a small
hand-made catalog, and check what the page says.

The catalog: a junk artifact the fields make; b, tier 2, made from the junk and 5 of a part, seen
by two detectors (and a multiplayer one) and made by fields on many levels; c, tier 3, made from 2 b,
on Dynamic Anomalies' lists and its random pick; z, tier 4, made by nothing at all; q, a quest
artifact with no tier. Checked: what the player knows (carried, the Guide, the jailbreak), which
artifacts are listed, the groups and their counts, the rows' order, an unknown entry that tells
nothing about the artifact, and a known entry's lines: kind, detectors, where, recipes and books,
what it goes into, the totals and what's missing.

    python test_page.py            the real script
    python test_page.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPTS = os.path.join(HERE, "..", "gamedata", "scripts")
PAGE = os.path.join(SCRIPTS, "almanac_page.script")
TREES = os.path.join(SCRIPTS, "almanac_trees.script")

#: name -> (text in almanac_page.script, its broken replacement); each must make this test fail
MUTANTS = {
    "carried": ("    if have and (have[sec] or 0) > 0 then\n", "    if false then\n"),
    "guide": ('return ok and open == true', 'return false'),
    "jailbreak": ("    if jailbreak() then\n        return true\n    end\n    if found(sec)", "    if found(sec)"),
    "unknown_leaks": ('        return { sec = sec, known = false, name = t("st_almanac_unknown"),',
                      '        return { sec = sec, known = false, name = a.name,'),
    "listed": ("    return known(a.sec, have) or turns_up(a)\n", "    return true\n"),
    "turns_up_craft": ("or a.dao_random or #a.made_by > 0", "or a.dao_random"),
    "tier_group": ('return a.kind ~= "i_arty_junk" and a.tier == g.tier', "return a.tier == g.tier"),
    "other_group": ("    return not (a.tier and a.tier >= 2 and a.tier <= 5)\n", "    return a.tier == nil\n"),
    "row_order": ("    table.sort(kn, function(x, y)\n", "    local _ = (function(x, y)\n"),
    "mp_detectors": ('        if not d:find("^mp_") then\n', "        if true then\n"),
    "field_order": ("            return x.w > y.w\n", "            return x.w < y.w\n"),
    "and_more": ("    if #names <= MAX_LEVELS then\n", "    if true then\n"),
    "dao_random": ("    if a.dao_random then\n", "    if false then\n"),
    "book_unread": ("    if not almanac_trees.book_known(book) then\n        return f(\"st_almanac_book_unread\", n)\n",
                    "    if false then\n        return f(\"st_almanac_book_unread\", n)\n"),
    "into_depth": ('u.depth == 1 and name or f("st_almanac_into_later", name)', "name"),
    "need_missing": ('for _, l in ipairs(count_lines(nd.missing, "warn")) do', 'for _, l in ipairs({}) do'),
    "sort_quotes": ("""return string.lower((name:gsub('^[%s"\\'\\171\\187]+', "")))""", "return string.lower(name)"),
    "found_known": ("    if found(sec) or learned(sec) then\n        return true\n    end\n", "    if learned(sec) then\n        return true\n    end\n"),
    "learned_known": ("    if found(sec) or learned(sec) then\n", "    if found(sec) then\n"),
    "heard_line": ("    elseif heard then\n", "    elseif false then\n"),
    "found_count": ("        if found(sec) then\n            n = n + 1\n", "        if true then\n            n = n + 1\n"),
    "group_hidden": ('        if total > 0 or g.id == "all" then\n', "        if true then\n"),
    "shown_tier": ("        return a.tier - 1\n", "        return a.tier\n"),
    "shown_from_two": ("a.tier and a.tier >= 2 then\n        return a.tier - 1", "a.tier and a.tier >= 1 then\n        return a.tier - 1"),
    "junk_kind": ('    if a.kind == "i_arty_junk" then\n        return t("st_almanac_kind_junk")\n    end\n', ""),
    "caption_counts": ('f("st_almanac_tab_caption", g.name, g.known, g.total)', 'f("st_almanac_tab_caption", g.name, g.total, g.known)'),
}

WORLD = r"""
STR = {
    st_almanac_fields = "Fields: %s", st_almanac_dao = "DAO: %s", st_almanac_dao_random = "DAO anywhere",
    st_almanac_and_more = "%s and %s more", st_almanac_part = "%s x%s", st_almanac_made_line = "%s: %s",
    st_almanac_book_unread = "%s (unread)", st_almanac_book_builtin = "built in", st_almanac_into_later = "then %s",
    st_almanac_totals = "%s crafts, %s bottom, %s parts", st_almanac_need_done = "all there: %s",
    st_almanac_need_missing = "%s crafts, missing %s", st_almanac_need_books = "unread: %s",
    st_almanac_kind_arty_tier = "Artifact %s", st_almanac_kind_junk = "Junk", st_almanac_kind_arty = "Artifact",
    st_almanac_weight = "W %s", st_almanac_unknown = "Unknown", st_almanac_unknown_entry = "Not met yet",
    st_almanac_detectors_none = "no detector",
}
game = { translate_string = function(id) return STR[id] or id end }
INI = {
    a_junk = { inv_name = "Junk A" }, b = { inv_name = "Bee", description = "b_descr" }, c = { inv_name = "Cee" },
    z = { inv_name = "Zed" }, q = { inv_name = "Quest" }, part_p = { inv_name = "Paw" },
    j2 = { inv_name = "Junk Two" }, k = { inv_name = '"Kay"' }, w = { inv_name = "Wee" },
    det_echo = { inv_name = "Echo" }, det_bear = { inv_name = "Bear" }, det_bear2 = { inv_name = "Bear" },
    mp_det = { inv_name = "MP" }, book1 = { inv_name = "Vol1" },
}
ini_sys = {
    r_string_ex = function(_, s, k) return INI[s] and INI[s][k] or nil end,
    section_exist = function(_, s) return INI[s] ~= nil end,
}
MCM = {}
ui_mcm = { get = function(k) return MCM[k] end }
ARTICLES = {}
ui_pda_encyclopedia_tab = {
    is_unlocked_article = function(id) return ARTICLES[id] == true end,
    is_unlocked_note = function(id) return false end,
}
game_achievements = { has_achievement = function() return false end }
local function art(sec, kind, tier, t)
    t.sec, t.kind, t.tier = sec, kind, tier
    t.name = INI[sec].inv_name
    t.weight = t.weight or 0.5
    t.fields, t.dao = t.fields or {}, t.dao or {}
    t.detectors, t.made_by, t.used_in = t.detectors or {}, t.made_by or {}, t.used_in or {}
    return t
end
LEVELS = {}
for i = 1, 10 do LEVELS["lvl" .. i] = { 0.1 * i } end
CAT = {
    artifacts = {
        a_junk = art("a_junk", "i_arty_junk", 1, { fields = { lvl1 = { 0.5 } }, used_in = { "r_b" } }),
        b = art("b", "i_arty", 2, { fields = LEVELS, detectors = { "det_echo", "det_bear", "det_bear2", "mp_det" },
                                    made_by = { "r_b" }, used_in = { "r_c", "r_k" } }),
        c = art("c", "i_arty", 3, { dao = { lvl2 = 0.25, lvl3 = 0.75 }, dao_random = true, made_by = { "r_c" } }),
        z = art("z", "i_arty", 4, {}),
        q = art("q", "i_arty", nil, {}),
        j2 = art("j2", "i_arty_junk", 2, { fields = { lvl1 = { 0.5 } } }),
        k = art("k", "i_arty", 4, { made_by = { "r_k" } }),
        w = art("w", "i_arty", 1, { fields = { lvl1 = { 0.5 } } }),
    },
    recipes = {
        { key = "r_b", result = "b", book = "recipe_basic_0", parts = { { "a_junk", 1 }, { "part_p", 5 } } },
        { key = "r_c", result = "c", book = "book1", parts = { { "b", 2 } } },
        { key = "r_k", result = "k", book = "book1", parts = { { "b", 1 } } },
    },
}
CAT.order = { "a_junk", "b", "c", "j2", "k", "q", "w", "z" }
almanac_data = { catalog = function() return CAT end }
FOUND, HEARD = {}, {}
almanac_found = {
    is_found = function(sec) return FOUND[sec] ~= nil end,
    found_at = function(sec) return FOUND[sec] end,
    is_learned = function(sec) return HEARD[sec] ~= nil end,
    learned_at = function(sec) return HEARD[sec] end,
    date_of = function(at) return at.date end,
    describe = function(at) return at.how end,
}
STR.st_almanac_found_on = "Found %s: %s"
STR.st_almanac_not_found = "Not found"
STR.st_almanac_learned_on = "Heard of %s: %s"
STR.st_almanac_group_junk = "Junk"
STR.st_almanac_tab_caption = "%s: %s of %s known"
"""


def run_module(lua, src, name):
    return lua.eval("function(src, name) local e = setmetatable({}, { __index = _G }) "
                    "local f = assert(loadstring(src, name)) setfenv(f, e) f() return e end")(src, name)


def main():
    mutant = sys.argv[1] if len(sys.argv) > 1 else None
    src = open(PAGE, encoding="utf-8").read()
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

    lua = L.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    lua.execute(WORLD)
    g.almanac_trees = run_module(lua, open(TREES, encoding="utf-8").read(), "almanac_trees")
    P = run_module(lua, src, "almanac_page")

    def lst(t):
        return [t[i] for i in range(1, len(t) + 1)] if t is not None else []

    def groups(have):
        return [(x.id, x.known, x.total) for x in lst(P.groups(have))]

    def rows(gid, have):
        return [(x.sec, x.name, x.known) for x in lst(P.rows(gid, have))]

    def entry(sec, have):
        e = P.entry(sec, have)
        if e is None:
            return None
        blocks = [(b.heading, [(l[1], l[2]) for l in lst(b.lines)]) for b in lst(e.blocks)]
        return {"known": e.known, "name": e.name, "kind": e.kind, "blocks": blocks}

    try:
        none = lua.table_from({})
        carry_b = lua.table_from({"b": 1, "a_junk": 1, "part_p": 2})
        # knowing: nothing carried, no article
        eq("known nothing", [P.known(s, none) for s in ("a_junk", "b", "c", "z")], [False] * 4)
        eq("known by carrying", P.known("b", carry_b), True)
        g.ARTICLES["encyclopedia_artefacts_c"] = True
        eq("known by the Guide", P.known("c", none), True)
        g.ARTICLES["encyclopedia_artefacts_c"] = None
        # listed: z and q turn up no way the catalog sees, so only once known
        eq("groups, nothing known", groups(none), [("all", 0, 6), ("junk", 0, 2), ("t1", 0, 1), ("t2", 0, 1), ("t3", 0, 1), ("other", 0, 1)])
        eq("rows, nothing known", [r[0] for r in rows("all", none)], ["a_junk", "b", "c", "j2", "k", "w"])
        eq("rows unknown", {r[1] for r in rows("all", none)}, {"Unknown"})
        eq("groups, b carried", groups(carry_b), [("all", 2, 6), ("junk", 1, 2), ("t1", 1, 1), ("t2", 0, 1), ("t3", 0, 1), ("other", 0, 1)])
        eq("rows, b carried", [(r[0], r[2]) for r in rows("all", carry_b)], [("b", True), ("a_junk", True), ("c", False), ("j2", False), ("k", False), ("w", False)])
        eq("rows t1 and other", (rows("t1", carry_b)[0][0], [r[0] for r in rows("other", carry_b)]), ("b", ["w"]))
        eq("caption", P.caption(lst(P.groups(carry_b))[1]), "Junk: 1 of 2 known")
        g.MCM["almanac/jailbreak"] = True
        eq("groups, jailbreak", groups(none), [("all", 8, 8), ("junk", 2, 2), ("t1", 1, 1), ("t2", 1, 1), ("t3", 2, 2), ("other", 2, 2)])
        eq("sorted without quotes", [r[1] for r in rows("all", none)],
           ["Bee", "Cee", "Junk A", "Junk Two", '"Kay"', "Quest", "Wee", "Zed"])
        g.MCM["almanac/jailbreak"] = None
        # an unknown entry says nothing of the artifact
        ue = entry("c", none)
        flat = repr(ue)
        eq("unknown entry", (ue["known"], ue["name"], ue["kind"]), (False, "Unknown", None))
        eq("unknown entry tells nothing", any(w in flat for w in ("Cee", "DAO", "lvl", "Vol1", "Bee")), False)
        # a known entry
        e = entry("b", carry_b)
        eq("kind", e["kind"], "Artifact 1")
        # the tier as the game shows it: the configs' less one; none for junk, tier 1 or no tier
        arts = g.CAT.artifacts
        eq("shown tiers", [P.kind_line(arts[s]) for s in ("b", "c", "z", "a_junk", "j2", "w", "q")],
           ["Artifact 1", "Artifact 2", "Artifact 3", "Junk", "Junk", "Artifact", "Artifact"])
        heads = [b[0] for b in e["blocks"]]
        eq("headings", heads, ["st_almanac_h_detectors", "st_almanac_h_where", "st_almanac_h_made",
                               "st_almanac_h_into", "st_almanac_h_totals", "st_almanac_h_need"])
        B = dict(e["blocks"])
        eq("detectors", B["st_almanac_h_detectors"], [("Bear, Echo", "body")])
        eq("where", B["st_almanac_h_where"], [("Fields: lvl10, lvl9, lvl8, lvl7, lvl6, lvl5, lvl4, lvl3 and 2 more", "body")])
        eq("made", B["st_almanac_h_made"], [("built in: Junk A x1, Paw x5", "body")])
        eq("into", B["st_almanac_h_into"], [("Cee", "body"), ('"Kay"', "body")])
        eq("totals", B["st_almanac_h_totals"], [("1 crafts, 1 bottom, 5 parts", "body"), ("Junk A x1", "body"), ("Paw x5", "dim")])
        eq("need", B["st_almanac_h_need"], [("1 crafts, missing 3", "body"), ("Paw x3", "warn")])
        # a find makes it known, after the pack is empty again, and the entry says when and how
        g.FOUND["z"] = lua.table_from({"date": "14.05.2012", "how": "picked up"})
        eq("known by a find", (P.known("z", none), [r[0] for r in rows("t3", none) if r[2]]), (True, ["z"]))
        eq("found line", (P.entry("z", none).found[1], P.entry("z", none).found[2]), ("Found 14.05.2012: picked up", "good"))
        eq("not found line", P.entry("b", carry_b).found[1], "Not found")
        eq("counts", list(P.counts(none)), [1, 7, 1])
        g.FOUND["z"] = None
        # heard of without holding one: known, and the entry says so; a find comes first
        g.HEARD["z"] = lua.table_from({"date": "15.05.2012", "how": "on the radio"})
        eq("known by hearing", P.known("z", none), True)
        eq("heard line", (P.entry("z", none).found[1], P.entry("z", none).found[2]), ("Heard of 15.05.2012: on the radio", "heading"))
        g.FOUND["z"] = lua.table_from({"date": "16.05.2012", "how": "picked up"})
        eq("a find first", P.entry("z", none).found[1], "Found 16.05.2012: picked up")
        g.FOUND["z"], g.HEARD["z"] = None, None
        e = entry("c", lua.table_from({"c": 1}))
        B = dict(e["blocks"])
        eq("where c", B["st_almanac_h_where"], [("DAO: lvl3, lvl2", "body"), ("DAO anywhere", "body")])
        eq("made c", B["st_almanac_h_made"], [("Vol1 (unread): Bee x2", "body")])
        eq("need c", B["st_almanac_h_need"][-1], ("unread: Vol1", "warn"))
        e = entry("a_junk", lua.table_from({"a_junk": 1}))
        B = dict(e["blocks"])
        eq("into a_junk", B["st_almanac_h_into"], [("Bee", "body"), ("then Cee", "dim"), ('then "Kay"', "dim")])
        eq("no totals for what nothing makes", "st_almanac_h_totals" in B, False)
    except Exception as ex:
        fails.append("the run crashed: %s" % str(ex).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
