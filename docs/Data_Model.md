# Oracle Knowledge Compiler (OKC) - Data Model Specification

This specification defines the core conceptual objects used throughout the OKC processing pipeline. These models are designed to be strictly internal, canonical, and universally applicable regardless of the origin of the data or its final destination.

---

## 1. Conversation

**Purpose:**  
The `Conversation` object acts as the highest-level container for chronological, sequential exchanges between entities (e.g., User and AI, or multi-agent). It provides context and bounding for the individual messages it contains.

**Properties:**  
- `id` (UUID): A globally unique identifier assigned during the Inventory stage.
- `source_id` (String): The original identifier provided by the source platform.
- `source_platform` (String): The origin system (e.g., "ChatGPT", "Claude", "LocalMarkdown").
- `title` (String): A descriptive label or topic for the conversation.
- `created_at` (Timestamp): The original creation time.
- `metadata` (Key-Value Map): Extensible dictionary for source-specific parameters (e.g., model version used, system prompts).

**Relationships:**  
- **Contains:** 1-to-N relationship with `Message` objects.
- **Yields:** 1-to-N relationship with `KnowledgeRecord` objects during the compilation phase.

**Lifecycle:**  
- **Created:** Instantiated during the Normalization stage from raw importer data.
- **Persisted:** Stored in the central inventory during the Inventory stage.
- **Referenced:** Accessed read-only during Indexing, Analysis, and Compilation.
- **Archived:** Preserved indefinitely as raw provenance after export.

**Future Extensions:**  
- Support for branched or threaded conversations (hierarchical structure rather than linear).
- Multi-modal conversation contexts (e.g., bounding audio files and images alongside text).

---

## 2. Message

**Purpose:**  
The `Message` object represents a single atomic utterance, turn, or block of text within a `Conversation`. It is the primary unit of text analyzed for meaning and context.

**Properties:**  
- `id` (UUID): A globally unique identifier.
- `conversation_id` (UUID): Foreign key linking back to the parent `Conversation`.
- `role` (Enum): The standardized identity of the sender (e.g., `USER`, `AI`, `SYSTEM`).
- `content` (String/Rich Text): The sanitized, normalized payload of the message.
- `timestamp` (Timestamp): The specific time the message was sent or generated.
- `annotations` (Key-Value Map): Analytical metadata appended during the pipeline (e.g., sentiment, extracted entities).

**Relationships:**  
- **Belongs To:** N-to-1 relationship with a `Conversation`.
- **Precedes/Follows:** 1-to-1 sequential relationship with other `Message` objects in the same context.
- **Constitutes:** N-to-1 or N-to-N relationship with `KnowledgeCluster` when grouped by topic.

**Lifecycle:**  
- **Created:** Instantiated alongside its parent `Conversation` during Normalization.
- **Mutated:** Only its `annotations` property is modified during the Analysis stage; the `content` remains immutable.
- **Clustered:** Evaluated and grouped during the Clustering stage.

**Future Extensions:**  
- Multi-part content arrays (e.g., a single message containing text, a base64 image, and a code execution block).
- Granular, inline entity tagging (mapping specific character offsets to knowledge nodes).

---

## 3. KnowledgeRecord

**Purpose:**  
The `KnowledgeRecord` object (also referred to as a Knowledge Node) is the fundamental unit of synthesized, compiled information. It represents a standalone concept, fact, or insight stripped of its conversational format.

**Properties:**  
- `id` (UUID): A globally unique identifier.
- `title` (String): A canonical, descriptive name for the concept.
- `summary` (String): A synthesized explanation or definition of the concept.
- `attributes` (Key-Value Map): Structured data specific to the concept (e.g., `status`, `domain`, `priority`).
- `confidence_score` (Float): An AI-generated metric indicating the reliability or consensus of the synthesized information.

**Relationships:**  
- **Derived From:** N-to-N relationship with `Message` objects (lineage tracking).
- **Belongs To:** N-to-1 relationship with a `KnowledgeCluster`.
- **Linked To:** N-to-N relationship with other `KnowledgeRecord` objects via explicit typed edges (e.g., `DEPENDS_ON`, `RELATED_TO`).

