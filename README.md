# LogiSecure


Agent-based and on-premise control hub for the automation, optimization, and real-time visibility of global logistics.

# How it Works

## System Architecture & Data Pipeline

The system ingests and processes global supply chain and transportation APIs in real-time. Below is the end-to-end execution pipeline:

### 1. Global Supply Chain Monitoring
The system continuously ingests data from open-source and global APIs (GNSS/GPS, Baidu Maps, aviation, and maritime transponders) to map live transit routes.

### 2. Incident Detection
An external global anomaly is registered (e.g., a port strike, extreme weather/typhoons, or geopolitical conflicts). LogiSecure immediately triggers a system-wide alert.

### 3. Local Asset Correlation
The system cross-references the incident's geographic coordinates with the secure, on-premise database to identify exactly which confidential shipments, cargo manifests, and corporate assets are impacted.

### 4. Local AMD-Powered Inference
Using the AMD ROCm stack and local GPU/NPU hardware, an internal LLM analyzes the disruption data completely offline. It simulates operational impact, calculates alternative multi-modal routes, and projects financial metrics.

### 5. Agentic Autonomous Execution (vs. Fixed Workflows)
Unlike rigid, rules-based workflows (`if/else` pipelines), LogiSecure operates as an autonomous agentic loop. It dynamically evaluates non-linear variables to execute a proactive response plan:
* **Automated Dispatch:** Pushes optimized GPS coordinates to external transit operators via API.
* **Human-in-the-loop:** Generates a pre-drafted client communication alert, staged and ready for final engineer/operator approval.

```mermaid
graph TD
    %% Definición de Estilos
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;
    classDef secure fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef agentic fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;

    %% Paso 1: Monitoreo
    subgraph Ingesta de Datos
        A[Global APIs: GNSS, GPS, Maritime, Aviation] --> B(Live Transit Mapping)
    end
    class A external;

    %% Paso 2: Detección
    B --> C{¿Se detecta anomalía?<br><i>Huelgas, clima, conflictos</i>}
    
    %% Paso 3: Correlación Local
    C -- Sí --> D[Trigger Alert]
    D --> E[Query On-Premise Local DB]
    subgraph Zona Segura (Confidencial)
        E --> F[Identify Impacted Assets & Cargo]
        
        %% Paso 4: Inferencia AMD
        F --> G[Local Inference Engine<br><b>AMD ROCm Stack + LLM</b>]
        G --> H[Simulate Impact & Multi-modal Routes]
    end
    class E,F,G,H secure;

    %% Paso 5: Ejecución Agente vs Workflow
    H --> I{Tomar Decisión<br><i>Loop Agente Autónomo</i>}
    
    I -->|Action 1| J[API Push: Updated GPS to External Operators]
    I -->|Action 2| K[Stage Draft: Client Communication Alert]
    
    K --> L[Human-in-the-Loop Approval]
    
    class I,J,K agentic;
    class J external;
```

## Technical Prerequisites & Local Setup

To run LogiSecure AI's autonomous inference loop locally, your workstation or on-premise server must satisfy the following hardware and software stack.

### 1. Hardware Requirements
* **GPU/Accelerator:** AMD Instinct Series (MI200, MI300, or newer) or Radeon RX 7000/9000 Series (e.g., RX 7900 XTX) with dedicated VRAM for LLM execution.
* **CPU:** x86_64 architecture (AVX2 instructions highly recommended).
* **Firmware:** **Secure Boot must be disabled** or configured with custom MOK keys to allow the AMD kernel-mode module to load. 
* **BIOS Note:** Integrated Graphics (IGP) must be **disabled** in the BIOS to prevent runtime initialization crashes with ROCm.

### 2. Host Operating System & Drivers
* **OS:** Ubuntu 24.04 LTS / 22.04 LTS or RHEL 9.x (Linux Kernel 5.15 or newer).
* **Kernel Driver:** Install the official AMD kernel-mode driver (`amdgpu-dkms`).
* **ROCm Stack:** **ROCm v7.1 or v7.2** (verify via `rocminfo`).

### 3. GPU Permissions Setup (Crucial)
By default, non-root users cannot access the GPU hardware compute layers. Run the following command on your host machine to add your local user to the video and render groups:
```bash
sudo usermod -a -G video,render \$USER
# Log out and log back in for changes to take effect
```

### 4. Containerized Environment (Docker)
We leverage containerization via Docker to isolate dependencies. To expose the host's AMD compute layers inside the container, you must use the **AMD Container Runtime Toolkit** or map the device files explicitly.

#### Option A: Docker CLI Passthrough
```bash
docker run -it --network=host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --security-opt seccomp=unconfined \
  rocm/rocm-terminal:latest
```

#### Option B: Docker Compose (Recommended for Devs)
Add the following device mapping block into your local `docker-compose.yml`:
```yaml
services:
  logisecure-agent:
    image: rocm/rocm-terminal:latest
    network_mode: "host"
    devices:
      - "/dev/kfd:/dev/kfd"
      - "/dev/dri:/dev/dri"
    security_opt:
      - "seccomp=unconfined"
    volumes:
      - ./:/workspace
```

### 5. AI Engine & Frameworks
* **PyTorch:** Must use the explicit ROCm-compiled wheel (not the standard CUDA/CPU variant).
* **Local Ingestion:** Ensure your outbound firewall allows traffic for open-source aviation/maritime transponder APIs on ports specified in the network configuration.

