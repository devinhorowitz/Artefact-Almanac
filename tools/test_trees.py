"""Run almanac_trees.script under LuaJIT 2.0 against a small hand-made catalog and check its trees.

The catalog: a junk artifact and an artifact nothing makes; b made from the junk and 5 of a part
(and, second, from the other artifact); c made from 2 b, the junk and 2 of another part; d and e
made from each other; h made from b and c; k made from the artifact nothing makes. Checked: the
tree under c, its totals with and without the "artificer eagerness" achievement, a loop, the same
artifact in two branches, a bottom artifact that isn't junk, what each goes into, what one more
takes when the player already holds some of it (and that their counts aren't changed), the
inventory count, and which books the workshop would allow.

    python test_trees.py            the real script
    python test_trees.py MUTANT     a broken copy (see MUTANTS); the run must fail
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lua_jit import L  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "almanac_trees.script")

#: name -> (text in the script, its broken replacement); each must make this test fail
MUTANTS = {
    "first_recipe": ("local key = a and a.made_by[1]", "local key = a and a.made_by[#a.made_by]"),
    "eager_over_4": ("if eager and n > 4 then", "if eager and n >= 4 then"),
    "multiply": ("local k = amount(p[2], eager) * n", "local k = amount(p[2], eager)"),
    "loop": ("    if not r or path[sec] then\n", "    if not r then\n"),
    "path_reset": ("    path[sec] = nil\n    return node\n", "    return node\n"),
    "junk": ("if C.artifacts[node.sec].kind == KIND_JUNK then", "if true then"),
    "up_depth": ("out[#out + 1] = { sec = res, via = key, depth = depth }", "out[#out + 1] = { sec = res, via = key, depth = 1 }"),
    "need_top": ("        if not top then\n", "        if true then\n"),
    "need_copy": ("    local left = {}\n    for k, v in pairs(have or {}) do\n        left[k] = v\n    end\n",
                  "    local left = have or {}\n"),
    "missing_count": ("            t.missing_count = t.missing_count + n\n", ""),
    "need_eager": ("want(p[1], amount(p[2], eager) * n, path)", "want(p[1], p[2] * n, path)"),
    "book_item": ("    if not ini_sys:section_exist(book) then\n        return true\n",
                  "    if not ini_sys:section_exist(book) then\n        return false\n"),
    "carried_count": ("add(t, item:section(), 1)", "t[item:section()] = 1"),
}

WORLD = r"""
local function art(sec, kind, made_by, used_in)
    return { sec = sec, kind = kind, made_by = made_by, used_in = used_in }
