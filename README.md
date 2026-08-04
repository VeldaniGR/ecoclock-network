# Eco'clock Network 🌿                                                                            
                                                                                                    
  > **Plataforma de confianza para donaciones verificadas a organizaciones ecologistas, con donación
de cómputo distribuido.**                                                                           
                                                                                                    
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
  | **Fase 4** | Beta pública: instaladores, auto-update | ⏳ Pendiente |                           
                                                                                                    
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
                                                                                                    
  ## 📚 Documentación adicional                                                                     
                                                                                                    
  - [`docs/architecture.md`](docs/architecture.md) — arquitectura detallada                         
  - [`docs/ideas.md`](docs/ideas.md) — ideas y notas del proyecto                                   
  - [`docs/legal/checklist-asociacion.md`](docs/legal/checklist-asociacion.md) — pasos para         
constituir la asociación                                                                            
                                                                                                    
  ## 📜 Licencia                                                                                    
                                                                                                    
  **MIT License** — código abierto: cualquier persona puede auditar y contribuir.                               
                                                                                                    
  Eco'clock apuesta por la transparencia total: el código es público, las cuentas serán públicas,   
las verificaciones de ONGs serán públicas. Confianza mediante apertura.                             
                                                                                                    
  ## 🤝 Contribuir                                                                                  
                                                                                                    
  Por ahora el proyecto está en fase temprana (sólo el fundador + asistente AI). Cuando llegue a beta    
pública (Fase 3-4), abriremos issues y PRs.                                                         
                                                                                                    
  ---                                                                                               
                                                                                                    
  **Hecho con 💚 para el planeta.**
