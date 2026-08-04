# Oracle Knowledge Compiler (OKC) - Processing Pipeline

This document details the complete processing pipeline of the Oracle Knowledge Compiler (OKC). The pipeline is a deterministic sequence of stages designed to ingest, validate, analyze, and synthesize knowledge from diverse AI systems and text inputs.

---

## 1. Import

**Purpose:**  
To ingest raw data from external sources and parse it into an initial, unvalidated, memory-resident format.

**Input:**  
Raw data sources such as API endpoints, JSON exports, CSV files, PDFs, Markdown documents, or HTML files.

**Output:**  
Raw, source-specific data objects (e.g., `RawChatGPTExport`, `RawMarkdownDocument`).

**Responsibilities:**  
- Interface with external systems or file systems to read the data.
- Handle authentication and pagination for API sources.
- Parse raw byte streams into structured or semi-structured data formats (e.g., JSON parsing).
- Log the provenance of the data (source URI, timestamp, source type).

**Failure Conditions:**  
- Source unavailable (network errors, file not found).
- Invalid credentials or permissions.
- Unparseable input formats (e.g., malformed JSON, corrupted PDF).

---

## 2. Validation

**Purpose:**  
To ensure the imported raw data adheres to the expected source-specific schema before any transformation occurs.

**Input:**  
Raw, source-specific data objects from the Import stage.

**Output:**  
Validated, source-specific data objects.

**Responsibilities:**  
- Perform schema validation against expected structures.
- Identify missing mandatory fields or unexpected data types.
- Discard or quarantine corrupted records.
- Generate a validation report detailing structural anomalies.

**Failure Conditions:**  
- Schema mismatch (e.g., an API changed its response format).
- Missing critical fields (e.g., a message without a timestamp or author).
- Invalid data types that cannot be safely cast.

---

## 3. Normalization

**Purpose:**  
To map validated, source-specific data into OKC's universal internal data model (e.g., `Conversation` and `Message`).

**Input:**  
Validated, source-specific data objects.

**Output:**  
Normalized `Conversation` and `Message` objects.

**Responsibilities:**  
- Map disparate field names to standard OKC fields (e.g., mapping `create_time` and `timestamp` to `created_at`).
- Standardize role designations (e.g., mapping "assistant", "bot", and "model" to `Role.AI`).
- Extract and standardize metadata (tags, conversation titles).
- Sanitize and format text content (e.g., standardizing markdown, stripping unwanted HTML).

**Failure Conditions:**  
- Unmappable critical fields.
- Unsupported role types or data structures.
- Fatal text encoding errors during sanitization.

---

## 4. Inventory

**Purpose:**  
To register the normalized data into a central tracking system, ensuring every piece of data is uniquely identifiable and its lineage is preserved.

**Input:**  
Normalized `Conversation` and `Message` objects.

**Output:**  
Inventoried items with assigned Universal Unique Identifiers (UUIDs) and persisted lineage metadata.

**Responsibilities:**  
- Generate deterministic or random UUIDs for new conversations and messages.
- Persist metadata regarding the item's origin, import batch, and normalization timestamp.
- Detect and flag exact duplicates that have already been imported.
- Write records to a central inventory database or ledger.

**Failure Conditions:**  
- Database connection or write failures.
- ID collisions (if using deterministic hashing).
- Metadata persistence failures.

---

## 5. Indexing

**Purpose:**  
To create search indices over the text and metadata, enabling rapid retrieval during downstream AI analysis and user queries.

**Input:**  
Inventoried `Conversation` and `Message` objects.

**Output:**  
Searchable indices (e.g., BM25 text index, vector embeddings).

**Responsibilities:**  
- Tokenize and stem text content.
- Generate vector embeddings for semantic search (optional at this stage, depending on architecture).
- Build reverse indices for keywords and metadata tags.
- Update the search backend (e.g., Elasticsearch, local SQLite FTS, vector database).

**Failure Conditions:**  
- Search backend unavailability.
- Out of memory (OOM) errors during bulk indexing.
- Embedding generation API limits or timeouts.

---

