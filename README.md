# Wardly Voice AI Clinical Assistant

## Project Overview

The **Wardly Voice AI Clinical Assistant** is a specialized Voice AI Agent engineered for high-stakes clinical environments. Integrating advanced Python-based AI logic with a high-performance JavaScript frontend, the system enables reactive visualization—providing clinicians with real-time, hands-free data interaction and visual feedback during patient care workflows.

## Video Demonstration

> **[Loom Link](https://www.loom.com/share/d4880483d45144e3afa71b96dbcef4b8)**
> 
> This video demonstrates the seamless, real-time interaction between the voice agent and the clinical dashboard, illustrating how vocal commands trigger instantaneous visual state changes.

## System Architecture

### Architecture Flow

The system utilizes a decoupled architecture where the server acts as a message broker between the AI inference logic and the user interface. The interaction lifecycle follows this sequence:

1. **Voice Input**: The system captures audio from the clinical environment.
2. **Python Agent Logic**: The `agent.py` module processes the audio to perform intent recognition and clinical logic execution. Uses Pydantic for strict schemas that prevent hallucination.
3. **Server Broadcast**: The Python backend transmits state updates and parsed data to the `server.py` component, which functions as a bridge to the frontend.
4. **JS Reactive Update**: The JavaScript-based web dashboard receives these signals and reactively updates the visualization layer to reflect the current clinical context.

### Tech Stack

The project's composition reflects a heavyweight visualization dashboard controlled by a streamlined AI agent.

| Component | Technology |
| :--- | :--- |
| **Frontend** | JavaScript |
| **Backend/Agent** | Python, Pydantic, Livekit |
| **Package Management** | `uv` (Python) |

## Getting Started

### Prerequisites

* **Python**: Refer to `.python-version` for the required version.
* **uv**: The fast Python package installer and resolver.

### Installation

1. **Clone the Repository**: Clone the project files to your local machine.
2. **Install Agent Dependencies**: Use `uv` to synchronize the Python environment based on the lockfile.
3. **Install Web Dependencies**: Navigate to the `web` directory and install the required JavaScript packages.

## Execution Guide

To initialize the clinical assistant, you must run the backend, the communication bridge, and the frontend simultaneously. Open three separate terminals:

### Terminal 1: The Agent

Initialize the core AI logic:

```bash
cd agent
python agent.py
```
### Terminal 2: The Server
Launch the server to facilitate real-time communication between the agent and the dashboard:


```bash
cd agent
python server.py
```

### Terminal 3: The Web Frontend
Launch the development server to view the reactive visualization dashboard:

```bash
cd web
python -m http.server 8000
```

## License & Contributions
### License
This project is currently released for Demonstration Purposes Only. All rights reserved unless otherwise stated in future releases.
