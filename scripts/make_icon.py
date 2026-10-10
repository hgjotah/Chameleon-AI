from pathlib import Path

from PIL import Image, ImageDraw

directory = Path(__file__).resolve().parents[1] / "src" / "chameleon" / "assets" / "icons"
directory.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), "#080d0b")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((5, 5, 251, 251), radius=48, outline="#286544", width=7)
draw.arc((44, 40, 215, 218), 48, 310, fill="#51fa8b", width=28)
draw.ellipse((143, 40, 218, 115), fill="#51fa8b")
draw.ellipse((181, 56, 203, 78), fill="#080d0b")
draw.line((78, 126, 103, 148, 78, 170), fill="#d8ecdf", width=9)
draw.line((121, 169, 161, 169), fill="#d8ecdf", width=9)
image.save(directory / "chameleon.png")
image.save(
    directory / "chameleon.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
