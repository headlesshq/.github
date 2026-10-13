#!/usr/bin/env python3
"""Generate the project tiles for the organization profile README.

Reads scripts/tiles.json (a list of rows, each a list of tiles) and writes
a light and a dark SVG per tile to profile/assets/tiles/. The logo is
embedded as base64, since GitHub serves SVGs as images that cannot load
external resources. Then rewrites the grid in profile/README.md between
the <!-- tiles:start --> and <!-- tiles:end --> markers.

Usage: python3 scripts/generate_tiles.py
"""

import base64
import html
import io
import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "scripts" / "tiles.json"
ASSETS = ROOT / "profile" / "assets"
OUT = ASSETS / "tiles"
README = ROOT / "profile" / "README.md"

WIDTH = 280
LOGO_SIZE = 96
LOGO_Y = 28
NAME_Y = LOGO_Y + LOGO_SIZE + 34
DESC_Y = NAME_Y + 26
LINE_HEIGHT = 19
WRAP_CHARS = 34
RADIUS = 16
DISPLAY_WIDTH = 260
# Logos are downscaled before embedding to keep the SVGs small (2x of display size).
EMBED_SIZE = LOGO_SIZE * 2

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# Colors follow GitHub's Primer palette so the tiles blend into both themes.
THEMES = {
    "light": {
        "bg_top": "#ffffff",
        "bg_bottom": "#f6f8fa",
        "border": "#d1d9e0",
        "title": "#1f2328",
        "text": "#59636e",
        "glow": "#0969da",
    },
    "dark": {
        "bg_top": "#151b23",
        "bg_bottom": "#0d1117",
        "border": "#3d444d",
        "title": "#f0f6fc",
        "text": "#9198a1",
        "glow": "#4493f8",
    },
}


def encode_logo(path: Path) -> str:
    try:
        from PIL import Image
    except ImportError:
        return base64.b64encode(path.read_bytes()).decode()

    with Image.open(path) as image:
        image = image.convert("RGBA")
        image.thumbnail((EMBED_SIZE, EMBED_SIZE), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()


def render_tile(tile: dict, theme: dict, logo: str, height: int) -> str:
    lines = textwrap.wrap(tile["description"], WRAP_CHARS)
    description = "\n".join(
        f'    <tspan x="{WIDTH / 2}" y="{DESC_Y + i * LINE_HEIGHT}">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    logo_x = (WIDTH - LOGO_SIZE) / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{html.escape(tile['name'])}: {html.escape(tile['description'])}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{theme['bg_top']}"/>
      <stop offset="1" stop-color="{theme['bg_bottom']}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0" r="0.6">
      <stop offset="0" stop-color="{theme['glow']}" stop-opacity="0.12"/>
      <stop offset="1" stop-color="{theme['glow']}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="{RADIUS}" fill="url(#bg)" stroke="{theme['border']}"/>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="{RADIUS}" fill="url(#glow)"/>
  <image x="{logo_x}" y="{LOGO_Y}" width="{LOGO_SIZE}" height="{LOGO_SIZE}" href="data:image/png;base64,{logo}"/>
  <text x="{WIDTH / 2}" y="{NAME_Y}" text-anchor="middle" font-family="{FONT}" font-size="18" font-weight="600" fill="{theme['title']}">{html.escape(tile['name'])}</text>
  <text text-anchor="middle" font-family="{FONT}" font-size="13" fill="{theme['text']}">
{description}
  </text>
</svg>
"""


def render_grid(rows: list) -> str:
    parts = ["<!-- tiles:start -->"]
    for row in rows:
        parts.append('<p align="center">')
        for tile in row:
            alt = html.escape(f"{tile['name']}: {tile['description']}")
            parts.append(
                f'  <a href="{tile["url"]}"><picture>'
                f'<source media="(prefers-color-scheme: dark)" srcset="assets/tiles/{tile["id"]}-dark.svg">'
                f'<img src="assets/tiles/{tile["id"]}-light.svg" width="{DISPLAY_WIDTH}" alt="{alt}">'
                f"</picture></a>"
            )
        parts.append("</p>")
    parts.append("<!-- tiles:end -->")
    return "\n".join(parts)


def main() -> None:
    rows = json.loads(DATA.read_text())
    tiles = [tile for row in rows for tile in row]

    # All tiles share the height of the one with the longest description.
    max_lines = max(len(textwrap.wrap(t["description"], WRAP_CHARS)) for t in tiles)
    height = DESC_Y + (max_lines - 1) * LINE_HEIGHT + 30

    OUT.mkdir(parents=True, exist_ok=True)
    for tile in tiles:
        logo = encode_logo(ASSETS / tile["logo"])
        for name, theme in THEMES.items():
            path = OUT / f"{tile['id']}-{name}.svg"
            path.write_text(render_tile(tile, theme, logo, height))
            print(f"wrote {path.relative_to(ROOT)}")

    readme = README.read_text()
    pattern = re.compile(r"<!-- tiles:start -->.*?<!-- tiles:end -->", re.S)
    if not pattern.search(readme):
        raise SystemExit(f"{README.relative_to(ROOT)} has no <!-- tiles:start --> / <!-- tiles:end --> markers")
    README.write_text(pattern.sub(lambda _: render_grid(rows), readme))
    print(f"updated {README.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
