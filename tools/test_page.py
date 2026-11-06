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
    "need_missing": ('for _, l in ipairs(count_lines(C, nd.missing, "warn")) do', 'for _, l in ipairs({}) do'),
    "sort_quotes": ("""return string.lower((name:gsub('^[%s"\\'\\171\\187]+', "")))""", "return string.lower(name)"),
    "found_known": ("    if found(sec) or learned(sec) then\n        return true\n    end\n", "    if learned(sec) then\n        return true\n    end\n"),
    "learned_known": ("    if found(sec) or learned(sec) then\n", "    if found(sec) then\n"),
    "heard_line": ("    elseif heard then\n", "    elseif false then\n"),
    "found_count": ("        if found(sec) then\n            n = n + 1\n", "        if true then\n            n = n + 1\n"),
    "group_hidden": ('        if total > 0 or g.id == "all" then\n', "        if true then\n"),
    "shown_tier": ("        return a.tier - 1\n", "        return a.tier\n"),
    "shown_from_two": ("a.tier and a.tier >= 2 then\n        return a.tier - 1", "a.tier and a.tier >= 1 then\n        return a.tier - 1"),
    "junk_kind": ('    if a.kind == "i_arty_junk" then\n        s = t("st_almanac_kind_junk")\n', '    if false then\n        s = t("st_almanac_kind_junk")\n'),
    "made_part_link": ('art and "body" or "dim", art }', 'art and "body" or "dim", nil }'),
    "into_link": ('u.depth == 1 and "body" or "dim",\n                              u.sec }', 'u.depth == 1 and "body" or "dim",\n                              nil }'),
    "count_link": ('{ f("st_almanac_part", x.name, x.n), role, x.sec }', '{ f("st_almanac_part", x.name, x.n), role }'),
    "book_source_unread": ("local src = unread and source_text(C, r.book)", "local src = source_text(C, r.book)"),
    "melter_line": ("    if nd.crafts > 0 and (have[almanac_data.MELTER] or 0) == 0 then\n", "    if false then\n"),
    "melter_carried": ("    if nd.crafts > 0 and (have[almanac_data.MELTER] or 0) == 0 then\n", "    if nd.crafts > 0 then\n"),
    "drop_range": ("lo = math.min(lo or d.chance, d.chance)", "lo = d.chance"),
    "any_rank": ('        if ranks[""] then\n', "        if false then\n"),
    "wanted_now": ("for _, who in ipairs(ok and now or {}) do", "for _, who in ipairs({}) do"),
    "wanted_listed": ("    if W and W.arts[a.sec] then\n", "    if W then\n"),
    "caption_found": ("                if found(sec) then\n                    fd = fd + 1\n", "                if false then\n                    fd = fd + 1\n"),
    "supply_need": ("    put(need_block(C, a, supply, eager, range))", "    put(need_block(C, a, have, eager, range))"),
    "stash_note": ('    if range then\n        lines[#lines + 1] = { f("st_almanac_need_stashes", range), "dim" }',
                   '    if false then\n        lines[#lines + 1] = { f("st_almanac_need_stashes", range), "dim" }'),
    "supply_caller": ("    if have == nil and _supply then\n", "    if _supply then\n"),
    "caption_counts": ('g.name, g.known, g.total, g.found)', 'g.name, g.total, g.known, g.found)'),
    "tree_link": ('{ t("st_almanac_tree_open"), "body", a.sec, "tree" }', '{ t("st_almanac_tree_open"), "body", a.sec }'),
    "tree_book_short": ('return n:match("(%S+%s+%S*%d%S*)%s*$") or n', "return n"),
    "tree_unread": ("unread = unread or not almanac_trees.book_known(b)", "unread = false"),
    "tree_zone": ("        if #order > 0 then\n            layers = layers + 1\n", "        if true then\n            layers = layers + 1\n"),
    "tree_under_dim": ('            n.role = dim and "dim" or "link"\n', '            n.role = "link"\n'),
    "tree_part_dim": ('role = spare and "dim" or role }', "role = role }"),
    "tree_carried_parts": ('local spare = dim or n.state == "carried"', "local spare = dim"),
    "tree_crafts": ("                    crafts = crafts + n.n - n.got\n", "                    crafts = crafts + n.n\n"),
    "tree_find_more": ("local s = n.got > 0 and f(\"st_almanac_tree_find_more\", rest)", "local s = false"),
    "tree_supply": ("    local supply = supply_for(have)\n    local C", "    local supply = carry(have)\n    local C"),
    "held_role": ('got >= n and "good" or (got == 0 and "warn" or "heading")', 'got >= n and "good" or "warn"'),
    "kind_level": ('        s = f("st_almanac_kind_level", s, t(id))\n', ""),
    "mutant_kind": ('        return kind:find("^i_mutant") ~= nil\n', "        return true\n"),
    "mutant_prefix": ('    return sec:find("^mutant_part_") ~= nil\n', "    return false\n"),
    "totals_items": ('local head = o > 0 and f("st_almanac_totals_items", tt.crafts, n_arts, m, o) or',
                     'local head = false and f("st_almanac_totals_items", tt.crafts, n_arts, m, o) or'),
    "tree_sum_items": ('out.sum = o > 0 and f("st_almanac_tree_sum_items"', 'out.sum = false and f("st_almanac_tree_sum_items"'),
}

