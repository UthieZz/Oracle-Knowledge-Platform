import os
from src.services.import_service import ImportService
from src.services.pipeline_service import PipelineService
from src.analyzers.knowledge_index_builder import KnowledgeIndexBuilder
from src.analyzers.entity_engine import EntityEngine
from src.compiler.markdown_compiler import MarkdownCompiler
from src.services.export_service import ExportService
import glob

def compile_data():
    print("Initializing services...")
    import_service = ImportService()
    
    # 1. Import
    uploads_dir = "uploads"
    files = glob.glob(os.path.join(uploads_dir, "*.json"))
    if not files:
        print(f"No files found in {uploads_dir}. Please upload files first.")
        return
        
    print(f"Found {len(files)} files to import.")
    for f in files:
        print(f"Importing {f}...")
        try:
            import_service.run_import_dispatcher(f)
        except Exception as e:
            print(f"Failed to import {f}: {e}")
    
    package = import_service.get_package()
    if not package:
        print("Failed to create knowledge package.")
        return
        
    # 2. Analyze
    print("Running Analysis (Entities & Index)...")
    entity_engine = EntityEngine()
    index_builder = KnowledgeIndexBuilder()
    
    entity_engine.analyze(package)
    index_builder.analyze(package)
    
    # 3. Export
    print("Exporting knowledge...")
    export_service = ExportService()
    export_service.export_knowledge(package)
    
    print("Compilation complete.")

if __name__ == "__main__":
    compile_data()