## 6. Analysis

**Purpose:**  
To extract deeper meaning, entities, intents, and core concepts from the text using NLP and AI models.

**Input:**  
Inventoried and Indexed `Conversation` and `Message` objects.

**Output:**  
Enriched objects containing extracted entities, themes, sentiment, and concept tags.

**Responsibilities:**  
- Run Named Entity Recognition (NER) to identify people, places, tools, and topics.
- Perform intent classification and sentiment analysis.
- Extract summary keywords and domain classifications.
- Append these findings as structured metadata to the messages and conversations.

**Failure Conditions:**  
- NLP/AI service timeouts or rate limits.
- Context window overflow for excessively large messages.
- Non-deterministic model failures producing unparseable analytical outputs.

---

## 7. Clustering

**Purpose:**  
To group conceptually related messages and conversations together, breaking down chronological silos into thematic clusters.

**Input:**  
Enriched messages and conversations from the Analysis stage.

**Output:**  
`ConceptCluster` objects grouping related nodes and messages.

**Responsibilities:**  
- Calculate semantic similarity between items using vector distance (e.g., cosine similarity) or keyword overlap.
- Execute clustering algorithms (e.g., DBSCAN, K-Means, or hierarchical clustering) to form groups.
- Identify outlier messages and assign them to generic or new clusters.
- Name and label clusters based on the predominant extracted concepts.

**Failure Conditions:**  
- Insufficient data to form meaningful clusters.
- High computational complexity causing timeouts (e.g., $O(N^2)$ comparisons without optimization).
- Highly fragmented clusters due to poor tuning of similarity thresholds.

---

## 8. Compilation

**Purpose:**  
To synthesize clustered, redundant information into a cohesive, canonical knowledge representation (a "Knowledge Node").

**Input:**  
`ConceptCluster` objects.

**Output:**  
`KnowledgeNode` objects representing synthesized, deduplicated information.

**Responsibilities:**  
- Feed clustered messages into a generative AI model to synthesize the core insights.
- Resolve contradictions or flag them for human review.
- Generate canonical documentation, summaries, and structural outlines for the concept.
- Attach lineage references, pointing back to the original source messages that formed the node.

**Failure Conditions:**  
- Generative AI hallucination or degradation in output quality.
- Over-compression leading to loss of critical nuances.
- AI provider API errors or context window limits.

---

## 9. Cross-Linking

**Purpose:**  
To establish explicit relationships between distinct compiled `KnowledgeNode` objects, creating a fully connected Knowledge Graph.

**Input:**  
Compiled `KnowledgeNode` objects.

**Output:**  
A connected Knowledge Graph of nodes and edges (`Relationships`).

**Responsibilities:**  
- Detect references, prerequisites, or related concepts between nodes.
- Generate typed edges (e.g., `DEPENDS_ON`, `RELATED_TO`, `CONTRADICTS`).
- Resolve semantic orphans by forcing similarity checks against the broader graph.
- Validate graph integrity (e.g., preventing recursive dependencies where inappropriate).

**Failure Conditions:**  
- Creation of highly dense, unnavigable "hairball" graphs due to overly aggressive linking.
- Missing edge connections due to stringent similarity thresholds.
- Infinite loops in hierarchical relationship generation.

---

## 10. Export

**Purpose:**  
To serialize the final compiled Knowledge Graph and push it to target platforms or external formats.

**Input:**  
Connected Knowledge Graph (Nodes and Edges) and raw inventoried data.

**Output:**  
Exported files (e.g., Markdown vault for Obsidian, Notion pages, JSON exports) or API push confirmations.

**Responsibilities:**  
- Translate OKC's internal model into the specific format required by the destination system.
- Manage rate limits and API interactions for external platforms (e.g., Notion, Confluence).
- Render Markdown files with appropriate frontmatter, tags, and internal wiki-links.
- Handle incremental updates by diffing the existing state against the new compiled state.

**Failure Conditions:**  
- Target platform API unavailability or rate limits.
- File system permission errors during local export.
- Data mapping constraints (e.g., target platform does not support required metadata fields).
