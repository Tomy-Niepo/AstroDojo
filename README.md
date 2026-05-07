# AstroDojo

Sitio estático para estudiar problemas de olimpiadas de astronomía, organizados por tema y dificultad.

**Sitio**: [tomy-niepo.github.io/AstroDojo](https://tomy-niepo.github.io/AstroDojo/)

---

## Estructura del repositorio

```
exercises/
  <institucion>/
    <tema>/
      <id>/
        meta.yaml
        imagen.png      (o .jpg, .jpeg, .webp, .svg)
formulas/               # hojas de fórmulas por tema (una imagen por tema)
contribute/             # wizard web para armar ejercicios
templates/              # plantillas Jinja2 del sitio
static/                 # CSS y JS
build.py                # generador del sitio estático
site/                   # salida generada (gitignored)
```

---

## Formato de un ejercicio

Cada ejercicio es una carpeta con exactamente dos archivos:

```
exercises/<institucion>/<tema>/<id>/
  meta.yaml
  imagen.<ext>
```

### `meta.yaml`

```yaml
institucion: olimpiada-argentina         # slug de la institución (kebab-case)
tema: mecanica-celeste                   # uno de los 9 temas válidos (ver abajo)
subtemas: [cinematica, energia]          # lista de subtemas (puede ser vacía: [])
dificultad: intermedio                   # (opcional) facil | intermedio | dificil
anio: 2025                               # año (entero)
etapa: nacional                          # provincial | nacional | internacional
fuente: "Olimpiada Argentina de Astronomía 2025, Nacional"
solucion: "https://ejemplo.com/sol.pdf"  # (opcional) URL a la solución
```

### Temas válidos

| Slug | Nombre |
|------|--------|
| `coordenadas-celestes` | Coordenadas Celestes y Tiempo |
| `mecanica-celeste` | Mecánica Celeste |
| `optica` | Óptica |
| `instrumentos` | Instrumentos |
| `astrofisica` | Astrofísica |
| `cosmologia` | Cosmología |
| `magnitudes` | Magnitudes |
| `radiacion` | Radiación |
| `galaxias` | Galaxias |

### Convención de ID

El ID es el nombre de la carpeta. Formato sugerido: `<anio>-<etapa>-ej<numero>`, por ejemplo `2025-nacional-ej03`. No es estricto, pero debe ser único dentro de su tema.

### Imagen

Un archivo llamado `imagen.<ext>` donde `<ext>` es `png`, `jpg`, `jpeg`, `webp` o `svg`. Es la captura/foto del enunciado del problema.

---

## Contribuir via Pull Request

Un PR debe **agregar una carpeta** (o varias) dentro de `exercises/`. Nada más. Esto minimiza conflictos entre contribuidores que trabajan en distintas instituciones o temas.

### Pasos

1. Forkeá el repositorio.
2. Creá la carpeta del ejercicio con la estructura de arriba.
3. Commiteá solo la carpeta nueva:
   ```bash
   git add exercises/<institucion>/<tema>/<id>/
   git commit -m "Add <id> (<tema>)"
   git push
   ```
4. Abrí un Pull Request. El CI valida automáticamente que los `meta.yaml` sean correctos.

### Institución nueva

Si tu institución no existe todavía, simplemente creá la carpeta. Por ejemplo, para agregar un ejercicio de la Olimpiada Brasileña:

```
exercises/olimpiada-brasilena/optica/2025-nacional-ej01/
  meta.yaml
  imagen.png
```

No hace falta configurar nada extra — el build detecta instituciones automáticamente.

### Ejemplo mínimo de PR

```
exercises/olimpiada-argentina/astrofisica/2024-provincial-ej02/
  meta.yaml
  imagen.png
```

Donde `meta.yaml` contiene:
```yaml
institucion: olimpiada-argentina
tema: astrofisica
subtemas: [luminosidad, magnitudes]
anio: 2024
etapa: provincial
fuente: "Olimpiada Argentina de Astronomía 2024, Provincial"
```

---

## Agregar ejercicios con un LLM / agente

El formato está diseñado para que un LLM pueda procesar PDFs de exámenes y generar las carpetas de ejercicios automáticamente. El flujo típico es:

1. Darle al LLM el PDF de un examen.
2. Indicarle qué ejercicios extraer (o todos).
3. El LLM toma un screenshot de cada ejercicio, clasifica el tema y subtemas, y genera la carpeta completa.

**Importante**: el LLM **no** asigna dificultad — eso lo hace un humano después. El campo `dificultad` es opcional.

### Prompt de referencia

```
Tengo el PDF adjunto de un examen de olimpiada de astronomía.
Necesito que generes las carpetas de ejercicios para el repositorio AstroDojo.

Para cada ejercicio del PDF:
1. Tomá un screenshot del enunciado y guardalo como imagen.png
2. Determiná el tema (uno de: coordenadas-celestes, mecanica-celeste, optica,
   instrumentos, astrofisica, cosmologia, magnitudes, radiacion, galaxias)
3. Listá los subtemas relevantes
4. Generá el meta.yaml (NO incluyas dificultad, eso se asigna después)
5. Creá la carpeta completa

Formato del meta.yaml:
  institucion: <slug-kebab-case>
  tema: <tema>
  subtemas: [<subtema1>, <subtema2>]
  anio: <año>
  etapa: <provincial|nacional|internacional>
  fuente: "<Nombre de la olimpiada año, Etapa>"
  solucion: "<url>"  # opcional

Estructura de carpetas:
  exercises/<institucion>/<tema>/<anio>-<etapa>-ej<numero>/
    meta.yaml
    imagen.png

Deducí la institución del contenido del PDF (nombre de la olimpiada, país, etc.)
y convertila a un slug kebab-case (ej: "olimpiada-argentina",
"olimpiada-latinoamericana", "ioaa").
```

### Ejemplo: procesar un PDF completo

Con un PDF de 5 ejercicios de la Olimpiada Argentina 2025 Nacional, el LLM debería generar:

```
exercises/olimpiada-argentina/mecanica-celeste/2025-nacional-ej01/
  meta.yaml
  imagen.png
exercises/olimpiada-argentina/optica/2025-nacional-ej02/
  meta.yaml
  imagen.png
exercises/olimpiada-argentina/astrofisica/2025-nacional-ej03/
  meta.yaml
  imagen.png
...
```

### Script de ayuda para agregar en masa

```python
import yaml
from pathlib import Path
import shutil

def add_exercise(institucion, tema, exercise_id, anio, etapa, fuente,
                 image_path, subtemas=None, solucion=None, dificultad=None):
    """Agregar un ejercicio al repositorio."""
    folder = Path(f"exercises/{institucion}/{tema}/{exercise_id}")
    folder.mkdir(parents=True, exist_ok=True)

    meta = {
        "institucion": institucion,
        "tema": tema,
        "subtemas": subtemas or [],
        "anio": anio,
        "etapa": etapa,
        "fuente": fuente,
    }
    if dificultad:
        meta["dificultad"] = dificultad
    if solucion:
        meta["solucion"] = solucion

    with open(folder / "meta.yaml", "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

    ext = Path(image_path).suffix
    shutil.copy2(image_path, folder / f"imagen{ext}")
```

### Validar después de agregar

```bash
python build.py --validate-only
```

---

## Usar el wizard de contribución

Entrá a `/contribute` en el sitio. El wizard te guía paso a paso para armar ejercicios y descargar un ZIP con la estructura correcta. Después podés abrir un PR con esos archivos.

---

## Desarrollo local

```bash
pip install pyyaml jinja2
python build.py
# Abrí site/index.html en el navegador
```

### Validar sin construir

```bash
python build.py --validate-only
```

### Deploy

El sitio se despliega automáticamente a GitHub Pages vía GitHub Actions en cada push a `main`.
