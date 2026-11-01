# Changelog

## Unreleased

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
- **PDAs and Ecologists:** a dead stalker's PDA you pick up has its owner's notes on one to three
  artifacts you don't know (by its size), and any Ecologist will tell you of one, once a day each
  ("Have your people learned anything new about artifacts?"); those found on the level you're on
  come first.
- **`tools/build.py`** checks the mod (scripts compile under LuaJIT 2.0, versions match, tests
  pass) and installs it into MO2.
