# Oracle Knowledge Platform
# OKC — Oracle Knowledge Compiler & Studio

## Vision

The Oracle Knowledge Platform is an AI-agnostic knowledge compilation and management ecosystem.

It imports conversations and documents from multiple AI systems and other sources, normalizes them into a universal internal format, extracts structured knowledge, builds relationships between concepts, and provides a powerful Workbench for exploring and interacting with your knowledge.

## Quick Start

### Running the Compiler
To process sources and generate a knowledge package:
```bash
python run.py compiler
```

### Running the Workbench
To explore the compiled knowledge:
```bash
python run.py workbench
```

*Note: If no desktop GUI is available (e.g., in Google Cloud Shell), the Workbench will automatically start a web server on port 8080. Use the **Web Preview** feature in Cloud Shell to access it.*

## Supported Inputs

- ChatGPT
- Gemini
- Claude
- Grok
- Copilot
- Perplexity
- Markdown
- PDF
- HTML
- Plain Text

## Feature Set

✅ **Multi-Source Importers:** Normalizes data from diverse platforms.
✅ **Knowledge Engine:** Extracts entities, builds indices, and generates summaries.
✅ **Knowledge Workbench:** A NotebookLM-inspired interface for knowledge exploration.
✅ **Web Fallback:** Full support for Cloud Shell and remote environments.

## Current Version

1.1.0
