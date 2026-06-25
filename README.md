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
edit.py                 # app local para editar ejercicios (puerto 5050)
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
modalidad: individual                    # (opcional) individual | grupal
nivel: N1                                # (opcional) nivel del ejercicio
numero: 3                                # número del ejercicio dentro del examen
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

El ID es el nombre de la carpeta. Formato: `<institucion>-<anio>-<etapa>[-<modalidad>][-<nivel>]-ej<numero>`

Ejemplos:
- `olimpiada-argentina-2025-nacional-individual-N1-ej03`
- `olimpiada-argentina-2024-nacional-grupal-ej01`
- `ioaa-2023-internacional-ej05`

El ID debe ser único globalmente (no solo dentro del tema), ya que el sitio usa el ID como URL.

### Imagen

Un archivo llamado `imagen.<ext>` donde `<ext>` es `png`, `jpg`, `jpeg`, `webp` o `svg`. Es la captura/foto del enunciado del problema.

---

## Editar ejercicios localmente con `edit.py`

`edit.py` es una app Flask local (puerto 5050) para editar y revisar ejercicios existentes. Solo muestra ejercicios que ya están en `exercises/` (comprometidos o no).

```bash
pip install -r requirements.txt
python edit.py
# Abrí http://localhost:5050
```

### Funcionalidades

- **Hub de temas**: vista principal con los 9 temas, mostrando cuántos ejercicios tiene cada uno (igual que el sitio público).
- **Vista por tema**: ejercicios de un tema con filtros por subtema, año, dificultad, etapa y nivel.
- **Vista "Todos"**: todos los ejercicios de todos los temas con filtros por año, tema, dificultad, etapa y nivel.
- **Edición individual**: editar metadata (tema, subtemas, dificultad, fuente, solución, etc.) y reemplazar la imagen de un ejercicio.
- **Edición masiva**: filtrar ejercicios por múltiples criterios y aplicar un mismo valor de campo a todos los resultados de una vez (útil para asignar la misma URL de solución a todos los ejercicios de un año/competencia).

---

## Contribuir con nuevos ejercicios usando el wizard (recomendado para principiantes)

En la parte superior a la derecha de la pagina, clickeando el boton 'contribuir', se abre el "wizard", donde se pueden añadir ejercicios manualmente uno por uno con una UI facil. Luego de añadir todos los ejercicios, el wizard tiene todos los pasos a seguir para que aparezcan en la pagina.

## Contribuir con nuevos ejercicios desde la terminal

### Pasos

1. Forkeá el repositorio.

2. Creá las carpetas de ejercicios directamente dentro de `exercises/<institucion>/<tema>/<id>/`:

   ```
   exercises/
     olimpiada-argentina/
       mecanica-celeste/
         olimpiada-argentina-2025-nacional-individual-N1-ej03/
           meta.yaml
           imagen.png
   ```

3. **(Opcional)** Revisá y editá los ejercicios con la app local:
   ```bash
   pip install -r requirements.txt
   python edit.py
   # Abrí http://localhost:5050
   ```

4. Verificá corriendo el script `build.py`:
   ```bash
   python build.py --validate-only
   ```

5. Crea el PR:
   ```bash
   git add exercises/
   git commit -m "Add exercises for <institution> <year>"
   git push
   ```

---

## Agregar ejercicios con un LLM / agente

El formato está diseñado para que un LLM pueda procesar PDFs de exámenes y generar las carpetas de ejercicios automáticamente.

**Importante**: el LLM **no** asigna dificultad — eso lo hace un humano después con `edit.py`. El campo `dificultad` es opcional.

### Imagenes

Se recomienda fuertemente instalar alguna herramienta que habilite al agente tomar capturas de PDFs, como `pdftoppm` o `ghostscript`.

### Prompt de referencia

```
Tu objetivo es crear archivos para ejercicios de astronomia para un directorio publico a partir de PDFs que existen en este directorio.

Herramientas disponibles:
- SI existen, herramientas de terminal para tomar fotos de PDFs (pdftoppm, ghostscript, etc.)
- build.py --validate-only: valida que los meta.yaml sean correctos.

Para cada ejercicio del PDF:
1. Usá la herramienta dedicada para screenshotear la página del enunciado. Si hay varios ejercicios por página o un ejercicio toma mas de una pagina, utilizá la herramienta correctamente para recortar.
2. Determiná el tema (uno de: coordenadas-celestes, mecanica-celeste, optica, instrumentos, astrofisica, cosmologia, magnitudes, radiacion, galaxias).
3. Listá los subtemas relevantes.
4. Determiná la institución a la que pertenece. Si ya hay ejercicios de esa institución, usá exactamente el mismo slug. Si es nueva, asigná un slug en kebab-case (ej: "olimpiada-argentina", "ioaa", "olimpiada-iberoamericana").
5. Generá la carpeta del ejercicio con meta.yaml + imagen.png directamente en exercises/<institucion>/<tema>/<id>/.
   NO incluyas dificultad en el meta.yaml.

Formato del meta.yaml:
  institucion: <slug-kebab-case>
  tema: <tema>
  subtemas: [<subtema1>, <subtema2>]
  anio: <año>
  etapa: <provincial|nacional|internacional>
  modalidad: <individual|grupal>  # si aplica
  nivel: <N1|N2|...>              # si aplica
  numero: <número del ejercicio>
  fuente: "<Nombre de la olimpiada año, Etapa>"
  solucion: "<url>"  # opcional

Formato del ID (nombre de carpeta): <institucion>-<anio>-<etapa>[-<modalidad>][-<nivel>]-ej<numero>
Ejemplo: olimpiada-argentina-2025-nacional-individual-N1-ej03

Cuando termines, corré "python build.py --validate-only" para verificar.
```
