import os
import sys
import logging
from okc.models.knowledge_package import KnowledgePackage, KnowledgeObject, Provenance
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.analyzers.entity_extractor import EntityExtractor
from okc.search.hybrid_rag import HybridRAGEngine
from okc.exporters.sqlite_exporter import SQLiteExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OKC_Driver")


def run_pipeline(source_file: str, tenant_id: str, silo_id: str) -> None:
    logger.info("Initializing Oracle Knowledge Compiler Pipeline...")

    # Step 1: Ingestion & Object Creation
    logger.info(f"Loading input file: {source_file}")
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
                    silo_id=silo_id
                ),
                content="Discussed Python and SQLite integration for OKP using React frontend.",
                attachments=[{"file_path": "diagram.png"}]
            )
        ]
    )

    # Step 2: Attachment Processing (Upgrade 2)
    attachment_pass = AttachmentProcessingPass()
    pkg = attachment_pass.execute(pkg)

    # Step 3: Entity & Pattern Analysis
    analyzer = EntityExtractor()
    pkg = analyzer.run(pkg)

    # Step 4: Hybrid RAG Indexing (Upgrade 3)
    rag_engine = HybridRAGEngine()
    rag_engine.index_package(pkg)
    search_results = rag_engine.search("SQLite Python integration", tenant_id=tenant_id, silo_id=silo_id)
    logger.info(f"Hybrid Search Validation Hits: {len(search_results)}")

    # Step 5: Local Database Export
    exporter = SQLiteExporter(db_path="okp_local.db")
    exporter.export(pkg, tenant_id=tenant_id, silo_id=silo_id)

    logger.info("Pipeline run completed successfully.")


if __name__ == "__main__":
    tenant = os.environ.get("OKP_TENANT_ID", "tenant_default")
    silo = os.environ.get("OKP_SILO_ID", "silo_default")
    file_path = sys.argv[1] if len(sys.argv) > 1 else "uploads/sample_export.json"

    run_pipeline(file_path, tenant, silo)
