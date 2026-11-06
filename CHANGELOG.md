# Changelog

## 1.0.1 — 2026-11-06

- **The crafting tree:** an artifact's recipe links to its whole tree, layer by layer, in the page's
  place: the artifact at the top, each craft's artifacts on the row below, wired to it, down to the
  ones only the Zone makes. Each shows its icon, its name (a link to its entry) and the mutant parts
  its own craft takes, counted against what you carry; each row, the book its crafts need and
  whether it's read. An artifact you carry cuts its branch, which dims. Back, or Escape flat,
  returns to the entry.
- A link is followed at the next frame rather than inside its own click.
- **Klondaik** (checked against 1.4e): an artifact's line names Klondaik's own level beside the
  tier ("Artifact, tier 2; Klondaik level 4"), the level its descriptions call "Level: Tier 4", by
  Klondaik's own names (Absolute, Modifier and the rest). Its optional "Artefact spawn modded"
  fields (Agroprom underground, X8, Dead City, the Chernobyl NPP and others) count in "Where the
  Zone makes it".
- Totals and the tree's summary count mutant parts apart from the other items a recipe takes
  (Klondaik's take drugs, kerosene and bandages).

## 1.0.0 — 2026-11-01

- **The census** (`tools/census.py`): a read-only pass over an install's configs, as the game
  reads them, that lists every artifact with its card, tier, perk and detectors, the crafting
  trees, each level's fields and Dynamic Anomalies list, where the books and the Artefact Melter
  come from, and the artifacts that never turn up.
- **The design** (`docs/DESIGN.md`): 1.0 is the almanac and the crafting trees; the survey comes
  in 1.1.
- **The in-game census** (`almanac_census.script`): after each load and each emission or psi storm,
  one line in `almanac_census.jsonl` counting the artifacts lying free and owned on every level,
  who spawned the free ones and how old they are, and the levels due a roll. Read-only.
- **The catalog** (`almanac_data.script`): built once per load from the running game's configs:
  artifacts with containers, tiers and detectors, the workshop's recipes, each level's fields from
  the anomaly zones' own spawn settings, and Dynamic Anomalies' lists. `tools/catalog_lua.py` runs it
  over an install's configs and compares it with the offline census, answer for answer.
- **The crafting trees** (`almanac_trees.script`): any artifact's tree down to the artifacts nothing
  makes and the mutant parts, what it goes into, the totals for one, and what one more takes when
  what you carry is used first, with the workshop's own rules for amounts and books.
- **The page:** the Almanac in your PDA: tabs across the top for all, junk and tiers 1 to 4,
  numbered and marked as the game shows them (tier N has N chevrons, as on its icons), with how
  many you know, the artifacts, and each one's entry with the inventory's stat card, detectors,
  where the Zone makes it, its recipe, what it goes into, and how much you still need. Open it from
  Mod App Creator's tile, its own PDA tab, or a key that opens it flat (MCM). Artifacts you haven't
  met stay unknown unless MCM's "Show everything" is on.
- **Where books come from:** a recipe book you haven't read says who sells it and who may carry one
  ("Carried by Master, Legend-rank stalkers (4%)"), and so does the Artefact Melter when you have
  none with you.
- **Asked for:** each entry says whether one of your tasks wants the artifact now, and which
  traders, squads and named stalkers may ask for one in a fetch task.
- **Links:** every artifact an entry names (its parts, what it goes into, the totals, what's
  missing) opens that artifact's entry. A tab's caption also counts what you've found.
- **Finds:** the first time an artifact comes into your hands, the Almanac remembers it: the date,
  how (picked up, looted, bought, given, made at the Melter) and where, shown on its page, with a
  PDA message (MCM's "Messages" turns them off). Found artifacts stay known. They're kept in your
  save under the Almanac's own key; a save loads fine with the Almanac removed.
- **Hearing of an artifact:** when the radio tells you a stalker found one, or a task asks you for
  one, it stops being unknown, and its entry says who and where ("on the radio, Vasya found one
  in Garbage, near the depot"; "Sakharov asked you for one"), with a PDA message.
- **Russian:** every string of the page, the messages, the Ecologists' talk and MCM, in the game's
  own Russian terms (Плавильщик артефактов, Справочник, учёные).
- **Nearby stashes:** with Craft From Stashes, "With what you carry" also counts what your stashes
  within its range hold (and a Melter in one), as the workshop does, and says so.
- **PDAs and Ecologists:** a dead stalker's PDA you pick up has its owner's notes on one to three
  artifacts you don't know (by its size), and any Ecologist will tell you of one, once a day each
  ("Have your people learned anything new about artifacts?"); those found on the level you're on
  come first.
- **`tools/build.py`** checks the mod (scripts compile under LuaJIT 2.0, versions match, tests
  pass) and installs it into MO2.
- **`tools/release.py`** packages a release zip, and `INSTALL-WITH-CLAUDE.md` lets an AI agent
  install, update or remove the Almanac.
