# Design

The Artefact Almanac is a PDA guide to the Zone's artifacts for G.A.M.M.A. (Anomaly 1.5.3 with
Modded Exes, LuaJIT 2.0.4): every artifact in the running game with its stat card, tier, the
detectors that see it and where the Zone makes it; a crafting tree that says how much a higher
tier takes; and, after 1.0, a survey tied to reputation that sends short-lived word that an
artifact you want could be in a region, without making it easy. It's a sibling to Arsenal,
Seasons of the Zone and Factions of the Zone.

**Where it started.** The user, on the G.A.M.M.A. Discord on 2026-10-31: "Artefact almanac being
like a digital guide to artifacts and a sort of crafting tree to explain how much you need to
craft higher tier artefact, along with some sort of "detector" or survery function tied to
reputation, so you get a hint or some sort of short term notice that an artefact you want couple
be in a particular region without making it easy."

This is a plan, not a manual. What exists today is two read-only censuses, one of an install's
configs (`tools/census.py`) and one of the running game's artifacts (`almanac_census.script`), and
the start of the in-game catalog (`almanac_data.script`).

## Decisions (2026-11-01)

- **1.0 is the almanac and the crafting trees.** The survey comes in 1.1.
- **The economy stays as it is.** No items, money, spawns, prices or stat changes. A survey notice
  costs nothing but the standing it needs.
- **The survey's standing is Seasons' networks:** goodwill with the Ecologists, Clear Sky or ISG,
  sharing Seasons' pick when Seasons runs, so one standing buys both the forecast and the survey.
  Factions of the Zone's trust tiers can take the place of raw goodwill once they exist.
- **Your detector limits what you can ask about.** The network reports only artifacts on your
  current detector's list.
- **A notice names a level, and lapses at the next emission or psi storm,** when the fields roll
  again.
- **A notice may be wrong at low standing.** "There could be one" can miss, less often as standing
  grows. "There is one" is never false when it's sent.
- **What counts:** artifacts and junk artifacts. Belt attachments (plates, cooling, oxygen tanks)
  belong to Arsenal ("if it can be 'equipped' then it counts to the arsenal"), mutant hides to the
  Zone Cookbook and Bestiary.
- **Arsenal and the Almanac are separate apps** that link to each other's pages when both are
  installed. No trader prices.
