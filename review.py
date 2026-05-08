#!/usr/bin/env python3
"""AstroDojo Review — local Flask app for reviewing staged exercises in new-exercises/."""

import subprocess
import sys
from pathlib import Path

import yaml
from flask import Flask, flash, redirect, render_template_string, request, send_file, url_for
from werkzeug.utils import secure_filename

from build import (
    REQUIRED_FIELDS,
    TOPIC_DISPLAY,
    VALID_DIFICULTAD,
    VALID_ETAPA,
    VALID_TEMAS,
)

app = Flask(__name__)
app.secret_key = "astrodojo-review-local-only"

BASE_DIR = Path(__file__).resolve().parent
STAGING_DIR = BASE_DIR / "new-exercises"
ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_staged_exercises():
    """Load all exercises from new-exercises/."""
    exercises = []
    if not STAGING_DIR.exists():
        return exercises
    for child in sorted(STAGING_DIR.iterdir()):
        meta_path = child / "meta.yaml"
        if child.is_dir() and meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
            meta["_id"] = child.name
            meta["_folder"] = str(child)
            img_candidates = [p for p in child.glob("imagen.*") if p.suffix.lower() in ALLOWED_IMG_EXT]
            meta["_imagen"] = img_candidates[0].name if img_candidates else None
            exercises.append(meta)
    return exercises


def find_staged_exercise(exercise_id):
    """Find a single staged exercise by folder name."""
    folder = STAGING_DIR / exercise_id
    meta_path = folder / "meta.yaml"
    if not folder.is_dir() or not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    meta["_id"] = exercise_id
    meta["_folder"] = str(folder)
    img_candidates = [p for p in folder.glob("imagen.*") if p.suffix.lower() in ALLOWED_IMG_EXT]
    meta["_imagen"] = img_candidates[0].name if img_candidates else None
    return meta


def validate_meta(meta):
    """Validate exercise metadata. Returns list of error strings."""
    errors = []
    missing = REQUIRED_FIELDS - set(k for k in meta.keys() if not k.startswith("_"))
    if missing:
        errors.append(f"Missing fields: {', '.join(sorted(missing))}")
    if meta.get("dificultad") and meta["dificultad"] not in VALID_DIFICULTAD:
        errors.append(f"Invalid dificultad '{meta['dificultad']}'")
    if meta.get("etapa") and meta["etapa"] not in VALID_ETAPA:
        errors.append(f"Invalid etapa '{meta['etapa']}'")
    if meta.get("tema") and meta["tema"] not in VALID_TEMAS:
        errors.append(f"Invalid tema '{meta['tema']}'")
    if meta.get("subtemas") and not isinstance(meta["subtemas"], list):
        errors.append("subtemas must be a list")
    if meta.get("anio") and not isinstance(meta["anio"], int):
        errors.append("anio must be an integer")
    if not meta.get("_imagen"):
        errors.append("No imagen.* file found")
    return errors


def save_image(file_storage, dest_dir):
    """Save uploaded image as imagen.<ext>, removing any previous one."""
    if not file_storage or file_storage.filename == "":
        return
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMG_EXT:
        raise ValueError(f"Image extension '{ext}' not allowed. Use: {ALLOWED_IMG_EXT}")
    for old in dest_dir.glob("imagen.*"):
        old.unlink()
    file_storage.save(str(dest_dir / f"imagen{ext}"))


# ---------------------------------------------------------------------------
# Templates (inline Jinja2)
# ---------------------------------------------------------------------------

LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AstroDojo Review{% block title_extra %}{% endblock %}</title>
<style>
  :root { --bg: #f5f6fa; --card: #fff; --accent: #4a6cf7; --danger: #e74c3c;
          --success: #28a745; --text: #222; --muted: #888; --border: #ddd; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.5; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .container { max-width: 1100px; margin: 0 auto; padding: 1rem; }
  nav { background: #1a1a2e; color: #fff; padding: .75rem 1rem; display: flex;
        align-items: center; gap: 1.5rem; flex-wrap: wrap; }
  nav a { color: #ccc; } nav a:hover { color: #fff; }
  nav .brand { font-weight: 700; font-size: 1.1rem; color: #fff; }
  .flash { padding: .6rem 1rem; border-radius: 4px; margin-bottom: 1rem; }
  .flash.success { background: #d4edda; color: #155724; }
  .flash.error { background: #f8d7da; color: #721c24; }
  table { width: 100%; border-collapse: collapse; background: var(--card);
          border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  th, td { padding: .55rem .75rem; text-align: left; border-bottom: 1px solid var(--border); font-size: .9rem; }
  th { background: #f0f1f5; font-weight: 600; position: sticky; top: 0; }
  tr:hover { background: #f8f9ff; }
  .thumb { max-height: 48px; max-width: 80px; border-radius: 3px; }
  .btn { display: inline-block; padding: .4rem .9rem; border: none; border-radius: 4px;
         cursor: pointer; font-size: .85rem; color: #fff; text-decoration: none; }
  .btn-primary { background: var(--accent); } .btn-primary:hover { background: #3b5de7; }
  .btn-danger { background: var(--danger); } .btn-danger:hover { background: #c0392b; }
  .btn-success { background: var(--success); } .btn-success:hover { background: #218838; }
  .btn-secondary { background: #6c757d; } .btn-secondary:hover { background: #565e64; }
  .btn-sm { padding: .25rem .55rem; font-size: .8rem; }
  form.inline { display: inline; }
  fieldset { border: 1px solid var(--border); border-radius: 6px; padding: 1rem 1.25rem;
             margin-bottom: 1rem; background: var(--card); }
  legend { font-weight: 600; padding: 0 .4rem; }
  label { display: block; margin-top: .6rem; font-weight: 500; font-size: .9rem; }
  input[type=text], input[type=number], input[type=url], select, textarea {
    width: 100%; padding: .4rem .6rem; border: 1px solid var(--border);
    border-radius: 4px; font-size: .9rem; margin-top: .2rem; }
  input[type=file] { margin-top: .3rem; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1.5rem; }
  .form-actions { margin-top: 1rem; display: flex; gap: .5rem; }
  .preview-img { max-width: 200px; border-radius: 4px; margin-top: .5rem; }
  .no-img { color: var(--muted); font-style: italic; font-size: .85rem; }
  .valid-ok { color: var(--success); font-weight: 600; }
  .valid-err { color: var(--danger); font-weight: 600; }
  pre.output { background: #1a1a2e; color: #0f0; padding: 1rem;
       border-radius: 6px; max-height: 400px; overflow: auto; font-size: .82rem; white-space: pre-wrap; }
  .error-list { color: var(--danger); font-size: .82rem; margin: 0; padding-left: 1.2rem; }
</style>
</head>
<body>
<nav>
  <span class="brand">AstroDojo Review</span>
  <a href="/">Staged Exercises</a>
  <a href="/import">Import All</a>
</nav>
<div class="container" style="margin-top:1rem;">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="flash {{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>
</body>
</html>
"""

INDEX_PAGE = """
{% extends layout %}
{% block title_extra %} — Staged Exercises{% endblock %}
{% block content %}
<h2 style="margin-bottom:.75rem;">Staged Exercises ({{ exercises|length }})</h2>
{% if not exercises %}
  <p style="color:var(--muted);">No exercises found in <code>new-exercises/</code>. Drop exercise folders there to get started.</p>
{% else %}
  <div style="margin-bottom:.75rem; display:flex; gap:.5rem;">
    <a href="/import" class="btn btn-success">Import All to exercises/</a>
  </div>
  <table>
  <tr><th>Img</th><th>ID</th><th>Tema</th><th>Etapa</th><th>Year</th><th>Fuente</th><th>Valid</th><th>Actions</th></tr>
  {% for ex in exercises %}
  <tr>
    <td>{% if ex._imagen %}<img class="thumb" src="/img/{{ ex._id }}/{{ ex._imagen }}">{% else %}<span class="no-img">-</span>{% endif %}</td>
    <td>{{ ex._id }}</td>
    <td>{{ topic_display.get(ex.tema, ex.tema or '-') }}</td>
    <td>{{ ex.etapa or '-' }}</td>
    <td>{{ ex.anio or '-' }}</td>
    <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ ex.fuente or '-' }}</td>
    <td>
      {% if ex._errors %}
        <span class="valid-err" title="{{ ex._errors|join('; ') }}">&#10007;</span>
        <ul class="error-list">{% for e in ex._errors %}<li>{{ e }}</li>{% endfor %}</ul>
      {% else %}
        <span class="valid-ok">&#10003;</span>
      {% endif %}
    </td>
    <td style="white-space:nowrap;">
      <a href="/edit/{{ ex._id }}" class="btn btn-primary btn-sm">Edit</a>
      <form class="inline" method="post" action="/delete/{{ ex._id }}"
        onsubmit="return confirm('Delete {{ ex._id }} from staging?');">
        <button class="btn btn-danger btn-sm" type="submit">Del</button>
      </form>
    </td>
  </tr>
  {% endfor %}
  </table>
{% endif %}
{% endblock %}
"""

EDIT_PAGE = """
{% extends layout %}
{% block title_extra %} — Edit {{ meta._id }}{% endblock %}
{% block content %}
<h2>Edit {{ meta._id }}</h2>
<form method="post" enctype="multipart/form-data">
<fieldset><legend>Classification</legend>
  <div class="form-row">
    <div><label>Institucion</label>
      <input type="text" name="institucion" value="{{ meta.institucion or '' }}" required
        placeholder="e.g. olimpiada-argentina"></div>
    <div><label>Tema</label><select name="tema" required>
      {% for t in valid_temas|sort %}<option value="{{t}}" {{ 'selected' if t==meta.tema }}>{{topic_display.get(t,t)}}</option>{% endfor %}
    </select></div>
  </div>
  <div class="form-row">
    <div><label>Subtemas (comma-separated)</label>
      <input type="text" name="subtemas" value="{{ meta.subtemas|default([])|join(', ') }}"
        placeholder="e.g. cinematica, energia"></div>
    <div><label>Etapa</label><select name="etapa" required>
      {% for e in valid_etapa|sort %}<option value="{{e}}" {{ 'selected' if e==meta.etapa }}>{{e}}</option>{% endfor %}
    </select></div>
  </div>
</fieldset>
<fieldset><legend>Details</legend>
  <div class="form-row">
    <div><label>Year</label><input type="number" name="anio" value="{{ meta.anio or '' }}" required></div>
    <div><label>Dificultad (optional)</label><select name="dificultad">
      <option value="">-</option>
      {% for d in valid_dif|sort %}<option value="{{d}}" {{ 'selected' if d==meta.dificultad }}>{{d}}</option>{% endfor %}
    </select></div>
  </div>
  <div class="form-row">
    <div><label>Fuente</label><input type="text" name="fuente" value="{{ meta.fuente or '' }}" required
      placeholder="e.g. Olimpiada Argentina 2025, Nacional"></div>
    <div><label>Solucion URL (optional)</label><input type="url" name="solucion" value="{{ meta.solucion or '' }}"></div>
  </div>
  <div class="form-row">
    <div><label>Image{% if meta._imagen %} (current: {{ meta._imagen }}){% endif %}</label>
      <input type="file" name="imagen" accept="image/*">
      {% if meta._imagen %}<br><img class="preview-img" src="/img/{{ meta._id }}/{{ meta._imagen }}">{% endif %}
    </div>
  </div>
</fieldset>
<div class="form-actions">
  <button type="submit" class="btn btn-primary">Save changes</button>
  <a href="/" class="btn btn-secondary">Cancel</a>
</div>
</form>
{% endblock %}
"""

IMPORT_PAGE = """
{% extends layout %}
{% block title_extra %} — Import{% endblock %}
{% block content %}
<h2 style="margin-bottom:.75rem;">Import Exercises</h2>
<p style="margin-bottom:1rem;color:var(--muted);font-size:.9rem;">
  This will validate all exercises in <code>new-exercises/</code> and move them into <code>exercises/&lt;inst&gt;/&lt;tema&gt;/&lt;id&gt;/</code>.</p>
<div style="display:flex;gap:.5rem;margin-bottom:1rem;">
  <form method="post">
    <button type="submit" name="mode" value="dry-run" class="btn btn-secondary">Dry Run (preview)</button>
    <button type="submit" name="mode" value="import" class="btn btn-success">Import All</button>
  </form>
</div>
{% if output is not none %}
  <h3 style="margin-top:1rem;">Output</h3>
  <pre class="output">{{ output }}</pre>
{% endif %}
{% endblock %}
"""

_TEMPLATES = {
    "index": INDEX_PAGE,
    "edit": EDIT_PAGE,
    "import": IMPORT_PAGE,
}


def rp(name, **ctx):
    """Render a named page template inside the layout."""
    tpl_src = _TEMPLATES[name]
    title_extra = ""
    if "{% block title_extra %}" in tpl_src:
        title_extra = tpl_src.split("{% block title_extra %}")[1].split("{% endblock %}")[0]
    content = ""
    if "{% block content %}" in tpl_src:
        content = tpl_src.split("{% block content %}")[1].rsplit("{% endblock %}", 1)[0]
    html = (
        LAYOUT
        .replace("{% block title_extra %}{% endblock %}", title_extra)
        .replace("{% block content %}{% endblock %}", content)
    )
    return render_template_string(html, **ctx)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    exercises = load_staged_exercises()
    # Attach validation errors to each exercise
    for ex in exercises:
        ex["_errors"] = validate_meta(ex)
    return rp("index", exercises=exercises, topic_display=TOPIC_DISPLAY)


@app.route("/edit/<exercise_id>", methods=["GET", "POST"])
def edit(exercise_id):
    exercise_id = secure_filename(exercise_id)
    meta = find_staged_exercise(exercise_id)
    if not meta:
        flash(f"Exercise '{exercise_id}' not found in staging.", "error")
        return redirect(url_for("index"))

    if request.method == "GET":
        return rp("edit", meta=meta, valid_temas=VALID_TEMAS, valid_dif=VALID_DIFICULTAD,
                  valid_etapa=VALID_ETAPA, topic_display=TOPIC_DISPLAY)

    # POST — save edits
    subtemas_raw = request.form.get("subtemas", "").strip()
    subtemas = [s.strip() for s in subtemas_raw.split(",") if s.strip()] if subtemas_raw else []

    try:
        anio = int(request.form.get("anio", 0))
    except ValueError:
        flash("Year must be an integer.", "error")
        return redirect(url_for("edit", exercise_id=exercise_id))

    updated = {
        "institucion": request.form.get("institucion", "").strip(),
        "tema": request.form.get("tema", "").strip(),
        "subtemas": subtemas,
        "anio": anio,
        "etapa": request.form.get("etapa", "").strip(),
        "fuente": request.form.get("fuente", "").strip(),
    }
    dif = request.form.get("dificultad", "").strip()
    if dif:
        updated["dificultad"] = dif
    sol = request.form.get("solucion", "").strip()
    if sol:
        updated["solucion"] = sol

    errors = validate_meta(updated)
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("edit", exercise_id=exercise_id))

    folder = STAGING_DIR / exercise_id
    with open(folder / "meta.yaml", "w", encoding="utf-8") as f:
        yaml.dump(updated, f, allow_unicode=True, default_flow_style=False)

    try:
        save_image(request.files.get("imagen"), folder)
    except ValueError as ve:
        flash(str(ve), "error")

    flash(f"Updated {exercise_id}.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<exercise_id>", methods=["POST"])
def delete(exercise_id):
    exercise_id = secure_filename(exercise_id)
    folder = STAGING_DIR / exercise_id
    if folder.exists() and folder.is_dir():
        import shutil
        shutil.rmtree(folder)
        flash(f"Deleted {exercise_id} from staging.", "success")
    else:
        flash(f"Exercise '{exercise_id}' not found.", "error")
    return redirect(url_for("index"))


@app.route("/img/<exercise_id>/<filename>")
def staged_image(exercise_id, filename):
    """Serve images from the staging directory."""
    exercise_id = secure_filename(exercise_id)
    filename = secure_filename(filename)
    return send_file(STAGING_DIR / exercise_id / filename)


@app.route("/import", methods=["GET", "POST"])
def import_page():
    output = None
    if request.method == "POST":
        mode = request.form.get("mode", "dry-run")
        cmd = [sys.executable, "import_exercises.py"]
        if mode == "dry-run":
            cmd.append("--dry-run")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=60,
            )
            output = result.stdout
            if result.stderr:
                output += "\n--- stderr ---\n" + result.stderr
            if result.returncode == 0:
                if mode == "dry-run":
                    flash("Dry run completed.", "success")
                else:
                    flash("Import completed.", "success")
            else:
                flash(f"Import failed (exit code {result.returncode}).", "error")
        except subprocess.TimeoutExpired:
            output = "Import timed out after 60 seconds."
            flash("Import timed out.", "error")
        except Exception as exc:
            output = str(exc)
            flash(f"Import error: {exc}", "error")

    return rp("import", output=output)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    STAGING_DIR.mkdir(exist_ok=True)
    print("AstroDojo Review running at http://localhost:5112")
    print(f"Staging directory: {STAGING_DIR}/")
    app.run(host="127.0.0.1", port=5112, debug=True)
