# Arquitectura — Eco'clock Network

Documento de diseño de alto nivel. Alineado con el [README](../README.md) del repositorio.

**Estado:** borrador vivo (actualizado con Posidonia oceanica y cliente móvil).

---

## 1. Objetivos del sistema

Eco'clock Network es una plataforma con tres pilares:

| Pilar | Qué resuelve | Componente principal |
|-------|----------------|----------------------|
| **Confianza en donaciones** | Evitar donar a entidades no auditadas | Whitelist de ONGs + reglas de transparencia (95 % / 5 %) |
| **Transparencia operativa** | Justificar el 5 % de costes | Publicación de gastos e infraestructura |
| **Cómputo distribuido** | Aprovechar CPU/GPU ociosa para datos ambientales | API de tareas + clientes (CLI, GUI, móvil) |

Este documento se centra en la **arquitectura técnica** del cómputo distribuido y de la API. La capa de donaciones monetarias y legal (asociación, whitelist) se detalla en `docs/legal/` e ideas de producto en `docs/ideas.md`.

---

## 2. Vista general

```
                    ┌─────────────────────────────────────────┐
                    │              Clientes                   │
                    │  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
                    │  │ CLI     │ │ GUI     │ │ Flutter   │  │
                    │  │ Python  │ │ PyQt6   │ │ (móvil)   │  │
                    │  └────┬────┘ └────┬────┘ └─────┬─────┘  │
                    └───────┼──────────┼─────────────┼────────┘
                            │          │             │
                            └──────────┼─────────────┘
                                       │ HTTPS / JWT
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │         API FastAPI (server/)           │
                    │  /health  /auth/*  /tasks/*  /me/*      │
                    └───────┬─────────────────────┬───────────┘
                            │                     │
              ┌─────────────▼──────┐    ┌─────────▼──────────┐
              │    PostgreSQL      │    │  Redis (opcional)  │
              │  users, tasks,     │    │  colas / caché     │
              │  results, credits  │    └────────────────────┘
              └─────────┬──────────┘
                        │
                        ▼
              ┌─────────────────────────────────────────┐
              │     Orígenes de datos / tareas          │
              │  · Teselas satelitales (NDVI, etc.)     │
              │  · Cartografía Posidonia (Atlas, etc.)  │
              └─────────────────────────────────────────┘
```

**Repositorios:**

- **ecoclock-network** (este repo): servidor, CLI, GUI de escritorio, definición de tareas.
- **ecoclock-mobile**: cliente Android/iOS (Flutter) contra la misma API.

---

## 3. Componentes

### 3.1 Servidor API (`server/`)