- **Words:** the name is "Artefact Almanac", as the game spells it ("Artefact Melter", "The Art
  of Artefacts Fusion"); prose says "artifact".

## What the census found

`tools/census.py` reads an install's configs after DLTX, as the game would, and writes
`census.json` and `CENSUS.md`. The figures below come from a run over a current G.A.M.M.A.
install on 2026-11-01. Facts marked *inference* weren't checked in game.

- **102 artifacts:** 69 of kind `i_arty` and 33 `i_arty_junk`. 148 containers (lead boxes and the
  three belt containers) fold into the artifact they hold, by the section-name suffix as
  Perk-Based Artefacts reads it. 40 have a PDA Guide article; 31 have a Perk-Based Artefacts hook,
  27 with a perk name in its comment.
- **Detectors:** Echo 63, Bear 73, Veles, Svarog and Grizzly 83, read from `af_class_1` up to the
  first gap (*inference*: the engine's own reading). The Grizzly lists Arot-8 twice. 19 artifacts
  are on no list.
- **Fields** (`bind_anomaly_zone.script`, base): each pick takes one of a field's groups at
  random, then one of the group's artifacts. Artefacts Reinvention registers 34 groups; its
  `af_*_t0` and `af_special` groups are defined but not registered, so the 123 picks of 913 that
  name one spawn nothing. 45 artifacts can come from a field: config tier 2 to 4 artifacts (the
  game's tiers 1 to 3) and 13 kinds of junk. No field yields config tier 5.
- **Dynamic Anomalies** (`drx_da_main_artefacts.script`, run under LuaJIT 2.0 over these configs):
  33 levels with a list (60 artifacts across them), and a random pick, 25% of the time by
  default, from 64 artifacts as its script builds the list. Atom and Fountain are on no list and
  come from that pick or from stashes. New Tasks takes its Lost Soul and Prometheus out of the pick
  at load (`z_nta_compatibility.script`), so in game they come only from its quests; the offline
  census can't see that edit, the in-game catalog does.
- **Crafting** (`craft.ltx` section 7, read as the workshop reads it): 36 recipes make an
  artifact, all at the Artefact Melter: 10 known from the start, 13 from Vol. 1, 9 from Vol. 2, 4
  from Vol. 3. Three more (gauss rounds) take one. Expanded to the bottom, the Compass is 11
  crafts, 4 junk artifacts and 35 mutant parts; the Volat Emerald 11, 4 and 31; the Knot 11, 4 and
  39; the Heart of the Oasis 7, 2 and 27. The Compass, Volat Emerald and Heart of the Oasis (tier
  5) come only from crafting.
- **Books and the Melter:** Sakharov sells Vol. 1 and the Melter, Hermann Vol. 1, Vol. 2 and the
  Melter, at every supply level. Vol. 3 comes only from bodies' `[endgame_recipes]` (G.A.M.M.A.
  Economy's `death_items.ltx`).
- **Never turns up:** 33 artifacts have no field, Dynamic Anomalies, workshop, trader, body,
  stash or loadout source.
  - 13 of Quests Rebalance's 15 Artefact Hunter artifacts (`af_ah_*`) are named by its tasks;
    Mycelium r4 and r5 by none.
  - 14 have no mention outside the files that define them: the nine SoC artifacts, Black Stone,
    Helium, Gimlet, Basilisk and the multiplayer Flash.
  - Three are story items: the Jupiter half artifact, the Monolith shard and Zaton's twisted
    artifact. `marker` only shares its name with map-marker code.

  The census's source map lists each one's mentions; each needs a look before it leaves the
  counts.

**The in-game census** (`almanac_census.script`), first run on 2026-11-01 on a save in Darkscape:
- The whole alife held 41 artifacts. 3 lay free on the player's level, all from its fields; 23 lay
  free on four other levels; 15 were owned (stalkers 10, boxes 5).
- 12 of the 23 elsewhere were 5 game days old or more, so the despawner would release them the
  moment the player arrived.
- Who spawned a free artifact is known only on the loaded level: field ids come from its zone
  binders, and Dynamic Anomalies tracked none at that point.
- Every level but the current one was due its post-emission roll, underground ones included
  (their weathers are `w_indoor_*`, and the base code skips only `indoor`).
- A full sweep of the alife's 65,534 ids took about 30 ms.

## Prior art

A survey of ModDB, GitHub and G.A.M.M.A.'s #mods-posting on 2026-11-01 (21 mods ranked, pages and
source read) found:

- **The catalog and the trees exist offline, the totals and the live read don't.** The G.A.M.M.A.
  Item Database (stalker-gamma-db.com, AGPL: ideas only) shows stat cards, the 36 Melter recipes
  and field shares from a snapshot. Its tree opens a level at a time and never sums a tree to junk
  and parts, and it counts the unregistered `af_*_t0` groups as spawnable. Nothing reads the running
  game after DLTX.
- **Surveys come in three shapes.** Exact map markers (Artifact Signature Locator, Detection
  Support) get called cheating; a free field highlight (Artifact Field Markers) is liked but "too
  easy"; placed scanners (ZAD's QUARTZ-1M, which tips on new artifacts in surveyed fields of the
  player's level) are what players ask for. The most-raised theme (13 people) is that a hint must
  cost something.
- **A marker that points at nothing reachable** (underground, rolled away, a field that stopped
  spawning) is a top complaint (8 people). A notice never promises a specific spot or artifact.
- **Which detector sees an artifact (7) and how a perk works (5) are wanted,** and other mods
  change both (Perkifact Rebalance, detector mods), so both are read live.
- **Installed here and overlapping:** Crafting Info in Tooltips (279), Encyclopedia Messages
  Restored (176, a PDA tip when an artifact's Guide article unlocks), Grulag's in-game G.A.M.M.A.
  Manual and its Guide article injector, Workshop Parts Inventory (390), Craft From Stashes (471).
  The Almanac must sit beside them, not replace them.

## 1.0: the almanac

**The catalog** (`almanac_data.script`) is built once per load, on first use, from the running
game's configs: every artifact with its containers, tier and detectors, the workshop's recipes, each
level's fields with the chance a pick names each artifact, and Dynamic Anomalies' lists. Its fields
come from the anomaly zones' own spawn settings (`[anomal_zone] cfg`), since the engine's config
file list leaves out `configs\scripts`; that also counts only fields the Zone actually spawns. Run
offline over this install's configs, it gives the census's answers to the last comparison (1,026
of them). Built in game on 2026-11-01 (186-483 ms, once per load on first use) it matched the
census on names, tiers, containers, detectors, recipes and every tree, and corrected it on fields:
119 configs in use, not 120 (no zone uses Pole's `pol_smart_terrain_1_3`), and the four
`pri_2c_*` configs sit on SoC Pripyat rather than CoP Pripyat. The in-game catalog is the
Almanac's truth; the offline census reads fields by folder and can't see other scripts' edits at
load.

**The page** (0.1.0, checked in game 2026-11-01): the groups (all, junk, tiers 1-4, others) as tabs
across the top, each a mark and how many of its artifacts are known; then the artifacts of the
chosen one beside the entry. **Tiers are numbered as the game shows them,** one below the configs'
`tier`: Perk-Based Artefacts lowers every tier of 2 or more by one, its text speaks of tier 1 to 3
artifacts, and GRIP's icons put N white chevrons on tier N (config tier 2 to 5 shows as 1 to 4).
Junk shows no tier. The tabs carry the same chevrons; all is the Almanac's crystal, junk (no
chevron on its icons) a pitted stone. The census keeps the configs' numbers. The entry: the
inventory's own stat card (GAMMA's caps included), the game's description, the detectors, where the
Zone makes it, the recipe and its book, what it goes into, the totals from scratch, and what's still
missing with what the player carries. It opens three ways: Mod App Creator's tile by default when MAC is installed,
its own tab (MCM, or always without MAC), or an MCM key that opens it flat.

**Finds** (`almanac_found.script`, checked in game 2026-11-01): an artifact is found the first time
one enters the inventory, however it came (picked up, looted from a stash or a body, bought, given,
made at the Melter, or already in the pack at a load); a container counts as the artifact it holds.
Each find keeps its date, way and place (a game vertex and position, put into words when shown:
"picked up in Darkscape, at the sawmill"), and a new one is a PDA message unless MCM's "Messages" is
off. A found artifact stays known. The finds are the save's only Almanac state, under
`m_data.almanac` (schema 1, plain values); a save loads cleanly with the Almanac removed, the key
left unread.

**Learning without holding** (`almanac_learn.script`): an artifact is heard of, and so known, when
the radio's "found an artifact" news about it reaches the player (the stalker's name and where he
stood are kept), or when one of the player's tasks asks for it (its giver is kept). The news is
queued and may never be sent, so the artifact is learned only once its message goes out:
`DynamicNewsManager:FoundArtefact` is wrapped to note the queued text, `dynamic_news_helper.send_tip`
to catch it. Tasks are read every few seconds from the fetch item each keeps
(`<task id>_fetch`), quietly at a load. Heard-of records sit beside the finds in
`m_data.almanac.learned`. Still to come: Ecologist talks and looted PDAs.

**One entry per artifact** of kind `i_arty` or `i_arty_junk`, with its containers folded in. An
artifact that never turns up short of console commands stays out of the counts, and the source
map backs every such call.

**A page:**
- The inventory's own stat card, built in game by `utils_ui.stats_table.artefact` (HD Inventory
  Icons Framework's), so G.A.M.M.A.'s numbers and caps show as the inventory shows them.
- Tier (G.A.M.M.A.'s `tier`, not the PDA Guide's `af_rank`), weight, and the Perk-Based Artefacts
  perk in the game's own description text.
- The detectors that list it.
- Where the Zone makes it: the levels whose fields can yield it and the levels whose Dynamic
  Anomalies list holds it, likeliest first; "only by crafting" or "a quest artifact" where that's
  the case. A level, never a spot.
- Made from and goes into, each a link to that artifact's page.
- Who wants it: fetch tasks and Ecologist tasks that ask for it.

**Knowledge, immersive by default,** with an MCM jailbreak that opens everything:
- A new game knows what the PDA Guide has unlocked and what the player carries.
- An artifact becomes known when it enters the inventory, when an Ecologist talks about it, from a
  PDA, from "found an artifact" news on a faction channel, from a task that names it, and from an
  Immersive Identification tag.
- Reading a book opens its recipes; until then a tree shows the book a step needs and where it
  comes from.
- Unknown entries show as unknown, so the catalog doesn't spoil where the best artifacts come from.

**Collecting:** found counts by tier, and when and where each was found, as Arsenal's records
keep it (`arsenal_where`: a game vertex and position, worded by `GetPointDescription` when shown).

## 1.0: crafting trees

**The trees** (`almanac_trees.script`) are built on the catalog: `down` (the tree under an
artifact, a node per step, counts multiplied out), `up` (what it goes into, nearest first),
`totals` (crafts, books, the artifacts nothing makes, mutant parts), `need` (one more of it, using
what the player holds first, at any step, and what's still missing), `carried` (the inventory by
section) and `book_known` (as the workshop decides it: a book item once its note is read; a
built-in recipe set such as `recipe_basic_0` from the start). A step takes the first recipe that
makes its artifact; a loop stops at the artifact it would repeat. Every artifact's totals equal
the census's, offline and in game, where all 102 trees take under a millisecond.

- **The tree for any artifact,** up and down: each step with its book, the Melter and its parts.
- **How much you need:** the tree expanded down to junk artifacts and mutant parts, set against
  what the player carries (and, with Craft From Stashes, what nearby stashes hold). Read in game
  from `itms_manager.ini_craft`, the live file with DLTX, as the workshop reads it: the key's first
  two characters dropped, 6, 8 or 10 fields, amounts over 4 one less with the "artificer
  eagerness" achievement.
- **Books not yet read,** and where each comes from.
- **Later:** a plan handed to the workshop, as Workbench hands upgrades to the toolkit.

## 1.1: the survey

**What it can say, and nothing else.** The survey never spawns, moves or reserves anything.
- *"There is one":* an unowned artifact of that kind lies on a level now. An id sweep like the
  despawner's finds them, on demand or once a game hour. Fields and Dynamic Anomalies spawn only
  on the player's level (others roll on arrival), so on any other level this can only be one left
  from an earlier visit. The in-game census found such leftovers, but half were old enough for the
  despawner to release on arrival: a notice never names one the despawner will release.
- *"There could be one":* a level's fields or Dynamic Anomalies list can yield it, and the level is
  due its post-emission roll (`m_data.artefact_respawn_levels`), which happens when the player
  arrives.

**The gate:** standing with the chosen network, in steps as Seasons' forecasts are (200 for the
coarse tier, 700 for the exact one there), and only artifacts on the detector the player carries.

