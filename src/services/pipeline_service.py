class PipelineService:
    def __init__(self):
        self.status = "Idle"

    def run_pipeline(self):
        self.status = "Running"
        return {"status": self.status, "message": "Pipeline started."}

    def cancel_pipeline(self):
        self.status = "Cancelled"
        return {"status": self.status, "message": "Pipeline cancelled."}

    def get_pipeline_status(self):
        return {"status": self.status, "progress": 0.0}
