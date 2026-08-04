# Oracle Knowledge Compiler (OKC)
## Product Specification v1.0

**Role:** Lead Product Architect & UX Designer  
**Status:** V1.0 Foundation  

---

## 1. Product Vision
The Oracle Knowledge Compiler (OKC) is a desktop application designed to distill raw AI conversations and documents into structured, cross-referenced, and reusable knowledge. 
It operates under a strict philosophy: **Conversations are immutable source material; knowledge is the product.** 
OKC deterministically parses, indexes, and compiles this raw material into an Intermediate Representation (KnowledgePackage) before exporting it to secondary "second brain" platforms like NotebookLM, Obsidian, or Notion. AI should enrich the knowledge, not replace the deterministic processing pipeline.

## 2. Primary User Goals
- **Aggregate Knowledge:** Seamlessly import conversation histories from diverse AI platforms (ChatGPT, Gemini) into a unified workspace.
- **Process Deterministically:** Run a transparent, predictable pipeline to extract entities, map topics, and index content without hallucination.
- **Maintain Provenance:** Ensure every compiled knowledge artifact retains a strict reference back to the original conversation and prompt.
- **Compile & Export:** Output the knowledge base into structured formats (e.g., topic-centric Markdown files) ready for ingestion by other tools.

## 3. Core Workflow
1. **Initialize Project:** User creates or opens a local OKC Knowledge Project.
2. **Ingest Sources:** User adds raw export files (e.g., ChatGPT JSON) to the project.
3. **Execute Pipeline:** User triggers the compilation process. The UI orchestrates the core engine (`Importers → KnowledgePackage → Analyzers → Compiler → Exporters`).
4. **Monitor Execution:** User observes real-time progress, logs, and stage transitions.
5. **Review Output:** User reviews a post-compilation summary (topics generated, entities found) and accesses the generated output folder.

## 4. Functional Requirements
- **Project Management:** Create, load, and save local workspace configurations.
- **Source Management:** Add, remove, and validate input files (JSON, CSV, etc.) from supported platforms.
- **Pipeline Orchestration:** Trigger the Python-based OKC core engine without embedding business logic in the UI.
- **Real-Time Monitoring:** Display stdout/stderr streams, pipeline stage indicators, and progress metrics during execution.
- **Plugin Discovery:** Dynamically list available Importer, Analyzer, Compiler, and Exporter plugins by querying the Plugin Registry.
- **Data Visualization:** Present post-compilation summaries (e.g., Total Conversations, Top Topics, Entity counts).

## 5. Non-Functional Requirements
- **Stateless UI:** The UI must act strictly as a presentation and orchestration layer; all data mutation happens in the `KnowledgePackage`.
- **Local-First & Private:** All deterministic processing occurs locally. The application must not require an internet connection for its core pipeline.
- **Responsiveness:** The UI must remain entirely unblocked during heavy pipeline execution (e.g., processing 100MB+ JSON exports) using asynchronous background processes.
- **Extensibility:** The UI must dynamically adapt to new plugins without requiring frontend code changes (e.g., rendering settings based on plugin metadata).

## 6. User Personas
- **The "Second Brain" Architect:** A productivity enthusiast with thousands of AI conversations. They want to extract concepts and ideas into their personal knowledge base (NotebookLM/Obsidian) without manually copying and pasting.
- **The Deep Researcher:** A user conducting prolonged research across multiple AI sessions. They need to identify recurring entities (Companies, Technologies, People) and cross-reference them.
- **The Developer / Power User:** Needs to write custom Python `Analyzer` plugins to extract specific proprietary business logic and wants the UI to seamlessly run their custom scripts.

## 7. Navigation Structure
A simple, flat, sidebar-driven navigation model:
- **Dashboard:** High-level project metrics and recent activity.
- **Data Sources:** Management of raw AI exports.
- **Compilation Engine:** The pipeline runner, logs, and progress tracking.
- **Knowledge Explorer:** A read-only browser for the compiled `KnowledgePackage` statistics.
- **Settings:** Plugin toggles, output directories, and application preferences.

## 8. Screen Inventory
1. **Welcome / Project Selection Screen**
2. **Dashboard Screen**
3. **Data Sources Screen**
4. **Pipeline Runner Screen**
5. **Post-Compile Summary Modal / Screen**
6. **Knowledge Explorer Screen**
7. **Settings Screen**

