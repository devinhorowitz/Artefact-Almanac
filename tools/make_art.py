"""The Almanac's own art, drawn here so no texture pack can move it:

- textures/ui/almanac_app.dds: the launcher tile for Mod App Creator, an anomaly's swirl with a
  faceted crystal in its eye, as flat art in the PDA's colors like the tiles beside it: light gray
  (enabled), amber (highlighted), white (touched), dim gray (disabled). A 512x512 four-state
  atlas: e top-left, h top-right, t bottom-left, d bottom-right
  (configs/ui/textures_descr/ui_almanac.xml).
- textures/ui/almanac_px.dds: 4x4 white, tinted by the page for rules and panels.
- textures/ui/almanac_marks.dds: the group tabs' marks, white outlined in black so the page can
  tint them, 64x64 each, left to right: all (the crystal in a ring), junk (a pitted stone:
  junk carries no tier mark), tiers 1 to 4 as the game shows them (N chevrons for tier N, as GRIP
  marks an artifact's tier on its icon), other (a dashed ring); the last cell is left clear for the tabs' buttons, which
  only take the clicks (a 3t button keeps its texture at its XML size, so the page draws the tabs'
  panels itself).

    python make_art.py [PREVIEW.png]
"""
import math
import os
import struct
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "..", "gamedata", "textures", "ui")
STATES = {                            # quadrant origin -> color
    "e": ((0, 0), (200, 200, 200)),
    "h": ((256, 0), (238, 196, 112)),
    "t": ((0, 256), (255, 255, 255)),
    "d": ((256, 256), (110, 110, 110)),
}
SS = 4                                # supersampling for smooth edges
MARK = 64                             # a mark's cell in almanac_marks.dds
MARKS = ["all", "junk", "t1", "t2", "t3", "t4", "other"]


def shape():
    """The All tab's mask, 256x256: a ring, and inside it a six-sided crystal with its facets cut
    (the first tile's art, which reads better than the swirl at a tab's size)."""
    n = 256 * SS
    m = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(m)

    def s(*v):
        return [x * SS for x in v]

    d.ellipse(s(28, 28, 228, 228), fill=255)                           # the ring
    d.ellipse(s(44, 44, 212, 212), fill=0)
    crystal = [(128, 58), (176, 96), (176, 160), (128, 198), (80, 160), (80, 96)]
    d.polygon(s(*[c for p in crystal for c in p]), fill=255)            # the crystal
    cuts = Image.new("L", (n, n), 0)
    c = ImageDraw.Draw(cuts)
    for a, b in (((128, 58), (128, 198)), ((80, 96), (176, 160)), ((176, 96), (80, 160))):
        c.line(s(*a, *b), fill=255, width=7 * SS)                        # its facets
    m = ImageChops.subtract(m, cuts)
    return m.resize((256, 256), Image.LANCZOS)


def tile_shape():
    """The tile's mask, 256x256 (the user's pick from the 2026-11-01 slate): an anomaly's three
    spiral arms, and in its clear eye the crystal with its facets cut."""
    n = 256 * SS
    m = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(m)

    def s(*v):
        return [x * SS for x in v]

    for arm in range(3):
        pts = []
        for i in range(60):
            t = i / 59
            a = math.radians(arm * 120 + t * 250)
            r = 34 + t * 78
            pts += [128 + r * math.cos(a), 128 + r * math.sin(a)]
        d.line(s(*pts), fill=255, width=12 * SS, joint="curve")          # the arms
    d.ellipse(s(86, 86, 170, 170), fill=0)                                # the eye
    k = 0.42
    crystal = [(128 + (x - 128) * k, 128 + (y - 128) * k)
               for x, y in [(128, 58), (176, 96), (176, 160), (128, 198), (80, 160), (80, 96)]]
    d.polygon(s(*[c for p in crystal for c in p]), fill=255)              # the crystal
    for a, b in (((128, 58), (128, 198)), ((80, 96), (176, 160)), ((176, 96), (80, 160))):
        d.line(s(128 + (a[0] - 128) * k, 128 + (a[1] - 128) * k, 128 + (b[0] - 128) * k, 128 + (b[1] - 128) * k),
               fill=0, width=int(7 * k * SS))                             # its facets
    return m.resize((256, 256), Image.LANCZOS)