| Capa | Responsabilidad |
|------|-----------------|
| **api/** | Rutas HTTP: autenticación, tareas, perfil/créditos |
| **core/** | Configuración (`.env`), JWT, hash de contraseñas, email (p. ej. Resend) |
| **db/** | Modelos SQLAlchemy y sesión async |
| **schemas/** | Contratos Pydantic (request/response) |

**Endpoints relevantes (contrato actual / previsto):**

| Método | Ruta | Uso |
|--------|------|-----|
| `GET` | `/health` | Liveness |
| `POST` | `/auth/register` | Alta (email, username, password) |
| `POST` | `/auth/login` | JWT (`access_token`) |
| `GET` | `/auth/me` | Usuario autenticado |
| `POST` | `/auth/forgot-password` | Inicio reset (email) — *previsto* |
| `POST` | `/auth/reset-password` | Nueva contraseña con token — *previsto* |
| `GET` | `/tasks/next` | Asigna y devuelve siguiente tarea |
| `POST` | `/tasks/submit` | Resultado + créditos |
| `GET` | `/me/credits` | Resumen e historial de créditos |

Autenticación: **Bearer JWT** (`sub` = username). Las rutas de tareas y créditos requieren usuario válido.

### 3.2 Persistencia

Modelo conceptual:

```
User 1──* Task 1──* Result
  │         │
  │         └──* Credit
  └────────────* Credit
```

- **User:** email, username, hashed_password, timestamps.
- **Task:** name, payload (JSON), status (`pending` → `assigned` → `done`), user_id, assigned_at, completed_at.
- **Result:** task_id, output (JSON), compute_time_sec opcional.
- **Credit:** user_id, task_id, amount (float), granted_at.

Al hacer `submit`, en la misma transacción: se marca la tarea `done`, se guarda el resultado y se inserta un **Credit** (p. ej. `CREDITS_PER_TASK` en config). No hay demora artificial: el crédito es inmediato en BD.

### 3.3 Clientes

| Cliente | Stack | Distribución |
|---------|--------|--------------|
| **CLI** | Python, requests | PyInstaller onedir (Linux/Windows) |
| **GUI** | PyQt6 | Mismo empaquetado / desarrollo local |
| **Móvil** | Flutter | APK/AAB vía GitHub Actions (repo `ecoclock-mobile`) |

Todos hablan el **mismo contrato HTTP**. La `baseUrl` apunta a:

- local: `http://127.0.0.1:8000`
- desarrollo: túnel (p. ej. ngrok)
- producción prevista: `https://api.ecoclock.org`

### 3.4 Tareas de cómputo (`tasks/`)

Cada tipo de tarea define:

1. **Payload** que el servidor entrega en `/tasks/next`.
2. **Cálculo** que ejecuta el cliente (o simula en beta).
3. **Output** que se envía en `/tasks/submit`.

#### 3.4.1 NDVI (implementación de referencia / dummy)

- Objetivo: índice de vegetación a partir de bandas roja / NIR.
- Payload de ejemplo: `type`, `tile_id`, `bands`, `description`.
- Sirve de plantilla para el ciclo assign → compute → submit → credit.

#### 3.4.2 Posidonia oceanica (planificado)

- **Indicador:** superficie (y, a futuro, evolución) de praderas de *Posidonia oceanica*.
- **Fuente de referencia:** datos y cartografía publicados por el [Atlas Posidonia](https://atlasposidonia.com/es) (contexto Illes Balears / Mediterráneo: biología, distribución, impactos, conservación).
- **Flujo previsto:**
  1. Ingesta o referencia a capas/teselas derivadas de cartografía pública o partners.
  2. Fragmentación en unidades de trabajo (celdas, polígonos, tiles).
  3. Cada cliente recibe un payload (id de unidad, metadatos, parámetros de cálculo).
  4. El resultado (p. ej. superficie estimada, máscara, estadísticas) se agrega en servidor para informes o verificación cruzada.

La definición concreta de algoritmos (clasificación, cambio de cobertura, etc.) se documentará en `tasks/posidonia/` cuando se implemente.

---

## 4. Flujos principales

### 4.1 Autenticación

```
Cliente                    API
   │  POST /auth/register    │
   │ ───────────────────────▶│  crea User
   │  POST /auth/login       │
   │ ───────────────────────▶│  devuelve access_token
   │  Authorization: Bearer  │
   │  GET /auth/me           │
   │ ───────────────────────▶│  UserResponse
```

Registro y login usan **username** en el login; el registro exige también **email**. El móvil puede hacer auto-login tras registro (register → login → me).

### 4.2 Ciclo de una tarea

```
Cliente                         API                         BD
   │  GET /tasks/next            │                           │
   │ ───────────────────────────▶│  busca pending o crea    │
   │                             │  dummy / real             │
   │                             │  status=assigned          │
   │ ◀──── TaskResponse ─────────│                           │
   │  (cómputo local / simulado) │                           │
   │  POST /tasks/submit         │                           │
   │  { task_id, output }        │  Result + Credit + done   │
   │ ───────────────────────────▶│ ─────────────────────────▶│
   │  GET /me/credits            │                           │
   │ ───────────────────────────▶│  total + recent           │
```

### 4.3 Reset de contraseña (previsto)

Depende de email transaccional (p. ej. **Resend**):

1. `POST /auth/forgot-password` con email o username → token de un solo uso (JWT con `purpose=password_reset`).
2. Envío de correo con enlace o código.
3. `POST /auth/reset-password` con token + nueva contraseña.

Sin API desplegada y sin proveedor de email configurado, la UI móvil puede existir pero el flujo no completa.

---

## 5. Despliegue

| Entorno | Cómo |
|----------|------|
| **Local** | `docker compose up -d` → API en `:8000`, Postgres, Redis |
| **Desarrollo remoto** | Misma API detrás de túnel HTTPS (ngrok u otro) para móviles |
| **Producción** | Dominio API estable (`api.ecoclock.org`), secretos en entorno, HTTPS terminado en proxy/reverse |

Variables típicas (`.env`): `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CREDITS_PER_TASK`, y a futuro `RESEND_API_KEY`, `EMAIL_FROM`.

---

## 6. Seguridad (resumen)

- Contraseñas con **bcrypt**; nunca en claro.
- **JWT** con expiración; logout = borrar token en cliente.
- Reset password: tokens de corta vida y propósito explícito.
- No revelar en forgot-password si el email/usuario existe (respuesta genérica).
- Clientes móviles: cabecera `ngrok-skip-browser-warning` solo en desarrollo con ngrok.
- Secretos solo en servidor; la app solo guarda el JWT (opcionalmente en SharedPreferences).

---

## 7. Créditos

- Unidad simbólica (**créditos Eco'clock**), sin valor monetario.
- Inspiración de sistemas tipo BOINC; la implementación es propia.
- `amount` es **float** en API y BD; los clientes deben parsear `num`, no asumir solo `int`.

---

## 8. Decisiones y no-objetivos (por ahora)

**Decisiones:**

- Una sola API para todos los clientes.
- Tareas con payload JSON flexible por `type`.
- Posidonia como segundo eje de datos ambientales, anclado a fuentes públicas mediterráneas.

**Fuera de alcance inmediato:**

- Marketplace de donaciones monetarias completo.
- Verificación científica peer-reviewed de cada resultado de Posidonia (se diseñará agregación/consistencia más adelante).
- Deep links de reset en móvil (fase posterior; primero token en correo + pantalla en app).

---

## 9. Referencias

- [README del proyecto](../README.md)
- [Atlas Posidonia](https://atlasposidonia.com/es) — contexto y datos de *Posidonia oceanica*
- [ecoclock.org](https://ecoclock.org)
- Repositorio móvil: [VeldaniGR/ecoclock-mobile](https://github.com/VeldaniGR/ecoclock-mobile)

---

*Última revisión de este borrador: alineado con README (Posidonia, clientes multiplataforma, créditos inmediatos, reset pendiente de API).*
