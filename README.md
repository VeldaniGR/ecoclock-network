# Eco'clock Network 🌿

> **Plataforma de confianza para donaciones verificadas a organizaciones ecologistas, con donación de cómputo distribuido.**

Cliente y servidor del proyecto [Eco'clock](https://ecoclock.org) — *en construcción activa*.

Eco'clock combina tres pilares:

1. **Whitelist verificada de ONGs** — solo organizaciones auditadas bajo criterios claros pueden recibir donaciones a través de la plataforma.
2. **Transparencia operativa** — el 95 % de cada donación va a las ONGs receptoras; el 5 % cubre gastos operativos (hosting, dominio, infraestructura), todo públicamente justificado.
3. **Donación de cómputo distribuido** — clientes (CLI, GUI de escritorio y app móvil) permiten donar capacidad de cómputo ociosa para procesar datos ambientales (deforestación, praderas de *Posidonia oceanica*, etc.).

## 🎯 Misión

Crear un **intermediario de confianza** entre quienes quieren contribuir al cuidado del medio ambiente y las organizaciones que realizan el trabajo de campo, reduciendo el riesgo de donar a proyectos opacos o no verificados.

## 📐 Arquitectura (resumen)

```
┌──────────────────────┐       HTTPS        ┌─────────────────────┐
│  Clientes            │ ─────────────────▶ │  Servidor API       │
│  · CLI / GUI PyQt6   │                    │  FastAPI + Postgres │
│  · App Flutter       │                    └──────────┬──────────┘
└──────────────────────┘                               │
                                                       ▼
                                            ┌─────────────────────┐
                                            │  Copernicus CDSE    │
                                            │  Sentinel-2 L2A     │
                                            │  (STAC / token)     │
                                            │  → Task.payload     │
                                            └─────────────────────┘
```

- **Servidor** (`server/`): API REST, autenticación JWT, asignación de tareas, créditos y resultados.
- **Cliente de escritorio** (`client/`): CLI y GUI PyQt6; binarios onedir en [Releases](https://github.com/VeldaniGR/ecoclock-network/releases).
- **App móvil**: repositorio [ecoclock-mobile](https://github.com/VeldaniGR/ecoclock-mobile) (Flutter), misma API.


### Indicadores ambientales

| Indicador | Fuente satélite primaria | Notas |
|-----------|--------------------------|--------|
| **Vegetación / NDVI** | **Copernicus Sentinel-2** (CDSE) | Independiente de GFW |
| **Posidonia (superficie)** | **Copernicus Sentinel-2** (CDSE) | Atlas Posidonia = referencia cartográfica opcional, no API obligatoria |

La *Posidonia oceanica* es una planta marina endémica del Mediterráneo (no un alga): genera oxígeno, fija CO₂, estabiliza fondos y playas y sostiene biodiversidad. El Atlas Posidonia documenta su presencia, impactos (fondeo, contaminación, clima) y conservación en Baleares; Eco'clock usará ese tipo de información cartográfica/publicada como base de tareas de cómputo distribuido sobre **extensión de pradera**, de momento, no sobre blanqueo coralino.

## 🛠️ Stack tecnológico

### Servidor

- **Python** + **FastAPI** (API REST)
- **PostgreSQL** (datos)
- **Redis** (cola de tareas)
- **SQLAlchemy** (ORM) + **Pydantic** (validación)
- **python-jose** / **bcrypt** (JWT y contraseñas)
- **Docker** + **docker-compose**

### Cliente de escritorio

- **Python**
- **PyQt6** (GUI)
- **requests** (HTTP)
- **NumPy** (cálculo)
- **PyInstaller** (empaquetado **onedir** → `dist/ecoclock-cli/` + `_internal/`)

### App móvil (repo separado)

- **Flutter** / Dart
- Misma API (`/auth`, `/tasks`, `/me/credits`, …)

## 📂 Estructura del repositorio

```
ecoclock-network/
├── server/                 # API FastAPI + lógica de negocio
│   ├── app/
│   │   ├── api/            # Endpoints (auth, tasks, me, …)
│   │   ├── core/           # Config, seguridad, JWT
│   │   ├── db/             # Modelos SQLAlchemy
│   │   └── schemas/        # Pydantic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── client/                 # CLI + GUI de escritorio
│   ├── cli.py
│   ├── gui/                # PyQt6
│   └── requirements.txt
│
├── tasks/                  # Definición de tareas (dummy / real)
│   └── ndvi/               # Ejemplo: NDVI
│
├── docs/
│   ├── architecture.md     # (pendiente / en redacción)
│   ├── ideas.md
│   └── legal/
│       └── checklist-asociacion.md
│
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
├── scripts/
│   └── seed_posidonia_tasks.py   # STAC CDSE → tareas posidonia
├── server/app/services/
│   └── copernicus.py             # token + search STAC
├── tasks/
│   ├── ndvi/
│   └── posidonia/                # README esquema payload
```

## 🚀 Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Cimientos: repo, docs, entorno local | 🟢 Hecha |
| **Fase 1** | Prototipo: servidor + cliente CLI | 🟢 Hecha |
| **Fase 2** | GUI PyQt6 (login → next → submit E2E) | 🟢 Hecha |
| **Fase 3** | Créditos, verificación estilo BOINC | 🟢 Hecha (tag v0.3.0-fase3) |
| **Fase 4** | Beta: instaladores, auto-update | 🟢 Hecha (v0.5.0–v0.5.3) |
| **v0.5.3** | Binarios onedir Linux/Windows, fix DLL, auto-update | 🟢 [Release](https://github.com/VeldaniGR/ecoclock-network/releases/tag/v0.5.3) |
| **Móvil** | Cliente Flutter + API ngrok / futura api.ecoclock | 🟡 En curso |
| **CDSE / token** | Credenciales servidor + `get_cdse_token` | 🟢 Hecha (local) |
| **Seed posidonia** | Script STAC → Task pending | 🟡 Fase C |


## 📦 Descargas

Binarios oficiales (GitHub Actions, formato **onedir**):

- [ecoclock-cli v0.5.3 · Linux x86_64 (tar.gz)](https://github.com/VeldaniGR/ecoclock-network/releases/download/v0.5.3/ecoclock-cli-v0.5.3-linux-x86_64.tar.gz)
- [ecoclock-cli v0.5.3 · Windows x86_64 (zip)](https://github.com/VeldaniGR/ecoclock-network/releases/download/v0.5.3/ecoclock-cli-v0.5.3-windows-x86_64.zip)

Todos los releases: <https://github.com/VeldaniGR/ecoclock-network/releases>

## 🏃 Cómo correr el proyecto en local

```bash
# Servidor + Postgres + Redis
docker compose up -d

# Health check
curl http://localhost:8000/health

# Cliente CLI (tarea de ejemplo)
python client/cli.py
```

### Binario autocontenido (PyInstaller — onedir)

```bash
./scripts/build-linux.sh
# → dist/ecoclock-cli/
```

**Linux:**

```bash
tar -xzf ecoclock-cli-v0.5.3-linux-x86_64.tar.gz
./ecoclock-cli/ecoclock-cli --base-url https://api.ecoclock.org login
./ecoclock-cli/ecoclock-cli --base-url http://127.0.0.1:8000 next
ECOCLOCK_BASE_URL=http://127.0.0.1:8000 ./ecoclock-cli/ecoclock-cli me
```

**Windows:**

```powershell
Expand-Archive ecoclock-cli-v0.5.3-windows-x86_64.zip
.\ecoclock-cli\ecoclock-cli.exe --base-url https://api.ecoclock.org login
.\ecoclock-cli\ecoclock-cli.exe --base-url http://127.0.0.1:8000 next
```

### Auto-actualización

```bash
ecoclock update          # descarga y reemplaza
ecoclock update --check  # solo informa si hay release nuevo
```

## 📚 Documentación adicional

- [`docs/architecture.md`](docs/architecture.md) — arquitectura detallada *(en redacción)*
- [`docs/ideas.md`](docs/ideas.md) — ideas y notas
- [`docs/legal/checklist-asociacion.md`](docs/legal/checklist-asociacion.md) — checklist asociación
- [Atlas Posidonia](https://atlasposidonia.com/es) — datos y contexto de *Posidonia oceanica* (Baleares)

## 📜 Licencia

**MIT License** — código abierto: cualquiera puede auditar y contribuir.

Eco'clock apuesta por la transparencia: código público, y a medio plazo cuentas y verificaciones de ONGs también públicas.

## 🤝 Contribuir

Por ahora el proyecto está en fase temprana (fundador + asistencia AI). Cuando la beta esté abierta al público general, se habilitarán issues y PRs de forma más amplia.

---

**Hecho con 💚 para el planeta.**
