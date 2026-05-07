# AstroDojo

Sitio estático para estudiar problemas de olimpiadas argentinas de astronomía.

## Estructura

```
exercises/
  olimpiada-argentina/
    mecanica/
      2023-nacional-ej01/
        imagen.png
        meta.yaml
    optica/
    termodinamica/
    electromagnetismo/
    astronomia-observacional/
    astrofisica/
build.py            # generador del sitio
templates/          # plantillas Jinja2
static/             # CSS y JS
contribute/         # wizard para contribuir ejercicios
site/               # salida generada (no se commitea)
```

## Agregar ejercicios via PR

1. Creá una carpeta en `exercises/olimpiada-argentina/<tema>/<anio>-<etapa>-ej<numero>/`
2. Agregá `imagen.png` (la imagen del problema) y `meta.yaml`
3. `meta.yaml` debe tener estos campos:

```yaml
institucion: olimpiada-argentina
tema: mecanica
subtemas: [cinematica, energia]
dificultad: intermedio   # facil | intermedio | dificil
anio: 2023
etapa: nacional          # provincial | nacional | internacional
fuente: "Olimpiada Argentina de Astronomía 2023, Nacional"
```

4. Abrí un PR. El CI valida automáticamente el schema.

## Usar el wizard de contribución

Entrá a `/contribute` en el sitio. El wizard te guía paso a paso para armar los ejercicios.

Al final tenés dos opciones:

### Opción 1: Descargar ZIP y abrir un PR

1. Hacé clic en **"Descargar ZIP"** en el paso final del wizard.
2. Descomprimí el ZIP — adentro vas a encontrar la carpeta `exercises/` con la estructura correcta de archivos (`meta.yaml` + `imagen.png` por cada ejercicio).
3. Hacé un fork de este repositorio en GitHub (botón "Fork" arriba a la derecha).
4. Cloná tu fork: `git clone https://github.com/TU-USUARIO/AstroDojo.git`
5. Copiá las carpetas del ZIP descomprimido dentro de tu clon, respetando la estructura (las carpetas van dentro de `exercises/olimpiada-argentina/<tema>/`).
6. Commiteá y pusheá:
   ```bash
   git add exercises/
   git commit -m "Agregar ejercicios de [año] [etapa]"
   git push
   ```
7. Abrí un Pull Request desde tu fork hacia este repositorio. El CI valida automáticamente que los `meta.yaml` tengan el formato correcto.

### Opción 2: Enviar para revisión

Hacé clic en **"Enviar para revisión"** — esto manda los ejercicios a un formulario donde un mantenedor los revisa y los sube por vos. No necesitás cuenta de GitHub.

## Desarrollo local

```bash
pip install pyyaml jinja2
python build.py
# Abrí site/index.html en el navegador
```

## Validar sin construir

```bash
python build.py --validate-only
```
