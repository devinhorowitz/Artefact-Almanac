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
- **The page:** the Almanac in your PDA, laid out like the Guide: groups by tier, the artifacts, and
  each one's entry with the inventory's stat card, detectors, where the Zone makes it, its recipe,
  what it goes into, and how much you still need. Open it from Mod App Creator's tile, its own PDA
  tab, or a key that opens it flat (MCM). Artifacts you haven't met stay unknown unless MCM's "Show
  everything" is on.
- **`tools/build.py`** checks the mod (scripts compile under LuaJIT 2.0, versions match, tests
  pass) and installs it into MO2.
