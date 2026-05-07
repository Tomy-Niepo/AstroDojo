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
dificultad: intermedio                   # facil | intermedio | dificil
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
dificultad: facil
anio: 2024
etapa: provincial
fuente: "Olimpiada Argentina de Astronomía 2024, Provincial"
```

---

## Agregar ejercicios con un LLM / agente

El formato está diseñado para que un LLM pueda generar ejercicios a partir de capturas de pantalla de problemas. El flujo es:

### Prompt de referencia

```
Tengo una imagen de un problema de olimpiada de astronomía. Necesito que generes
los archivos para AstroDojo.

Datos del problema:
- Institución: olimpiada-argentina
- Año: 2025
- Etapa: nacional
- Número de ejercicio: 3

Instrucciones:
1. Mirá la imagen y determiná el tema (uno de: coordenadas-celestes,
   mecanica-celeste, optica, instrumentos, astrofisica, cosmologia,
   magnitudes, radiacion, galaxias).
2. Determiná la dificultad (facil, intermedio, dificil).
3. Listá los subtemas relevantes.
4. Generá el meta.yaml con el formato exacto de abajo.
5. Guardá la imagen como imagen.png en la carpeta correspondiente.

Formato del meta.yaml:
  institucion: <slug-kebab-case>
  tema: <tema>
  subtemas: [<subtema1>, <subtema2>]
  dificultad: <facil|intermedio|dificil>
  anio: <año>
  etapa: <provincial|nacional|internacional>
  fuente: "<Nombre de la olimpiada año, Etapa>"

La carpeta debe ser: exercises/<institucion>/<tema>/<anio>-<etapa>-ej<numero>/
```

### Agregar en masa con un script

Para agregar varios ejercicios programáticamente, cada ejercicio necesita:

```python
import yaml
from pathlib import Path

def add_exercise(institucion, tema, exercise_id, dificultad, anio, etapa, fuente,
                 image_path, subtemas=None, solucion=None):
    """Agregar un ejercicio al repositorio."""
    folder = Path(f"exercises/{institucion}/{tema}/{exercise_id}")
    folder.mkdir(parents=True, exist_ok=True)

    meta = {
        "institucion": institucion,
        "tema": tema,
        "subtemas": subtemas or [],
        "dificultad": dificultad,
        "anio": anio,
        "etapa": etapa,
        "fuente": fuente,
    }
    if solucion:
        meta["solucion"] = solucion

    with open(folder / "meta.yaml", "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

    # Copiar la imagen
    import shutil
    ext = Path(image_path).suffix
    shutil.copy2(image_path, folder / f"imagen{ext}")

# Ejemplo:
add_exercise(
    institucion="olimpiada-argentina",
    tema="optica",
    exercise_id="2025-nacional-ej03",
    dificultad="intermedio",
    anio=2025,
    etapa="nacional",
    fuente="Olimpiada Argentina de Astronomía 2025, Nacional",
    image_path="/ruta/a/captura.png",
    subtemas=["refraccion", "lentes"],
)
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
