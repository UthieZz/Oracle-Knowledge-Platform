"""KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage.

Connectors and SyncEngine never write KnowledgePackage. This processor
feeds the existing PlainTextImporter path for create/update, then upserts
or removes objects so that retrieval reflects deletions and updates.

Source identity is namespaced as source|tenant_id|silo_id|object_id so that
identical object_ids from different connectors/scopes cannot collide.
Legacy unscoped markers remain readable.

Permission_change: recorded in package.metadata["permissions"] keyed by scoped id;
read=False is enforced fail-closed by KnowledgePackageRetriever for explicit entries.
Delete cleans the corresponding permission entry.

Optional package_path loads/saves the package as canonical JSON (atomic write)
so the living knowledge survives process restarts. process() rolls back in-memory
package, source index and metadata if _persist raises after mutation.

On init, a non-dict permissions metadata entry is normalized to an empty dict
so subsequent operations remain robust if the living package was externally
corrupted.
"""