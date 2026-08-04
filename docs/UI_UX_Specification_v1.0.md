# Oracle Knowledge Compiler (OKC) 
## UI/UX Design Specification v1.0

**Role:** Lead UX Designer  
**Status:** V1.0 Foundation  

---

## 1. Application Overview

### 1.1 Navigation Hierarchy & Flow
The application uses a persistent left-hand Sidebar Navigation to move between the primary contexts. 
- **Global Sidebar:** Project Switcher (top), Dashboard, Import, Pipeline Runner, Knowledge Explorer, Search, Export, Settings, Plugin Manager.
- **Top Bar:** Contextual actions based on the current screen (e.g., Breadcrumbs, Window Controls, Status Indicator showing "Idle" or "Processing").

### 1.2 Responsive Behavior
- **Desktop Standard (1440x900+):** Full Sidebar with labels, multi-column layouts fully expanded.
- **Desktop Small (1024x768):** Sidebar collapses to icon-only. Data tables compress non-essential columns behind a "..." overflow menu.
- **Minimum Window Size:** The UI prevents resizing below 800x600 to ensure complex pipeline and explorer views remain legible.

### 1.3 Thin Orchestration Principle
The UI contains **zero business logic**. It strictly sends configurations to the underlying Python engine, reads the resulting `KnowledgePackage` state, and displays it. Actions in the UI map directly to triggering Importers, Analyzers, Compilers, and Exporters.

---

## 2. Screen Specifications

### 2.1 Project Manager
- **Purpose:** Allow users to create new knowledge spaces or switch between existing local workspaces.
- **Layout:** Centered modal/overlay upon startup, or full-screen view when selected from the top of the sidebar.
- **Components:**
  - **Cards:** Grid of recent projects showing Project Name, Last Compiled Date, Total Conversations, and File Path.
  - **Buttons:** Primary "Create New Project" button, Secondary "Browse Local Project" button.
- **Empty State:** Large placeholder graphic with "You don't have any knowledge projects yet. Create one to start compiling your second brain."
- **User Interactions:** Clicking a project card instantly loads the project into the global context and navigates to the Dashboard.

### 2.2 Dashboard
- **Purpose:** Provide a high-level overview of the currently active project's health and statistics.
- **Layout:** Standard grid layout. Top row for high-level KPIs, bottom row split into two sections (Recent Imports & Top Topics).
- **Components:**
  - **KPI Cards:** Total Conversations, Total Messages, Extracted Entities, Compiled Topics.
  - **Tables:** "Recent Imports" (Filename, Date, Status). "Top Topics" (Topic Name, Conversation Count, File Size).
- **Empty State:** "No data compiled yet. Go to the Import Wizard to begin." with a primary call-to-action button linking to Import.
- **Loading State:** Skeleton loaders for KPI cards while parsing the local `KnowledgePackage`.

### 2.3 Import Wizard
- **Purpose:** Manage the ingestion of raw AI exports into the project. Trigger Importer plugins.
- **Layout:** Split view. Left side: Dropzone and File Selection. Right side: List of staged and processed files.
- **Components:**
  - **Dropzone:** Large dashed-border area reading "Drag & Drop ChatGPT or Gemini exports here (.json, .zip, .csv)".
  - **File List (Table):** Filename, Size, Detected Type (ChatGPT/Gemini), Status (Pending/Imported).
  - **Buttons:** Primary "Add Files" (opens OS dialog), Secondary "Clear List".
- **Status Indicators:** Icons next to files (Gray Circle = Pending, Spinning Circle = Parsing, Green Check = Ready, Red Exclamation = Invalid format).
- **Error States:** Toast notification if an unsupported file type is dropped.

### 2.4 Pipeline Runner
- **Purpose:** The core engine interface. Orchestrates the flow from Importer to Exporter and provides real-time transparency.
- **Layout:** Top half: Visual Pipeline Stepper. Bottom half: Real-time Terminal/Log Viewer.
- **Components:**
  - **Pipeline Stepper:** Visual nodes connected by lines: `Importers → KnowledgePackage → Analyzers → Compiler → Exporters`.
  - **Action Bar:** Giant Primary "Run Pipeline" button. Secondary "Cancel" button (disabled when idle).
  - **Terminal Window:** Dark background, monospace text area displaying `stdout`/`stderr` from the Python engine.
