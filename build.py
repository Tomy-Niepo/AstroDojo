#!/usr/bin/env python3
"""Build script for AstroDojo — static site generator for astronomy olympiad exercises."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

EXERCISES_DIR = Path("exercises")
TEMPLATES_DIR = Path("templates")
SITE_DIR = Path("site")
STATIC_DIR = Path("static")

REQUIRED_FIELDS = {"institucion", "tema", "subtemas", "dificultad", "anio", "etapa", "fuente"}
VALID_DIFICULTAD = {"facil", "intermedio", "dificil"}
VALID_ETAPA = {"provincial", "nacional", "internacional"}
VALID_TEMAS = {
    "mecanica", "optica", "termodinamica",
    "electromagnetismo", "astronomia-observacional", "astrofisica",
}

TOPIC_DISPLAY = {
    "mecanica": "Mecánica",
    "optica": "Óptica",
    "termodinamica": "Termodinámica",
    "electromagnetismo": "Electromagnetismo",
    "astronomia-observacional": "Astronomía Observacional",
    "astrofisica": "Astrofísica",
}


def load_exercises():
    """Walk the exercises directory and load all meta.yaml files."""
    exercises = []
    for meta_path in sorted(EXERCISES_DIR.rglob("meta.yaml")):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        if meta is None:
            meta = {}
        meta["_folder"] = str(meta_path.parent)
        meta["_id"] = meta_path.parent.name
        # Check for image
        img_candidates = list(meta_path.parent.glob("imagen.*"))
        if img_candidates:
            meta["_imagen"] = img_candidates[0].name
        else:
            meta["_imagen"] = None
        exercises.append(meta)
    return exercises


def validate_exercise(meta, path):
    """Validate a single exercise's metadata. Returns list of error strings."""
    errors = []
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(sorted(missing))}")

    if meta.get("dificultad") and meta["dificultad"] not in VALID_DIFICULTAD:
        errors.append(f"{path}: invalid dificultad '{meta['dificultad']}' (must be one of {VALID_DIFICULTAD})")

    if meta.get("etapa") and meta["etapa"] not in VALID_ETAPA:
        errors.append(f"{path}: invalid etapa '{meta['etapa']}' (must be one of {VALID_ETAPA})")

    if meta.get("tema") and meta["tema"] not in VALID_TEMAS:
        errors.append(f"{path}: invalid tema '{meta['tema']}' (must be one of {VALID_TEMAS})")

    if meta.get("subtemas") and not isinstance(meta["subtemas"], list):
        errors.append(f"{path}: subtemas must be a list")

    if meta.get("anio") and not isinstance(meta["anio"], int):
        errors.append(f"{path}: anio must be an integer")

    return errors


def validate_all(exercises):
    """Validate all exercises. Returns (is_valid, errors)."""
    all_errors = []
    for ex in exercises:
        errs = validate_exercise(ex, ex["_folder"])
        all_errors.extend(errs)
    return len(all_errors) == 0, all_errors


def build_site(exercises):
    """Generate the static site from templates and exercise data."""
    # Clean output
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    # Group exercises by institution, then by topic
    institutions = {}
    for ex in exercises:
        inst = ex.get("institucion", "unknown")
        tema = ex.get("tema", "unknown")
        institutions.setdefault(inst, {})
        institutions[inst].setdefault(tema, [])
        institutions[inst][tema].append(ex)

    # Build exercises.json for client-side filtering
    exercises_json = []
    for ex in exercises:
        exercises_json.append({
            "id": ex["_id"],
            "institucion": ex.get("institucion"),
            "tema": ex.get("tema"),
            "subtemas": ex.get("subtemas", []),
            "dificultad": ex.get("dificultad"),
            "anio": ex.get("anio"),
            "etapa": ex.get("etapa"),
            "fuente": ex.get("fuente"),
            "imagen": f"exercises/{ex.get('institucion')}/{ex.get('tema')}/{ex['_id']}/{ex['_imagen']}" if ex.get("_imagen") else None,
        })

    with open(SITE_DIR / "exercises.json", "w", encoding="utf-8") as f:
        json.dump(exercises_json, f, ensure_ascii=False, indent=2)

    # Render index page
    tmpl_index = env.get_template("index.html")
    html = tmpl_index.render(
        institutions=institutions,
        topic_display=TOPIC_DISPLAY,
    )
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Render topic pages
    for inst, topics in institutions.items():
        inst_dir = SITE_DIR / inst
        inst_dir.mkdir(parents=True, exist_ok=True)
        for tema, exs in topics.items():
            topic_dir = inst_dir / tema
            topic_dir.mkdir(parents=True, exist_ok=True)

            # Collect all subtemas for this topic
            all_subtemas = set()
            for ex in exs:
                for s in ex.get("subtemas", []):
                    all_subtemas.add(s)

            tmpl_topic = env.get_template("topic.html")
            html = tmpl_topic.render(
                institucion=inst,
                tema=tema,
                tema_display=TOPIC_DISPLAY.get(tema, tema),
                exercises=exs,
                subtemas=sorted(all_subtemas),
            )
            with open(topic_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(html)

    # Copy exercise images into site
    for ex in exercises:
        if ex.get("_imagen"):
            src = Path(ex["_folder"]) / ex["_imagen"]
            dest_dir = SITE_DIR / "exercises" / ex.get("institucion", "") / ex.get("tema", "") / ex["_id"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / ex["_imagen"])

    # Copy static assets
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, SITE_DIR / "static", dirs_exist_ok=True)

    # Copy contributor wizard
    contribute_src = Path("contribute")
    if contribute_src.exists():
        shutil.copytree(contribute_src, SITE_DIR / "contribute", dirs_exist_ok=True)

    print(f"Built site with {len(exercises)} exercises into {SITE_DIR}/")


def main():
    parser = argparse.ArgumentParser(description="Build AstroDojo static site")
    parser.add_argument("--validate-only", action="store_true", help="Only validate meta.yaml files, don't build")
    args = parser.parse_args()

    exercises = load_exercises()

    if not exercises:
        print("WARNING: No exercises found.")
        if args.validate_only:
            print("Validation passed (no exercises to validate).")
            return
    else:
        is_valid, errors = validate_all(exercises)
        if not is_valid:
            print("Validation FAILED:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print(f"Validation passed for {len(exercises)} exercises.")

    if args.validate_only:
        return

    build_site(exercises)


if __name__ == "__main__":
    main()
