#!/usr/bin/env python3
"""Import exercises from the new-exercises/ staging folder into exercises/<inst>/<tema>/<id>/."""

import argparse
import shutil
import sys
from pathlib import Path

import yaml

from build import (
    REQUIRED_FIELDS,
    TOPIC_DISPLAY,
    VALID_DIFICULTAD,
    VALID_ETAPA,
    VALID_TEMAS,
)

STAGING_DIR = Path("new-exercises")
EXERCISES_DIR = Path("exercises")
ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


def load_staged_exercises():
    """Find all exercise folders in new-exercises/ that contain a meta.yaml."""
    exercises = []
    if not STAGING_DIR.exists():
        return exercises
    for child in sorted(STAGING_DIR.iterdir()):
        meta_path = child / "meta.yaml"
        if child.is_dir() and meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
            meta["_id"] = child.name
            meta["_folder"] = child
            # Check for image
            img_candidates = [p for p in child.glob("imagen.*") if p.suffix.lower() in ALLOWED_IMG_EXT]
            meta["_imagen"] = img_candidates[0].name if img_candidates else None
            exercises.append(meta)
    return exercises


def validate_exercise(meta):
    """Validate a single exercise's metadata. Returns list of error strings."""
    exercise_id = meta["_id"]
    errors = []

    missing = REQUIRED_FIELDS - set(k for k in meta.keys() if not k.startswith("_"))
    if missing:
        errors.append(f"{exercise_id}: missing fields: {', '.join(sorted(missing))}")

    if meta.get("dificultad") and meta["dificultad"] not in VALID_DIFICULTAD:
        errors.append(f"{exercise_id}: invalid dificultad '{meta['dificultad']}' (must be one of {VALID_DIFICULTAD})")

    if meta.get("etapa") and meta["etapa"] not in VALID_ETAPA:
        errors.append(f"{exercise_id}: invalid etapa '{meta['etapa']}' (must be one of {VALID_ETAPA})")

    if meta.get("tema") and meta["tema"] not in VALID_TEMAS:
        errors.append(f"{exercise_id}: invalid tema '{meta['tema']}' (must be one of {VALID_TEMAS})")

    if meta.get("subtemas") and not isinstance(meta["subtemas"], list):
        errors.append(f"{exercise_id}: subtemas must be a list")

    if meta.get("anio") and not isinstance(meta["anio"], int):
        errors.append(f"{exercise_id}: anio must be an integer")

    if "solucion" in meta and not isinstance(meta["solucion"], str):
        errors.append(f"{exercise_id}: solucion must be a string (URL)")

    if not meta.get("_imagen"):
        errors.append(f"{exercise_id}: no imagen.* file found")

    return errors


def get_target_path(meta):
    """Compute the target path: exercises/<inst>/<tema>/<id>/."""
    inst = meta.get("institucion", "")
    tema = meta.get("tema", "")
    exercise_id = meta["_id"]
    return EXERCISES_DIR / inst / tema / exercise_id


def main():
    parser = argparse.ArgumentParser(description="Import exercises from new-exercises/ into the exercises/ hierarchy.")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be imported without moving anything.")
    args = parser.parse_args()

    if not STAGING_DIR.exists():
        print(f"Staging directory '{STAGING_DIR}' does not exist. Nothing to import.")
        sys.exit(0)

    exercises = load_staged_exercises()
    if not exercises:
        print(f"No exercises found in '{STAGING_DIR}/'. Nothing to import.")
        sys.exit(0)

    print(f"Found {len(exercises)} exercise(s) in {STAGING_DIR}/\n")

    # Pass 1: Validate all exercises
    all_errors = []
    skipped = []
    to_import = []

    for meta in exercises:
        errors = validate_exercise(meta)
        target = get_target_path(meta)

        if target.exists():
            skipped.append((meta["_id"], target))
            continue

        if errors:
            all_errors.extend(errors)
        else:
            to_import.append((meta, target))

    # Report skipped
    if skipped:
        print("SKIPPED (target already exists):")
        for eid, target in skipped:
            print(f"  - {eid} -> {target}")
        print()

    # Report errors
    if all_errors:
        print("VALIDATION ERRORS:")
        for e in all_errors:
            print(f"  - {e}")
        print(f"\nImport aborted. Fix the errors above and try again.")
        sys.exit(1)

    if not to_import:
        print("No exercises to import (all skipped or staging is empty).")
        sys.exit(0)

    # Show what will be imported
    print("TO IMPORT:")
    for meta, target in to_import:
        display_tema = TOPIC_DISPLAY.get(meta.get("tema", ""), meta.get("tema", ""))
        print(f"  {meta['_id']} -> {target}  ({display_tema})")
    print()

    if args.dry_run:
        print("Dry run — no files were moved.")
        sys.exit(0)

    # Pass 2: Move all validated exercises
    moved = 0
    for meta, target in to_import:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(meta["_folder"]), str(target))
        moved += 1
        print(f"  Moved {meta['_id']} -> {target}")

    print(f"\nImported {moved} exercise(s).")
    print("Reminder: run 'python build.py --validate-only' to verify.")


if __name__ == "__main__":
    main()
