#!/usr/bin/env python3
"""Extract exercise images from a PDF and optionally generate exercise folders.

Usage examples:

  # Screenshot every page of a PDF as a numbered PNG:
  python extract_exercises.py exam.pdf --outdir screenshots/

  # Screenshot specific pages:
  python extract_exercises.py exam.pdf --pages 2,3,5 --outdir screenshots/

  # Crop a region (left%, top%, right%, bottom%) — useful when a page has
  # multiple exercises and you only want one:
  python extract_exercises.py exam.pdf --pages 3 --crop 0,0,100,50 --outdir screenshots/

  # Generate a full exercise folder ready for the repo:
  python extract_exercises.py exam.pdf --pages 2 \
      --institucion olimpiada-argentina --tema optica \
      --anio 2025 --etapa nacional --exercise-num 1 \
      --fuente "Olimpiada Argentina de Astronomía 2025, Nacional"

  # Process multiple exercises at once (one page each, sequential numbering):
  python extract_exercises.py exam.pdf --pages 1,2,3,4,5 \
      --institucion olimpiada-argentina --tema mecanica-celeste \
      --anio 2025 --etapa nacional --exercise-num 1 \
      --fuente "Olimpiada Argentina de Astronomía 2025, Nacional"

Requires: pip install pymupdf pyyaml
"""

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF
import yaml

from build import build_exercise_id


def render_page(doc, page_num, dpi=200, crop=None):
    """Render a PDF page to a PNG bytes buffer.

    Args:
        doc: fitz.Document
        page_num: 0-indexed page number
        dpi: render resolution
        crop: optional (left%, top%, right%, bottom%) tuple, each 0-100
    Returns:
        PNG bytes
    """
    page = doc[page_num]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    if crop:
        left_pct, top_pct, right_pct, bottom_pct = crop
        x0 = int(pix.width * left_pct / 100)
        y0 = int(pix.height * top_pct / 100)
        x1 = int(pix.width * right_pct / 100)
        y1 = int(pix.height * bottom_pct / 100)
        pix = fitz.Pixmap(pix, 0) if pix.alpha else pix
        cropped = fitz.Pixmap(pix.colorspace, fitz.IRect(x0, y0, x1, y1), pix.alpha)
        cropped.copy(pix, fitz.IRect(x0, y0, x1, y1))
        return cropped.tobytes("png")

    return pix.tobytes("png")


def parse_pages(pages_str, total):
    """Parse a pages string like '1,3,5-7' into 0-indexed page numbers."""
    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            for p in range(int(start), int(end) + 1):
                pages.append(p - 1)
        else:
            pages.append(int(part) - 1)
    return [p for p in pages if 0 <= p < total]


def main():
    parser = argparse.ArgumentParser(
        description="Extract exercise images from a PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--pages", help="Pages to extract (1-indexed), e.g. '1,3,5-7'. Default: all pages")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    parser.add_argument(
        "--crop",
        help="Crop region as left%%,top%%,right%%,bottom%% (each 0-100). "
             "E.g. '0,0,100,50' for the top half of the page",
    )
    parser.add_argument("--outdir", default=".", help="Output directory for screenshots (default: current dir)")

    # Exercise metadata (if provided, generates full exercise folders)
    meta_group = parser.add_argument_group("exercise metadata (generates folders if provided)")
    meta_group.add_argument("--institucion", help="Institution slug, e.g. 'olimpiada-argentina'")
    meta_group.add_argument("--tema", help="Topic slug, e.g. 'mecanica-celeste'")
    meta_group.add_argument("--anio", type=int, help="Year")
    meta_group.add_argument("--etapa", help="Stage: provincial, nacional, or internacional")
    meta_group.add_argument("--fuente", help="Source description")
    meta_group.add_argument("--subtemas", default="", help="Comma-separated subtemas (optional)")
    meta_group.add_argument("--modalidad", help="Modality: individual or grupal (optional)")
    meta_group.add_argument("--nivel", help="Level: N1, N2, N3, N4 (optional)")
    meta_group.add_argument("--solucion", help="Solution URL (optional)")
    meta_group.add_argument("--exercise-num", type=int, default=1, help="Starting exercise number (default: 1)")

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    if args.pages:
        page_nums = parse_pages(args.pages, total_pages)
    else:
        page_nums = list(range(total_pages))

    if not page_nums:
        print("No valid pages to process.", file=sys.stderr)
        sys.exit(1)

    crop = None
    if args.crop:
        parts = [float(x) for x in args.crop.split(",")]
        if len(parts) != 4:
            print("Error: --crop must be 4 comma-separated values", file=sys.stderr)
            sys.exit(1)
        crop = tuple(parts)

    # Determine mode: screenshot-only or full exercise folders
    generate_folders = all([args.institucion, args.tema, args.anio, args.etapa, args.fuente])

    if generate_folders:
        subtemas = [s.strip() for s in args.subtemas.split(",") if s.strip()] if args.subtemas else []
        exercises_dir = Path("exercises")
        exercise_num = args.exercise_num

        for page_num in page_nums:
            meta = {
                "institucion": args.institucion,
                "tema": args.tema,
                "subtemas": subtemas,
                "anio": args.anio,
                "etapa": args.etapa,
                "numero": exercise_num,
                "fuente": args.fuente,
            }
            if args.modalidad:
                meta["modalidad"] = args.modalidad
            if args.nivel:
                meta["nivel"] = args.nivel
            if args.solucion:
                meta["solucion"] = args.solucion

            eid = build_exercise_id(meta)
            folder = exercises_dir / args.institucion / args.tema / eid
            folder.mkdir(parents=True, exist_ok=True)

            # Render and save image
            png_bytes = render_page(doc, page_num, dpi=args.dpi, crop=crop)
            (folder / "imagen.png").write_bytes(png_bytes)

            with open(folder / "meta.yaml", "w", encoding="utf-8") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

            print(f"  Created {folder}/")
            exercise_num += 1

        print(f"\nGenerated {len(page_nums)} exercise(s). Run 'python build.py --validate-only' to check.")

    else:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        for page_num in page_nums:
            png_bytes = render_page(doc, page_num, dpi=args.dpi, crop=crop)
            out_path = outdir / f"page-{page_num + 1}.png"
            out_path.write_bytes(png_bytes)
            print(f"  Saved {out_path}")

        print(f"\nExtracted {len(page_nums)} page(s) to {outdir}/")

    doc.close()


if __name__ == "__main__":
    main()
