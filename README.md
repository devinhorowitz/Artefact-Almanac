# Artefact Almanac

**A PDA guide to the Zone's artifacts.** Every artifact in your game with its stat card, tier,
the detectors that see it and where the Zone makes it, and a crafting tree that says how much a
higher tier takes. Later, word from a scientific network, earned with your standing, that an
artifact you want could be in a region.

A mod for the S.T.A.L.K.E.R. Anomaly modpack G.A.M.M.A. (Anomaly 1.5.3 with Modded Exes), a
sibling to [Seasons of the Zone](https://github.com/devinhorowitz/seasonsofthezone),
[Arsenal](https://github.com/devinhorowitz/GAMMA-Arsenal-App) and
[Factions of the Zone](https://github.com/devinhorowitz/factionsofthezone).

## Status

Early development. The plan is in [docs/DESIGN.md](docs/DESIGN.md).

**The in-game census** (`gamedata/scripts/almanac_census.script`, the only thing the mod holds so
far). Once after each load, and once after each emission and psi storm, it counts every artifact the
game holds, level by level: the ones lying free, by kind, with who spawned them (a field or Dynamic
Anomalies) and how long ago Artefacts Reinvention's despawner first saw them, and the ones someone
owns (you, a stalker, a box, a mutant). It also lists the levels due their post-emission roll. It
only reads, and takes about 30 ms. Each census is one line in `almanac_census.jsonl` in the game's
appdata folder (`<Anomaly>\appdata`), with a summary line in the game's log:

```
[almanac-census] 2018-11-02 08:47 (load) on k01_darkscape: 3 free here, 23 free elsewhere, 15 owned, 33 levels due, 29 ms
```

**The catalog** (`gamedata/scripts/almanac_data.script`), what the Almanac's pages will read:
built once per load from the running game's configs, it holds every artifact with its containers,
tier and detectors, the workshop's recipes, each level's anomaly fields and the chance a field's pick
names each artifact, and Dynamic Anomalies' lists. Nothing shows it yet.

`python -I tools/build.py` checks the mod and installs it as the MO2 mod "Artefact Almanac"
(`--mods <folder>` for another MO2 instance). `python -I tools/catalog_lua.py` runs the catalog over
an install's configs and compares it with the offline census.

**The census** reads an install's configs as the game would (Mod Organizer 2's file order and
DLTX) and writes what the Almanac will show: every artifact with its card, tier, perk and
detectors; every recipe and each artifact's tree to the bottom; each level's fields and Dynamic
Anomalies list; who sells or drops each book and the Artefact Melter; and the artifacts that never
turn up. It changes nothing.

```
python -I tools/census.py [OUT_DIR]
```

Paths come from `ALMANAC_GAMMA`, `ALMANAC_PROFILE`, `ALMANAC_ANOMALY` and `ALMANAC_BASE_CONFIGS`
(see `tools/gamecfg.py`). It needs Python 3 and `lupa` with LuaJIT 2.0.

## Tests

```
python -I tools/test_census.py
python -I tools/test_ingame_census.py
python -I tools/test_catalog.py
python -I tools/mutants.py
```

Each test lists mutants, broken copies of the code it covers; `mutants.py` checks that every one
fails.

## License

MIT. See [LICENSE](LICENSE).