## 9. Screen Responsibilities
- **Welcome Screen:** Recent projects list, "Create New Project", "Open Project".
- **Dashboard:** Displays overall database health. E.g., "528 Conversations in Database", "36 Topics Compiled", "6,787 Entities Extracted".
- **Data Sources:** A drag-and-drop zone for `.json` or `.zip` exports. Lists active files, file sizes, and detected formats (ChatGPT vs Gemini).
- **Pipeline Runner:** Features a prominent "Compile Knowledge Base" button. Once running, displays a visual node-graph or stepper of the pipeline (`Importing... → Analyzing... → Compiling...`) alongside a scrolling terminal window.
- **Knowledge Explorer:** A data table / list view of the generated topics (e.g., `React.md`, `Oracle.md`) and extracted entities. Provides quick links to open the output files in the OS file explorer.
- **Settings:** Checkboxes to enable/disable specific Analyzer plugins. Directory path configurations for `output/markdown`.

## 10. User Journey
1. **Onboarding:** User launches OKC, is greeted by a clean interface, and creates a "Tech Research" project.
2. **Setup:** User drags their `conversations.json` from ChatGPT into the Data Sources screen. The UI validates the file format.
3. **Execution:** User clicks the "Compilation Engine" tab and hits "Run Pipeline". 
4. **Feedback:** A stepper highlights "Importer". A log window shows `"Imported 528 conversations"`. The stepper moves to "Analyzers" and shows `"Extracting entities..."`. 
5. **Success:** The pipeline finishes. A summary card appears: `"Compiled 36 Topic Documents. Total Size: 57MB."`
6. **Handoff:** User clicks "Open Output Folder" and imports the resulting Markdown files directly into NotebookLM.

## 11. Information Architecture
```text
[OKC Workspace / Project]
 │
 ├── Input Sources (Raw data paths)
 │    ├── ChatGPT (JSON)
 │    └── Gemini (JSON/CSV)
 │
 ├── Pipeline Configuration
 │    ├── Active Importers
 │    ├── Active Analyzers (Entity Engine, Index Builder)
 │    └── Active Compilers (Markdown Compiler)
 │
 ├── Execution State (Transient)
 │    ├── Live Logs
 │    └── Progress Metrics
 │
 └── Output / Knowledge Base
      ├── Markdown Topic Files (e.g. Go.md, React.md)
      ├── Entities JSON
      └── Index JSON
```

## 12. Project Lifecycle
- **Draft:** Data sources added, but pipeline has not been run.
- **Processing:** Core engine is actively mutating the `KnowledgePackage`. UI is locked in read-only mode for configuration.
- **Compiled:** Pipeline complete. Outputs are generated and ready for exploration.
- **Stale/Dirty:** New data sources added or plugin configurations changed since the last successful compile, prompting the user to re-run.

## 13. Compile Pipeline UX
- **Visual Nodes:** The pipeline should be visualized horizontally. When a stage is active, it pulses. When complete, it turns green with a checkmark.
- **Log Legibility:** The terminal output should be styled cleanly (monospace font, color-coded for INFO, WARNING, ERROR).
- **Graceful Interruption:** A "Cancel Pipeline" button must safely terminate the background process without corrupting the workspace.

## 14. Error Handling Strategy
- **Validation Before Execution:** Check if input files exist and output directories are writable before starting the Python process.
- **Non-Fatal Plugin Errors:** If a specific Analyzer fails (e.g., Unicode error in print), the UI should highlight that node in yellow/red, capture the stack trace in a collapsible accordion, but (if the core architecture allows) attempt to proceed or halt cleanly.
- **Clear User Guidance:** Translate cryptic Python tracebacks into actionable UI banners (e.g., `"The Markdown Compiler failed. Check file permissions in the output directory."`).

## 15. Settings
- **Global Settings:** Theme (Dark/Light/System), Default Project Directory.
- **Project Settings:**
  - Output folder paths.
  - Threshold configurations (e.g., `MIN_CONVERSATIONS_PER_TOPIC = 2`).
  - Plugin toggle switches (queried dynamically from `PluginRegistry`).

## 16. Future Expansion Considerations
- **AI Configuration:** UI space for entering API keys (OpenAI, Anthropic) for Phase 4+ when AI summarization and relationship mapping plugins are introduced.
- **Plugin Marketplace:** A dedicated tab for downloading new Analyzers and Compilers directly from a community repository.
- **Knowledge Graph UI:** A future screen dedicated to visualizing the Entity/Topic relationships directly within the app before exporting.
