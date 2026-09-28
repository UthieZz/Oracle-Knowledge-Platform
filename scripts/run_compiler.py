import os
import sys
import logging

from okc.plugins import default_okc_registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OKC_Driver")


def run_pipeline(source_file: str, tenant_id: str, silo_id: str) -> None:
    logger.info("Initializing Oracle Knowledge Compiler Pipeline (v2)...")
    registry = default_okc_registry()

    if not os.path.isfile(source_file):
        logger.warning("Source file missing (%s); falling back to synthetic package path", source_file)
        from okc.models.knowledge_package import KnowledgeObject, KnowledgePackage, Provenance

        pkg = KnowledgePackage(
            package_id="pkg_run_001",
            objects=[
                KnowledgeObject(
                    object_id="obj_001",
                    title="System Architecture Notes",
                    provenance=Provenance(
                        source_platform="chatgpt",
                        source_file=source_file,
                        tenant_id=tenant_id,
                        silo_id=silo_id,
                    ),
                    content="Discussed Python and SQLite integration for OKP using React frontend.",
                    attachments=[{"file_path": "diagram.png"}],
                )
            ],
        )
    else:
        importer = registry.get("importer", "json_v2_importer").plugin
        logger.info("Importing via %s: %s", registry.get("importer", "json_v2_importer").name, source_file)
        pkg = importer.process(source_file, tenant_id=tenant_id, silo_id=silo_id)

    attachment_pass = __import__("okc.compiler.passes.attachment_processing_pass", fromlist=["AttachmentProcessingPass"]).AttachmentProcessingPass(registry=registry)
    pkg = attachment_pass.execute(pkg)
    analyzer = registry.get("analyzer", "entity_extractor").plugin
    pkg = analyzer.run(pkg)

    rag_engine = HybridRAGEngine()
    rag_engine.index_package(pkg)
    hits = rag_engine.search("SQLite Python integration", tenant_id=tenant_id, silo_id=silo_id)
    logger.info("Hybrid Search Validation Hits: %s", len(hits))

    exporter = registry.get("exporter", "sqlite_exporter").plugin
    exporter.db_path = "okp_local.db"
    exporter.export(pkg, tenant_id=tenant_id, silo_id=silo_id)
    logger.info("Pipeline run completed successfully (%s objects).", len(pkg.objects))


if __name__ == "__main__":
    tenant = os.environ.get("OKP_TENANT_ID", "tenant_default")
    silo = os.environ.get("OKP_SILO_ID", "silo_default")
    file_path = sys.argv[1] if len(sys.argv) > 1 else "uploads/sample_export.json"
    run_pipeline(file_path, tenant, silo)
