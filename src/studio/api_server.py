from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import werkzeug
from src.studio.controllers.studio_controller import StudioController
from src.services.import_service import ImportService
from src.services.pipeline_service import PipelineService
from src.services.export_service import ExportService

app = Flask(__name__)
CORS(app)

# UPLOAD_FOLDER for temporary storage
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize controllers and services
# In a real scenario, these would be managed more robustly (e.g., via a main controller)
controller = StudioController(main_controller=None)
import_service = ImportService()
pipeline_service = PipelineService()
export_service = ExportService()

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Returns metadata for the dashboard."""
    controller.knowledge_service.load_workspace() # Refresh data
    platforms = controller.get_platforms()
    print(f"DEBUG: Platforms found: {platforms}")
    
    # Calculate knowledge objects
    knowledge_objects = 0
    for p in platforms:
        plat_dir = controller.knowledge_service.platforms[p]["path"]
        ko_dir = os.path.join(plat_dir, "knowledge_objects")
        print(f"DEBUG: Checking {ko_dir}")
        if os.path.exists(ko_dir):
            files = [f for f in os.listdir(ko_dir) if f.endswith(".md")]
            print(f"DEBUG: Found files: {files}")
            knowledge_objects += len(files)
        else:
            print(f"DEBUG: Dir does not exist: {ko_dir}")
            
    stats = {
        "platforms": len(platforms),
        "conversations": sum(len(controller.get_conversations(p)) for p in platforms),
        "status": pipeline_service.get_pipeline_status()["status"],
        "last_compile": controller.knowledge_service.root_manifest.get("compilation_run", {}).get("exported_at", "Never"),
        "knowledge_objects": knowledge_objects
    }
    return jsonify(stats)

@app.route('/api/platforms', methods=['GET'])
def get_platforms_list():
    controller.knowledge_service.load_workspace()
    return jsonify(controller.get_platforms())

@app.route('/api/knowledge-objects', methods=['GET'])
def get_knowledge_objects():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    query = request.args.get('query', '').lower()
    
    all_objs = controller.knowledge_service.get_knowledge_objects()
    if query:
        all_objs = [o for o in all_objs if query in o["title"].lower()]
        
    paginated, total = paginate_results(all_objs, page, limit)
    return jsonify({"data": paginated, "total": total, "page": page, "limit": limit})

@app.route('/api/entities', methods=['GET'])
def get_entities():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    query = request.args.get('query', '').lower()
    
    all_ents = controller.knowledge_service.get_entities()
    if query:
        all_ents = [e for e in all_ents if query in e.get("value", "").lower()]
        
    paginated, total = paginate_results(all_ents, page, limit)
    return jsonify({"data": paginated, "total": total, "page": page, "limit": limit})

@app.route('/api/attachments', methods=['GET'])
def get_attachments():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    query = request.args.get('query', '').lower()
    
    all_atts = controller.knowledge_service.get_attachments()
    if query:
        all_atts = [a for a in all_atts if query in a.get("name", "").lower()]
        
    paginated, total = paginate_results(all_atts, page, limit)
    return jsonify({"data": paginated, "total": total, "page": page, "limit": limit})

def paginate_results(results, page, limit):
    start = (page - 1) * limit
    end = start + limit
    return results[start:end], len(results)

@app.route('/api/conversations', methods=['GET'])
def get_conversations_paginated():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    query = request.args.get('query', '').lower()
    
    # In a real app, this would be a more robust query
    all_conversations = []
    for p in controller.get_platforms():
        all_conversations.extend(controller.get_conversations(p))
    
    if query:
        all_conversations = [c for c in all_conversations if query in c.get("title", "").lower()]
        
    paginated, total = paginate_results(all_conversations, page, limit)
    return jsonify({"data": paginated, "total": total, "page": page, "limit": limit})


@app.route('/api/knowledge/<platform>/<title>', methods=['GET'])
def get_knowledge_object(platform, title):
    content = controller.get_knowledge_object(platform, title)
    return jsonify({"content": content})

@app.route('/api/import/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = werkzeug.utils.secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    import_service.add_import_files([os.path.abspath(filepath)])
    return jsonify({"message": "File uploaded successfully", "filename": filename, "path": filepath})

@app.route('/api/import/queue', methods=['GET'])
def get_import_queue():
    return jsonify(import_service.get_imported_files())

@app.route('/api/compile', methods=['POST'])
def run_compile():
    # 1. Start Pipeline
    pipeline_service.run_pipeline()
    
    # 2. Run Importers for all queued files
    queued_files = import_service.get_imported_files()
    for f in queued_files:
        path = f["path"]
        # Detect platform and run importer
        filename = os.path.basename(path).lower()
        if "grok" in filename:
            import_service.run_grok_import(path)
        elif "gemini" in filename:
            import_service.run_gemini_import(path)
        else:
            # Assume ChatGPT
            from src.importers.chatgpt_importer import ChatGPTImporter
            # We don't have a run_chatgpt_import in ImportService, let's manually run it
            # This is a bit of a hack based on existing code structure
            importer = ChatGPTImporter(input_dir=os.path.dirname(path))
            package = import_service.get_package() or KnowledgePackage()
            importer.import_data(package)
            
    # 3. Export/Compile
    package = import_service.get_package()
    if package:
        export_service.export_knowledge(package)
        pipeline_service.status = "Idle"
        return jsonify({"status": "Success", "message": "Compilation complete."})
    else:
        pipeline_service.status = "Idle"
        return jsonify({"status": "Error", "message": "No data to compile."}), 400

@app.route('/api/pipeline/status', methods=['GET'])
def get_pipeline_status():
    return jsonify(pipeline_service.get_pipeline_status())

@app.route('/api/search', methods=['GET'])
def search_knowledge():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])
    results = controller.search(query)
    return jsonify(results)

@app.route('/api/chat', methods=['POST'])
def chat_grounded():
    data = request.json
    query = data.get('query', '')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    response = controller.chat(query)
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
