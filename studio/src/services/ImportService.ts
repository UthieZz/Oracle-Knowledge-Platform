export const ImportService = {
  async getDashboardStats() {
    // Reusing the existing FirestoreService for consistency
    const { FirestoreService } = await import('./FirestoreService');
    return FirestoreService.getDashboardStats();
  },

  async uploadFile(file: File) {
    console.log("[IMPORT] Triggering local pipeline for:", file.name);
    // In this architecture, the browser moves the file to the local `uploads/` dir
    // and triggers the canonical compiler.
    try {
      // Assuming a bridge exists to interact with the local filesystem
      // If this fails, we fall back to manual instructions
      const formData = new FormData();
      formData.append('file', file);
      
      // Attempt to invoke the pipeline trigger
      const response = await fetch('/api/import/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error("Failed to upload file");
      return { success: true };
    } catch (err) {
      console.error("[IMPORT] Browser-to-local bridge failed. Falling back to manual mode.");
      return { success: false, error: "Manual move required." };
    }
  },

  async compile(file_name: string) {
    console.log("[IMPORT] Invoking local compiler for:", file_name);
    // Trigger the canonical OKC pipeline
    try {
      const response = await fetch(`/api/import/compile?file=${encodeURIComponent(file_name)}`, {
        method: 'POST'
      });
      return await response.json();
    } catch (err) {
      console.error("[IMPORT] Compilation failed:", err);
      return { status: 'Error', message: 'Compiler invocation failed.' };
    }
  }
};
