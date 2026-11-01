"""Write gamedata/configs/plugins/almanac_traders.ltx: which traders use each trade config, by the
name strings of their characters. A running game can read a trade config's stock, but not which
NPC's logic names it: that's in the NPC logic files (configs\\scripts, which the game's config
listing leaves out) and often in a smart terrain job's section ([logic@<npc>]). Ported from
Arsenal's tools/census.py ([arsenal_trade]).

    [almanac_trade]
    trade_ecolog_sakharov = yan_st_sakharov_name       the traders' name strings ("-" when none has
                                                       a name of his own); a config nobody's logic
                                                       uses sells nothing and isn't listed

A logic section's NPC: the spawn sections whose custom_data is its file ([logic]), the one its
suitable line names (check_npc_name), the one a smart terrain job is named for ([logic@<npc
section>]), or the one the file is named after. A generated name (a nameless NPC) is left out.

Run after GAMMA changes the NPC character or logic files (gamecfg.py names the settings it needs):
    python -I traders.py
"""
import collections
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gamecfg  # noqa: E402

OUT = os.path.join(HERE, "..", "gamedata", "configs", "plugins", "almanac_traders.ltx")


def expand(vfs, rel):
    """an XML file as the engine reads it: #include lines replaced by the files they name
    (relative to configs, wildcards allowed)"""
    text, _ = vfs.read("configs\\" + rel)
    if text is None:
        return ""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") and "#include" in s:
            m = re.search(r'"([^"]*)"', s)
            if m:
                inc = m.group(1).replace("/", "\\")
                if "*" in inc:
                    d, mask = inc.rsplit("\\", 1)
                    for f in vfs.listdir("configs\\" + d, mask):
                        out.append(expand(vfs, d + "\\" + f))
                else:
                    out.append(expand(vfs, inc))
            continue
        out.append(line)
    return "\n".join(out)


def blocks(text, tag):
    """(attributes, body) of each <tag ...>...</tag>, comments left out"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.findall(r"<%s\b([^>]*)>(.*?)</%s>" % (tag, tag), text, re.S)


def field(body, tag):
    return [x.strip() for x in re.findall(r"<%s\b[^>]*>(.*?)</%s>" % (tag, tag), body, re.S)]


def attr(attrs, name):
    m = re.search(r'%s\s*=\s*"([^"]*)"' % name, attrs)
    return m.group(1) if m else None


def trade_map(vfs, S):
    """trade config stem -> the name strings of the traders whose logic uses it, in file order"""
    def sv(sec, key):
        return (S.get(sec) or {}).get(key)

    files = [x.strip() for x in (sv("profiles", "specific_characters_files") or "").split(",") if x.strip()]
    pfiles = [x.strip() for x in (sv("profiles", "files") or "").split(",") if x.strip()]
    chars = {}
    for f in files:
        for attrs, body in blocks(expand(vfs, "gameplay\\" + f + ".xml"), "specific_character"):
            chars[attr(attrs, "id")] = (field(body, "name") or [None])[0]
    profiles = {}
    for f in pfiles:
        for attrs, body in blocks(expand(vfs, "gameplay\\" + f + ".xml"), "character"):
            profiles[attr(attrs, "id")] = (field(body, "specific_character") or [None])[0]

    rx = re.compile(r"^\s*trade\s*=\s*items\\trade\\([\w\-]+)\.ltx\s*$", re.I)
    named = re.compile(r"check_npc_name\(([\w\-]+)\)", re.I)
    npcs = [s for s, d in S.items() if d.get("character_profile")]
    by_cd = collections.defaultdict(list)
    for s in npcs:
        by_cd[(S[s].get("custom_data") or "").strip().lower()].append(s)

    def npc_sections(x):
        x = (x or "").lower()
        if not x:
            return []
        for c in (x, x + "_stalker", re.sub(r"_logic$", "", x)):
            if c in S and S[c].get("character_profile"):
                return [c]
        found = [s for s in npcs if x in s.lower() and not s.endswith("_squad")]
        return found if len(found) == 1 else []

    def trader_name(sec):
        prof = (S.get(sec) or {}).get("character_profile")
        char = profiles.get(prof) or prof
        n = chars.get(char)
        return n if n and not n.startswith("GENERATE_NAME") else None

    trade = collections.OrderedDict()
    for rel in sorted(vfs.files):
        if not (rel.startswith("configs\\scripts\\") and rel.endswith(".ltx")):
            continue
        text, _ = vfs.read(rel)
        sections, cur = collections.OrderedDict(), None
        for line in (text or "").splitlines():
            line = line.split(";")[0]
            m = re.match(r"^\s*\[([^\]]+)\]", line)
            if m:
                cur = m.group(1).split(":")[0].strip()
                sections.setdefault(cur, [])
            elif cur is not None:
                sections[cur].append(line)
        for sec, body in sections.items():
            cfgs = [m.group(1).lower() for m in (rx.match(x) for x in body) if m]
            if not cfgs:
                continue
            owners = list(by_cd.get(rel[len("configs\\"):].lower(), [])) if sec == "logic" else []
            for x in body:
                if x.strip().lower().startswith("suitable"):
                    for n in named.findall(x):
                        owners += npc_sections(n)
            if not owners and "@" in sec:
                owners = npc_sections(sec.split("@", 1)[1])
            if not owners:
                owners = npc_sections(os.path.splitext(os.path.basename(rel))[0])
            for c in cfgs:
                who = trade.setdefault(c, [])
                for o in owners:
                    n = trader_name(o)
                    if n and n not in who:
                        who.append(n)
    return trade


def text_of(trade):
    out = ["; Artefact Almanac: the trade configs some NPC's logic uses (items\\trade\\<name>.ltx), with",
           "; the name strings of the traders using it, by tools/traders.py (%s). The game reads"
           % datetime.date.today().isoformat(),
           "; each config's stock itself.",
           "[almanac_trade]"]
    for t in sorted(trade):
        out.append("%s = %s" % (t, ", ".join(trade[t]) or "-"))
    return "\r\n".join(out) + "\r\n"


def main():
    vfs, S = gamecfg.system()
    trade = trade_map(vfs, S)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(text_of(trade).encode("cp1251"))
    named = sum(1 for v in trade.values() if v)
    print("wrote %s: %d trade configs, %d with named traders" % (os.path.normpath(OUT), len(trade), named))


if __name__ == "__main__":
    main()
