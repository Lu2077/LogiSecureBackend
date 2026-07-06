# LogiSecure
Project | AI-AMD

========================================================================================
             HYBRID ARCHITECTURE FLOW DIAGRAM: LOGISECURE AI
========================================================================================

 [ EXTERNAL PUBLIC ENVIRONMENT ]          [ SECURE LOCAL ENVIRONMENT (ON-PREMISE / CLIENT) ]
 ───────────────────────────────          ──────────────────────────────────────────────────

  ┌──────────────────────┐
  │     GLOBAL APIs      │
  │     (Live Data)      │
  ├──────────────────────┤
  │ • OpenSky (Air)      │
  │ • AISstream (Sea)    │
  │ • OSRM/OSM (Land)    │
  │ • Open-Meteo (Weather│
  └──────────┬───────────┘
             │
             │ (REST Requests / WebSockets)
             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │ DIRECTORY: backend/                                                             │
  │                                                                                 │
  │  ┌───────────────────────┐               ┌───────────────────────────────────┐  │
  │  │ api/                  │               │ ai_agents/                        │  │
  │  ├───────────────────────┤               ├───────────────────────────────────┤  │
  │  │ • traffic_air.py      │               │ • database.py                     │  │
  │  │ • traffic_sea.py      │               │   (Internal & CONFIDENTIAL        │  │
  │  │ • traffic_land.py     │               │    corporate database:            │  │
  │  │ • weather.py          │               │    Cargo manifests, SKUs, prices) │  │
  │  └──────────┬────────────┘               └─────────────────┬─────────────────┘  │
  │             │                                              │                    │
  │             └──────────────────────┬───────────────────────┘                    │
  │                                    │                                            │
  │                                    ▼ (Correlates Public Context + Private Data) │
  │                      ┌───────────────────────────┐                              │
  │                      │ ai_agents/router.py       │                              │
  │                      │ (Agentic Orchestrator)    │                              │
  │                      └─────────────┬─────────────┘                              │
  │                                    │                                            │
  │                                    ▼ (Local Hardware Inference Execution)       │
  │             ┌────────────────────────────────────────────────────────┐          │
  │             │ LOCAL AI INFRASTRUCTURE STACK (AMD POWERED)            │          │
  │             ├────────────────────────────────────────────────────────┤          │
  │             │ • Engine: AMD ROCm™ Ecosystem                          │          │
  │             │ • Hardware: AMD Radeon™ / Instinct™ GPUs               │          │
  │             │ • Local Models (models/):                              │          │
  │             │   - Llama 3.1 8B/70B (Quantized GGUF for Text/Reasoning│          │
  │             │   - Llama 3.2 Vision (For Spatial Map/Image Analytics) │          │
  │             └──────────────────────┬─────────────────────────────────┘          │
  │                                    │                                            │
  │                                    ▼ (Serves Secure & Parsed Clean JSON)        │
  │                      ┌───────────────────────────┐                              │
  │                      │ main.py (FastAPI Endpoint)│                              │
  │                      └─────────────┬─────────────┘                              │
  └────────────────────────────────────┼────────────────────────────────────────────┘
                                       │
                                       │ (Secure Local HTTP Traffic / CORS)
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │ DIRECTORY: deploy/ (CONTAINER ORCHESTRATION & DEV-OPS)                          │
  ├─────────────────────────────────────────────────────────────────────────────────┤
  │ • Dockerfile.backend  ──> Builds isolated AMD ROCm runtime execution environment│
  │ • Dockerfile.frontend ──> Packages and compiles production-ready React client   │
  │ • docker-compose.yml  ──> Boots whole multi-container architecture via single   │
  │                           on-premise deployment command: 'docker-compose up'    │
  └────────────────────────────────────┬────────────────────────────────────────────┘
                                       │
                                       │ (Exposed Local Secure Port Tracking)
                                       ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │ DIRECTORY: frontend/ (USER INTERFACE / REACT APP)                               │
  ├─────────────────────────────────────────────────────────────────────────────────┤
  │ • src/components/MapView.jsx   ──> Renders asset markers & dynamic path shapes  │
  │ • src/components/Dashboard.jsx ──> Displays live risk alerts & CEO KPIs metrics │
  └─────────────────────────────────────────────────────────────────────────────────┘

========================================================================================

