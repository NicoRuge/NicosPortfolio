#!/usr/bin/env python3
"""
optimize_for_web.py
-------------------
Converts photos in the current directory to web-optimized copies.
Output is placed in a ./web/ subfolder.

Supported input:  JPG, JPEG, PNG, TIFF, WEBP, BMP
Output format:    JPEG or WebP (configurable below)

Requirements:
    pip install Pillow
"""

from PIL import Image, ImageOps
from pathlib import Path
import sys

# ── Configuration ──────────────────────────────────────────────────────────────

CONFIG = {
    # Max width in pixels. Height scales proportionally. 0 = no limit.
    "max_width": 2048,

    # JPEG quality (1–95). 80–85 is a good web trade-off.
    # For WebP, same range applies (85 is near-lossless at much smaller size).
    "quality": 82,

    # Output format: "jpeg" or "webp"
    "output_format": "jpeg",

    # Strip EXIF metadata from output (recommended for web: privacy + file size)
    "strip_metadata": True,

    # Output subfolder (created next to the source images)
    "output_dir": "web",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}

# ── Core logic ─────────────────────────────────────────────────────────────────

def process_image(src: Path, dst: Path, cfg: dict) -> tuple[bool, str]:
    try:
        with Image.open(src) as img:
            # Correct orientation from EXIF before anything else
            img = ImageOps.exif_transpose(img)

            # Convert to RGB — required for JPEG output (no alpha channel)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Resize if wider than max_width
            if cfg["max_width"] > 0 and img.width > cfg["max_width"]:
                ratio = cfg["max_width"] / img.width
                new_size = (cfg["max_width"], int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            fmt = cfg["output_format"]
            save_kwargs = {"format": fmt, "quality": cfg["quality"]}

            if fmt == "jpeg":
                save_kwargs["optimize"] = True
                save_kwargs["progressive"] = True
                if not cfg["strip_metadata"]:
                    # Preserve ICC color profile (important for A7 III files)
                    icc = img.info.get("icc_profile")
                    if icc:
                        save_kwargs["icc_profile"] = icc
            elif fmt == "webp":
                save_kwargs["method"] = 6  # slower encode, better compression

            img.save(dst, **save_kwargs)

        src_kb = src.stat().st_size / 1024
        dst_kb = dst.stat().st_size / 1024
        reduction = 100 - (dst_kb / src_kb * 100)
        return True, f"{src_kb:7.0f} KB -> {dst_kb:6.0f} KB  ({reduction:.0f}% smaller)"

    except Exception as e:
        return False, str(e)


def main():
    cfg = CONFIG
    source_dir = Path.cwd()
    output_dir = source_dir / cfg["output_dir"]
    output_dir.mkdir(exist_ok=True)

    ext = ".jpg" if cfg["output_format"] == "jpeg" else ".webp"

    images = sorted(
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not images:
        print("No supported images found in the current directory.")
        sys.exit(0)

    print(f"Found {len(images)} image(s) — writing to ./{cfg['output_dir']}/\n")
    print(f"  {'File':<40} {'Size change'}")
    print(f"  {'-'*40} {'-'*35}")

    ok = err = 0
    for src in images:
        dst = output_dir / (src.stem + ext)
        success, info = process_image(src, dst, cfg)
        status = "  " if success else "! "
        print(f"{status}{src.name:<40} {info}")
        if success:
            ok += 1
        else:
            err += 1

    print(f"\nDone. {ok} converted, {err} failed.")


if __name__ == "__main__":
    main()