def mark_mask(name):
    """A mark's shape, MARK x MARK, white on black."""
    n = MARK * SS
    m = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(m)

    def s(*v):
        return [x * SS for x in v]

    if name == "all":
        return shape().resize((MARK, MARK), Image.LANCZOS)
    if name == "junk":
        # a pitted stone
        d.ellipse(s(13, 13, 51, 51), fill=255)
        for x, y, r in ((25, 25, 5), (39, 31, 4), (28, 40, 3.5)):
            d.ellipse(s(x - r, y - r, x + r, y + r), fill=0)
    elif name == "other":
        # a dashed ring: eight gaps
        d.ellipse(s(12, 12, 52, 52), fill=255)
        d.ellipse(s(19, 19, 45, 45), fill=0)
        cut = Image.new("L", (n, n), 0)
        c = ImageDraw.Draw(cut)
        for k in range(8):
            a = math.radians(k * 45 + 22.5)
            c.line(s(32, 32, 32 + 30 * math.cos(a), 32 + 30 * math.sin(a)), fill=255, width=5 * SS)
        m = ImageChops.subtract(m, cut)
    else:
        # tier N: N chevrons stacked, pointing up
        count = int(name[1:])
        w, h, step = 40, 14, 11
        top = (MARK - (h + (count - 1) * step)) / 2
        for i in range(count):
            y = top + i * step
            d.line(s(32 - w / 2, y + h, 32, y, 32 + w / 2, y + h), fill=255, width=7 * SS, joint="curve")
    return m.resize((MARK, MARK), Image.LANCZOS)


def marks():
    """The marks, white outlined in black, then a clear cell."""
    out = Image.new("RGBA", (MARK * len(MARKS) + MARK, MARK), (0, 0, 0, 0))
    for i, name in enumerate(MARKS):
        fill = mark_mask(name)
        edge = fill.filter(ImageFilter.MaxFilter(5))
        cell = Image.new("RGBA", (MARK, MARK), (0, 0, 0, 0))
        cell.putalpha(edge)
        white = Image.new("RGBA", (MARK, MARK), (255, 255, 255, 0))
        white.putalpha(fill)
        cell.alpha_composite(white)
        out.paste(cell, (i * MARK, 0))
    return out


def atlas(mask):
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for (x, y), color in STATES.values():
        t = Image.new("RGBA", (256, 256), color + (0,))
        t.putalpha(mask)
        out.paste(t, (x, y))
    return out


def write_dds(img, path):
    """Uncompressed A8R8G8B8 DDS, no mipmaps (as Arsenal's and Factions' tiles)."""
    w, h = img.size
    head = struct.pack("<4s7I44x9I12x4x", b"DDS ", 124, 0x100F, h, w, w * 4, 0, 1,
                       32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000, 0x1000)
    assert len(head) == 128
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(head + img.convert("RGBA").tobytes("raw", "BGRA"))


def main():
    img = atlas(tile_shape())
    write_dds(img, os.path.join(UI, "almanac_app.dds"))
    write_dds(Image.new("RGBA", (4, 4), (255, 255, 255, 255)), os.path.join(UI, "almanac_px.dds"))
    mk = marks()
    write_dds(mk, os.path.join(UI, "almanac_marks.dds"))
    print("wrote almanac_app.dds, almanac_px.dds and almanac_marks.dds in", os.path.normpath(UI))
    if len(sys.argv) > 1:
        bg = Image.new("RGBA", (img.size[0], img.size[1] + MARK + 16), (24, 26, 28, 255))
        bg.alpha_composite(img)
        bg.alpha_composite(mk.crop((0, 0, min(mk.size[0], img.size[0]), MARK)), (0, img.size[1] + 8))
        bg.save(sys.argv[1])
        print("preview", sys.argv[1])


if __name__ == "__main__":
    main()
