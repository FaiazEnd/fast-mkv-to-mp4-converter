"""Generate high-resolution sharp modern logo and multi-resolution Windows .ico icon."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def create_logo(size=512):
    # Create RGBA canvas
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark Slate Base Card with subtle sharp chamfered/angled geometry
    bg_margin = int(size * 0.06)
    bg_box = [bg_margin, bg_margin, size - bg_margin, size - bg_margin]
    
    # Draw deep slate sharp polygon base
    draw.rectangle(bg_box, fill="#181920", outline="#2c2d38", width=max(2, int(size * 0.01)))

    # Inner subtle tech accent border
    inner_m = int(size * 0.09)
    draw.rectangle([inner_m, inner_m, size - inner_m, size - inner_m], outline="#242530", width=max(1, int(size * 0.005)))

    # 2. Sharp Geometric Conversion Emblem
    # Center coordinates
    cx, cy = size // 2, size // 2
    scale = size * 0.35

    # Left Geometric Arrow / Wing (Coral Red #ff4d4d)
    # Sharp angular polygon pointing right/down
    poly_coral = [
        (cx - scale * 0.75, cy - scale * 0.70),
        (cx - scale * 0.15, cy - scale * 0.70),
        (cx + scale * 0.25, cy - scale * 0.25),
        (cx - scale * 0.05, cy - scale * 0.25),
        (cx - scale * 0.35, cy - scale * 0.55),
        (cx - scale * 0.75, cy - scale * 0.15),
    ]
    draw.polygon(poly_coral, fill="#ff4d4d")

    # Lower Geometric Arrow / Wing (Warm Amber #f5a623)
    # Sharp angular polygon looping back
    poly_amber = [
        (cx + scale * 0.75, cy + scale * 0.70),
        (cx + scale * 0.15, cy + scale * 0.70),
        (cx - scale * 0.25, cy + scale * 0.25),
        (cx + scale * 0.05, cy + scale * 0.25),
        (cx + scale * 0.35, cy + scale * 0.55),
        (cx + scale * 0.75, cy + scale * 0.15),
    ]
    draw.polygon(poly_amber, fill="#f5a623")

    # Center Dynamic Sharp Diamond Core
    diamond_r = scale * 0.26
    diamond = [
        (cx, cy - diamond_r),
        (cx + diamond_r * 1.1, cy),
        (cx, cy + diamond_r),
        (cx - diamond_r * 1.1, cy),
    ]
    draw.polygon(diamond, fill="#ffffff", outline="#181920", width=max(2, int(size * 0.012)))

    # Center Play / Pulse Accent
    play_w = diamond_r * 0.45
    play_tri = [
        (cx - play_w * 0.6, cy - play_w * 0.7),
        (cx + play_w * 0.8, cy),
        (cx - play_w * 0.6, cy + play_w * 0.7),
    ]
    draw.polygon(play_tri, fill="#ff4d4d")

    return img


def main():
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)

    # 1. Generate 512x512 Master Logo
    logo = create_logo(512)
    logo_path = assets_dir / "logo.png"
    logo.save(logo_path, format="PNG")
    print(f"[OK] Saved {logo_path}")

    # 2. Generate 256x256 Preview Logo
    logo_256 = logo.resize((256, 256), Image.Resampling.LANCZOS)
    logo_256.save(assets_dir / "logo_256.png", format="PNG")

    # 3. Generate Multi-Size Windows .ICO
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [logo.resize(s, Image.Resampling.LANCZOS) for s in ico_sizes]
    
    ico_path = assets_dir / "icon.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[1:]
    )
    print(f"[OK] Saved multi-resolution Windows icon {ico_path}")


if __name__ == "__main__":
    main()
