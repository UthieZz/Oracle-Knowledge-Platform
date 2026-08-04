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
    stats = {
        "platforms": len(platforms),
        "conversations": sum(len(controller.get_conversations(p)) for p in platforms),
        "status": pipeline_service.get_pipeline_status()["status"],
        "last_compile": controller.knowledge_service.root_manifest.get("compilation_run", {}).get("exported_at", "Never")
    }
    return jsonify(stats)

@app.route('/api/platforms', methods=['GET'])
def get_platforms():
    return jsonify(controller.get_platforms())

@app.route('/api/conversations/<platform>', methods=['GET'])
def get_conversations(platform):
    return jsonify(controller.get_conversations(platform))

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
        # Simplified logic: detect platform and run importer
        # In this prototype, we'll assume Gemini for JSON files containing 'My Activity'
        # and ChatGPT for others for demonstration purposes.
        if path.endswith(".json"):
            import_service.run_gemini_import(path)
            
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

if __name__ == '__main__':
    app.run(port=5000, debug=True)
