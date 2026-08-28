import { pythonBundle } from './pythonBundle';

declare global {
  interface Window {
    loadPyodide: any;
  }
}

class PyodideService {
  private pyodide: any = null;
  private isInitializing: boolean = false;

  async init() {
    if (this.pyodide) return this.pyodide;
    if (this.isInitializing) {
      while (this.isInitializing) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      return this.pyodide;
    }

    this.isInitializing = true;
    console.log('Initializing Pyodide...');
    
    try {
      this.pyodide = await window.loadPyodide();
      
      // Setup virtual filesystem
      for (const [filePath, content] of Object.entries(pythonBundle)) {
        const dir = filePath.substring(0, filePath.lastIndexOf('/'));
        this.pyodide.FS.mkdirTree(dir);
        this.pyodide.FS.writeFile(filePath, content);
      }
      
      // Create __init__.py files to make them packages
      const dirs = new Set<string>();
      for (const filePath of Object.keys(pythonBundle)) {
        let currentDir = filePath.substring(0, filePath.lastIndexOf('/'));
        while (currentDir) {
          dirs.add(currentDir);
          currentDir = currentDir.substring(0, currentDir.lastIndexOf('/'));
        }
      }
      
      for (const dir of dirs) {
        this.pyodide.FS.writeFile(`${dir}/__init__.py`, '');
      }

      console.log('Pyodide initialized and filesystem prepared.');
    } catch (err) {
      console.error('Failed to initialize Pyodide:', err);
    } finally {
      this.isInitializing = false;
    }

    return this.pyodide;
  }

  async runChatGPTImport(fileContent: string, fileName: string) {
    const py = await this.init();
    
    // Write the input file to the virtual FS
    py.FS.mkdirTree('input');
    const inputPath = `input/${fileName}`;
    py.FS.writeFile(inputPath, fileContent);

    const runScript = `
import json
import os
from src.importers.chatgpt_importer import ChatGPTImporter
from src.models.knowledge_package import KnowledgePackage
from src.analyzers.entity_engine import EntityEngine
from src.analyzers.inventory_builder import InventoryBuilder
from src.analyzers.knowledge_index_builder import KnowledgeIndexBuilder
from src.compiler.markdown_compiler import MarkdownCompiler

def run_poc(input_path):
    package = KnowledgePackage()
    
    # 1. Import
    importer = ChatGPTImporter(input_dir=os.path.dirname(input_path))
    # Override discover_files to only return our specific file
    importer.discover_files = lambda: [input_path]
    package = importer.import_data(package)
    
    # 2. Analyze
    EntityEngine().analyze(package)
    InventoryBuilder().analyze(package)
    KnowledgeIndexBuilder().analyze(package)
    
    # 3. Compile
    MarkdownCompiler(output_dir="output/markdown").compile(package)
    
    # Prepare result
    result = {
        "conversations_count": len(package.conversations),
        "entities_count": len(package.entities),
        "inventory_count": len(package.inventory),
        "index_categories": list(package.index.keys()),
        "markdown_files": os.listdir("output/markdown") if os.path.exists("output/markdown") else []
    }
    return json.dumps(result)

run_poc("${inputPath}")
`;

    const resultJson = await py.runPythonAsync(runScript);
    return JSON.parse(resultJson);
  }
}

export const pyodideService = new PyodideService();
