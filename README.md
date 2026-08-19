# Eco'clock Network 🌿                                                                            
                                                                                                    
  > **Plataforma de confianza para donaciones verificadas a organizaciones ecologistas, con donación
de cómputo distribuido.**

# ecoclock-network                                                                                                                                                                                                
                                                                                                                                                                                                                    
 🌱 Cliente y servidor del proyecto [Eco'clock 2026](https://ecoclock.org).                                                                                                                                           
                                                                                                                                                                                                                    
                                                                                                    
  Eco'clock es un proyecto que combina tres pilares:                                                
                                                                                                    
  1. **Whitelist verificada de ONGs** — solo organizaciones auditadas bajo criterios claros pueden  
recibir donaciones a través de la plataforma.                                                       
  2. **Transparencia operativa** — el 95% de cada donación va a las ONGs receptoras, el 5% cubre    
gastos operativos (hosting, dominio, infraestructura), todo públicamente justificado.               
  3. **Donación de cómputo distribuido** — una app estilo BOINC permite a cualquier persona donar   
capacidad de cómputo de su ordenador cuando no lo está usando, para procesar datos ambientales      
(deforestación, arrecifes de coral, etc.).                                                          
                                                                                                    
  ## 🎯 Misión                                                                                      
                                                                                                    
  Crear un **intermediario de confianza** entre personas que quieren contribuir al cuidado del medio
ambiente y organizaciones que realmente hacen el trabajo, eliminando el riesgo de donar a           
"tapaderas" o proyectos opacos.                                                                     
                                                                                                    
  ## 📐 Arquitectura (resumen)                                                                      
                                                                                                    
  ```                                                                                               
  ┌─────────────────┐         ┌─────────────────┐                                                   
  │  Cliente (GUI)  │ ───────▶│  Servidor       │                                                   
  │  PyQt6 / CLI    │  HTTPS  │  FastAPI        │                                                   
  └─────────────────┘         │  + PostgreSQL   │                                                   
                              │  + Redis        │                                                   
                              └────────┬────────┘                                                   
                                       │                                                            
                                       ▼                                                            
                              ┌─────────────────┐                                                   
                              │  Datasets       │                                                   
                              │  - Deforestación│                                                   
                              │  - Arrecifes    │                                                   
                              └─────────────────┘                                                   
  ```                                                                                               
                                                                                                    
  Más detalle en [`docs/architecture.md`](docs/architecture.md).                                    
                                                                                                    
  ## 🛠️ Stack tecnológico                                                                           
                                                                                                    
  ### Servidor                                                                                      
  - **Python 3.13** + **FastAPI** (API REST)                                                        
  - **PostgreSQL** (base de datos principal)                                                        
  - **Redis** (cola de tareas)                                                                      
  - **SQLAlchemy** (ORM) + **Pydantic** (validación)                                                
  - **python-jose** (JWT para autenticación)                                                        
  - **Docker** + **docker-compose** (despliegue)                                                    
                                                                                                    
  ### Cliente                                                                                       
  - **Python 3.13**                                                                                 
  - **PyQt6** (GUI multiplataforma)                                                                 
  - **requests** (HTTP al servidor)                                                                 
  - **NumPy** (cálculo numérico)                                                                    
  - **PyInstaller** (empaquetado a ejecutable)                                                      
                                                                                                    
  ## 📂 Estructura del repositorio                                                                  
                                                                                                    
  ```                                                                                               
  ecoclock-network/                                                                                 
  ├── server/              # API FastAPI + lógica de negocio                                        
  │   ├── app/                                                                                      
  │   │   ├── api/         # Endpoints                                                              
  │   │   ├── core/        # Config, seguridad, JWT                                                 
  │   │   ├── db/          # Modelos SQLAlchemy                                                     
  │   │   ├── schemas/     # Pydantic schemas                                                       
  │   │   └── tasks/       # Lógica de tareas BOINC                                                 
  │   ├── tests/                                                                                    
  │   ├── Dockerfile                                                                                
  │   └── requirements.txt                                                                          
  │                                                                                                 
  ├── client/              # Cliente (CLI y luego GUI)                                              
  │   ├── cli.py           # Cliente de línea de comandos                                           
  │   ├── gui/             # PyQt6 (Fase 2)                                                         
  │   └── requirements.txt                                                                          
  │                                                                                                 
  ├── tasks/               # Definición de tareas dummy/real                                        
  │   └── ndvi/            # Cálculo NDVI (Normalized Difference Vegetation Index)                  
  │                                                                                                 
  ├── docs/                                                                                         
  │   ├── architecture.md                                                                           
  │   ├── ideas.md                                                                                  
  │   └── legal/                                                                                    
  │       └── checklist-asociacion.md                                                               
  │                                                                                                 
  ├── docker-compose.yml   # Levanta servidor + Postgres + Redis                                    
  ├── .gitignore                                                                                    
  ├── LICENSE                                                                                       
  └── README.md                                                                                     
  ```                                                                                               
                                                                                                    
  ## 🚀 Estado del proyecto                                                                         
                                                                                                    
  | Fase | Descripción | Estado |                                                                   
  |------|-------------|--------|                                                                   
  | **Fase 0** | Cimientos: repo, docs, entorno local | 🟢 Hecha |
  | **Fase 1** | Prototipo funcional: servidor + cliente CLI | 🟢 Hecha |
  | **Fase 2** | GUI básica con PyQt6 | 🟢 Hecha (verificada E2E contra server   
real con login → next → submit)|
  | **Fase 3** | Características BOINC: créditos, verificación | 🟢 Hecha (E2E 3/3 verdes, tag v0.3.0-fase3) |
  | **Fase 4** | Beta pública: instaladores, auto-update | 🟢 Hecha (4.4, 4.5, 4.6, 4.7, v0.5.0, v0.5.1) |
  | **v0.5.0** | Release oficial con binarios Linux + Windows reales | 🟢 [v0.5.0](https://github.com/VeldaniGR/ecoclock-network/releases/tag/v0.5.0) |

  ## 📦 Descargas                                                                                                                                                                                                   
                                                                                                                                                                                                                    
  Binarios oficiales (auto-construidos en GitHub Actions):                                                                                                                                                          
                                                                                                                                                                                                                    
  - [ecoclock-cli v0.5.0 · Linux x86_64](https://github.com/VeldaniGR/ecoclock-network/releases/download/v0.5.0/ecoclock-cli-v0.5.0-linux-x86_64)                                                                   
  - [ecoclock-cli v0.5.0 · Windows x86_64 (.exe)](https://github.com/VeldaniGR/ecoclock-network/releases/download/v0.5.0/ecoclock-cli-v0.5.0-windows-x86_64.exe)                                                    
                                                                                                                                                                                                                    
  Todos los releases: https://github.com/VeldaniGR/ecoclock-network/releases
                                                                                                  
  ## 🏃 Cómo correr el proyecto en local                                                            
                                                                                                    
  (Se completará en Fase 1)                                                                         
                                                                                                    
  ```bash                                                                                           
  # Levantar servidor + dependencias                                                                
  docker compose up -d                                                                              
                                                                                                    
  # Verificar que el servidor responde                                                              
  curl http://localhost:8000/health                                                                 
                                                                                                    
  # Correr cliente CLI (descarga y procesa una tarea dummy)                                         
  python client/cli.py                                                                              
  ```
### Binario autocontenido (PyInstaller)                                     
  - [Releases oficiales con binarios Linux + Windows](https://github.com/VeldaniGR/ecoclock-network/releases/tag/v0.5.0) 
 
Para distribuir la CLI sin necesidad de tener Python instalado: 
 
```bash                                                                                                                                                                                                             
  ./scripts/build-linux.sh                                                                                                                                                                                          
```                                                                                                                                                                                                                 
                                                                                                                                                                                                                    
Resultado: dist/ecoclock-cli (~13 MB, standalone).                                                                                                                                                                  
                                                                                                                                                                                                                    
Uso:                                                                                                                                                                                                                
                                                                                                                                                                                                                    
```bash                                                                                                                                                                                                             
  ./dist/ecoclock-cli --base-url https://api.ecoclock.org login                                                                                                                                                     
  ./dist/ecoclock-cli --base-url http://127.0.0.1:8000 next   # server local                                                                                                                                        
  ECOCLOCK_BASE_URL=http://127.0.0.1:8000 ./dist/ecoclock-cli me   # override por env                                                                                                                               
```                                                                                               
  ### Auto-actualización                                                                                                                                                                                            
                                                                                                                                                                                                                    
  El binario puede actualizarse solo:                                                                                                                                                                               
                                                                                                                                                                                                                    
  ```bash                                                                                                                                                                                                           
  ecoclock update         # descarga y reemplaza la versión actual                                                                                                                                                  
  ecoclock update --check  # solo informa: ¿hay release más nuevo?
```                                                                                                    
### 📚 Documentación adicional                                                                     
                                                                                                    
  - [`docs/architecture.md`](docs/architecture.md) — arquitectura detallada *(pendiente de escribir)*
  - [`docs/ideas.md`](docs/ideas.md) — ideas y notas del proyecto *(pendiente de escribir)*
  - [`docs/legal/checklist-asociacion.md`](docs/legal/checklist-asociacion.md) — pasos para constituir la asociación *(pendiente de escribir)*
                                                                                                    
  ## 📜 Licencia                                                                                    
                                                                                                    
  **MIT License** — código abierto: cualquier persona puede auditar y contribuir.                               
                                                                                                    
  Eco'clock apuesta por la transparencia total: el código es público, las cuentas serán públicas,   
las verificaciones de ONGs serán públicas. Confianza mediante apertura.                             
                                                                                                    
  ## 🤝 Contribuir                                                                                  
                                                                                                    
  Por ahora el proyecto está en fase temprana (sólo el fundador + asistente AI). Cuando llegue a beta abierta al público general (post-Fase 4), abriremos issues y PRs.                                                         
                                                                                                    
  ---                                                                                               
                                                                                                    
  **Hecho con 💚 para el planeta.**
