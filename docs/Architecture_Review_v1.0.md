# Oracle Knowledge Compiler (OKC)
## Architecture Review v1.0

**Role:** Senior Software Architect  
**Status:** Review Complete  

---

## Executive Summary
The PySide6 UI foundation successfully establishes a decoupled shell structure separating presentation from business logic via Services. However, before the real compiler core is connected, critical architectural gaps regarding concurrency, inversion of control, and data contracts must be resolved to ensure long-term stability and prevent UI locking.

---

## 1. Concurrency and Async Readiness
**Finding:** The current architecture executes service methods synchronously on the main thread (e.g., `pipeline_service.run_pipeline()`). The real compiler processes tens of megabytes of JSON and generates hundreds of Markdown files.
**Impact:** Running this synchronously will completely lock the PySide6 UI thread, triggering OS "Application Not Responding" dialogues. 
- **[CRITICAL] Background Workers:** Implement a thread pool (e.g., `QThreadPool` and `QRunnable` or native `QThread`) for all heavy service calls, particularly `PipelineService.run_pipeline()` and `ImportService.add_import_files()`.
- **[CRITICAL] Thread-Safe State:** `KnowledgePackage` will be accessed by the background compiler thread. We must ensure thread safety (locks or isolated copies) if the UI attempts to read the package (e.g., `KnowledgeExplorer`) while the pipeline runs.

## 2. Dependency Injection & Coupling
**Finding:** `MainController` currently hard-instantiates all services (`self.project_service = ProjectService()`). Views directly depend on the monolithic `MainController`.
**Impact:** This violates the Dependency Inversion Principle, making unit testing services difficult and coupling the entire application to concrete implementations.
- **[RECOMMENDED] Dependency Injection Container:** Introduce a lightweight DI mechanism (or factory pattern) in `main.py` to instantiate and inject services into controllers.
- **[RECOMMENDED] Controller Splitting:** The `MainController` is a God Object. Split it into domain-specific controllers (`ProjectController`, `PipelineController`, `KnowledgeController`) injected only into the views that need them.

## 3. Communication & Event Streaming
**Finding:** The current compiler relies heavily on standard `print()` statements for transparency. The UI requires real-time progress updates. 
**Impact:** Standard `return` statements from services are insufficient for streaming logs or progress percentages back to the `PipelineRunnerView`.
- **[CRITICAL] Event Bus / Qt Signals:** The `PipelineService` must expose `QSignal`s (e.g., `log_emitted`, `progress_updated`, `stage_changed`). The core compiler's print statements must be intercepted via a custom `logging` handler and piped into these signals.

## 4. Service Contracts & Data Transfer Objects (DTOs)
**Finding:** Services currently return primitive dictionaries (e.g., `{"status": "Success"}`). 
**Impact:** Weakly typed data boundaries will lead to runtime errors when the UI expects a specific key that a plugin doesn't provide.
- **[RECOMMENDED] Domain Models / DTOs:** Define strict Pydantic models or Python `@dataclass` objects for the service boundaries (e.g., `ProjectInfo`, `PipelineResult`, `PluginManifest`). The UI must never receive unstructured dicts.
- **[CRITICAL] KnowledgePackage Integration:** Ensure the `KnowledgeService` strictly returns read-only views or copies of the `KnowledgePackage` data to prevent accidental UI mutations.

## 5. UI Separation of Concerns
**Finding:** UI views currently execute logic directly inside event handlers (e.g., `SettingsView` loops over plugins and calls `self.controller.plugin_service.toggle_plugin()`).
**Impact:** The View is performing business orchestration, violating MVC/MVVM.
- **[RECOMMENDED] Delegate to Controllers:** Views should purely emit signals (e.g., `self.plugin_toggled.emit(name, state)`). The controller handles the signal, invokes the service, and updates the View's model.

## 6. Error Handling Strategy
**Finding:** There is no global error boundary in the PySide6 setup.
**Impact:** Unhandled exceptions in a plugin or file IO will crash the entire application to the desktop.
- **[CRITICAL] Global Exception Handler:** Override `sys.excepthook` to catch unhandled exceptions, log them safely, and display a user-friendly error dialog.
- **[RECOMMENDED] Service Result Pattern:** Services should return a `Result` monad or tuple (e.g., `success, data, error_message`) rather than raising exceptions across the thread boundary to the UI.

## 7. Future Multi-Source Integration
**Finding:** `import_service.add_import_files()` currently accepts a simple list of paths.
**Impact:** When we add Claude, Markdown, and PDFs, the system won't know which importer to use.
- **[NICE TO HAVE] Importer Routing Logic:** Enhance the `ImportService` to analyze file MIME types and headers (or ask the user via the UI) to correctly route the file to the corresponding `Importer` plugin (ChatGPT vs Gemini).

## 8. Folder Structure Improvements
**Finding:** The `/ui` folder mixes logic and presentation somewhat broadly.
- **[NICE TO HAVE] Feature-Based Grouping:** Instead of `/windows` and `/dialogs`, consider organizing by feature: `src/ui/dashboard/`, `src/ui/pipeline/`, etc., keeping the specific controllers, views, and view-models co-located for better maintainability.

---

## Conclusion
The shell is conceptually sound but strictly requires **threading (QThread/QRunnable)**, **Qt Signals for log streaming**, and a **Dependency Injection** refactor before we wire the core `run.py` engine to the UI. Proceeding without these will result in an unresponsive, tightly coupled desktop application.
