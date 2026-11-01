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
- **`tools/build.py`** checks the mod (scripts compile under LuaJIT 2.0, versions match, tests
  pass) and installs it into MO2.
