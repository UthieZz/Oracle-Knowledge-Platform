import os
import logging
from typing import Optional

from okc.models.knowledge_package import KnowledgePackage

logger = logging.getLogger(__name__)


class CompilerAdapter:
    """
    Orchestrates the ingestion, analysis, compilation, and export phases into a
    single, executable pipeline.
    """

    def __init__(
        self,
        importer,
        analyzer_registry,
        compiler,
        exporter
    ):
        self.importer = importer
        self.analyzer_registry = analyzer_registry
        self.compiler = compiler
        self.exporter = exporter

    def execute_pipeline(
        self,
        source_filepath: str,
        tenant_id: Optional[str] = None,
        silo_id: Optional[str] = None,
        incremental: bool = False
    ) -> KnowledgePackage:
        """
        Executes the complete compilation lifecycle.
        Enforces tenant and silo boundary security prior to runtime.
        """

        # Enterprise Hardening: Granular Data Governance
        active_tenant = tenant_id or os.environ.get("OKP_TENANT_ID")
        active_silo = silo_id or os.environ.get("OKP_SILO_ID")

        if not active_tenant or not active_silo:
            raise PermissionError(
                "Export refused: OKP_TENANT_ID and OKP_SILO_ID are required to enforce "
                "enterprise tenant-and-silo data boundaries."
            )

        logger.info(f"Starting pipeline for {source_filepath} (Tenant: {active_tenant}, Silo: {active_silo})")

        # Phase 1: Ingestion (Replaces media placeholders)
        logger.info("Executing Ingestion phase...")
        raw_knowledge_package = self.importer.process(source_filepath, active_tenant, active_silo)

        # Phase 2: Analysis (Dynamic Entity Extraction & NLP)
        logger.info("Executing Analysis phase...")
        analyzed_package = self.analyzer_registry.run_all(raw_knowledge_package)

        # Phase 3: Compilation (Markdown Generation)
        logger.info("Executing Compilation phase...")
        compiled_package = self.compiler.compile(analyzed_package)

        # Phase 4: Export (Persistence & Semantic Chunking Initiation)
        logger.info("Executing Export phase...")
        if incremental and not self._has_delta_changes(compiled_package):
            logger.info("Incremental compilation mode: No delta changes detected. Skipping export.")
        else:
            self.exporter.export(compiled_package, tenant_id=active_tenant, silo_id=active_silo)

        logger.info("OKC Pipeline execution successfully completed.")
        return compiled_package

    def _has_delta_changes(self, package: KnowledgePackage) -> bool:
        """
        Evaluates whether the newly compiled package contains updates compared to
        the existing remote index to support delta compilations.
        """
        # Delta logic to compare content_fingerprints goes here
        return True
