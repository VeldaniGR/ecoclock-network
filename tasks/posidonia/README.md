# Tarea: Posidonia oceanica (superficie de pradera)

> **Estado:** esqueleto / planificado — aún no hay worker real en producción.

Módulo de cómputo distribuido orientado a estimar o agregar **superficie de praderas** de *Posidonia oceanica* a partir de unidades cartográficas o teselas derivadas de datos públicos.

**Referencia de contexto y datos:** [Atlas Posidonia](https://atlasposidonia.com/es) (Illes Balears / Mediterráneo).

Este indicador **no** modela blanqueamiento de arrecifes de coral.

---

## Objetivo

Que cada cliente (CLI, GUI o app móvil) reciba una **unidad de trabajo** acotada, ejecute un cálculo local (o simulado en beta) y devuelva un **output** estandarizado para que el servidor pueda:

1. Registrar el resultado y otorgar créditos Eco'clock.
2. Agregar resultados (superficie total, cobertura por zona, etc.) en fases posteriores.
3. Opcionalmente contrastar resultados entre clientes (verificación cruzada).

---

## Ciclo de vida (igual que el resto de tareas)

```
GET  /tasks/next     →  payload tipo "posidonia"
     (cómputo local)
POST /tasks/submit   →  { task_id, output, compute_time_sec? }
```

El servidor asigna `status=assigned`, y al submit crea `Result` + `Credit` y marca `done`.

---

## Payload propuesto (`Task.payload`)

JSON flexible; campos mínimos recomendados:

```json
{
  "type": "posidonia",
  "version": 1,
  "unit_id": "POS-BAL-2024-T0042",
  "region": "Illes Balears",
  "bbox": {
    "min_lon": 2.45,
    "min_lat": 39.50,
    "max_lon": 2.55,
    "max_lat": 39.58,
    "crs": "EPSG:4326"
  },
  "source": {
    "name": "atlas_posidonia",
    "url": "https://atlasposidonia.com/es",
    "layer_ref": "optional-layer-or-dataset-id",
    "year": 2024
  },
  "params": {
    "metric": "surface_m2",
    "method": "placeholder",
    "notes": "Beta: el cliente puede devolver un resultado simulado."
  },
  "description": "Estimar superficie de Posidonia oceanica en la unidad indicada."
}
```

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `type` | sí | Debe ser `"posidonia"` |
| `version` | recomendado | Versión del esquema de payload |
| `unit_id` | sí | Identificador estable de la celda / polígono / tile |
| `region` | no | Etiqueta humana (p. ej. Baleares) |
| `bbox` | según método | Extensión geográfica de la unidad |
| `source` | recomendado | Procedencia (Atlas Posidonia u otro) |
| `params.metric` | sí | Qué se pide: p. ej. `surface_m2`, `coverage_ratio` |
| `params.method` | no | Algoritmo previsto (`placeholder` en beta) |
| `description` | no | Texto para UI |

En **beta**, el servidor puede generar un payload dummy (análogo al NDVI actual) sin ficheros pesados en el cliente.

---

## Output propuesto (`Result.output`)

```json
{
  "type": "posidonia",
  "version": 1,
  "unit_id": "POS-BAL-2024-T0042",
  "metric": "surface_m2",
  "value": 12500.0,
  "unit": "m2",
  "confidence": null,
  "method": "placeholder",
  "client": {
    "device": "flutter_mobile",
    "app_version": "0.5.3"
  },
  "processed_at": "2026-09-23T10:00:00Z"
}
```

| Campo | Descripción |
|-------|-------------|
| `value` | Resultado numérico principal (superficie, ratio, …) |
| `unit` | Unidad coherente con `metric` (`m2`, `ha`, `0-1`, …) |
| `confidence` | Opcional (0–1 o etiqueta) cuando exista modelo real |
| `method` | Debe reflejar lo ejecutado (`placeholder` en simulación) |

### Ejemplo de submit (cliente)

```json
{
  "task_id": 42,
  "output": {
    "type": "posidonia",
    "version": 1,
    "unit_id": "POS-BAL-2024-T0042",
    "metric": "surface_m2",
    "value": 12500.0,
    "unit": "m2",
    "method": "placeholder",
    "processed_at": "2026-09-23T10:00:00Z"
  },
  "compute_time_sec": 1.2
}
```

---

## Comportamiento del cliente (fases)

| Fase | Comportamiento |
|------|----------------|
| **Beta / actual** | Si `method` es `placeholder` (o no hay datos locales): generar output simulado coherente con el payload y enviar submit. |
| **v1** | Descargar o usar datos asociados a `unit_id` / `bbox` y calcular métrica real. |
| **v2+** | Verificación cruzada, agregación en servidor, posibles créditos variables por complejidad. |

---

## Estructura de carpeta prevista

```
tasks/posidonia/
├── README.md           # este archivo
├── schema/             # (opcional) JSON Schema de payload/output
│   ├── payload.v1.json
│   └── output.v1.json
├── worker/             # (futuro) lógica de cálculo reutilizable
│   └── __init__.py
└── fixtures/           # (futuro) payloads de ejemplo para tests
    └── sample_next.json
```

---

## Relación con el servidor

- Creación de tareas: jobs admin / seed / cola que insertan filas `Task` con `name` tipo `posidonia-…` y `payload` JSON.
- `/tasks/next` no necesita cambios de ruta: basta con devolver payloads con `"type": "posidonia"`.
- Los clientes deben ramificar por `payload["type"]` (igual que con `"ndvi"`).

---

## Notas legales y de datos

- Respetar licencias y condiciones de uso de cualquier capa descargada del Atlas u otras fuentes.
- Preferir datos abiertos o acuerdos explícitos antes de redistribuir rasters pesados dentro del payload.
- En duda, el payload solo lleva **referencias** (`layer_ref`, `unit_id`) y el worker obtiene los datos por canal autorizado.

---

## Referencias

- [Atlas Posidonia](https://atlasposidonia.com/es)
- [Arquitectura del proyecto](../../docs/architecture.md)
- Tarea de referencia existente: `tasks/ndvi/`
