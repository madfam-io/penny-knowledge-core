# AGENTS.md

> **MISSION:** You are an expert Python engineer working on the **PENNY Knowledge Core**. This system orchestrates a fleet of headless "AnyType" nodes to serve as the long-term memory for an Agentic AI.

## 🗺️ Project Ontology & Map

This project is NOT a standard web app. It is a **multi-tenant bridge** between HTTP clients (MCP) and a P2P encrypted network (AnyType).

* **`src/server/`**: The FastAPI / MCP server. The "Brain".
* **`src/router/`**: Logic for routing requests to specific containers based on `profile_id`.
* **`src/tools/`**: The "skills" exposed to the LLM (e.g., `create_object`, `ensure_schema`).
* **`docker/`**: Configurations for the headless AnyType "Heart" nodes.

## 🏗️ Architectural Constraints (READ CAREFULLY)

1. **State Management**:
* The MCP Server is **stateless**. Do not store conversation history here.
* The AnyType Heart containers are **stateful**. They hold the encrypted DB.
* *Rule:* Never try to restart a Heart container during a transaction.


2. **Concurrency**:
* AnyType's gRPC API is single-threaded per account.
* *Rule:* If you add a batch import tool, you MUST implement a queue/delay (e.g., 50ms sleep) between writes to avoid locking the local DB.


3. **The "Hydra" Pattern**:
* We do not have *one* API URL. We have a *map* of URLs.
* `SessionContext` determines which URL to hit.
* *Rule:* All tools must accept a `profile_name` argument (defaulting to 'personal') to look up the correct target URL in `FLEET_CONFIG`.



## 💻 Coding Conventions

* **Language**: Python 3.11+
* **Type Safety**: STRICT. Use `pydantic` for all Tool Inputs/Outputs.
* **Style**: Google Docstrings.
* **Async**: All I/O (especially HTTP calls to the hearts) must be `async/await`.

## 🧪 Testing Guidelines

**WARNING:** Do not run tests against your live/production AnyType account.

1. **Integration Tests**:
* Requires `docker-compose up -d` to be running.
* Use the "Burner" profile defined in `.env.test`.


2. **Mocking**:
* When writing unit tests for `src/tools/`, MOCK the HTTP response from the Heart. Do not make actual network calls unless it is an integration test.



## 🛠️ Common Tasks (How-To)

**Task: Adding a New MCP Tool**

1. Define the Input Schema in `src/schemas.py` using Pydantic.
2. Implement logic in `src/tools/my_new_tool.py`.
3. Register the tool in `src/server/main.py`.
4. *Crucial:* Add a "Reasoning Trace" log. The tool should print what it is doing so the user sees it in the Chainlit UI.

**Task: Updating the Schema Architect**

* The logic for `ensure_schema` is complex. It involves diffing a JSON manifest against the live graph.
* *Rule:* Always fetch the existing `Type` list before trying to create a new one. Duplicate Type names are allowed by AnyType but confusing for Agents. We must enforce uniqueness by Name.

## 🚨 Security Red Lines

1. **Mnemonics**: NEVER log the `MNEMONIC` or `AUTH_TOKEN`.
2. **Egress**: The `anytype-heart` containers should only talk to the official AnySync nodes.
3. **Validation**: All text inputs destined for `create_object` must be sanitized to prevent injection attacks (though AnyType is fairly resilient, text fields should be treated as untrusted).