**Not easy:**
- A level, never a spot.
- A delay before word comes, and a window that ends at the next emission or psi storm.
- One notice a day per network.
- Others can get there first: stalkers pick artifacts up, and the despawner clears them after 5
  game days.
- At low standing, "there could be one" can be a miss.

That is the cost players ask for, paid in standing, time and uncertainty rather than rubles.

**Lore and delivery:** the Ecologists' instruments and the fields where the player has set their
scanners. A PDA message in the network leader's voice (Sakharov, Lebedev or Major Hernandez), sent
the way Seasons sends its forecasts, with MCM's quiet switch. A Leads list with each notice's
expiry. Nothing on the HUD.

## Opening it, look and text

- **Three ways in, the player's choice:** its own PDA tab (Modded Exes' `pda_dynamic_tabs` and
  DXML), Mod App Creator's tile, or an MCM key that opens it flat. MAC isn't required, and the tile
  gives way to the tab when MAC is present.
- **The vanilla PDA look,** as Arsenal's.
- **English and Russian,** reusing Seasons' term choices.

## Saves

- Its own `m_data` key only: what's known, found, wanted, and the survey's leads, with a schema
  version.
- The catalog is rebuilt from the configs on each load, never saved.
- Never writes another mod's state. Removing it leaves a save that loads as if it were never
  there.

