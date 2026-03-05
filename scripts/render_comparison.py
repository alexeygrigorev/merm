#!/usr/bin/env python3
"""Render pymermaid vs mmdc SVGs to PNG and compute visual similarity scores.

Usage:
    uv run python scripts/render_comparison.py

Outputs:
    docs/comparisons/<category>/<name>_pymermaid.png
    docs/comparisons/<category>/<name>_mmdc.png
    docs/comparisons/<category>/<name>_diff.png
    docs/comparison_report.md
    docs/comparison_gallery.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

CORPUS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "corpus"
REFERENCE_DIR = PROJECT_ROOT / "tests" / "reference" / "corpus"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "comparisons"
PNG_WIDTH = 800  # render width for comparison


def svg_to_png(svg_path: Path, png_path: Path, width: int = PNG_WIDTH) -> bool:
    """Convert SVG to PNG using cairosvg."""
    try:
        import cairosvg

        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=width,
        )
        return True
    except Exception as e:
        print(f"  Failed to convert {svg_path.name}: {e}")
        return False


def render_pymermaid(mmd_path: Path, svg_path: Path) -> bool:
    """Render a .mmd file with pymermaid."""
    try:
        from pymermaid import render_diagram

        source = mmd_path.read_text()
        svg = render_diagram(source)
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg)
        return True
    except Exception as e:
        print(f"  Failed to render {mmd_path.name} with pymermaid: {e}")
        return False


def compute_ssim(img1_path: Path, img2_path: Path) -> float | None:
    """Compute SSIM between two PNG images."""
    try:
        import numpy as np
        from PIL import Image
        from skimage.metrics import structural_similarity

        img1 = Image.open(img1_path).convert("L")  # grayscale
        img2 = Image.open(img2_path).convert("L")

        # Resize to same dimensions
        target_size = (max(img1.width, img2.width), max(img1.height, img2.height))
        img1 = img1.resize(target_size, Image.Resampling.LANCZOS)
        img2 = img2.resize(target_size, Image.Resampling.LANCZOS)

        arr1 = np.array(img1)
        arr2 = np.array(img2)

        score = structural_similarity(arr1, arr2)
        return round(score, 4)
    except Exception as e:
        print(f"  SSIM failed: {e}")
        return None


def compute_pixel_diff(img1_path: Path, img2_path: Path, diff_path: Path) -> float | None:
    """Compute pixel difference percentage and save diff image."""
    try:
        import numpy as np
        from PIL import Image

        img1 = Image.open(img1_path).convert("RGB")
        img2 = Image.open(img2_path).convert("RGB")

        target_size = (max(img1.width, img2.width), max(img1.height, img2.height))
        img1 = img1.resize(target_size, Image.Resampling.LANCZOS)
        img2 = img2.resize(target_size, Image.Resampling.LANCZOS)

        arr1 = np.array(img1, dtype=np.float32)
        arr2 = np.array(img2, dtype=np.float32)

        diff = np.abs(arr1 - arr2)
        diff_pct = (np.count_nonzero(diff.max(axis=2) > 30) / (diff.shape[0] * diff.shape[1])) * 100

        # Save diff image (amplified)
        diff_img = np.clip(diff * 3, 0, 255).astype(np.uint8)
        Image.fromarray(diff_img).save(diff_path)

        return round(diff_pct, 2)
    except Exception as e:
        print(f"  Pixel diff failed: {e}")
        return None


def generate_gallery(results: list[dict], output_path: Path) -> None:
    """Generate HTML gallery for visual comparison."""
    html = """<!DOCTYPE html>
