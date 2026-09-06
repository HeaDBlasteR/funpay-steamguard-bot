import logging
import re

from PIL import Image, ImageDraw, ImageFont

from .config import EMOJI_FONT_PATH, UI_FONT_PATH, UI_FONT_SIZE

logger = logging.getLogger(__name__)

EMOJI_RE = re.compile(
    "(["
    "\U0001F000-\U0001FAFF"
    "←-⇿"
    "⌀-➿"
    "⬀-⯿"
    "Ⓜ〰️‍"
    "]+)"
)


ELLIPSIS = "…"

VARIATION_SELECTOR = "\uFE0F"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def split_runs(text: str) -> list[tuple[str, bool]]:
    return [
        (part, bool(EMOJI_RE.fullmatch(part)))
        for part in EMOJI_RE.split(text)
        if part
    ]


def load_fonts(size: int = UI_FONT_SIZE):
    return (
        ImageFont.truetype(UI_FONT_PATH, size),
        ImageFont.truetype(EMOJI_FONT_PATH, size),
    )


def render_text_image(
    text: str,
    fonts,
    color: tuple[int, int, int],
    background: tuple[int, int, int],
    max_width: int,
    height: int,
) -> Image.Image:
    text_font, emoji_font = fonts
    image = Image.new("RGB", (max_width, height), background)
    draw = ImageDraw.Draw(image)

    top = max((height - text_font.size) // 2 - 2, 0)
    runs = split_runs(text.replace(VARIATION_SELECTOR, ""))

    def font_for(is_emoji):
        return emoji_font if is_emoji else text_font

    def width_of(part, is_emoji):
        return int(draw.textlength(part, font=font_for(is_emoji)))

    total = sum(width_of(part, is_emoji) for part, is_emoji in runs)
    limit = max_width

    if total > max_width:
        limit = max_width - width_of(ELLIPSIS, False)

    x = 0
    truncated = False

    for part, is_emoji in runs:
        if x + width_of(part, is_emoji) <= limit:
            draw.text(
                (x, top),
                part,
                font=font_for(is_emoji),
                fill=color,
                embedded_color=is_emoji,
            )
            x += width_of(part, is_emoji)
            continue

        for char in part:
            char_width = width_of(char, is_emoji)

            if x + char_width > limit:
                truncated = True
                break

            draw.text(
                (x, top),
                char,
                font=font_for(is_emoji),
                fill=color,
                embedded_color=is_emoji,
            )
            x += char_width

        if truncated:
            break

    if truncated:
        draw.text((x, top), ELLIPSIS, font=text_font, fill=color)

    return image