end
CAT = {
    artifacts = {
        a_junk = art("a_junk", "i_arty_junk", {}, { "r_b", "r_c" }),
        f = art("f", "i_arty", {}, { "x_b2", "r_k" }),
        b = art("b", "i_arty", { "r_b", "x_b2" }, { "r_c", "r_h" }),
        c = art("c", "i_arty", { "r_c" }, { "r_h" }),
        d = art("d", "i_arty", { "r_d" }, { "r_e" }),
        e = art("e", "i_arty", { "r_e" }, { "r_d" }),
        h = art("h", "i_arty", { "r_h" }, {}),
        k = art("k", "i_arty", { "r_k" }, {}),
    },
    recipes = {
        { key = "r_b", result = "b", book = "book1", parts = { { "a_junk", 1 }, { "part_p", 5 } } },
        { key = "x_b2", result = "b", book = "book3", parts = { { "f", 1 } } },
        { key = "r_c", result = "c", book = "book2", parts = { { "b", 2 }, { "a_junk", 1 }, { "part_q", 2 } } },
        { key = "r_d", result = "d", book = "book1", parts = { { "e", 1 } } },
        { key = "r_e", result = "e", book = "book1", parts = { { "d", 1 } } },
        { key = "r_h", result = "h", book = "book2", parts = { { "b", 1 }, { "c", 1 } } },
        { key = "r_k", result = "k", book = "book1", parts = { { "f", 1 }, { "part_p", 1 } } },
    },
}
almanac_data = { catalog = function() return CAT end }
SECTIONS = { book1 = true, book2 = true }
NOTES = { encyclopedia__notes_book1 = true }
ini_sys = { section_exist = function(_, s) return SECTIONS[s] == true end }
ui_pda_encyclopedia_tab = { is_unlocked_note = function(n) return NOTES[n] == true end }
ITEMS = { "a_junk", "part_p", "a_junk", "wpn_pm" }
db = { actor = { iterate_inventory = function(self, fn)
    for i, s in ipairs(ITEMS) do fn(self, { section = function() return s end }) end
end } }
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

    lua = L.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(WORLD)
    env = lua.eval("function(src) local e = setmetatable({}, { __index = _G }) local f = assert(loadstring(src, 'almanac_trees')) setfenv(f, e) f() return e end")
    T = env(src)

    def d(t):
        return {k: v for k, v in t.items()} if t is not None else None

    def totals(sec, eager=False):
        t = T.totals(sec, eager)
        if t is None:
            return None
        return {"crafts": t.crafts, "books": sorted(t.books.keys()), "artifacts": d(t.artifacts),
                "parts": d(t.parts), "junk": t.junk, "part_count": t.part_count}

    def node(x):
        return {"sec": x.sec, "n": x.n, "recipe": x.recipe,
                "parts": [node(x.parts[i]) for i in range(1, len(x.parts) + 1)]}

    try:
        eq("amount", [T.amount(5, True), T.amount(4, True), T.amount(5, False)], [4, 4, 5])
        eq("tree under c", node(T.down("c", False)), {
            "sec": "c", "n": 1, "recipe": "r_c", "parts": [
                {"sec": "b", "n": 2, "recipe": "r_b", "parts": [
                    {"sec": "a_junk", "n": 2, "recipe": None, "parts": []},
                    {"sec": "part_p", "n": 10, "recipe": None, "parts": []}]},
                {"sec": "a_junk", "n": 1, "recipe": None, "parts": []},
                {"sec": "part_q", "n": 2, "recipe": None, "parts": []}]})
        eq("totals c", totals("c"), {"crafts": 3, "books": ["book1", "book2"], "artifacts": {"a_junk": 3},
                                     "parts": {"part_p": 10, "part_q": 2}, "junk": 3, "part_count": 12})
        eq("totals c, eager", totals("c", True)["parts"], {"part_p": 8, "part_q": 2})
        eq("totals of what nothing makes", [totals("a_junk"), totals("f")], [None, None])
        eq("a loop stops", totals("d"), {"crafts": 2, "books": ["book1"], "artifacts": {"d": 1}, "parts": {},
                                        "junk": 0, "part_count": 0})
        eq("b in two branches", totals("h"), {"crafts": 5, "books": ["book1", "book2"], "artifacts": {"a_junk": 4},
                                              "parts": {"part_p": 15, "part_q": 2}, "junk": 4, "part_count": 17})
        eq("a bottom artifact that isn't junk", totals("k"), {"crafts": 1, "books": ["book1"], "artifacts": {"f": 1},
                                                              "parts": {"part_p": 1}, "junk": 0, "part_count": 1})
        up = [(u.sec, u.via, u.depth) for u in T.up("f").values()]
        eq("up from f", up, [("b", "x_b2", 1), ("k", "r_k", 1), ("c", "r_c", 2), ("h", "r_h", 2)])
        eq("up from a_junk", sorted((u.sec, u.depth) for u in T.up("a_junk").values()),
           [("b", 1), ("c", 1), ("h", 2)])

        have = lua.table_from({"b": 1, "a_junk": 1, "part_p": 3, "part_q": 5, "c": 4})
        r = T.need("c", have, False)
        eq("need c", (r.crafts, sorted(r.books.keys()), d(r.used), d(r.missing), r.missing_count, r.done),
           (2, ["book1", "book2"], {"b": 1, "a_junk": 1, "part_p": 3, "part_q": 2}, {"part_p": 2, "a_junk": 1}, 3, False))
        eq("have unchanged", d(have), {"b": 1, "a_junk": 1, "part_p": 3, "part_q": 5, "c": 4})
        r = T.need("c", lua.table_from({"b": 2, "a_junk": 1, "part_q": 2}), False)
        eq("need c, all there", (r.crafts, d(r.missing), r.missing_count, r.done), (1, {}, 0, True))
        r = T.need("c", lua.table_from({"a_junk": 3, "part_p": 8, "part_q": 2}), True)
        eq("need c, eager", (r.crafts, d(r.missing), r.done), (3, {}, True))
        eq("need of what nothing makes", T.need("f", lua.table_from({})), None)
        eq("carried", d(T.carried()), {"a_junk": 2, "part_p": 1, "wpn_pm": 1})
        eq("books", [T.book_known("book1"), T.book_known("book2"), T.book_known("recipe_basic_0")], [True, False, True])
    except Exception as e:
        fails.append("the run crashed: %s" % str(e).splitlines()[0])
    for f in fails:
        print("FAIL " + f)
    if fails:
        sys.exit(1)
    print("ok: %d checks" % n[0])


if __name__ == "__main__":
    main()
