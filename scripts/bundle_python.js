import fs from 'fs';
import path from 'path';

const filesToBundle = [
  'src/core/interfaces.py',
  'src/models/knowledge_package.py',
  'src/models/conversation.py',
  'src/models/message.py',
  'src/models/entity.py',
  'src/importers/chatgpt_importer.py',
  'src/analyzers/entity_engine.py',
  'src/analyzers/inventory_builder.py',
  'src/analyzers/knowledge_index_builder.py',
  'src/compiler/markdown_compiler.py'
];

const bundle = {};

filesToBundle.forEach(file => {
  const fullPath = path.resolve(file);
  if (fs.existsSync(fullPath)) {
    bundle[file] = fs.readFileSync(fullPath, 'utf8');
  }
});

const content = `export const pythonBundle: Record<string, string> = ${JSON.stringify(bundle, null, 2)};`;

fs.writeFileSync('studio/src/services/pythonBundle.ts', content);
console.log('Python bundle generated at studio/src/services/pythonBundle.ts');
