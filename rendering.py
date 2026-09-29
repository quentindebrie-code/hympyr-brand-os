"""Deterministic template rendering to PNG and PDF without design software."""
from __future__ import annotations

import io
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageOps

BUILTIN_COLORS = {
    "V-50": "#EAF7F1", "V-500": "#1A9E68", "V-900": "#073D27",
    "B-400": "#2E78D5", "O-500": "#FF5C28", "Blanc": "#FFFFFF",
}
DEFAULT_LAYERS = [
    {"type": "rect", "field": "", "x": 0, "y": 944, "width": 1080, "height": 136, "size": 0, "font": "", "color": "O-500", "align": "left"},
    {"type": "text", "field": "eyebrow", "x": 80, "y": 100, "width": 920, "height": 60, "size": 30, "font": "Poppins", "color": "V-500", "align": "left"},
    {"type": "text", "field": "title", "x": 80, "y": 260, "width": 920, "height": 390, "size": 82, "font": "Poppins", "color": "V-900", "align": "left"},
    {"type": "text", "field": "body", "x": 80, "y": 700, "width": 920, "height": 190, "size": 36, "font": "Poppins", "color": "V-900", "align": "left"},
]


def color_value(token: str, colors: dict[str, str]) -> str:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", token or ""):
        return token
    return colors.get(token, BUILTIN_COLORS.get(token, "#073D27"))


@lru_cache(maxsize=32)
def font_path(family: str, weight: int = 400) -> str | None:
    """Cache a Google Fonts TTF. Return None if the font service is unavailable."""
    family = family.strip()
    if not re.fullmatch(r"[\w -]{1,100}", family, re.UNICODE):
        return None
    from pathlib import Path
    import tempfile

    url = "https://fonts.googleapis.com/css2?family=" + urllib.parse.quote(family.replace(" ", "+"), safe="+") + f":wght@{weight}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)"})
        with urllib.request.urlopen(request, timeout=5) as response:
            css = response.read(100_000).decode("utf-8")
        match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
        if not match:
            return None
        with urllib.request.urlopen(match.group(1), timeout=8) as response:
            data = response.read(3_000_000)
        if not data.startswith((b"\x00\x01\x00\x00", b"true")):
            return None
        path = Path(tempfile.gettempdir()) / f"hympyr-font-{re.sub(r'[^a-z0-9]', '-', family.lower())}-{weight}.ttf"
        path.write_bytes(data)
        return str(path)
    except (OSError, ValueError):
        return None


def get_font(family: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    path = font_path(family, weight) if family else None
    try:
        return ImageFont.truetype(path or "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _wrapped(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in value.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=font) <= width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
                while draw.textlength(line, font=font) > width and len(line) > 1:
                    cut = len(line) - 1
                    while cut > 1 and draw.textlength(line[:cut], font=font) > width:
                        cut -= 1
                    lines.append(line[:cut])
                    line = line[cut:]
        lines.append(line)
    return lines


def render(template: dict, fields: dict[str, str], colors: dict[str, str], asset_loader=None) -> Image.Image:
    width, height = int(template["width"]), int(template["height"])
    if not (200 <= width <= 4000 and 200 <= height <= 4000):
        raise ValueError("Dimensions de gabarit invalides.")
    image = Image.new("RGB", (width, height), color_value(template.get("background_token", "Blanc"), colors))
    if template.get("background_asset_id") and asset_loader:
        data = asset_loader(template["background_asset_id"])
        with Image.open(io.BytesIO(data)) as background:
            image.paste(ImageOps.fit(background.convert("RGB"), (width, height)))
    draw = ImageDraw.Draw(image)
    for layer in template.get("layers", []):
        kind = layer.get("type")
        x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
        w, h = int(layer.get("width", 0)), int(layer.get("height", 0))
        if w <= 0 or h <= 0:
            continue
        fill = color_value(str(layer.get("color", "V-900")), colors)
        if kind == "rect":
            draw.rectangle((x, y, x + w, y + h), fill=fill)
        elif kind == "image" and asset_loader and layer.get("field"):
            data = asset_loader(str(layer["field"]))
            with Image.open(io.BytesIO(data)) as source:
                inset = ImageOps.contain(source.convert("RGBA"), (w, h))
                image.paste(inset, (x, y), inset)
            draw = ImageDraw.Draw(image)
        elif kind == "text":
            value = str(fields.get(str(layer.get("field", "")), ""))
            if not value:
                continue
            size = max(10, min(300, int(layer.get("size", 40))))
            family = str(layer.get("font", "Poppins"))
            for candidate in range(size, 9, -1):
                font = get_font(family, candidate, int(layer.get("weight") or 700))
                lines = _wrapped(draw, value, font, w)
                spacing = int(candidate * 0.22)
                bbox = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=spacing)
                if bbox[3] - bbox[1] <= h:
                    break
            # Clip to the declared box; overflowing copy never spills into another layer.
            overlay = Image.new("RGBA", (w, h))
            od = ImageDraw.Draw(overlay)
            yy = -bbox[1]
            for line in lines:
                line_width = draw.textlength(line, font=font)
                align = layer.get("align", "left")
                xx = (w - line_width) / 2 if align == "center" else w - line_width if align == "right" else 0
                od.text((xx, yy), line, font=font, fill=fill)
                yy += candidate + spacing
            image.paste(overlay, (x, y), overlay)
            draw = ImageDraw.Draw(image)
    return image


def encode_image(image: Image.Image, format: str = "PNG") -> bytes:
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()
