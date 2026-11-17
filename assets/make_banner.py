"""Render the SOW README banner (assets/banner.gif).

The background is generated here, so there's no stock art to license. Text uses Inter
(SIL Open Font License 1.1): download it from https://github.com/rsms/inter/releases and
point this at its extras/ttf folder.

    uv run --no-project --with pillow --with numpy python assets/make_banner.py <inter>/extras/ttf assets/banner.gif
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, S = 1280, 320, 2                     # draw at 2x, downsample for smooth text
BLACK, CREAM, ORANGE, TEAL, MUTED = (5, 5, 5), (245, 239, 230), (240, 138, 75), (47, 85, 96), (154, 165, 168)
SKILLS = [
    ("findable", "Can people find your site?"),
    ("compliance", "Is it set up the right way?"),
    ("guarded", "Does it ship security holes?"),
]


def background() -> Image.Image:
    w, h = W * S, H * S
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = x / w, y / h
    # slanted, wavy ribbons like the old banner
    phase = xn * 7.0 + np.sin(yn * 2.6 + xn * 3.0) * 0.9 - yn * 1.2
    wave = np.sin(phase * np.pi)
    band = np.clip((wave + 0.15) * 1.9, 0, 1) ** 1.2          # ribbons with crisp edges and dark gaps
    height = yn                                              # orange low, teal lower, cream top
    cream = np.clip(1.2 - height * 1.6, 0, 1)
    orange = np.exp(-((height - 0.58 + 0.12 * np.sin(xn * 9)) ** 2) / 0.02) * 1.4
    teal = np.clip((height - 0.55) * 2.2, 0, 1)
    col = np.zeros((h, w, 3), np.float32)
    for c, wgt in ((CREAM, cream), (ORANGE, np.clip(orange, 0, 1)), (TEAL, teal)):
        col += np.array(c, np.float32) * wgt[..., None]
    col /= np.maximum(cream + np.clip(orange, 0, 1) + teal, 1e-3)[..., None]
    img = np.array(BLACK, np.float32) * (1 - band[..., None]) + col * band[..., None]
    # fade to black on the right for the text
    shade = np.clip((xn - 0.36) / 0.4, 0, 1) ** 1.2 * 0.93
    img = img * (1 - shade[..., None]) + np.array(BLACK, np.float32) * shade[..., None]
    # film grain (fixed seed: identical in every frame, so the GIF only stores the text changes)
    rng = np.random.default_rng(7)
    img += rng.normal(0, 9, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)


def tracked(draw, xy_right, text, font, fill, tracking):
    """Right-aligned text with letter spacing."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy_right[0] - total, xy_right[1]
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += wch + tracking


def layer(fonts, active: int, alpha: float) -> Image.Image:
    """Text over transparent 2x canvas. alpha fades only the rotating skill line."""
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    R = 1200 * S
    tracked(d, (R, 58 * S), "SOW", fonts["light"], CREAM + (255,), 10 * S)
    tracked(d, (R, 152 * S), "Stay On Web", fonts["reg22"], ORANGE + (255,), 3 * S)
    name, q = SKILLS[active]
    a = int(255 * alpha)
    tracked(d, (R, 200 * S), name, fonts["semi30"], CREAM + (a,), 0)
    tracked(d, (R, 240 * S), q, fonts["reg20"], (201, 195, 186, a), 0)
    # bottom line: every skill, the active one in orange
    parts = ["skills for coding agents", "·"] + [x for i, s in enumerate(SKILLS) for x in ((s[0], i), "·")][:-1]
    f = fonts["reg14"]
    sep = d.textlength("  ", font=f)
    items = [(p if isinstance(p, str) else p[0], (ORANGE if not isinstance(p, str) and p[1] == active else MUTED))
             for p in parts]
    total = sum(d.textlength(t, font=f) for t, _ in items) + sep * (len(items) - 1)
    x = R - total
    for t, c in items:
        d.text((x, 280 * S), t, font=f, fill=c + (255,))
        x += d.textlength(t, font=f) + sep
    return im.resize((W, H), Image.LANCZOS)


def rounded_mask() -> Image.Image:
    m = Image.new("L", (W * S, H * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W * S - 1, H * S - 1), 20 * S, fill=255)
    return m.resize((W, H), Image.LANCZOS).point(lambda v: 255 if v > 127 else 0)


def main():
    fd, out = Path(sys.argv[1]), Path(sys.argv[2])
    still = Path(sys.argv[sys.argv.index("--still") + 1]) if "--still" in sys.argv else None
    fonts = {"light": ImageFont.truetype(str(fd / "Inter-Light.ttf"), 76 * S),
             "reg22": ImageFont.truetype(str(fd / "Inter-Regular.ttf"), 22 * S),
             "semi30": ImageFont.truetype(str(fd / "Inter-SemiBold.ttf"), 30 * S),
             "reg20": ImageFont.truetype(str(fd / "Inter-Regular.ttf"), 20 * S),
             "reg14": ImageFont.truetype(str(fd / "Inter-Regular.ttf"), 14 * S)}
    bg = background().convert("RGBA")
    mask = rounded_mask()
    fade = [i / 6 for i in range(1, 7)]
    frames, durations = [], []
    for k in range(len(SKILLS)):
        for a in fade:                                  # fade in
            frames.append((k, a)); durations.append(60)
        frames.append((k, 1.0)); durations.append(2200)  # hold
        for a in reversed(fade[:-1]):                    # fade out
            frames.append((k, a)); durations.append(50)
        frames.append((k, 0.0)); durations.append(120)
    rgb = [Image.alpha_composite(bg, layer(fonts, k, a)).convert("RGB") for k, a in frames]
    if still:
        hold = [i for i, d in enumerate(durations) if d == 2200][0]
        rgb[hold].save(still)
    # one shared palette from the held frames, no dithering (grain already hides banding)
    sample = Image.new("RGB", (W, H * 3))
    for i, idx in enumerate([j for j, d in enumerate(durations) if d == 2200]):
        sample.paste(rgb[idx], (0, H * i))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    out_frames = []
    for im in rgb:
        q = im.quantize(palette=pal, dither=Image.Dither.NONE)
        q.paste(255, mask=Image.eval(mask, lambda v: 255 - v))   # index 255 = transparent corners
        out_frames.append(q)
    out_frames[0].save(out, save_all=True, append_images=out_frames[1:], duration=durations, loop=0,
                       transparency=255, disposal=1, optimize=False)
    print(f"{out}: {len(out_frames)} frames, {out.stat().st_size / 1024:.0f} KB, loop {sum(durations) / 1000:.1f}s")


if __name__ == "__main__":
    main()
