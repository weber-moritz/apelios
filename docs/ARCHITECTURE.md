# Apelios Architecture Blueprint
**Version:** 1.2  
**Status:** Active Source of Truth  
**Architecture Style:** Micro-Kernel / Decoupled Event-Driven Pipeline

## 1. System Vision
This project utilizes a **Micro-Kernel Architecture** centered on a **Decoupled Event-Driven Pipeline**. The **Main Orchestrator** manages the system lifecycle and implements **Dependency Injection** to provide a shared **Event Broker** instance to all modules.

Input Modules (Hardware/Virtual) act as adapters that capture raw signals and publish them as **Normalized Input Events** (0.0 ... 1.0) to the broker. The **Mapping Middleware** subscribes to these events, performing **Data Transformation** (sensitivity, inversion, and remapping) based on a dynamic **JSON Mapping Table**.

Once processed, the broker **dispatches** the resulting **Control Commands** to the **Output Layer**, ensuring a clear **Separation of Concerns** between hardware interaction and domain logic.

---

## 2. Structural Diagram

```mermaid
graph TD
    %% Define Styles
    classDef orch fill:#b71c1c,stroke:#d32f2f,color:#fff,font-weight:bold;
    classDef input fill:#0d47a1,stroke:#1976d2,color:#fff;
    classDef broker fill:#4a148c,stroke:#ab47bc,color:#fff,font-weight:bold;
    classDef logic fill:#1b5e20,stroke:#66bb6a,color:#fff;
    classDef config fill:#e65100,stroke:#ff9800,color:#fff;
    classDef output fill:#222,stroke:#444,color:#777,stroke-dasharray: 5 5;
    classDef interface fill:none,stroke:#888,color:#aaa,stroke-dasharray: 5 5;

    subgraph SYSTEM ORCHESTRATION [SYSTEM ORCHESTRATION - Lifecycle Manager]
        Orch[Main Orchestrator<br>Service Manager]:::orch
    end

    subgraph COMMUNICATION [COMMUNICATION - Broker]
        Broker((Event Broker<br>Pub/Sub Hub)):::broker
    end

    subgraph INPUT LAYER [INPUT LAYER - I/O Adapters]
        HW[Hardware<br>Steam Deck Driver]:::input
        GUI[Virtual<br>GUI Input Module]:::input
        BaseI[BaseInput Class<br>Interface Contract]:::interface
        BaseI -.-> HW
        BaseI -.-> GUI
    end

    subgraph LOGIC LAYER [LOGIC LAYER - Middleware]
        Map[Mapping Middleware<br>Transformation]:::logic
        JSON[(Mapping Table<br>JSON Config)]:::config
        JSON -- Table Lookup --> Map
    end

    subgraph OUTPUT LAYER [OUTPUT LAYER - Out of Scope]
        Out[Output Adapter<br>e.g. ArtNet Mock]:::output
    end

    %% Dependency Injection Flow
    Orch -. Inject Broker Instance .-> HW
    Orch -. Inject Broker Instance .-> Map
    Orch -. Inject Broker Instance .-> Out

    %% Signal Flow
    HW -- InputEvent --> Broker
    GUI -- InputEvent --> Broker
    Broker -- Raw Notify --> Map
    Map -- Control Command --> Broker
    Broker -. Control Command .-> Out
```

---

## 3. Layer Definitions

### A. System Orchestration (Lifecycle Manager)
* **Main Orchestrator:** The micro-kernel of the application. It is responsible for booting the network server, instantiating the Event Broker client, and injecting that shared client into the Input, Logic, and Output layers.

### B. Communication (Event Broker)
* **Pub/Sub Hub:** The absolute center of the data pipeline. Modules never talk to each other directly; they only communicate via Pub/Sub topics on the broker (e.g., NATS).

### C. Input Layer (I/O Adapters)
* **Responsibility:** Capture hardware/virtual inputs, normalize them to a standard scale (0.0 to 1.0) or standard delta/rate intents, and publish them.
* **Interface Contract:** All inputs must inherit from `BaseInput` to ensure they expose standard startup/shutdown and publishing methods.

#### Input Event Contract (Current)
* **Payload:** `{"source": str, "value": float}`
* **Type Resolution:** Input intent (`absolute`, `delta`, `rate`) is resolved in the Middleware from the mapping profile, not carried in adapter payloads.
* **Timing Model:** Frame `dt` is provided by the Main Orchestrator heartbeat (`tick` loop), not derived from event timestamps.

### D. Logic Layer (Middleware)
* **Mapping Middleware:** Subscribes to raw inputs. Uses the `process_frame()` loop to accumulate deltas, apply rates over time, and calculate final target states.
* **JSON Mapping Table:** An injected configuration file that dictates which input maps to which output, alongside settings like sensitivity and merge strategies.

### E. Output Layer (Out of Scope)
* **Responsibility:** Subscribes to the final `Control Commands` from the Broker and translates them into physical protocols (like ArtNet/DMX). 

---

## 4. Key Architectural Decisions (ADRs)