## Compatibility and performance

- **The files that decide what it reads move with G.A.M.M.A.:** Perk-Based Artefacts' whole-file
  item configs, Artefacts Reinvention's `craft.ltx` and `artefacts.ltx` and its Dynamic Anomalies
  lists. Rerun the census after a dev2 sync touches them.
- **Dynamic Anomalies here is Jack Harris's Anti Lag copy** with local fixes.
- **The workshop's `UIWorkshopCraft:UpdateItem` and `:Craft` are stubs other mods fill in**
  (Serious Workshop optimization's `ui_workshop.script`), so a hand-off to the workshop must wrap,
  never replace.
- **`pda_16.xml` has one owner** (Seasons and INTERFECTOR both ship one); the tab goes through
  DXML.
- **The catalog is built once per load**, not on every PDA open (Arsenal's rebuild made 440-500 KB
  of garbage each time). An id sweep runs on demand or once a game hour.

## Partners

- **Seasons of the Zone:** `sotz_api.blowout()`'s network and tier, so one standing buys forecast
  and survey, and its forecast's next emission ends a notice.
- **Factions of the Zone:** trust tiers in place of raw goodwill once they exist; a war can cut a
  network.
- **Arsenal:** links between pages; patterns and tools copied (each repo stands alone).
- **Immersive Identification:** an identified stalker's finds as a lead, through its public calls
  only.
- **Zone Cookbook and Bestiary:** a recipe's mutant parts link to its pages, and the hides live
  there.

## Later

- A belt planner (effects summed under G.A.M.M.A.'s caps).
- Empower planning (the Melter restores an artifact's condition from a duplicate).
- Display cases as a shelf.
- Ecologist contracts on the fetch tasks.
- An earned jailbreak.

## Still open

- How the survey's delay, its odds of a miss by standing, and its daily limit are tuned (1.1).
- How many artifacts a real play session leaves per level, and how often a field or Dynamic
  Anomalies actually yields one after an emission: the in-game census, left on through play, would
  answer both.