- **User Interactions:** Clicking "Run Pipeline" disables the button, changes "Cancel" to active, and begins pulsing the active stage in the stepper.
- **Loading/Running State:** Active node pulses. Log window auto-scrolls to the bottom.
- **Error State:** If a plugin fails, the stepper halts, the failing node turns red, and the terminal highlights the exception block in red. A dialog pops up: "Pipeline Halted: Review logs for details."

### 2.5 Knowledge Explorer
- **Purpose:** Browse the structured output within the `KnowledgePackage` (Topics, Entities, Relationships).
- **Layout:** Two-pane layout. Left pane: Tree view / Category list. Right pane: Data table of the selected category.
- **Components:**
  - **Sidebar Tree:** Categories like "Topics", "Entities (People, Companies, Technologies)", "Index".
  - **Data Table:** Sortable columns based on selection (e.g., Topic Name, Source Conversations, Entity Count).
  - **Buttons:** "Open in OS Explorer" to view the generated Markdown files.
- **Interactions:** Clicking a row in the data table navigates to the *Knowledge Object Viewer*.
- **Empty State:** "Pipeline has not generated any knowledge yet. Run the Pipeline first."

### 2.6 Knowledge Object Viewer
- **Purpose:** Deep dive into a specific entity or compiled topic without leaving the app.
- **Layout:** Master-Detail or full-screen document view. Top header with metadata, main body with content.
- **Components:**
  - **Header:** Object Name (e.g., "Firebase (Technology)"), Total References, First Seen Date.
  - **Body (Markdown Render):** If viewing a Topic, renders the Markdown preview of the compiled knowledge document.
  - **Cards / List:** If viewing an Entity, lists all conversations where this entity appeared.
- **Keyboard Shortcuts:** `Esc` or `Backspace` to return to the Knowledge Explorer.

### 2.7 Search
- **Purpose:** Global, fast text search across all compiled knowledge and raw indexed conversations.
- **Layout:** Command-Palette style overlay (Cmd+K / Ctrl+K) or a dedicated full-screen search view.
- **Components:**
  - **Search Input:** Large, autofocus input field.
  - **Filter Chips:** "All", "Topics", "Entities", "Raw Conversations".
  - **Results List:** Highlighted search terms in context (snippet view).
- **Empty State:** "Type to search your second brain."
- **User Interactions:** Up/Down arrows to navigate results, `Enter` to open the selected Knowledge Object Viewer.

### 2.8 Export Manager
- **Purpose:** Orchestrate Exporter plugins to package the knowledge base for secondary tools.
- **Layout:** Card grid of available Exporters.
- **Components:**
  - **Exporter Cards:** "Export to NotebookLM (Markdown)", "Export to Obsidian", "Export Raw JSON".
  - **Dialogs:** Clicking a card opens a dialog with specific configuration options for that exporter (e.g., output directory path).
- **Status Indicators:** Progress bar inside the dialog when exporting.
- **Success State:** "Export Complete. [Open Folder] button."

### 2.9 Settings
- **Purpose:** Application-level and Project-level preferences.
- **Layout:** Left tab list (General, Appearance, Project Paths, Advanced), Right content area.
- **Components:**
  - **Form Inputs:** Text inputs for directory paths, dropdowns for Theme (Light/Dark).
  - **Toggles:** Advanced developer settings (e.g., "Show debug logs in Pipeline Runner").
- **Interactions:** Auto-saves on blur/toggle change. Toast notification confirms "Settings saved".

### 2.10 Plugin Manager
- **Purpose:** View, enable, and configure the plugins registered in the `PluginRegistry`.
- **Layout:** Grouped lists by plugin type (Importers, Analyzers, Compilers, Exporters).
- **Components:**
  - **List Items:** Plugin Name, Version, Author, Description, and a Toggle Switch (Enable/Disable).
  - **Badges:** Indicates plugin health or compatibility warnings.
- **User Interactions:** Toggling a plugin off removes it from the Pipeline Runner stepper flow. The UI dynamically queries the backend registry to populate this screen.

---

## 3. Keyboard Shortcuts (Global)
- **Ctrl/Cmd + P:** Open Project Manager
- **Ctrl/Cmd + K:** Open Global Search
- **Ctrl/Cmd + R:** Jump to Pipeline Runner and initiate run
- **Ctrl/Cmd + ,:** Open Settings
- **Esc:** Close active modal / return to previous screen
