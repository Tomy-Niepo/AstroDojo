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

## Contribuir con nuevos ejercicios (recomendado)

La forma más fácil de agregar ejercicios es usando la carpeta de staging `new-exercises/`:

### Pasos

1. Creá carpetas de ejercicios dentro de `new-exercises/` (estructura plana, sin subcarpetas de institución/tema):
   ```
   new-exercises/
     2025-nacional-ej03/
       meta.yaml
       imagen.png
     2025-provincial-ej01/
       meta.yaml
       imagen.jpg
   ```

2. **(Opcional)** Revisá y editá los ejercicios con la app local:
   ```bash
   python review.py
   # Abrí http://localhost:5112
   ```
   La app muestra los ejercicios con sus imágenes, indica errores de validación, y permite editar metadata y reemplazar imágenes.

3. Importá los ejercicios a la estructura correcta:
   ```bash
   # Preview sin mover nada:
   python import_exercises.py --dry-run

   # Importar (mueve las carpetas a exercises/<inst>/<tema>/<id>/):
   python import_exercises.py
   ```

4. Verificá y hacé el PR:
   ```bash
   python build.py --validate-only
   git add exercises/
   git commit -m "Add new exercises"
   git push
   ```

La carpeta `new-exercises/` está en `.gitignore` — es solo para uso local.

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

El formato está diseñado para que un LLM pueda procesar PDFs de exámenes y generar las carpetas de ejercicios automáticamente.

**Importante**: el LLM **no** asigna dificultad — eso lo hace un humano después. El campo `dificultad` es opcional.

### `extract_exercises.py`

Script incluido para extraer imágenes de páginas de un PDF. Un agente puede usarlo directamente, o se puede usar manualmente.

```bash
pip install -r requirements.txt

# Screenshotear todas las páginas de un PDF:
python extract_exercises.py exam.pdf --outdir screenshots/

# Solo páginas específicas:
python extract_exercises.py exam.pdf --pages 2,3,5 --outdir screenshots/

# Recortar (top half de la página):
python extract_exercises.py exam.pdf --pages 3 --crop 0,0,100,50 --outdir screenshots/

# Generar carpetas de ejercicios completas (1 ejercicio por página):
python extract_exercises.py exam.pdf --pages 1,2,3,4,5 \
    --institucion olimpiada-argentina --tema mecanica-celeste \
    --anio 2025 --etapa nacional --exercise-num 1 \
    --fuente "Olimpiada Argentina de Astronomía 2025, Nacional"
```

Cuando se pasan los flags de metadata (`--institucion`, `--tema`, `--anio`, `--etapa`, `--fuente`), el script genera la carpeta completa con `meta.yaml` + `imagen.png` lista para commitear. Si no, simplemente extrae PNGs.

### Flujo para un agente/LLM

1. El agente recibe el PDF de un examen.
2. Usa `extract_exercises.py` para extraer screenshots de cada ejercicio (una página o recorte por ejercicio).
3. Mira cada imagen, clasifica el tema y subtemas.
4. Genera las carpetas finales (ya sea con el mismo script usando los flags de metadata, o creando `meta.yaml` a mano).

### Prompt de referencia

```
Tengo el PDF adjunto de un examen de olimpiada de astronomía.
Necesito que generes las carpetas de ejercicios para el repositorio AstroDojo.

Herramientas disponibles:
- extract_exercises.py: extrae screenshots de páginas del PDF y opcionalmente
  genera las carpetas de ejercicios completas. Corré
  "python extract_exercises.py --help" para ver las opciones.
- build.py --validate-only: valida que los meta.yaml sean correctos.

Para cada ejercicio del PDF:
1. Usá extract_exercises.py para screenshotear la página del enunciado.
   Si hay varios ejercicios por página, usá --crop para recortar.
2. Determiná el tema (uno de: coordenadas-celestes, mecanica-celeste, optica,
   instrumentos, astrofisica, cosmologia, magnitudes, radiacion, galaxias).
3. Listá los subtemas relevantes.
4. Generá la carpeta del ejercicio con meta.yaml + imagen.png.
   NO incluyas dificultad en el meta.yaml — eso se asigna después.

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

Cuando termines, corré "python build.py --validate-only" para verificar.
```

### Ejemplo: resultado esperado

Con un PDF de 5 ejercicios de la Olimpiada Argentina 2025 Nacional, el agente debería generar:

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