**Lifecycle:**  
- **Created:** Synthesized during the Compilation stage by generative AI summarizing a cluster.
- **Refined:** Updated during Cross-Linking to establish edges.
- **Exported:** Translated into pages, markdown notes, or database rows during the Export stage.

**Future Extensions:**  
- Versioning support (tracking how a knowledge record evolves across multiple imports).
- Trust weighting based on the authority of the source `Message` objects.

---

## 4. KnowledgeCluster

**Purpose:**  
The `KnowledgeCluster` object is a transient or semi-persistent grouping mechanism used to collect thematically similar messages before they are compiled into a formal `KnowledgeRecord`.

**Properties:**  
- `id` (UUID): A globally unique identifier.
- `theme` (String): An AI-generated or keyword-based label describing the cluster's focus.
- `cohesion_score` (Float): A metric indicating how tightly related the items in the cluster are.
- `centroid_vector` (Array): The mathematical center of the cluster in the embedding space (if vector clustering is used).

**Relationships:**  
- **Contains:** 1-to-N relationship with `Message` objects.
- **Produces:** 1-to-1 or 1-to-N relationship with `KnowledgeRecord` objects upon synthesis.

**Lifecycle:**  
- **Created:** Generated dynamically during the Clustering stage.
- **Evaluated:** Used as the context window for generative AI during Compilation.
- **Discarded/Archived:** Generally discarded after Compilation, though it may be logged for audit purposes.

**Future Extensions:**  
- Hierarchical clustering (clusters within clusters) to support broad topics breaking down into sub-topics.
- Persistent clusters that update incrementally as new `Message` objects are indexed.

---

## 5. KnowledgeIndex

**Purpose:**  
The `KnowledgeIndex` is a structural object that facilitates rapid search, retrieval, and deduplication across all ingested data and compiled knowledge.

**Properties:**  
- `index_type` (Enum): The underlying mechanism (e.g., `LEXICAL_BM25`, `VECTOR_HNSW`).
- `dimensions` (Integer): The size of the embedding vectors (if applicable).
- `last_updated` (Timestamp): Time of the most recent indexing operation.

**Relationships:**  
- **Indexes:** 1-to-N relationships with `Message`, `Conversation`, and `KnowledgeRecord` objects.

**Lifecycle:**  
- **Created:** Initialized during the Indexing stage or upon system startup.
- **Updated:** Incrementally appended as new objects pass through the Inventory stage.
- **Queried:** Actively utilized during the Analysis, Clustering, and Cross-Linking stages.

**Future Extensions:**  
- Distributed indexing support for multi-node deployments.
- Graph-native indexing (e.g., PageRank implementations over the cross-linked records).

---

## 6. ExportPackage

**Purpose:**  
The `ExportPackage` object encapsulates a coherent subset of the compiled Knowledge Graph intended for delivery to a specific external system. It manages the translation state and delivery status.

**Properties:**  
- `id` (UUID): A globally unique identifier.
- `target_platform` (Enum): The destination system (e.g., `OBSIDIAN`, `NOTION`, `SQLITE`).
- `status` (Enum): Current state of the export (e.g., `PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`).
- `payload` (Binary/Text): The serialized representation of the knowledge (e.g., a zip file of markdown, a JSON dump).
- `error_log` (Array): Any warnings or errors encountered during the format translation or API push.

**Relationships:**  
- **Packages:** 1-to-N relationship with `KnowledgeRecord` objects and their associated edges.

**Lifecycle:**  
- **Created:** Instantiated at the beginning of the Export stage.
- **Processed:** Serialized and translated by an exporter plugin.
- **Completed:** Marked as success or failure post-delivery, with logs retained for debugging.

**Future Extensions:**  
- Delta packages (only exporting records that have changed since the last successful package delivery).
- Webhook integrations to trigger external CI/CD pipelines upon successful package generation.
