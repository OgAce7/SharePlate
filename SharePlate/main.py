import sys
import uvicorn
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("======================================================")
    print("Starting SharePlate Integrated Web Platform & API Server")
    print("Local URL: http://localhost:8000")
    print("Donor Dashboard: http://localhost:8000/donor")
    print("NGO Dashboard: http://localhost:8000/ngo")
    print("API Docs: http://localhost:8000/docs")
    print("======================================================")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)