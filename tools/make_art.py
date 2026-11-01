"""The Almanac's own art, drawn here so no texture pack can move it:

- textures/ui/almanac_app.dds: the launcher tile for Mod App Creator, an artifact (a faceted
  crystal in a ring) as flat art in the PDA's colors like the tiles beside it: light gray
  (enabled), amber (highlighted), white (touched), dim gray (disabled). A 512x512 four-state
  atlas: e top-left, h top-right, t bottom-left, d bottom-right
  (configs/ui/textures_descr/ui_almanac.xml).
- textures/ui/almanac_px.dds: 4x4 white, tinted by the page for rules and panels.

    python make_art.py [PREVIEW.png]
"""
import os
import struct
import sys

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "..", "gamedata", "textures", "ui")
STATES = {                            # quadrant origin -> color
    "e": ((0, 0), (200, 200, 200)),
    "h": ((256, 0), (238, 196, 112)),
    "t": ((0, 256), (255, 255, 255)),
    "d": ((256, 256), (110, 110, 110)),
}
SS = 4                                # supersampling for smooth edges


def shape():
    """The tile's mask, 256x256: a ring, and inside it a six-sided crystal with its facets cut."""
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
    img = atlas(shape())
    write_dds(img, os.path.join(UI, "almanac_app.dds"))
    write_dds(Image.new("RGBA", (4, 4), (255, 255, 255, 255)), os.path.join(UI, "almanac_px.dds"))
    print("wrote almanac_app.dds and almanac_px.dds in", os.path.normpath(UI))
    if len(sys.argv) > 1:
        bg = Image.new("RGBA", img.size, (24, 26, 28, 255))
        bg.alpha_composite(img)
        bg.save(sys.argv[1])
        print("preview", sys.argv[1])


if __name__ == "__main__":
    main()
