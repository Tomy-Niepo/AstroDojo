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

El ID es el nombre de la carpeta. Formato sugerido: `<anio>-<etapa>-<individual/grupal>-ej<numero>`, por ejemplo `2025-nacional-grupal-ej03`. No es estricto, pero debe ser único dentro de su tema.

### Imagen

Un archivo llamado `imagen.<ext>` donde `<ext>` es `png`, `jpg`, `jpeg`, `webp` o `svg`. Es la captura/foto del enunciado del problema.

---

## Contribuir con nuevos ejercicios (recomendado)

La forma más fácil de agregar ejercicios es usando la carpeta de staging `new-exercises/`:

### Pasos

1. Forkeá el repositorio.

2. Creá la carpetas de ejercicios dentro de `new-exercises/` (estructura plana, sin subcarpetas de institución/tema):
(Si tu institución no existe todavía, solamente con que un ejercicio nuevo pertenezca a esa institucion la creará automaticamente.)
   ```
   new-exercises/
     2025-nacional-ej03/
       meta.yaml
       imagen.png
     2025-provincial-ej01/
       meta.yaml
       imagen.jpg
   ```

3. **(Opcional)** Revisá y editá los ejercicios con la app local:
   ```bash
   pip install -r requirements.txt
   python review.py
   # Abrí http://localhost:5112
   ```
   La app muestra los ejercicios con sus imágenes, indica errores de validación, y permite editar metadata y reemplazar imágenes.

4. Importá los ejercicios a la estructura correcta:
   ```bash
   # Preview sin mover nada:
   python import_exercises.py --dry-run

   # Importar (mueve las carpetas a exercises/<inst>/<tema>/<id>/):
   python import_exercises.py
   ```

5. Verificá corriendo el script `build.py`:
   ```bash
   python build.py --validate-only
   ```

6. Crea el PR:
   ```bash
   git add exercises/
   git commit -m "Add new exercises"
   git push
   ```

La carpeta `new-exercises/` es solo para uso local.

---

## Agregar ejercicios con un LLM / agente

El formato está diseñado para que un LLM pueda procesar PDFs de exámenes y generar las carpetas de ejercicios automáticamente.

**Importante**: el LLM **no** asigna dificultad — eso lo hace un humano después. El campo `dificultad` es opcional.

### Imagenes

Se recomienda fuertemente instalar alguna herramienta que habilite al agente tomar capturas de PDFs, como `pdftoppm` o `ghostscript`. Si no, el script `extract_excersises.py` esta destinado a ese proposito, pero no siempre funciona correctamente.

Cuando se pasan los flags de metadata (`--institucion`, `--tema`, `--anio`, `--etapa`, `--fuente`), el script genera la carpeta completa con `meta.yaml` + `imagen.png`. Si no, simplemente extrae PNGs.

### Prompt de referencia

```
Tu objetivo es crear archivos para ejercicios de astronomia para un directorio publico a partir de PDFs que existen en este directorio.

Herramientas disponibles:
- SI existen, herramientas de terminal para tomar fotos de PDFs
- extract_exercises.py: Alternativa para extraer screenshots de páginas del PDF y opcionalmente
  genera las carpetas de ejercicios completas. Corré
  "python extract_exercises.py --help" para ver las opciones.
- build.py --validate-only: valida que los meta.yaml sean correctos.

Para cada ejercicio del PDF:
1. Usá la herramienta dedicada o alternativamente extract_exercises.py para screenshotear la página del enunciado. Si hay varios ejercicios por página o un ejercicio toma mas de una pagina, utiliza la herramienta correctamente o usá --crop para recortar.
2. Determiná el tema (uno de: coordenadas-celestes, mecanica-celeste, optica, instrumentos, astrofisica, cosmologia, magnitudes, radiacion, galaxias).
3. Listá los subtemas relevantes.
4. Determina la institucion a la que pertenece. Si hay existentes, asegurate de usar exactamente la misma string que ya esta en uso. SI es una nueva institucion, asigna un string o preguntalo al usuario, de cualquier manera debe ser el mismo siempre para la misma institucion. debe ser en slug kebab-case (ej: "olimpiada-argentina", "olimpiada-latinoamericana", "ioaa").
5. Generá la carpeta del ejercicio con meta.yaml + imagen.png.
   NO incluyas dificultad en el meta.yaml.

Formato del meta.yaml:
  institucion: <slug-kebab-case>
  tema: <tema>
  subtemas: [<subtema1>, <subtema2>]
  anio: <año>
  etapa: <provincial|nacional|internacional>
  fuente: "<Nombre de la olimpiada año, Etapa>"
  solucion: "<url>"  # opcional

Nuevos ejercicios deberan ir en la carpeta de 'new-exercises', siguiendo el siguiente formato:

new-exercises/
     <id1>/
       meta.yaml
       imagen.png
     <id2>/
       meta.yaml
       imagen.jpg
donde el <id> indica año, etapa, numero de ejercicio, y si es requerido si fue grupal o individual. Por ejemplo '2025-nacional-grupal-ej03'

Cuando termines, corré "python build.py --validate-only" para verificar.
```
