"""Package the user-supplied logo into Windows icon sizes without altering it."""
from pathlib import Path

from PIL import Image, ImageDraw

directory = Path(__file__).resolve().parents[1] / "src/chameleon/assets/icons"
with Image.open(directory / "chameleon.png") as image:
    image.convert("RGBA").save(directory / "chameleon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

# Qt Essentials does not provide an SVG image plugin. Package the tiny native
# checkbox glyph as PNG so it works in the standalone runtime as well.
check = Image.new("RGBA", (80, 80))
ImageDraw.Draw(check).line([(20, 40), (34, 54), (60, 26)], fill="#10362e", width=10, joint="curve")
check.resize((20, 20), Image.Resampling.LANCZOS).save(directory / "check.png")
