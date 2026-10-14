# Tarea: Biodiversidad de Fungi (riqueza de especies)

> **Estado:** esqueleto / planificado — listo para seed + worker beta.

Módulo de cómputo distribuido orientado a estimar la **riqueza de especies del reino Fungi** a partir de ocurrencias georreferenciadas de GBIF en unidades espaciales acotadas (celdas / AOIs).

**Por qué Fungi** 
Los hongos son esenciales para la vida terrestre: forman micorrizas con la mayoría de plantas vasculares, descomponen materia orgánica y reciclan nutrientes. Sin ellos, gran parte de la vegetación colapsaría y, con ella, la vida terrestre. A pesar de su importancia, siguen siendo uno de los grupos con mayor déficit de datos y de visibilidad en monitorización ambiental. Eco'clock quiere contribuir a cerrar ese hueco.

**Fuente primaria:** [GBIF](https://www.gbif.org) — Infraestructura Mundial de Información sobre Biodiversidad. 
**Taxón fijo:** reino Fungi → `taxonKey=5` / `kingdomKey=5`.

---

## Objetivo

Que cada cliente (CLI, GUI o app móvil) reciba una **unidad de trabajo** acotada, consulte (o simule) ocurrencias de hongos en esa zona y devuelva un **output** estandarizado para que el servidor pueda:

1. Registrar el resultado y otorgar créditos Eco'clock.
2. Agregar resultados (riqueza por región, series temporales, etc.).
3. Contrastar resultados entre clientes (verificación cruzada estilo BOINC).

---

## Ciclo de vida (igual que el resto de tareas)

GET  /tasks/next     →  payload tipo "biodiversity"
(cómputo local)
POST /tasks/submit   →  { task_id, output, compute_time_sec? }
textEl servidor asigna `status=assigned`, y al submit crea `Result` + `Credit` y marca `done`.

---

## Payload propuesto (`Task.payload`)

json
{
  "type": "biodiversity",
  "version": 1,
  "unit_id": "BIO-FUNGI-VAL-2024-T0042",
  "region": "Comunidad Valenciana",
  "bbox": {
    "min_lon": -0.8,
    "min_lat": 38.7,
    "max_lon": 0.3,
    "max_lat": 39.7,
    "crs": "EPSG:4326"
  },
  "source": {
    "name": "gbif",
    "api": "https://api.gbif.org/v1",
    "country": "ES",
    "taxon_key": 5,
    "kingdom": "Fungi",
    "year_from": 2010,
    "year_to": 2025
  },
  "params": {
    "metric": "species_richness",
    "method": "occurrence_count",
    "has_coordinate": true,
    "limit": 300,
    "max_records": 3000
  },
  "description": "Calcular riqueza de especies de Fungi (taxonKey=5) a partir de ocurrencias GBIF en la celda indicada."
}

Campo,Obligatorio,Descripción
type,sí,"Debe ser ""biodiversity"""
version,recomendado,Versión del esquema
unit_id,sí,Identificador estable de la celda
region,no,Etiqueta humana
bbox,sí,Extensión geográfica (EPSG:4326)
source.taxon_key,sí,Siempre 5 (Fungi)
source.kingdom,sí,"""Fungi"""
params.metric,sí,"species_richness (principal), occurrence_count"
params.method,no,occurrence_count en beta
params.max_records,no,Tope para no saturar al cliente
