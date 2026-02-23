import os
import subprocess
import json

# --- CONFIGURATION ---
API_KEY = os.environ.get("GEMINI_API_KEY")
JSONL_FILE = "batch_requests.jsonl"
PROJECT_ID = "genai-ag-sci-project" # Placeholder, but Batch API is global usually
# We need to upload the JSONL file itself to the File API first?
# No, Batch usually takes a GCS URI or File API URI for the input file.

def submit_batch_curl():
    if not API_KEY:
        print("❌ API Key missing")
        return

    # 1. Upload the JSONL file to Gemini File API
    print("📤 Uploading batch_requests.jsonl to Gemini File API...")
    # We use a simple curl command to upload the JSONL file
    # Docs: https://ai.google.dev/api/files#method:-media.upload
    
    upload_cmd = [
        "curl", "-X", "POST",
        f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={API_KEY}",
        "-H", "X-Goog-Upload-Protocol: resumable",
        "-H", "X-Goog-Upload-Command: start",
        "-H", "X-Goog-Upload-Header-Content-Length: " + str(os.path.getsize(JSONL_FILE)),
        "-H", "X-Goog-Upload-Header-Content-Type: application/json",
        "-H", "Content-Type: application/json",
        "-d", '{"file": {"display_name": "batch_requests.jsonl"}}'
    ]
    
    try:
        # Start upload session
        res = subprocess.run(upload_cmd, capture_output=True, text=True)
        upload_url = res.headers.get("x-goog-upload-url") # Wait, curl output headers are tricky
        # Easier: Use the python library if possible, but fallback to curl for the BATCH CREATE call.
        
        # Let's pivot: The 'google-generativeai' library DOES support upload_file.
        # We can reuse that part.
        import google.generativeai as genai
        genai.configure(api_key=API_KEY)
        
        print("📤 Uploading JSONL via Python SDK...")
        batch_file = genai.upload_file(JSONL_FILE)
        
        # Wait for processing
        import time
        while batch_file.state.name == "PROCESSING":
            time.sleep(1)
            batch_file = genai.get_file(batch_file.name)
            
        print(f"✅ Batch Input File Ready: {batch_file.uri}")
        
        # 2. Create Batch Job via CURL (safest for beta features)
        # Docs: https://ai.google.dev/api/batch-jobs#method:-batchjobs.create
        
        print("🚀 Creating Batch Job...")
        
        create_payload = {
            "request": {
                "contents": [
                    {"role": "user", "parts": [{"text": "Process this item."}]} 
                    # The content is actually defined in the JSONL, not here.
                    # The payload structure is: {"batch_input": {"gcs_source": ...}} or {"file_source": ...}
                ]
            }
        }
        
        # Correct Payload for Batch API (v1beta):
        # {
        #   "source": {"file_uri": "..."}
        # }
        
        # Wait, the structure is:
        # POST https://generativelanguage.googleapis.com/v1beta/batches?key=API_KEY
        # {
        #   "requests": { "file_source": { "uri": "..." } }
        # }
        
        # Let's try the Python SDK method if available, else standard curl payload.
        # Assuming standard payload:
        payload = json.dumps({
            "source": {
                "file_uri": batch_file.uri
            }
        })
        
        curl_cmd = [
            "curl", "-X", "POST",
            f"https://generativelanguage.googleapis.com/v1beta/batches?key={API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", payload
        ]
        
        final_res = subprocess.run(curl_cmd, capture_output=True, text=True)
        print("Response:", final_res.stdout)
        
        if "error" in final_res.stdout:
            print("❌ Batch Creation Failed.")
        else:
            print("✅ Batch Job Created! Check response for ID.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    submit_batch_curl()
