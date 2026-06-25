#!/usr/bin/env python3
"""edit.py — review and edit exercises you've added locally before submitting a PR.

Only shows exercises that are new in your local copy (untracked, staged, or in
commits not yet pushed to the remote). Exercises already on the remote are hidden
so you can't accidentally modify someone else's work.

Usage:
    python edit.py
    # then open http://localhost:5050
"""

import shutil
import subprocess
from pathlib import Path

import yaml
from flask import Flask, flash, redirect, render_template_string, request, send_file, url_for

from build import (
    REQUIRED_FIELDS,
    TOPIC_DISPLAY,
    VALID_DIFICULTAD,
    VALID_ETAPA,
    VALID_TEMAS,
)

app = Flask(__name__)
app.secret_key = "astrodojo-edit-local-only"

BASE_DIR = Path(__file__).resolve().parent
EXERCISES_DIR = BASE_DIR / "exercises"
ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


# ---------------------------------------------------------------------------
# Git helpers — detect which exercises are locally new
# ---------------------------------------------------------------------------

def _git(*args, timeout=15):
    r = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=str(BASE_DIR), timeout=timeout,
    )
    return r.returncode, r.stdout, r.stderr


def get_local_exercise_ids():
    """Return the set of exercise folder-name IDs that are locally new."""
    ids = set()

    _, out, _ = _git("status", "--short", "-uall", "--", "exercises/")
    for line in out.splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip()
        path = line[3:].strip()
        if not (code.startswith("?") or code == "A" or code == "AM"):
            continue
        parts = Path(path).parts
        if len(parts) >= 4 and parts[0] == "exercises":
            ids.add(parts[3])

    for remote_ref in ("origin/main", "origin/master"):
        rc, out, _ = _git(
            "log", "--name-only", "--pretty=format:",
            f"{remote_ref}..HEAD", "--", "exercises/",
        )
        if rc != 0:
            continue
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = Path(line).parts
            if len(parts) >= 4 and parts[0] == "exercises":
                ids.add(parts[3])
        break

    return ids


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_local_exercises():
    local_ids = get_local_exercise_ids()
    exercises = []
    for meta_path in sorted(EXERCISES_DIR.rglob("meta.yaml")):
        eid = meta_path.parent.name
        if eid not in local_ids:
            continue
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        meta["_folder"] = str(meta_path.parent)
        meta["_id"] = eid
        meta["_rel"] = str(meta_path.parent.relative_to(EXERCISES_DIR))
        imgs = list(meta_path.parent.glob("imagen.*"))
        meta["_imagen"] = imgs[0].name if imgs else None
        exercises.append(meta)
    return exercises


def find_local_exercise(exercise_id):
    local_ids = get_local_exercise_ids()
    if exercise_id not in local_ids:
        return None
    for meta_path in EXERCISES_DIR.rglob("meta.yaml"):
        if meta_path.parent.name != exercise_id:
            continue
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        meta["_folder"] = str(meta_path.parent)
        meta["_id"] = exercise_id
        meta["_rel"] = str(meta_path.parent.relative_to(EXERCISES_DIR))
        imgs = list(meta_path.parent.glob("imagen.*"))
        meta["_imagen"] = imgs[0].name if imgs else None
        return meta
    return None


def validate_meta(meta):
    errors = []
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        errors.append(f"Faltan campos: {', '.join(sorted(missing))}")
    if meta.get("dificultad") and meta["dificultad"] not in VALID_DIFICULTAD:
        errors.append(f"Dificultad inválida: '{meta['dificultad']}'")
    if meta.get("etapa") and meta["etapa"] not in VALID_ETAPA:
        errors.append(f"Etapa inválida: '{meta['etapa']}'")
    if meta.get("tema") and meta["tema"] not in VALID_TEMAS:
        errors.append(f"Tema inválido: '{meta['tema']}'")
    if meta.get("subtemas") and not isinstance(meta["subtemas"], list):
        errors.append("subtemas debe ser una lista")
    if meta.get("anio") and not isinstance(meta["anio"], int):
        errors.append("anio debe ser un entero")
    if not meta.get("numero") or not isinstance(meta.get("numero"), int):
        errors.append("numero es requerido y debe ser un entero")
    return errors


def save_image(file_storage, dest_dir):
    if not file_storage or file_storage.filename == "":
        return
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMG_EXT:
        raise ValueError(f"Extensión '{ext}' no permitida. Usá: {ALLOWED_IMG_EXT}")
    for old in dest_dir.glob("imagen.*"):
        old.unlink()
    file_storage.save(str(dest_dir / f"imagen{ext}"))


def _filter_values(exercises):
    """Compute unique filter values from a list of exercises."""
    anios   = sorted({ex.get("anio")   for ex in exercises if ex.get("anio")},   reverse=True)
    temas   = sorted({ex.get("tema")   for ex in exercises if ex.get("tema")})
    etapas  = sorted({ex.get("etapa")  for ex in exercises if ex.get("etapa")})
    niveles = sorted({ex.get("nivel")  for ex in exercises if ex.get("nivel")})
    return anios, temas, etapas, niveles


# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------

