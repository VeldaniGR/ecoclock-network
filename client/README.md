# Eco'clock Network — Cliente (Fase 1)

Cliente de línea de comandos para el servidor de Eco'clock Network.

## Instalación

```bash
cd /home/veldanigranroble/Projects/ecoclock-network/client
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
# 1. Registrar un usuario
python3 -m client.cli register --email a@b.c --username alice --password secret

# 2. Login (guarda el token en $XDG_CONFIG_HOME/ecoclock/token.json, modo 0600)
python3 -m client.cli login --username alice --password secret

# 3. Ver datos del usuario
python3 -m client.cli me

# 4. Pedir la siguiente tarea
python3 -m client.cli next

# 5. Procesar y enviar resultado (manualmente)
python3 -m client.cli submit --task-id 1 --output '{"ndvi": 0.65}' --compute-time-sec 0.5

# 6. Flujo completo (auth + next + compute stub + submit)
python3 -m client.cli run \
  --email a@b.c --username alice --password secret \
  --register

# 7. Logout (borra el token local)
python3 -m client.cli logout
```

## Configuración por variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `ECOCLOCK_BASE_URL` | `http://127.0.0.1:8000` | URL del servidor |
| `ECOCLOCK_TIMEOUT` | `10` | Timeout HTTP en segundos |
| `XDG_CONFIG_HOME` | `~/.config` | Carpeta base para el token store |
| `ECOCLOCK_EMAIL` | _vacío_ | Email por defecto para `run` |
| `ECOCLOCK_USERNAME` | _vacío_ | Username por defecto para `run` |
| `ECOCLOCK_PASSWORD` | _vacío_ | Password por defecto para `run` |

## Tests

```bash
# Unit tests (rápidos, sin red)
pytest client/tests/

# Integration tests (requiere `docker compose up -d` en server/)
ECOCLOCK_RUN_INTEGRATION=1 pytest client/tests/ -m integration
```

## Notas de implementación

- `client/ndvi.py` es un **stub** que devuelve un NDVI aleatorio. En Fase 3
  se reemplaza por el cálculo real sobre imágenes satelitales, sin tocar
  `cli.py`. El hook está en `cmd_run` (línea `output = ndvi.compute(task)`).
- El token se guarda en `$XDG_CONFIG_HOME/ecoclock/token.json` con permisos
  `0600` (best-effort; en FS sin soporte, se omite).
- `cli.py` no requiere Pydantic. Toda la validación se delega al servidor.