WORLD = r"""
STR = {
    st_almanac_fields = "Fields: %s", st_almanac_dao = "DAO: %s", st_almanac_dao_random = "DAO anywhere",
    st_almanac_and_more = "%s and %s more", st_almanac_part = "%s x%s", st_almanac_made_book = "Book: %s",
    st_almanac_made_other = "Or (%s): %s", st_almanac_src_sold = "Sold by %s", st_almanac_src_carried = "Carried by %s (%s)",
    st_almanac_src_carried_any = "Carried (%s)", st_almanac_src_none = "Nowhere.", st_almanac_need_book = "unread: %s. %s",
    st_almanac_need_melter = "No melter. %s", st_almanac_wanted_now = "Task for %s", st_almanac_wanted_named = "Tasks from %s",
    st_almanac_wanted_factions = "Squads of %s", st_almanac_wanted_some = "Some tasks", st_almanac_wanted_none = "No task",
    st_rank_master = "Master", st_rank_legend = "Legend", stalker = "Loners", ecolog = "Ecologists",
    st_almanac_need_stashes = "Stashes %s",
    st_almanac_book_unread = "%s (unread)", st_almanac_book_builtin = "built in", st_almanac_into_later = "then %s",
    st_almanac_totals = "%s crafts, %s bottom, %s parts", st_almanac_need_done = "all there: %s",
    st_almanac_need_missing = "%s crafts, missing %s",
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
    mp_det = { inv_name = "MP" }, book1 = { inv_name = "Vol1" }, book2 = { inv_name = "Vol2" },
    melter = { inv_name = "Melter" },
}
ini_sys = {
    r_string_ex = function(_, s, k) return INI[s] and INI[s][k] or nil end,
    section_exist = function(_, s) return INI[s] ~= nil end,
}
MCM = {}
ui_mcm = { get = function(k) return MCM[k] end }
ARTICLES, NOTES = {}, {}
ui_pda_encyclopedia_tab = {
    is_unlocked_article = function(id) return ARTICLES[id] == true end,
    is_unlocked_note = function(id) return NOTES[id] == true end,
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
        { key = "r_k", result = "k", book = "book2", parts = { { "b", 1 } } },
    },
    -- book1 sold, book2 carried at two ranks (the lower chance first), the Melter sold; and three
    -- made up for source_text: nowhere, any rank, both ways
    sources = {
        book1 = { sellers = { ["Prof H"] = true, ["Prof S"] = true }, drops = {} },
        book2 = { sellers = {}, drops = { { comm = "stalker", rank = "master", chance = 0.02 },
                                          { comm = "dolg", rank = "legend", chance = 0.04 } } },
        melter = { sellers = { ["Prof H"] = true }, drops = {} },
        nowhere = { sellers = {}, drops = {} },
        any_rank = { sellers = {}, drops = { { comm = "stalker", rank = "", chance = 0.1 } } },
        both = { sellers = { ["Prof S"] = true }, drops = { { comm = "army", rank = "legend", chance = 0.04 } } },
    },
    wanted = { arts = { b = true, c = true }, names = { Sakharov = true, Beard = true }, factions = { stalker = true, ecolog = true } },
}
CAT.order = { "a_junk", "b", "c", "j2", "k", "q", "w", "z" }
almanac_data = { catalog = function() return CAT end, MELTER = "melter",
                 RANKS = { "", "novice", "trainee", "experienced", "professional", "veteran", "expert", "master", "legend" } }
ASKING = {}
almanac_learn = { asking = function(sec) return ASKING[sec] or {} end }
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
STR.st_almanac_tab_caption = "%s: %s of %s known, %s found"
STR.st_almanac_tree_title = "%s: tree"
STR.st_almanac_tree_sum = "%s crafts, %s layers, %s bottom, %s parts"
STR.st_almanac_tree_nobook = "No book"
STR.st_almanac_tree_crafts = "Crafts: %s"
STR.st_almanac_tree_unread = "unread"
STR.st_almanac_tree_zone = "Zone"
STR.st_almanac_tree_zone_sub = "makes these"
STR.st_almanac_tree_carried = "carried"
STR.st_almanac_tree_carried_n = "carried %s"
STR.st_almanac_tree_under = "not needed"
STR.st_almanac_tree_find = "find one"
STR.st_almanac_tree_find_n = "find %s"
STR.st_almanac_tree_find_more = "find %s more"
STR.st_almanac_tree_partial = "carried %s of %s"
INI.book3 = { inv_name = "The Art of Fusion Vol. 3" }
INI.part_p.kind = "i_mutant_part"
INI.kero = { inv_name = "Kero", kind = "i_misc" }
STR.st_almanac_kind_level = "%s, level %s"
STR.st_art_level_4 = "Four"
STR.st_almanac_totals_items = "%s crafts, %s bottom, %s parts, %s items"
STR.st_almanac_tree_sum_items = "%s crafts, %s layers, %s bottom, %s parts, %s items"
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
        blocks = [(b.heading, [(l[1], l[2], l[3]) for l in lst(b.lines)]) for b in lst(e.blocks)]
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
        eq("caption", P.caption(lst(P.groups(carry_b))[1]), "Junk: 1 of 2 known, 0 found")
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
                               "st_almanac_h_into", "st_almanac_h_wanted", "st_almanac_h_totals", "st_almanac_h_need"])
        B = dict(e["blocks"])
        eq("detectors", B["st_almanac_h_detectors"], [("Bear, Echo", "body", None)])
        eq("where", B["st_almanac_h_where"], [("Fields: lvl10, lvl9, lvl8, lvl7, lvl6, lvl5, lvl4, lvl3 and 2 more", "body", None)])
        # the recipe: its book (built in: no source), then a part a line, an artifact's a link
        eq("made", B["st_almanac_h_made"], [("st_almanac_tree_open", "body", "b"), ("Book: built in", "body", None), ("Junk A x1", "body", "a_junk"), ("Paw x5", "dim", None)])
        eq("into", B["st_almanac_h_into"], [("Cee", "body", "c"), ('"Kay"', "body", "k")])
        eq("totals", B["st_almanac_h_totals"], [("1 crafts, 1 bottom, 5 parts", "body", None), ("Junk A x1", "body", "a_junk"),
                                                ("Paw x5", "dim", None)])
        # no Melter in the pack: where one comes from
        eq("need", B["st_almanac_h_need"], [("1 crafts, missing 3", "body", None), ("Paw x3", "warn", None),
                                            ("No melter. Sold by Prof H.", "warn", None)])
        # asked for: the player's own task, then fetch tasks' givers by name and by faction
        eq("wanted", B["st_almanac_h_wanted"], [("Tasks from Beard, Sakharov", "body", None), ("Squads of Ecologists, Loners", "body", None)])
        g.ASKING["b"] = lua.table_from(["Sidorovich"])
        eq("wanted now", dict(entry("b", carry_b)["blocks"])["st_almanac_h_wanted"][0], ("Task for Sidorovich", "good", None))
        g.ASKING["b"] = None
        # where a book or the Melter comes from
        eq("sources", [P.source_text(g.CAT, s) for s in ("book1", "book2", "nowhere", "any_rank", "both", "none_such")],
           ["Sold by Prof H, Prof S.", "Carried by Master, Legend (2-4%).", "Nowhere.", "Carried (10%).",
            "Sold by Prof S. Carried by Legend (4%).", None])
        # a find makes it known, after the pack is empty again, and the entry says when and how
        g.FOUND["z"] = lua.table_from({"date": "14.05.2012", "how": "picked up"})
        eq("known by a find", (P.known("z", none), [r[0] for r in rows("t3", none) if r[2]]), (True, ["z"]))
        eq("found line", (P.entry("z", none).found[1], P.entry("z", none).found[2]), ("Found 14.05.2012: picked up", "good"))
        eq("not found line", P.entry("b", carry_b).found[1], "Not found")
        eq("counts", list(P.counts(none)), [1, 7, 1])
        eq("found in the caption", P.caption(lst(P.groups(none))[4]), "st_almanac_group_t3: 1 of 2 known, 1 found")
        eq("not asked for", dict(entry("z", none)["blocks"])["st_almanac_h_wanted"], [("No task", "dim", None)])
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
        eq("where c", B["st_almanac_h_where"], [("DAO: lvl3, lvl2", "body", None), ("DAO anywhere", "body", None)])
        # an unread book: where it comes from, under it; and again with what you carry
        eq("made c", B["st_almanac_h_made"], [("st_almanac_tree_open", "body", "c"), ("Book: Vol1 (unread)", "warn", None), ("Sold by Prof H, Prof S.", "dim", None),
                                              ("Bee x2", "body", "b")])
        eq("need c", B["st_almanac_h_need"][-2:], [("No melter. Sold by Prof H.", "warn", None),
                                                   ("unread: Vol1. Sold by Prof H, Prof S.", "warn", None)])
        # with the Melter in the pack, no word of one; with the book read, no word of where it's sold
        e = entry("c", lua.table_from({"c": 1, "melter": 1}))
        eq("melter carried", [l for l in dict(e["blocks"])["st_almanac_h_need"] if l[0].startswith("No melter")], [])
        g.NOTES["encyclopedia__notes_book1"] = True
        eq("book read", dict(entry("c", lua.table_from({"c": 1}))["blocks"])["st_almanac_h_made"][1:], [("Book: Vol1", "body", None), ("Bee x2", "body", "b")])
        g.NOTES["encyclopedia__notes_book1"] = None
        # the page's own fill: what's known by what's carried, crafting with the stashes in range too
        P.set_have(lua.table_from({}), lua.table_from({"a_junk": 1, "part_p": 5, "melter": 1}), 10)
        eq("stashes make nothing known", P.known("a_junk", None), False)
        g.MCM["almanac/jailbreak"] = True
        eq("need with the stashes", dict(entry("b", None)["blocks"])["st_almanac_h_need"],
           [("all there: 1", "good", None), ("Stashes 10", "dim", None)])
        eq("a caller's have alone", dict(entry("b", carry_b)["blocks"])["st_almanac_h_need"][0], ("1 crafts, missing 3", "body", None))
        g.MCM["almanac/jailbreak"] = None
        P.set_have(None, None, None)
        e = entry("a_junk", lua.table_from({"a_junk": 1}))
        B = dict(e["blocks"])
        eq("into a_junk", B["st_almanac_h_into"], [("Bee", "body", "b"), ("then Cee", "dim", "c"), ('then "Kay"', "dim", "k")])
        eq("no totals for what nothing makes", "st_almanac_h_totals" in B, False)

        # the crafting tree's words: the link in the recipe block opens it
        made = lst(lst(P.entry("c", lua.table_from({"c": 1})).blocks)[2].lines)[0]
        eq("tree link", (made[1], made[3], made[4]), ("st_almanac_tree_open", "c", "tree"))
        eq("tree book names", [P.tree_book(b) for b in ("book3", "book1", "recipe_basic_0")], ["Vol. 3", "Vol1", "No book"])

        def tree(sec, have):
            tr = P.tree(sec, have)
            if tr is None:
                return None
            rows = [(r.label, r.label_role, r.sub, r.unread, [x.sec for x in lst(r.nodes)]) for r in lst(tr.rows)]
            nodes = {}
            for r in lst(tr.rows):
                for x in lst(r.nodes):
                    nodes.setdefault(x.sec, []).append((x.name, x.role, (x.status[1], x.status[2]) if x.status else None,
                                                        [(ln.name, ln.count, ln.role) for ln in lst(x.lines)]))
            return tr.title, tr.sum, tr.leaves, rows, nodes

        title, total, leaves, rows, nodes = tree("c", none)
        eq("tree head", (title, total, leaves), ("Cee: tree", "3 crafts, 2 layers, 2 bottom, 10 parts", 1))
        # c's book unread: its row warns; b's recipe set is no item; the bottom row is the Zone's
        eq("tree rows", rows, [("Vol1", "warn", "Crafts: 1", "unread", ["c"]), ("No book", "heading", "Crafts: 2", None, ["b"]),
                               ("Zone", "heading", "makes these", None, ["a_junk"])])
        eq("tree nodes, nothing held", nodes, {"c": [("Cee", "link", None, [])],
                                               "b": [("Bee", "link", None, [("Paw", "0/10", "warn")])],
                                               "a_junk": [("Junk A", "link", ("find 2", "warn"), [])]})
        g.NOTES["encyclopedia__notes_book1"] = True
        title, total, leaves, rows, nodes = tree("c", lua.table_from({"b": 1, "part_p": 2, "a_junk": 1}))
        g.NOTES["encyclopedia__notes_book1"] = None
        eq("tree rows, some held", [r[:4] for r in rows], [("Vol1", "heading", "Crafts: 1", None), ("No book", "heading", "Crafts: 1", None),
                                                           ("Zone", "heading", "makes these", None)])
        eq("tree nodes, some held", (nodes["b"], nodes["a_junk"]),
           ([("Bee", "link", ("carried 1 of 2", "heading"), [("Paw", "2/5", "heading")])], [("Junk A", "link", ("carried", "good"), [])]))
        title, total, leaves, rows, nodes = tree("c", lua.table_from({"b": 2, "part_p": 9}))
        eq("tree under a carried one", (nodes["b"], nodes["a_junk"]),
           ([("Bee", "link", ("carried 2", "good"), [("Paw", "0/10", "dim")])], [("Junk A", "dim", ("not needed", "dim"), [])]))
        eq("tree finds more", tree("c", lua.table_from({"a_junk": 1}))[4]["a_junk"][0][2], ("find 1 more", "warn"))
        eq("tree finds one", tree("b", none)[4]["a_junk"][0][2], ("find one", "warn"))
        eq("no tree for what nothing makes", P.tree("a_junk", none), None)
        # the page's own fill: the stashes in range count, as in the entry's last block
        P.set_have(lua.table_from({}), lua.table_from({"part_p": 10}), 10)
        eq("tree with the stashes", tree("c", None)[4]["b"][0][3], [("Paw", "10/10", "good")])
        P.set_have(None, None, None)

        # with Klondaik: its own level beside the tier, by its own strings; one it doesn't name, none
        arts.k.art_level = 4
        eq("Klondaik's level", P.kind_line(arts.k), "Artifact 3, level Four")
        arts.k.art_level = 99
        eq("a level with no name", P.kind_line(arts.k), "Artifact 3")
        arts.k.art_level = None
        # a recipe taking an item that is no mutant part: counted apart, in the totals and the tree
        eq("mutant parts", [P.is_mutant_part(s) for s in ("part_p", "kero", "mutant_part_x")], [True, False, True])
        eq("totals, parts only", dict(entry("k", lua.table_from({"k": 1}))["blocks"])["st_almanac_h_totals"][0][0],
           "2 crafts, 1 bottom, 5 parts")
        r_k = [r for r in lst(g.CAT.recipes) if r.key == "r_k"][0]
        r_k.parts[2] = lua.table_from(["kero", 3])
        eq("totals with other items", dict(entry("k", lua.table_from({"k": 1}))["blocks"])["st_almanac_h_totals"][0][0],
           "2 crafts, 1 bottom, 5 parts, 3 items")
        eq("tree sum with other items", tree("k", none)[1], "2 crafts, 2 layers, 1 bottom, 5 parts, 3 items")
        r_k.parts[2] = None
    except Exception as ex:
        fails.append("the run crashed: %s" % str(ex).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
