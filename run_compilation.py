import sys
from src.services.import_service import ImportService

files_to_import = [
    'uploads/MyActivity(2)-4f440db610fea3cc.json',
    'uploads/prod-grok-backend.json',
    'uploads/MyActivity(1)-081f794118b580a5.json',
    'uploads/conversations-006.json',
    'uploads/conversations-005.json',
    'uploads/MyActivity(3)-081f794118b580a5.json',
    'uploads/test_data.json',
    'uploads/conversations-001.json',
    'uploads/conversations-000.json',
    'uploads/conversations-004.json',
    'uploads/conversations-003.json',
    'uploads/conversations-002.json'
]

import_service = ImportService()

results = {'gemini': {'conv': 0, 'msg': 0, 'att': 0, 'err': []},
           'grok': {'conv': 0, 'msg': 0, 'att': 0, 'err': []},
           'chatgpt': {'conv': 0, 'msg': 0, 'att': 0, 'err': []}}

for file_path in files_to_import:
    try:
        # Determine source type to map to results
        from src.services.import_dispatcher import detect_source_type, SourceType
        st = detect_source_type(file_path).value
        print(f"Importing {file_path} as {st}...")
        
        result = import_service.run_import_dispatcher(file_path)
        
        # Aggregate stats
        if st in results:
            # Need to get stats from result - this depends on the importer implementation
            # Grok and ChatGPT don't return stats in the same format as Gemini
            if st == 'gemini':
                results['gemini']['conv'] += result.get('conversations', 0)
                results['gemini']['msg'] += result.get('messages', 0)
                # Gemini importer might not return attachments?
                results['gemini']['err'].extend(result.get('errors', []))
            elif st == 'grok':
                results['grok']['conv'] += result.get('conversations', 0)
                results['grok']['msg'] += result.get('messages', 0)
                results['grok']['err'].extend(result.get('errors', []))
            elif st == 'chatgpt':
                # ChatGPT importer in Service only returns 'status': 'Done'
                results['chatgpt']['conv'] += 1 # Placeholder
                results['chatgpt']['err'].extend(result.get('errors', []))
                
    except Exception as e:
        print(f"Error importing {file_path}: {e}")
        
# Final stats
pkg = import_service.get_package()
total_objects = 0
if pkg:
    total_objects = len(pkg.conversations) + len(pkg.entities) + len(pkg.relationships) + \
                    len(pkg.topics) + len(pkg.clusters) + len(pkg.timeline) + \
                    len(pkg.inventory) + len(pkg.attachment_knowledge)

print("\n--- IMPORT REPORT ---")
print(f"Sources Processed: {results}")
print(f"Total KnowledgePackage Objects: {total_objects}")
