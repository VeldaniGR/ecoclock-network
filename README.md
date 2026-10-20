# Eco'clock Network 🌿

> **Plataforma de confianza para donaciones verificadas a organizaciones ecologistas, con donación de cómputo distribuido.**

Cliente y servidor del proyecto [Eco'clock](https://ecoclock.org) — *en construcción activa*.

Eco'clock combina tres pilares:

1. **Whitelist verificada de ONGs** — solo organizaciones auditadas bajo criterios claros pueden recibir donaciones a través de la plataforma.
2. **Transparencia operativa** — el 95 % de cada donación va a las ONGs receptoras; el 5 % cubre gastos operativos (hosting, dominio, infraestructura), todo públicamente justificado.
3. **Donación de cómputo distribuido** — clientes (CLI, GUI de escritorio y app móvil) permiten donar capacidad de cómputo ociosa para procesar datos ambientales (deforestación, praderas de *Posidonia oceanica*, etc.).

## 🎯 Misión

Crear un **intermediario de confianza** entre quienes quieren contribuir al cuidado del medio ambiente y las organizaciones que realizan el trabajo de campo, reduciendo el riesgo de donar a proyectos opacos o no verificados.

## Estado del servicio (producción)

| Recurso | URL / nota |
|---------|------------|
| **API** | `https://api.ecoclock.org` (Contabo, Docker, Caddy + HTTPS) |
| **Health** | `GET /health` → `{"status":"ok","service":"ecoclock-network",...}` |
| **Descargas** | [download.ecoclock.org](https://download.ecoclock.org) (CLI, GUI, APK) |
| **Landing** | [ecoclock.org](https://ecoclock.org) |

Clientes (CLI, GUI, APK) apuntan por defecto a la API de producción.

### Usar la red en producción (recomendado)

```bash
# Tras instalar CLI o desde el binario
ecoclock --base-url https://api.ecoclock.org login --username TU_USER --password TU_PASS
ecoclock --base-url https://api.ecoclock.org run --max-tasks 1
# o: ecoclock-gui  (usa la misma API por defecto)

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

### Cómo comprobamos los resultados?

Eco'clock no se limita a aceptar lo que envía cada ordenador. El proceso tiene varias capas de control de calidad:

1. **Revisión automática al enviar** — Cada resultado debe tener el formato correcto y valores plausibles (por ejemplo, un índice de vegetación en un rango posible, o una superficie coherente con la zona analizada).

*Hoy en producción:* validación de formato/valores al submit y créditos por tarea.  
*En evolución:* contraste multi-nodo y revisiones humanas sistemáticas (documentado en `docs/` al activarse).

2. **Contraste entre varios participantes** — La misma unidad de trabajo puede calcularse en más de un equipo. Si los resultados coinciden de forma razonable, se consideran válidos. Si discrepan mucho, el sistema los marca para revisar o solicita otro cálculo.

3. **Controles de calidad periódicos** — Sobre el conjunto de datos se analizan patrones raros, sesgos o resultados que no encajan con lo esperado para una región o una fecha.

4. **Revisión humana cuando importa** — En casos dudosos, en zonas piloto o antes de usar los datos en informes públicos, puede intervenir el equipo del proyecto.

Los créditos reconocen la participación; el valor de los datos se consolida cuando el resultado pasa estos filtros. En la fase beta parte del cálculo aún es de prueba y se indica con claridad.

> Detalle de implementación (estados, quórum, créditos): se documentará en `docs/` a medida que se active cada capa.

## 🛠️ Stack tecnológico

### Servidor

- **Python** + **FastAPI** (API REST)
- **PostgreSQL** (datos)
- **Redis** (cola de tareas)
- **SQLAlchemy** (ORM) + **Pydantic** (validación)
- **python-jose** / **bcrypt** (JWT y contraseñas)
- **Docker** + **docker-compose**

### Cliente de escritorio

- **Python** ≥ 3.10, empaquetado con `pyproject.toml` (setuptools)
- **Typer** + **Rich** (CLI)
- **PyQt6** (GUI, extra `gui`)
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
│   │   ├── schemas/        # Pydantic
│   │   └── services/       # copernicus.py: token + search STAC
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── client/                 # CLI + GUI de escritorio
│   ├── cli.py              # entry point: ecoclock
│   ├── gui/                # PyQt6
│   │   └── app.py          # entry point: ecoclock-gui
│   └── requirements.txt
│
├── tasks/                  # Definición de tareas (dummy / real)
│   ├── ndvi/               # Ejemplo: NDVI
│   └── posidonia/          # README esquema payload
│
├── docs/
│   ├── architecture.md     # (pendiente / en redacción)
│   ├── ideas.md
│   └── legal/
│       └── checklist-asociacion.md
│
├── scripts/                # seed de tareas (STAC CDSE), build-linux.sh
├── packaging/
|   ├── linux/
│   |    ├── install-desktop.sh
│   |    ├── ecoclock.desktop
│   |    └── ecoclock.png
|   └── windows/
|       ├── install-desktop.ps1
|       ├── install-desktop.bat
|       ├── ecoclock.ico
|       └── README.md           
│
├── pyproject.toml          # paquete Python + entry points (ecoclock, ecoclock-gui)
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

## Estado del proyecto

| Área | Descripción | Estado |
|------|-------------|--------|
| API producción | Contabo + Docker + Caddy (`api.ecoclock.org`) | Hecho |
| Auth | Registro, login JWT, forgot/reset password (Resend) | Hecho |
| Tareas | NDVI, Posidonia, biodiversidad; refill + cron | Hecho |
| CDSE | Credenciales en servidor; seed STAC Copernicus | Hecho (operativo en VPS) |
| Créditos | `/me/credits`; tracking `client` / `client_mode` | Hecho |
| CLI + GUI | Submit manual/auto; default `api.ecoclock.org` | Hecho |
| APK Flutter | Compute por tipo, créditos, reset password, contadores | Hecho |
| download.ecoclock.org | Descargas + explicación Copernicus | Hecho |
| Whitelist ONGs / donaciones € | Pilares de producto a medio plazo | Roadmap |
| i18n clientes (12 idiomas) | Landing ya multi-idioma; CLI/GUI/APK pendiente | Roadmap |

Fases 0–4 (prototipo → beta instaladores v0.5.x) están cerradas; el foco actual es **operación estable** y calidad de tareas reales.

## 📦 Descargas

- **Sitio de descargas:** [download.ecoclock.org](https://download.ecoclock.org)  
  (CLI Linux/Windows, APK Android, explicación de las tareas Copernicus)

- **Releases GitHub:** [ecoclock-network/releases](https://github.com/VeldaniGR/ecoclock-network/releases)  
  Última estable de ejemplo: [v0.5.3](https://github.com/VeldaniGR/ecoclock-network/releases/tag/v0.5.3)

- **App móvil (código):** [ecoclock-mobile](https://github.com/VeldaniGR/ecoclock-mobile)


## 📥 Instalación (pip / pipx)

El cliente es un paquete Python (`pyproject.toml`, requiere **Python ≥ 3.10**) que instala dos ejecutables en tu `PATH`:

| Comando        | Descripción                          |
|----------------|--------------------------------------|
| `ecoclock`     | Cliente de línea de comandos (CLI)   |
| `ecoclock-gui` | Aplicación gráfica de escritorio     |

```bash
# Solo CLI
pipx install .

# CLI + GUI (PyQt6)
pipx install ".[gui]"

# Desarrollo (entorno virtual, modo editable, con tests)
python -m venv .venv
source .venv/bin/activate
pip install -e ".[gui,dev]"
pytest
```

Extras disponibles: `gui` (PyQt6) y `dev` (pytest, pytest-asyncio, httpx).

### Icono en el escritorio (Linux)

Para que Eco'clock aparezca en el menú de aplicaciones con su logo:

```bash
./packaging/linux/install-desktop.sh packaging/linux/ecoclock.png
```

Copia `ecoclock.desktop` a `~/.local/share/applications/` y el icono a `~/.local/share/icons/hicolor/256x256/apps/`. Requiere haber instalado `ecoclock-gui` (extra `gui`).

## 🏃 Cómo correr el proyecto en local

### Servidor y cliente

```bash
# Servidor + Postgres + Redis
docker compose up -d

# Health check
curl http://localhost:8000/health

# Cliente CLI (tarea de ejemplo)
python client/cli.py     # o, con el paquete instalado: ecoclock
```

### Seed de tareas (Copernicus / Fase C)

Script: `scripts/seed_copernicus_tasks.py`

Consulta el STAC de Copernicus Data Space (Sentinel-2 L2A) y crea tareas
`pending` de tipo `ndvi` y `posidonia` para que CLI, GUI y APK las consuman
con `GET /tasks/next`.

```bash
# Requisitos: .env con DATABASE_URL, CDSE_USERNAME, CDSE_PASSWORD
source .venv/bin/activate
docker compose up -d

# Simulación (no escribe en DB)
python scripts/seed_copernicus_tasks.py --ndvi 5 --posidonia 5 --dry-run

# Inserción real
python scripts/seed_copernicus_tasks.py --ndvi 5 --posidonia 5
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

## Contribuir

La beta de **cómputo** está abierta: descarga en [download.ecoclock.org](https://download.ecoclock.org), prueba 10 minutos y reporta fallos en [Issues](https://github.com/VeldaniGR/ecoclock-network/issues).

PRs y discusiones técnicas bienvenidas en el repo. El núcleo de donaciones económicas / whitelist de ONGs avanza en paralelo y se documentará cuando tenga superficie usable.

**Hecho con 💚 para el planeta.**
