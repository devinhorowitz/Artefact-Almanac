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

Early development; nothing to install yet. The plan is in [docs/DESIGN.md](docs/DESIGN.md).

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
python -I tools/mutants.py
```

Each test lists mutants, broken copies of the code it covers; `mutants.py` checks that every one
fails.

## License

MIT. See [LICENSE](LICENSE).
