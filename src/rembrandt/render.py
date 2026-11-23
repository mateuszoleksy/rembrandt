import re
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

CHARS = ".:-=+*#%@▓█"

# Tried in order; falls back to Pillow's bundled font if none is installed
MONOSPACE_FONTS = ["Menlo.ttc", "DejaVuSansMono.ttf", "consola.ttf", "LiberationMono-Regular.ttf"]
FONT_SIZE = 14

# Terminal cells are roughly twice as tall as they are wide
TERMINAL_CHAR_ASPECT = 0.5


def _true_color(r, g, b, lum, boost):
    return (min(255, int(r * 1.4) + boost), min(255, int(g * 1.4) + boost), min(255, int(b * 1.4) + boost))


def _green(r, g, b, lum, boost):
    return (0, min(255, lum + boost), 0)


def _amber(r, g, b, lum, boost):
    v = min(255, lum + boost)
    return (v, int(v * 0.65), 0)


def _bw(r, g, b, lum, boost):
    v = min(255, lum + boost)
    return (v, v, v)


# key -> (label, colorizer)
MODES = {
    "color": ("True Color (1:1)", _true_color),
    "green": ("CRT Green", _green),
    "amber": ("Amber Terminal", _amber),
    "bw": ("Monochrome B&W", _bw),
}


@dataclass
class AsciiArt:
    """Grid of characters with one RGB color per character."""

    chars: list[str]
    colors: list[list[tuple[int, int, int]]]

    @property
    def width(self):
        return len(self.chars[0]) if self.chars else 0

    @property
    def height(self):
        return len(self.chars)


def parse_size(text):
    """Parse '1200x1900' (also 'X', '×' or spaces around it) into (1200, 1900)."""
    match = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", text)
    if not match or 0 in (w := int(match[1]), h := int(match[2])):
        raise ValueError(f"invalid size '{text}', expected e.g. 1200x1900")
    return w, h


def to_ascii(image, width=160, mode="color", boost=35, char_aspect=TERMINAL_CHAR_ASPECT, height=None):
    """Convert a PIL image to an AsciiArt grid.

    char_aspect is the width/height ratio of one character cell, used to keep
    the picture's proportions. Passing height overrides that and stretches the
    image to exactly width x height characters.
    """
    image = image.convert("RGB")
    if height is None:
        w, h = image.size
        height = max(1, int(width * (h / w) * char_aspect))
    data = iter(image.resize((width, height)).tobytes())
    pixels = list(zip(data, data, data))
    colorize = MODES[mode][1]
    last = len(CHARS) - 1

    chars, colors = [], []
    for y in range(height):
        row_chars, row_colors = [], []
        for r, g, b in pixels[y * width:(y + 1) * width]:
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            row_chars.append(CHARS[lum * last // 255])
            row_colors.append(colorize(r, g, b, lum, boost))
        chars.append("".join(row_chars))
        colors.append(row_colors)
    return AsciiArt(chars, colors)


@lru_cache(maxsize=1)
def _font():
    for name in MONOSPACE_FONTS:
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(size=FONT_SIZE)


@lru_cache(maxsize=1)
def _glyphs():
    """Pre-rendered glyph masks, so each character is a cheap paste instead of a text draw."""
    font = _font()
    ascent, descent = font.getmetrics()
    cell_w = int(max(font.getlength(c) for c in CHARS))
    cell_h = ascent + descent
    masks = {}
    for c in CHARS:
        mask = Image.new("L", (cell_w, cell_h), 0)
        offset = (cell_w - font.getlength(c)) / 2
        ImageDraw.Draw(mask).text((offset, 0), c, font=font, fill=255)
        masks[c] = mask
    return cell_w, cell_h, masks


def cell_aspect():
    cell_w, cell_h, _ = _glyphs()
    return cell_w / cell_h


def art_to_image(art):
    cell_w, cell_h, masks = _glyphs()
    result = Image.new("RGB", (art.width * cell_w, art.height * cell_h), (0, 0, 0))
    for y, (row_chars, row_colors) in enumerate(zip(art.chars, art.colors)):
        for x, (char, color) in enumerate(zip(row_chars, row_colors)):
            px, py = x * cell_w, y * cell_h
            result.paste(color, (px, py, px + cell_w, py + cell_h), masks[char])
    return result


def render_ascii_image(input_path, output_path, width=160, mode="color", boost=35, side_by_side=False, scale=1.0, size=None):
    """Render an image to an ASCII-art PNG.

    size=(w, h) produces exactly that many pixels and overrides width and
    scale; the picture is stretched if its proportions differ.
    """
    original = Image.open(input_path).convert("RGB")
    if size:
        # Pick the character grid that comes closest to the target, so the
        # final resize barely changes the glyphs and they stay sharp
        cell_w, cell_h, _ = _glyphs()
        ascii_w = size[0] / 2 if side_by_side else size[0]
        cols = max(1, round(ascii_w / cell_w))
        rows = max(1, round(size[1] / cell_h))
        art = to_ascii(original, cols, mode, boost, height=rows)
    else:
        art = to_ascii(original, width, mode, boost, char_aspect=cell_aspect())
    result = art_to_image(art)

    if side_by_side:
        orig_res = original.resize(result.size, Image.Resampling.LANCZOS)
        combined = Image.new("RGB", (result.width * 2, result.height))
        combined.paste(orig_res, (0, 0))
        combined.paste(result, (result.width, 0))
        result = combined

    if size:
        if result.size != tuple(size):
            result = result.resize(size, Image.Resampling.LANCZOS)
    elif scale != 1.0:
        result = result.resize((int(result.width * scale), int(result.height * scale)), Image.Resampling.LANCZOS)

    result.save(output_path)
    return f"{result.width}x{result.height} px"