<html>
<head>
<title>pymermaid vs mermaid.js Comparison</title>
<style>
body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
h1 { color: #333; }
.pair { display: flex; gap: 20px; margin: 20px 0; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.pair img { max-width: 380px; border: 1px solid #ddd; background: white; }
.label { font-weight: bold; margin-bottom: 5px; }
.score { margin-top: 5px; font-size: 14px; }
.score.good { color: #2a7; }
.score.ok { color: #a80; }
.score.bad { color: #c33; }
.name { font-size: 18px; font-weight: bold; color: #555; margin-top: 20px; }
table { border-collapse: collapse; margin: 20px 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #f0f0f0; }
</style>
</head>
<body>
<h1>pymermaid vs mermaid.js Visual Comparison</h1>
<table>
<tr><th>Diagram</th><th>SSIM</th><th>Pixel Diff %</th><th>Rating</th></tr>
"""
    for r in sorted(results, key=lambda x: x.get("ssim", 0)):
        ssim = r.get("ssim", "N/A")
        diff = r.get("pixel_diff", "N/A")
        if isinstance(ssim, float):
            if ssim >= 0.8:
                rating = "Good"
            elif ssim >= 0.6:
                rating = "OK"
            else:
                rating = "Needs Work"
        else:
            rating = "N/A"
        html += f'<tr><td>{r["name"]}</td><td>{ssim}</td><td>{diff}%</td><td>{rating}</td></tr>\n'

    html += "</table>\n"

    for r in sorted(results, key=lambda x: x.get("ssim", 0)):
        name = r["name"]
        ssim = r.get("ssim", "N/A")
        cls = "good" if isinstance(ssim, float) and ssim >= 0.8 else ("ok" if isinstance(ssim, float) and ssim >= 0.6 else "bad")
        rel = r.get("rel_path", name)
        html += f'<div class="name">{name} (SSIM: {ssim})</div>\n'
        html += '<div class="pair">\n'
        html += f'  <div><div class="label">pymermaid</div><img src="comparisons/{rel}_pymermaid.png"></div>\n'
        html += f'  <div><div class="label">mermaid.js (mmdc)</div><img src="comparisons/{rel}_mmdc.png"></div>\n'
        html += f'  <div><div class="label">Diff</div><img src="comparisons/{rel}_diff.png"></div>\n'
        html += '</div>\n'

    html += "</body></html>"
    output_path.write_text(html)


def main() -> None:
    results: list[dict] = []
    mmd_files = sorted(CORPUS_DIR.rglob("*.mmd"))
    print(f"Found {len(mmd_files)} corpus fixtures")

    for mmd_path in mmd_files:
        rel = mmd_path.relative_to(CORPUS_DIR)
        name = str(rel.with_suffix(""))
        category = rel.parent
        stem = rel.stem

        ref_svg = REFERENCE_DIR / category / f"{stem}.svg"
        if not ref_svg.exists():
            print(f"  Skipping {name}: no mmdc reference")
            continue

        print(f"Processing {name}...")
        out_dir = OUTPUT_DIR / category
        out_dir.mkdir(parents=True, exist_ok=True)

        # Render pymermaid SVG
        pm_svg = out_dir / f"{stem}_pymermaid.svg"
        if not render_pymermaid(mmd_path, pm_svg):
            continue

        # Convert to PNG
        pm_png = out_dir / f"{stem}_pymermaid.png"
        ref_png = out_dir / f"{stem}_mmdc.png"
        diff_png = out_dir / f"{stem}_diff.png"

        if not svg_to_png(pm_svg, pm_png):
            continue
        if not svg_to_png(ref_svg, ref_png):
            continue

        # Compute scores
        ssim = compute_ssim(pm_png, ref_png)
        pixel_diff = compute_pixel_diff(pm_png, ref_png, diff_png)

        result = {
            "name": name,
            "rel_path": str(category / stem),
            "ssim": ssim,
            "pixel_diff": pixel_diff,
        }
        results.append(result)
        print(f"  SSIM: {ssim}, Pixel diff: {pixel_diff}%")

    # Generate report
    print(f"\n{'='*60}")
    print(f"Results: {len(results)} diagrams compared")
    ssim_scores = [r["ssim"] for r in results if r["ssim"] is not None]
    if ssim_scores:
        avg = sum(ssim_scores) / len(ssim_scores)
        print(f"Average SSIM: {avg:.4f}")
        print(f"Min SSIM: {min(ssim_scores):.4f}")
        print(f"Max SSIM: {max(ssim_scores):.4f}")

    # Write markdown report
    report_path = PROJECT_ROOT / "docs" / "comparison_report.md"
    with open(report_path, "w") as f:
        f.write("# pymermaid vs mermaid.js Visual Comparison Report\n\n")
        if ssim_scores:
            f.write(f"**Average SSIM:** {avg:.4f}\n\n")
        f.write("| Diagram | SSIM | Pixel Diff % |\n")
        f.write("|---------|------|--------------|\n")
        for r in sorted(results, key=lambda x: x.get("ssim", 0)):
            f.write(f"| {r['name']} | {r.get('ssim', 'N/A')} | {r.get('pixel_diff', 'N/A')}% |\n")

    # Write JSON for programmatic use
    json_path = PROJECT_ROOT / "docs" / "comparison_scores.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Generate HTML gallery
    gallery_path = PROJECT_ROOT / "docs" / "comparison_gallery.html"
    generate_gallery(results, gallery_path)

    print(f"\nReport: {report_path}")
    print(f"Gallery: {gallery_path}")
    print(f"Scores: {json_path}")


if __name__ == "__main__":
    main()