_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
<style>
/* ── Edit bar ── */
.ed-bar {
  position: sticky; top: 0; z-index: 300;
  background: rgba(10,12,18,.97); backdrop-filter: blur(12px);
  border-bottom: 2px solid #bc8cff;
  display: flex; align-items: center; gap: .6rem;
  padding: .45rem 1.25rem; flex-wrap: wrap;
}
.ed-brand { font-weight: 700; color: #bc8cff; font-size: .92rem; margin-right: .25rem; }
.ed-divider { color: #30363d; font-size: 1.1rem; margin: 0 .1rem; }
.ed-tab {
  padding: .28rem .8rem; border-radius: 6px; font-size: .83rem; font-weight: 500;
  text-decoration: none; color: #8b949e; transition: background .12s, color .12s;
}
.ed-tab:hover { background: #21262d; color: #e6edf3; }
.ed-tab.active { background: rgba(188,140,255,.15); color: #bc8cff; }
.ed-bar .ed-link { color: #8b949e; font-size: .83rem; text-decoration: none; }
.ed-bar .ed-link:hover { color: #e6edf3; }
.ed-spacer { flex: 1; }
.ed-ibtn {
  padding: .3rem .85rem; border-radius: 6px; border: none; cursor: pointer;
  font-size: .82rem; font-weight: 600; font-family: inherit;
  text-decoration: none; display: inline-block;
}
.ed-ibtn-save { background: #238636; color: #fff; }
.ed-ibtn-save:hover { background: #2ea043; }
.ed-ibtn-del  { background: #b91c1c; color: #fff; }
.ed-ibtn-del:hover  { background: #dc2626; }
.ed-ibtn-bulk { background: #bc8cff; color: #000; }
.ed-ibtn-bulk:hover { background: #d6afff; }

/* ── Index cards ── */
.ed-card-wrap { position: relative; display: block; text-decoration: none; color: inherit; }
.ed-card-wrap .card { height: 100%; }
.ed-hover {
  position: absolute; inset: 0; border-radius: 8px;
  background: rgba(188,140,255,.15);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity .18s;
}
.ed-card-wrap:hover .ed-hover { opacity: 1; }
.ed-hover span {
  background: #bc8cff; color: #000; font-weight: 700; font-size: .9rem;
  padding: .4rem 1.1rem; border-radius: 6px;
}
.no-dif { background: #21262d; color: #8b949e; }

/* ── Empty state ── */
.ed-empty { text-align: center; padding: 4rem 1rem; color: #8b949e; }
.ed-empty h2 { color: #e6edf3; margin-bottom: .75rem; }
.ed-empty code { background: #21262d; padding: .15rem .4rem; border-radius: 4px;
                  color: #bc8cff; font-size: .9rem; }
.ed-empty ol { text-align: left; max-width: 480px; margin: 1.5rem auto 0;
               display: flex; flex-direction: column; gap: .6rem; }
.ed-empty ol li { color: #e6edf3; font-size: .92rem; }

/* ── Edit detail ── */
.ed-detail {
  display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 1.5rem;
  align-items: start;
}
@media (max-width: 780px) { .ed-detail { grid-template-columns: 1fr; } }
.ed-preview .exercise-image img { max-width: 100%; border-radius: 8px; display: block; }
.ed-preview .exercise-meta { display: flex; flex-wrap: wrap; gap: .4rem; margin: .75rem 0; }
.ed-panel {
  background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem;
  display: flex; flex-direction: column; gap: 1.1rem;
}
.ed-field label {
  display: block; font-size: .72rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .07em; color: #8b949e; margin-bottom: .35rem;
}
.ed-field input[type=text],
.ed-field input[type=url],
.ed-field input[type=number],
.ed-field select {
  width: 100%; background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; padding: .45rem .7rem; color: #e6edf3;
  font-size: .9rem; font-family: inherit;
}
.ed-field input:focus, .ed-field select:focus {
  outline: none; border-color: #bc8cff; box-shadow: 0 0 0 3px rgba(188,140,255,.15);
}
.ed-field input[type=file] { color: #8b949e; font-size: .85rem; }

/* Dificultad buttons */
.dif-group { display: flex; gap: .4rem; flex-wrap: wrap; }
.dif-lbl {
  padding: .3rem .9rem; border-radius: 6px; border: 2px solid #30363d;
  cursor: pointer; font-size: .85rem; font-weight: 500;
  background: #0d1117; color: #8b949e; transition: all .12s; user-select: none;
}
.dif-lbl:has(input:checked) { border-color: currentColor; }
.dif-lbl.d-facil:has(input:checked)  { color: #3fb950; background: rgba(63,185,80,.1);  border-color: #3fb950; }
.dif-lbl.d-inter:has(input:checked)  { color: #d29922; background: rgba(210,153,34,.1); border-color: #d29922; }
.dif-lbl.d-dific:has(input:checked)  { color: #f85149; background: rgba(248,81,73,.1);  border-color: #f85149; }
.dif-lbl.d-none:has(input:checked)   { color: #8b949e; background: #21262d; border-color: #8b949e; }
.dif-lbl:hover { border-color: #bc8cff; color: #bc8cff; }
.dif-lbl:has(input:checked):hover { border-color: currentColor; }

/* Subtema tags */
.tag-row { display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; }
.ed-tag {
  display: inline-flex; align-items: center; gap: .3rem;
  background: #21262d; border-radius: 4px; padding: .2rem .55rem;
  font-size: .8rem; color: #e6edf3;
}
.ed-tag button { background: none; border: none; color: #8b949e; cursor: pointer;
                  font-size: 1rem; line-height: 1; padding: 0; }
.ed-tag button:hover { color: #f85149; }
.ed-add-btn {
  background: none; border: 1px dashed #30363d; border-radius: 4px;
  padding: .2rem .6rem; font-size: .8rem; color: #8b949e; cursor: pointer; font-family: inherit;
}
.ed-add-btn:hover { border-color: #bc8cff; color: #bc8cff; }
#ed-new-tag {
  display: none; background: #0d1117; border: 1px solid #bc8cff; border-radius: 4px;
  padding: .2rem .5rem; color: #e6edf3; font-size: .82rem; font-family: inherit; width: 140px;
}

/* Collapsible advanced */
details.ed-adv { border: 1px solid #30363d; border-radius: 6px; padding: .1rem .9rem; }
details.ed-adv[open] { padding-bottom: .75rem; }
details.ed-adv summary {
  cursor: pointer; color: #8b949e; font-size: .82rem; padding: .5rem 0;
  list-style: none; user-select: none;
}
details.ed-adv summary::marker { display: none; }
details.ed-adv summary::before { content: '▶  '; font-size: .7rem; }
details.ed-adv[open] summary::before { content: '▼  '; }
.ed-adv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1.25rem; margin-top: .75rem; }

/* Flash */
.ed-flash { padding: .5rem 1rem; border-radius: 6px; font-size: .88rem; margin-bottom: .75rem; }
.ed-flash.success { background: rgba(63,185,80,.12); border: 1px solid #3fb950; color: #3fb950; }
.ed-flash.error   { background: rgba(248,81,73,.12); border: 1px solid #f85149; color: #f85149; }

/* Breadcrumb */
.ed-crumbs { font-size: .85rem; color: #8b949e; margin-bottom: .75rem; }
.ed-crumbs a { color: #8b949e; text-decoration: none; }
.ed-crumbs a:hover { color: #bc8cff; }
.ed-crumbs span { margin: 0 .35rem; }

/* PR guide box */
.pr-guide {
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 1.25rem 1.5rem; margin-top: 2.5rem;
}
.pr-guide h3 { color: #bc8cff; margin-bottom: .75rem; font-size: 1rem; }
.pr-guide ol { padding-left: 1.25rem; display: flex; flex-direction: column; gap: .5rem; }
.pr-guide li { color: #e6edf3; font-size: .9rem; }
.pr-guide code { background: #21262d; padding: .1rem .4rem; border-radius: 3px;
                  color: #bc8cff; font-size: .85rem; }
.pr-guide pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
                padding: .75rem 1rem; margin-top: .5rem; overflow-x: auto;
                font-size: .82rem; color: #3fb950; line-height: 1.6; }

/* ── Bulk edit ── */
.bulk-wrap { display: flex; flex-direction: column; gap: 1.5rem; }

.bulk-action-bar {
  background: #161b22; border: 1px solid #bc8cff; border-radius: 8px;
  padding: 1rem 1.25rem; display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end;
}
.bulk-action-bar .ba-field { display: flex; flex-direction: column; gap: .35rem; }
.bulk-action-bar label {
  font-size: .72rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .07em; color: #8b949e;
}
.bulk-action-bar select,
.bulk-action-bar input[type=text],
.bulk-action-bar input[type=url] {
  background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
  padding: .4rem .7rem; color: #e6edf3; font-size: .88rem; font-family: inherit; min-width: 220px;
}
.bulk-action-bar select:focus,
.bulk-action-bar input:focus {
  outline: none; border-color: #bc8cff; box-shadow: 0 0 0 3px rgba(188,140,255,.15);
}
.bulk-value-wrap { display: flex; flex-direction: column; gap: .35rem; }
.bulk-dif-group { display: flex; gap: .35rem; flex-wrap: wrap; margin-top: .1rem; }

.bulk-select-bar {
  display: flex; gap: .75rem; align-items: center; font-size: .85rem; color: #8b949e;
}
.bulk-select-bar a { color: #bc8cff; text-decoration: none; cursor: pointer; font-size: .83rem; }
.bulk-select-bar a:hover { text-decoration: underline; }
#bulk-count { font-weight: 600; color: #e6edf3; }

.bulk-table { width: 100%; border-collapse: collapse; font-size: .87rem; }
.bulk-table th {
  text-align: left; padding: .45rem .75rem; font-size: .7rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .07em; color: #8b949e;
  border-bottom: 2px solid #30363d; white-space: nowrap;
}
.bulk-table th:first-child { width: 36px; }
.bulk-table td { padding: .5rem .75rem; border-bottom: 1px solid #21262d; vertical-align: middle; }
.bulk-table tbody tr:hover td { background: #161b22; }
.bulk-table tbody tr.row-hidden { display: none; }
.bulk-table .col-id { font-family: monospace; font-size: .8rem; color: #bc8cff; }
.bulk-table .col-sol { font-size: .78rem; color: #8b949e; max-width: 200px;
                        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bulk-table .col-sol a { color: #58a6ff; text-decoration: none; }
.bulk-table .col-sol a:hover { text-decoration: underline; }
.bulk-no-results {
  text-align: center; color: #8b949e; padding: 2.5rem 1rem; font-size: .9rem;
}
input[type=checkbox] { accent-color: #bc8cff; width: 14px; height: 14px; cursor: pointer; }
</style>
"""

_HEAD = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page_title|default('Editar Ejercicios') }} — AstroDojo</title>
""" + _CSS + """
</head>
<body>"""

_FOOT = """</body></html>"""

# Shared tab bar snippet — rendered inside the ed-bar
_TABS = """
<span class="ed-divider">|</span>
<a href="{{ url_for('index') }}" class="ed-tab {{ 'active' if active_tab == 'index' }}">Mis Ejercicios</a>
<a href="{{ url_for('bulk') }}" class="ed-tab {{ 'active' if active_tab == 'bulk' }}">Edición Masiva</a>
"""

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

INDEX_TPL = _HEAD + """
<div class="ed-bar">
  <span class="ed-brand">✏&#xFE0F; Mis Ejercicios</span>
  """ + _TABS + """
</div>
<header><nav><a href="/" class="logo">AstroDojo</a></nav></header>
<main>
  <section class="topic-header">
    <h1>Mis Ejercicios Locales</h1>
    <p style="color:#8b949e;margin-top:.3rem;">
      {% if exercises %}
        {{ exercises|length }} ejercicio(s) nuevo(s) — solo los tuyos, listos para revisar antes del PR.
      {% else %}
        No se encontraron ejercicios locales nuevos.
      {% endif %}
    </p>
  </section>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="ed-flash {{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}

  {% if exercises %}

  <section class="filters">
    <div class="filter-group">
      <input type="text" id="search-input" class="search-input" placeholder="Buscar por ID, fuente, subtema…">
    </div>
    {% if anios|length > 1 %}
    <div class="filter-group">
      <h3>Año</h3>
      <div class="filter-buttons" id="anio-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for a in anios %}
        <button class="filter-btn" data-value="{{ a }}">{{ a }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    <div class="filter-group">
      <h3>Dificultad</h3>
      <div class="filter-buttons" id="diff-filters">
        <button class="filter-btn active" data-value="all">Todas</button>
        <button class="filter-btn" data-value="facil">Fácil</button>
        <button class="filter-btn" data-value="intermedio">Intermedio</button>
        <button class="filter-btn" data-value="dificil">Difícil</button>
        <button class="filter-btn" data-value="">Sin asignar</button>
      </div>
    </div>
    {% if temas|length > 1 %}
    <div class="filter-group">
      <h3>Tema</h3>
      <div class="filter-buttons" id="tema-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for t in temas %}
        <button class="filter-btn" data-value="{{ t }}">{{ topic_display.get(t, t) }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    {% if etapas|length > 1 %}
    <div class="filter-group">
      <h3>Etapa</h3>
      <div class="filter-buttons" id="etapa-filters">
        <button class="filter-btn active" data-value="all">Todas</button>
        {% for e in etapas %}
        <button class="filter-btn" data-value="{{ e }}">{{ e|title }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    {% if niveles|length > 1 %}
    <div class="filter-group">
      <h3>Nivel</h3>
      <div class="filter-buttons" id="nivel-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for n in niveles %}
        <button class="filter-btn" data-value="{{ n }}">{{ n }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
  </section>

  <div class="card-grid" id="exercise-grid">
    {% for ex in exercises %}
    <a href="{{ url_for('edit_detail', exercise_id=ex._id) }}"
       class="ed-card-wrap"
       data-anio="{{ ex.anio|default('') }}"
       data-dificultad="{{ ex.dificultad|default('') }}"
       data-tema="{{ ex.tema|default('') }}"
       data-etapa="{{ ex.etapa|default('') }}"
       data-nivel="{{ ex.nivel|default('') }}"
       data-subtemas="{{ ex.subtemas|default([])|join(',') }}"
       data-id="{{ ex._id }}"
       data-fuente="{{ ex.fuente|default('') }}">
      <div class="card exercise-card">
        {% if ex._imagen %}
        <div class="card-img-wrapper">
          <img src="{{ url_for('ex_image', path=ex._rel + '/' + ex._imagen) }}"
               alt="{{ ex._id }}" loading="lazy">
        </div>
        {% else %}
        <div class="placeholder-img">Sin imagen</div>
        {% endif %}
        <div class="card-body">
          {% if ex.dificultad %}
          <span class="badge badge-{{ ex.dificultad }}">{{ ex.dificultad|title }}</span>
          {% else %}
          <span class="badge no-dif">Sin dificultad</span>
          {% endif %}
          <span class="badge badge-etapa">{{ ex.etapa|default('')|title }}</span>
          <span class="badge badge-anio">{{ ex.anio|default('') }}</span>
          {% if ex.nivel is defined and ex.nivel %}
          <span class="badge" style="background:#21262d;color:#8b949e;">{{ ex.nivel }}</span>
          {% endif %}
          <div class="subtemas">
            {% for s in ex.subtemas|default([]) %}
            <span class="tag">{{ s|replace('-',' ')|title }}</span>
            {% endfor %}
          </div>
          <p class="fuente">{{ ex.fuente|default('') }}</p>
        </div>
        <div class="ed-hover"><span>Editar</span></div>
      </div>
    </a>
    {% endfor %}
  </div>

  <p id="no-results" class="hidden" style="text-align:center;color:#8b949e;padding:2rem;">
    No se encontraron ejercicios con esos filtros.
  </p>

  {% else %}
    <div class="ed-empty">
      <h2>No hay ejercicios locales nuevos</h2>
      <p>Todavía no agregaste ningún ejercicio que no esté en el repositorio remoto.</p>
      <ol>
        <li>Agregá ejercicios con el wizard (<code>contribute/index.html</code>)
            o con <code>python extract_exercises.py</code>.</li>
        <li>Si usaste el wizard, corré <code>python import_exercises.py</code>
            para mover los ejercicios a <code>exercises/</code>.</li>
        <li>Volvé a abrir esta página para revisarlos.</li>
      </ol>
    </div>
  {% endif %}

  <div class="pr-guide">
    <h3>¿Listo para enviar tu PR?</h3>
    <ol>
      <li>Revisá y editá tus ejercicios arriba (especialmente asigná la <strong>dificultad</strong>).</li>
      <li>Hacé commit de tus cambios:<br>
        <pre>git add exercises/
git commit -m "Add exercises: descripción breve"</pre>
      </li>
      <li>Subí tu rama y abrí un Pull Request en GitHub:<br>
        <pre>git push origin main
# Luego abrí un PR en https://github.com/Tomy-Niepo/AstroDojo</pre>
      </li>
    </ol>
  </div>
</main>
<script>
(function () {
  var active = { anio: 'all', dif: 'all', tema: 'all', etapa: 'all', nivel: 'all' };
  var search = '';
  var cards = document.querySelectorAll('.ed-card-wrap');
  var noResults = document.getElementById('no-results');

  function applyFilters() {
    var q = search.toLowerCase();
    var visible = 0;
    cards.forEach(function (c) {
      var ok =
        (active.anio  === 'all' || String(c.dataset.anio)  === active.anio) &&
        (active.dif   === 'all' || c.dataset.dificultad    === active.dif) &&
        (active.tema  === 'all' || c.dataset.tema          === active.tema) &&
        (active.etapa === 'all' || c.dataset.etapa         === active.etapa) &&
        (active.nivel === 'all' || c.dataset.nivel         === active.nivel) &&
        (!q ||
          c.dataset.id.toLowerCase().indexOf(q) !== -1 ||
          c.dataset.fuente.toLowerCase().indexOf(q) !== -1 ||
          c.dataset.subtemas.toLowerCase().indexOf(q) !== -1);
      c.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    if (noResults) noResults.classList.toggle('hidden', visible > 0);
  }

  function bindGroup(groupId, key) {
    var el = document.getElementById(groupId);
    if (!el) return;
    el.querySelectorAll('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        el.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        active[key] = btn.dataset.value;
        applyFilters();
      });
    });
  }

  bindGroup('anio-filters',  'anio');
  bindGroup('diff-filters',  'dif');
  bindGroup('tema-filters',  'tema');
  bindGroup('etapa-filters', 'etapa');
  bindGroup('nivel-filters', 'nivel');

  var si = document.getElementById('search-input');
  if (si) si.addEventListener('input', function () { search = si.value; applyFilters(); });
})();
</script>
""" + _FOOT


EDIT_TPL = _HEAD + """
<div class="ed-bar">
  <span class="ed-brand">✏&#xFE0F; Mis Ejercicios</span>
  """ + _TABS + """
  <span class="ed-spacer"></span>
  <button form="ed-form" type="submit" class="ed-ibtn ed-ibtn-save">Guardar cambios</button>
  <form method="post" action="{{ url_for('edit_delete', exercise_id=meta._id) }}"
        style="display:inline;"
        onsubmit="return confirm('¿Eliminar {{ meta._id }}? Esta acción no se puede deshacer.');">
    <button type="submit" class="ed-ibtn ed-ibtn-del">Eliminar</button>
  </form>
</div>
<header><nav><a href="{{ url_for('index') }}" class="logo">AstroDojo</a></nav></header>
<main>
  <div class="ed-crumbs">
    <a href="{{ url_for('index') }}">Mis Ejercicios</a>
    <span>/</span>
    <span>{{ topic_display.get(meta.tema, meta.tema) }}</span>
    <span>/</span>
    {{ meta._id }}
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="ed-flash {{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}

  <form id="ed-form" method="post" enctype="multipart/form-data">
    <div class="ed-detail">

      <!-- LEFT: preview -->
      <div class="ed-preview">
        <h2 style="font-size:1rem;color:#8b949e;margin-bottom:.75rem;">Vista previa</h2>
        {% if meta._imagen %}
        <div class="exercise-image">
          <img src="{{ url_for('ex_image', path=meta._rel + '/' + meta._imagen) }}"
               alt="{{ meta._id }}">
        </div>
        {% else %}
        <div class="placeholder-img exercise-placeholder">Sin imagen</div>
        {% endif %}
        <div class="exercise-meta" style="margin-top:.75rem;">
          {% if meta.dificultad %}
          <span class="badge badge-{{ meta.dificultad }}">{{ meta.dificultad|title }}</span>
          {% else %}
          <span class="badge no-dif">Sin dificultad</span>
          {% endif %}
          <span class="badge badge-etapa">{{ meta.etapa|default('')|title }}</span>
          <span class="badge badge-anio">{{ meta.anio|default('') }}</span>
          {% if meta.nivel is defined and meta.nivel %}
          <span class="badge" style="background:#21262d;color:#8b949e;">{{ meta.nivel }}</span>
          {% endif %}
          {% if meta.modalidad is defined and meta.modalidad %}
          <span class="badge" style="background:#21262d;color:#8b949e;">{{ meta.modalidad }}</span>
          {% endif %}
          <div class="subtemas" style="margin-top:.4rem;width:100%;">
            {% for s in meta.subtemas|default([]) %}
            <span class="tag">{{ s|replace('-',' ')|title }}</span>
            {% endfor %}
          </div>
        </div>
        <p class="fuente" style="color:#8b949e;font-size:.85rem;margin-top:.5rem;">
          {{ meta.fuente|default('') }}
        </p>
        {% if meta.solucion %}
        <div style="margin-top:.75rem;">
          <a href="{{ meta.solucion }}" target="_blank" class="btn-solution">Ver solución</a>
        </div>
        {% endif %}
      </div>

      <!-- RIGHT: edit panel -->
      <div class="ed-panel">
        <h2 style="font-size:1rem;color:#8b949e;margin-top:0;">Editar</h2>

        <!-- Dificultad -->
        <div class="ed-field">
          <label>Dificultad</label>
          <div class="dif-group">
            <label class="dif-lbl d-facil">
              <input type="radio" name="dificultad" value="facil" hidden
                {{ 'checked' if meta.dificultad == 'facil' }}>Fácil
            </label>
            <label class="dif-lbl d-inter">
              <input type="radio" name="dificultad" value="intermedio" hidden
                {{ 'checked' if meta.dificultad == 'intermedio' }}>Intermedio
            </label>
            <label class="dif-lbl d-dific">
              <input type="radio" name="dificultad" value="dificil" hidden
                {{ 'checked' if meta.dificultad == 'dificil' }}>Difícil
            </label>
            <label class="dif-lbl d-none">
              <input type="radio" name="dificultad" value="" hidden
                {{ 'checked' if not meta.dificultad }}>Sin asignar
            </label>
          </div>
        </div>

        <!-- Subtemas -->
        <div class="ed-field">
          <label>Subtemas</label>
          <div class="tag-row" id="tag-row">
            {% for s in meta.subtemas|default([]) %}
            <span class="ed-tag">
              {{ s }}
              <button type="button" onclick="removeTag(this)">×</button>
              <input type="hidden" name="subtemas_list" value="{{ s }}">
            </span>
            {% endfor %}
            <button type="button" class="ed-add-btn" id="ed-add-btn" onclick="showTagInput()">+ Agregar</button>
            <input type="text" id="ed-new-tag" placeholder="nuevo subtema…"
                   onkeydown="commitTag(event)" onblur="commitTagBlur()">
          </div>
        </div>

        <!-- Fuente -->
        <div class="ed-field">
          <label>Fuente</label>
          <input type="text" name="fuente" value="{{ meta.fuente|default('') }}" required
                 placeholder="e.g. Olimpiada Argentina de Astronomía 2024, Nacional">
        </div>

        <!-- Solución -->
        <div class="ed-field">
          <label>Solución URL <span style="font-weight:400;text-transform:none;">(opcional)</span></label>
          <input type="url" name="solucion" value="{{ meta.solucion|default('') }}"
                 placeholder="https://…">
        </div>

        <!-- Imagen -->
        <div class="ed-field">
          <label>Imagen{% if meta._imagen %} — actual: <code style="font-size:.8rem;color:#bc8cff;">{{ meta._imagen }}</code>{% endif %}</label>
          <input type="file" name="imagen" accept="image/*">
        </div>

        <!-- Advanced -->
        <details class="ed-adv">
          <summary>Campos avanzados (tema, año, etapa, modalidad…)</summary>
          <div class="ed-adv-grid">
            <div class="ed-field">
              <label>Tema</label>
              <select name="tema">
                {% for t in valid_temas|sort %}
                <option value="{{ t }}" {{ 'selected' if t == meta.tema }}>{{ topic_display.get(t,t) }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="ed-field">
              <label>Institución</label>
              <input type="text" name="institucion" value="{{ meta.institucion|default('') }}" required>
            </div>
            <div class="ed-field">
              <label>Año</label>
              <input type="number" name="anio" value="{{ meta.anio|default('') }}" required min="2000" max="2100">
            </div>
            <div class="ed-field">
              <label>Número de ejercicio</label>
              <input type="number" name="numero" value="{{ meta.numero|default('') }}" required min="1" max="99">
            </div>
            <div class="ed-field">
              <label>Etapa</label>
              <select name="etapa">
                {% for e in valid_etapa|sort %}
                <option value="{{ e }}" {{ 'selected' if e == meta.etapa }}>{{ e|title }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="ed-field">
              <label>Modalidad</label>
              <select name="modalidad">
                <option value="">—</option>
                <option value="individual" {{ 'selected' if meta.modalidad|default('') == 'individual' }}>Individual</option>
                <option value="grupal"     {{ 'selected' if meta.modalidad|default('') == 'grupal' }}>Grupal</option>
              </select>
            </div>
            <div class="ed-field" style="grid-column:1/-1;">
              <label>Nivel</label>
              <select name="nivel">
                <option value="">—</option>
                {% for n in ['N1','N2','N3','N4'] %}
                <option value="{{ n }}" {{ 'selected' if meta.nivel|default('') == n }}>{{ n }}</option>
                {% endfor %}
              </select>
            </div>
          </div>
        </details>

      </div>
    </div>
  </form>
</main>
<script>
function removeTag(btn) { btn.closest('.ed-tag').remove(); }
function showTagInput() {
  document.getElementById('ed-add-btn').style.display = 'none';
  var inp = document.getElementById('ed-new-tag');
  inp.style.display = 'inline-block';
  inp.focus();
}
function addTag(val) {
  val = val.trim().toLowerCase();
  if (!val) return;
  var row = document.getElementById('tag-row');
  var btn = document.getElementById('ed-add-btn');
  var span = document.createElement('span');
  span.className = 'ed-tag';
  span.innerHTML = val + ' <button type="button" onclick="removeTag(this)">x</button>'
    + '<input type="hidden" name="subtemas_list" value="' + val.replace(/"/g, '&quot;') + '">';
  row.insertBefore(span, btn);
}
function commitTag(e) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    var inp = document.getElementById('ed-new-tag');
    addTag(inp.value); inp.value = '';
  } else if (e.key === 'Escape') { resetTagInput(); }
}
function commitTagBlur() {
  var inp = document.getElementById('ed-new-tag');
  if (inp.value.trim()) addTag(inp.value);
  resetTagInput();
}
function resetTagInput() {
  var inp = document.getElementById('ed-new-tag');
  inp.value = ''; inp.style.display = 'none';
  document.getElementById('ed-add-btn').style.display = 'inline-block';
}
</script>
""" + _FOOT


BULK_TPL = _HEAD + """
<div class="ed-bar">
  <span class="ed-brand">✏&#xFE0F; Mis Ejercicios</span>
  """ + _TABS + """
  <span class="ed-spacer"></span>
  <button type="button" class="ed-ibtn ed-ibtn-bulk" onclick="submitBulk()">Aplicar a seleccionados</button>
</div>
<header><nav><a href="{{ url_for('index') }}" class="logo">AstroDojo</a></nav></header>
<main>
  <section class="topic-header">
    <h1>Edición Masiva</h1>
    <p style="color:#8b949e;margin-top:.3rem;">
      Filtrá, seleccioná ejercicios y aplicá un cambio a todos a la vez.
    </p>
  </section>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="ed-flash {{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}

  {% if exercises %}

  <!-- Filters -->
  <section class="filters">
    <div class="filter-group">
      <input type="text" id="bulk-search" class="search-input" placeholder="Buscar por ID, fuente, subtema…">
    </div>
    {% if anios|length > 1 %}
    <div class="filter-group">
      <h3>Año</h3>
      <div class="filter-buttons" id="b-anio-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for a in anios %}
        <button class="filter-btn" data-value="{{ a }}">{{ a }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    <div class="filter-group">
      <h3>Dificultad</h3>
      <div class="filter-buttons" id="b-diff-filters">
        <button class="filter-btn active" data-value="all">Todas</button>
        <button class="filter-btn" data-value="facil">Fácil</button>
        <button class="filter-btn" data-value="intermedio">Intermedio</button>
        <button class="filter-btn" data-value="dificil">Difícil</button>
        <button class="filter-btn" data-value="">Sin asignar</button>
      </div>
    </div>
    {% if temas|length > 1 %}
    <div class="filter-group">
      <h3>Tema</h3>
      <div class="filter-buttons" id="b-tema-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for t in temas %}
        <button class="filter-btn" data-value="{{ t }}">{{ topic_display.get(t, t) }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    {% if etapas|length > 1 %}
    <div class="filter-group">
      <h3>Etapa</h3>
      <div class="filter-buttons" id="b-etapa-filters">
        <button class="filter-btn active" data-value="all">Todas</button>
        {% for e in etapas %}
        <button class="filter-btn" data-value="{{ e }}">{{ e|title }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    {% if niveles|length > 1 %}
    <div class="filter-group">
      <h3>Nivel</h3>
      <div class="filter-buttons" id="b-nivel-filters">
        <button class="filter-btn active" data-value="all">Todos</button>
        {% for n in niveles %}
        <button class="filter-btn" data-value="{{ n }}">{{ n }}</button>
        {% endfor %}
      </div>
    </div>
    {% endif %}
  </section>

  <div class="bulk-wrap">

    <!-- Bulk action bar -->
    <div class="bulk-action-bar">
      <div class="ba-field">
        <label>Campo a editar</label>
        <select id="bulk-field" onchange="onFieldChange()">
          <option value="solucion">URL Solución</option>
          <option value="dificultad">Dificultad</option>
          <option value="fuente">Fuente</option>
          <option value="subtemas_add">Agregar subtemas (a los existentes)</option>
          <option value="subtemas_replace">Reemplazar subtemas</option>
          <option value="nivel">Nivel</option>
          <option value="modalidad">Modalidad</option>
        </select>
      </div>

      <div class="ba-field bulk-value-wrap" id="value-wrap">
        <label id="value-label">Valor</label>
        <!-- URL / text input (shown for most fields) -->
        <input type="url"  id="bulk-val-url"  placeholder="https://…" style="display:none;">
        <input type="text" id="bulk-val-text" placeholder="valor…">
        <!-- Dificultad button group (shown for dificultad) -->
        <div class="bulk-dif-group" id="bulk-dif-group" style="display:none;">
          <label class="dif-lbl d-facil">
            <input type="radio" name="bulk-dif-radio" value="facil" hidden>Fácil
          </label>
          <label class="dif-lbl d-inter">
            <input type="radio" name="bulk-dif-radio" value="intermedio" hidden>Intermedio
          </label>
          <label class="dif-lbl d-dific">
            <input type="radio" name="bulk-dif-radio" value="dificil" hidden>Difícil
          </label>
          <label class="dif-lbl d-none">
            <input type="radio" name="bulk-dif-radio" value="" hidden>Sin asignar
          </label>
        </div>
        <!-- Nivel select (shown for nivel) -->
        <select id="bulk-val-nivel" style="display:none;">
          <option value="">—</option>
          <option value="N1">N1</option>
          <option value="N2">N2</option>
          <option value="N3">N3</option>
          <option value="N4">N4</option>
        </select>
        <!-- Modalidad select -->
        <select id="bulk-val-modalidad" style="display:none;">
          <option value="">—</option>
          <option value="individual">Individual</option>
          <option value="grupal">Grupal</option>
        </select>
      </div>
    </div>

    <!-- Selection bar -->
    <div class="bulk-select-bar">
      <input type="checkbox" id="select-all" onchange="toggleAll(this.checked)">
      <label for="select-all" style="cursor:pointer;color:#e6edf3;">Seleccionar todos los visibles</label>
      <span style="color:#30363d;">|</span>
      <span><span id="bulk-count">0</span> seleccionados</span>
      <a onclick="clearAll()">Limpiar selección</a>
    </div>

    <!-- Exercise table -->
    <form id="bulk-form" method="post" action="{{ url_for('bulk') }}">
      <input type="hidden" name="field" id="field-hidden">
      <input type="hidden" name="value" id="value-hidden">
      <table class="bulk-table">
        <thead>
          <tr>
            <th></th>
            <th>ID</th>
            <th>Año</th>
            <th>Tema</th>
            <th>Dif.</th>
            <th>Etapa</th>
            <th>Nivel</th>
            <th>Subtemas</th>
            <th>Solución</th>
          </tr>
        </thead>
        <tbody id="bulk-tbody">
          {% for ex in exercises %}
          <tr data-anio="{{ ex.anio|default('') }}"
              data-dificultad="{{ ex.dificultad|default('') }}"
              data-tema="{{ ex.tema|default('') }}"
              data-etapa="{{ ex.etapa|default('') }}"
              data-nivel="{{ ex.nivel|default('') }}"
              data-subtemas="{{ ex.subtemas|default([])|join(',') }}"
              data-id="{{ ex._id }}"
              data-fuente="{{ ex.fuente|default('') }}">
            <td><input type="checkbox" name="ids" value="{{ ex._id }}" onchange="updateCount()"></td>
            <td class="col-id">
              <a href="{{ url_for('edit_detail', exercise_id=ex._id) }}"
                 style="color:#bc8cff;text-decoration:none;" title="Editar individualmente">{{ ex._id }}</a>
            </td>
            <td>{{ ex.anio|default('') }}</td>
            <td style="font-size:.82rem;">{{ topic_display.get(ex.tema, ex.tema|default('')) }}</td>
            <td>
              {% if ex.dificultad == 'facil' %}
              <span style="color:#3fb950;font-size:.8rem;font-weight:600;">Fácil</span>
              {% elif ex.dificultad == 'intermedio' %}
              <span style="color:#d29922;font-size:.8rem;font-weight:600;">Medio</span>
              {% elif ex.dificultad == 'dificil' %}
              <span style="color:#f85149;font-size:.8rem;font-weight:600;">Difícil</span>
              {% else %}
              <span style="color:#484f58;font-size:.8rem;">—</span>
              {% endif %}
            </td>
            <td style="font-size:.82rem;">{{ ex.etapa|default('')|title }}</td>
            <td style="font-size:.82rem;color:#8b949e;">{{ ex.nivel|default('') }}</td>
            <td style="font-size:.78rem;color:#8b949e;">
              {{ ex.subtemas|default([])|join(', ') or '—' }}
            </td>
            <td class="col-sol">
              {% if ex.solucion %}
              <a href="{{ ex.solucion }}" target="_blank" title="{{ ex.solucion }}">✓ Ver</a>
              {% else %}
              <span style="color:#484f58;">—</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <div id="bulk-no-results" class="bulk-no-results" style="display:none;">
        No hay ejercicios que coincidan con los filtros.
      </div>
    </form>

  </div>

  {% else %}
    <div class="ed-empty">
      <h2>No hay ejercicios locales nuevos</h2>
      <p>Agregá ejercicios primero y luego volvé a esta página.</p>
    </div>
  {% endif %}
</main>
<script>
// ── Filter state ──
var bActive = { anio: 'all', dif: 'all', tema: 'all', etapa: 'all', nivel: 'all' };
var bSearch = '';
var rows = document.querySelectorAll('#bulk-tbody tr');
var noRes = document.getElementById('bulk-no-results');

function applyBulkFilters() {
  var q = bSearch.toLowerCase();
  var visible = 0;
  rows.forEach(function (r) {
    var ok =
      (bActive.anio  === 'all' || String(r.dataset.anio)  === bActive.anio) &&
      (bActive.dif   === 'all' || r.dataset.dificultad    === bActive.dif) &&
      (bActive.tema  === 'all' || r.dataset.tema          === bActive.tema) &&
      (bActive.etapa === 'all' || r.dataset.etapa         === bActive.etapa) &&
      (bActive.nivel === 'all' || r.dataset.nivel         === bActive.nivel) &&
      (!q ||
        r.dataset.id.toLowerCase().indexOf(q) !== -1 ||
        r.dataset.fuente.toLowerCase().indexOf(q) !== -1 ||
        r.dataset.subtemas.toLowerCase().indexOf(q) !== -1);
    r.classList.toggle('row-hidden', !ok);
    if (ok) visible++;
  });
  noRes.style.display = visible === 0 ? '' : 'none';
  // uncheck hidden rows
  document.querySelectorAll('#bulk-tbody tr.row-hidden input[type=checkbox]').forEach(function (cb) {
    cb.checked = false;
  });
  updateCount();
  document.getElementById('select-all').checked = false;
}

function bindBulkGroup(groupId, key) {
  var el = document.getElementById(groupId);
  if (!el) return;
  el.querySelectorAll('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      el.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      bActive[key] = btn.dataset.value;
      applyBulkFilters();
    });
  });
}
bindBulkGroup('b-anio-filters',  'anio');
bindBulkGroup('b-diff-filters',  'dif');
bindBulkGroup('b-tema-filters',  'tema');
bindBulkGroup('b-etapa-filters', 'etapa');
bindBulkGroup('b-nivel-filters', 'nivel');

var bs = document.getElementById('bulk-search');
if (bs) bs.addEventListener('input', function () { bSearch = bs.value; applyBulkFilters(); });

// ── Select / count ──
function visibleRows() {
  return Array.from(rows).filter(function (r) { return !r.classList.contains('row-hidden'); });
}
function updateCount() {
  var n = document.querySelectorAll('#bulk-tbody input[type=checkbox]:checked').length;
  document.getElementById('bulk-count').textContent = n;
}
function toggleAll(checked) {
  visibleRows().forEach(function (r) {
    r.querySelector('input[type=checkbox]').checked = checked;
  });
  updateCount();
}
function clearAll() {
  document.querySelectorAll('#bulk-tbody input[type=checkbox]').forEach(function (cb) { cb.checked = false; });
  document.getElementById('select-all').checked = false;
  updateCount();
}

// ── Field switching ──
function onFieldChange() {
  var field = document.getElementById('bulk-field').value;
  var labels = {
    'solucion':         'URL de Solución',
    'dificultad':       'Dificultad',
    'fuente':           'Fuente',
    'subtemas_add':     'Subtemas a agregar (separados por coma)',
    'subtemas_replace': 'Nuevos subtemas (separados por coma)',
    'nivel':            'Nivel',
    'modalidad':        'Modalidad',
  };
  document.getElementById('value-label').textContent = labels[field] || 'Valor';

  var urlInp    = document.getElementById('bulk-val-url');
  var textInp   = document.getElementById('bulk-val-text');
  var difGroup  = document.getElementById('bulk-dif-group');
  var nivelSel  = document.getElementById('bulk-val-nivel');
  var modalSel  = document.getElementById('bulk-val-modalidad');

  urlInp.style.display   = 'none';
  textInp.style.display  = 'none';
  difGroup.style.display = 'none';
  nivelSel.style.display = 'none';
  modalSel.style.display = 'none';

  if (field === 'solucion') {
    urlInp.style.display = '';
  } else if (field === 'dificultad') {
    difGroup.style.display = '';
  } else if (field === 'nivel') {
    nivelSel.style.display = '';
  } else if (field === 'modalidad') {
    modalSel.style.display = '';
  } else {
    textInp.style.display = '';
  }
}
onFieldChange(); // init

// ── Submit ──
function getBulkValue() {
  var field = document.getElementById('bulk-field').value;
  if (field === 'solucion') return document.getElementById('bulk-val-url').value.trim();
  if (field === 'dificultad') {
    var r = document.querySelector('input[name="bulk-dif-radio"]:checked');
    return r ? r.value : '';
  }
  if (field === 'nivel')    return document.getElementById('bulk-val-nivel').value;
  if (field === 'modalidad') return document.getElementById('bulk-val-modalidad').value;
  return document.getElementById('bulk-val-text').value.trim();
}

function submitBulk() {
  var checked = document.querySelectorAll('#bulk-tbody input[type=checkbox]:checked');
  if (checked.length === 0) {
    alert('Seleccioná al menos un ejercicio.');
    return;
  }
  var field = document.getElementById('bulk-field').value;
  var value = getBulkValue();
  if (!value && field !== 'dificultad' && field !== 'nivel' && field !== 'modalidad') {
    if (!confirm('El valor está vacío. ¿Continuar de todas formas?')) return;
  }
  document.getElementById('field-hidden').value = field;
  document.getElementById('value-hidden').value  = value;
  document.getElementById('bulk-form').submit();
}
</script>
""" + _FOOT


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    exercises = load_local_exercises()
    anios, temas, etapas, niveles = _filter_values(exercises)
    return render_template_string(
        INDEX_TPL,
        exercises=exercises,
        page_title="Mis Ejercicios",
        topic_display=TOPIC_DISPLAY,
        active_tab="index",
        anios=anios, temas=temas, etapas=etapas, niveles=niveles,
    )


@app.route("/edit/<exercise_id>", methods=["GET", "POST"])
def edit_detail(exercise_id):
    meta = find_local_exercise(exercise_id)
    if not meta:
        flash(f"'{exercise_id}' no encontrado o no es un ejercicio tuyo.", "error")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template_string(
            EDIT_TPL, meta=meta,
            page_title=meta["_id"],
            topic_display=TOPIC_DISPLAY,
            valid_temas=VALID_TEMAS,
            valid_etapa=VALID_ETAPA,
            active_tab="index",
        )

    # POST — save
    inst = request.form.get("institucion", meta.get("institucion", "")).strip()
    if not inst:
        flash("Institución es requerida.", "error")
        return redirect(url_for("edit_detail", exercise_id=exercise_id))

    new_tema = request.form.get("tema", "").strip()
    subtemas = [s.strip().lower() for s in request.form.getlist("subtemas_list") if s.strip()]

    try:
        anio = int(request.form.get("anio", 0))
    except ValueError:
        flash("Año debe ser un entero.", "error")
        return redirect(url_for("edit_detail", exercise_id=exercise_id))

    try:
        numero = int(request.form.get("numero", 0))
    except ValueError:
        flash("Número debe ser un entero.", "error")
        return redirect(url_for("edit_detail", exercise_id=exercise_id))

    updated = {
        "institucion": inst,
        "tema": new_tema,
        "subtemas": subtemas,
        "anio": anio,
        "etapa": request.form.get("etapa", "").strip(),
        "numero": numero,
        "fuente": request.form.get("fuente", "").strip(),
    }
    dif = request.form.get("dificultad", "").strip()
    if dif:
        updated["dificultad"] = dif

    modalidad = request.form.get("modalidad", "").strip()
    if modalidad:
        updated["modalidad"] = modalidad

    nivel = request.form.get("nivel", "").strip()
    if nivel:
        updated["nivel"] = nivel

    sol = request.form.get("solucion", "").strip()
    if sol:
        updated["solucion"] = sol

    errors = validate_meta(updated)
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("edit_detail", exercise_id=exercise_id))

    old_folder = Path(meta["_folder"])
    new_folder = EXERCISES_DIR / inst / new_tema / exercise_id

    if str(new_folder) != str(old_folder):
        new_folder.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_folder), str(new_folder))
        try:
            old_folder.parent.rmdir()
        except OSError:
            pass
    else:
        new_folder = old_folder

    with open(new_folder / "meta.yaml", "w", encoding="utf-8") as f:
        yaml.dump(updated, f, allow_unicode=True, default_flow_style=False)

    try:
        save_image(request.files.get("imagen"), new_folder)
    except ValueError as ve:
        flash(str(ve), "error")

    flash(f"Guardado: {exercise_id}.", "success")
    return redirect(url_for("edit_detail", exercise_id=exercise_id))


@app.route("/edit/<exercise_id>/delete", methods=["POST"])
def edit_delete(exercise_id):
    meta = find_local_exercise(exercise_id)
    if not meta:
        flash(f"'{exercise_id}' no encontrado o no es un ejercicio tuyo.", "error")
        return redirect(url_for("index"))
    folder = Path(meta["_folder"])
    shutil.rmtree(folder)
    try:
        folder.parent.rmdir()
    except OSError:
        pass
    flash(f"Eliminado: {exercise_id}.", "success")
    return redirect(url_for("index"))


@app.route("/bulk", methods=["GET", "POST"])
def bulk():
    exercises = load_local_exercises()
    anios, temas, etapas, niveles = _filter_values(exercises)
    ctx = dict(
        exercises=exercises,
        page_title="Edición Masiva",
        topic_display=TOPIC_DISPLAY,
        active_tab="bulk",
        anios=anios, temas=temas, etapas=etapas, niveles=niveles,
    )

    if request.method == "GET":
        return render_template_string(BULK_TPL, **ctx)

    # POST — apply bulk edit
    ids   = request.form.getlist("ids")
    field = request.form.get("field", "").strip()
    value = request.form.get("value", "").strip()

    if not ids:
        flash("No se seleccionó ningún ejercicio.", "error")
        return render_template_string(BULK_TPL, **ctx)
    if not field:
        flash("Campo inválido.", "error")
        return render_template_string(BULK_TPL, **ctx)

    local_ids = get_local_exercise_ids()
    updated_count = 0
    skipped = []

    for eid in ids:
        if eid not in local_ids:
            skipped.append(eid)
            continue
        meta = find_local_exercise(eid)
        if not meta:
            skipped.append(eid)
            continue

        # Build updated meta (preserve all existing keys, mutate only the target field)
        folder = Path(meta["_folder"])
        current = {k: v for k, v in meta.items() if not k.startswith("_")}

        if field == "solucion":
            if value:
                current["solucion"] = value
            else:
                current.pop("solucion", None)

        elif field == "dificultad":
            if value:
                current["dificultad"] = value
            else:
                current.pop("dificultad", None)

        elif field == "fuente":
            current["fuente"] = value

        elif field == "subtemas_add":
            new_tags = [t.strip().lower() for t in value.split(",") if t.strip()]
            existing = current.get("subtemas") or []
            merged = list(existing)
            for t in new_tags:
                if t not in merged:
                    merged.append(t)
            current["subtemas"] = merged

        elif field == "subtemas_replace":
            current["subtemas"] = [t.strip().lower() for t in value.split(",") if t.strip()]

        elif field == "nivel":
            if value:
                current["nivel"] = value
            else:
                current.pop("nivel", None)

        elif field == "modalidad":
            if value:
                current["modalidad"] = value
            else:
                current.pop("modalidad", None)

        else:
            skipped.append(eid)
            continue

        with open(folder / "meta.yaml", "w", encoding="utf-8") as f:
            yaml.dump(current, f, allow_unicode=True, default_flow_style=False)
        updated_count += 1

    if updated_count:
        flash(f"Actualizado {updated_count} ejercicio(s).", "success")
    if skipped:
        flash(f"Omitidos (no locales o no encontrados): {', '.join(skipped)}", "error")

    # Reload exercises after edit
    exercises = load_local_exercises()
    anios, temas, etapas, niveles = _filter_values(exercises)
    ctx.update(exercises=exercises, anios=anios, temas=temas, etapas=etapas, niveles=niveles)
    return render_template_string(BULK_TPL, **ctx)


@app.route("/exercises-img/<path:path>")
def ex_image(path):
    return send_file(EXERCISES_DIR / path)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("AstroDojo Edit running at http://localhost:5050")
    print("Showing only exercises that are new in your local copy.")
    app.run(host="127.0.0.1", port=5050, debug=True)
