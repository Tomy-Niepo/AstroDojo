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

Entrá a `/contribute` en el sitio. El wizard te guía paso a paso para armar los archivos y descargar un ZIP listo para abrir un PR.

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
