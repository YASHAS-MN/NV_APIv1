import os
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Helper function to create temporary files for tests
def create_test_file(filename: str, content: bytes):
    with open(filename, "wb") as f:
        f.write(content)
    return filename

def test_sandbox_valid_python_file():
    # 1. A valid, simple supported Python file
    content = b"print('Hello from sandbox!')\n"
    filename = create_test_file("test_script.py", content)
    
    try:
        with open(filename, "rb") as f:
            response = client.post("/api/sandbox/execute", files={"file": ("test_script.py", f, "text/x-python")})
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["asset_name"] == "test_script.py"
        assert "execution" in data
        assert "transcript" in data
        assert "hash" in data
    finally:
        os.remove(filename)

def test_sandbox_unsupported_file():
    # 2. An unsupported file
    content = b"echo 'Hello'\n"
    filename = create_test_file("test_script.sh", content)
    
    try:
        with open(filename, "rb") as f:
            response = client.post("/api/sandbox/execute", files={"file": ("test_script.sh", f, "application/x-sh")})
            
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported file type" in data["detail"]
    finally:
        os.remove(filename)

def test_sandbox_empty_upload():
    # 3. An empty upload
    content = b""
    filename = create_test_file("empty.py", content)
    
    try:
        with open(filename, "rb") as f:
            response = client.post("/api/sandbox/execute", files={"file": ("empty.py", f, "text/x-python")})
            
        assert response.status_code == 400
        data = response.json()
        assert "Empty upload" in data["detail"]
    finally:
        os.remove(filename)

def test_sandbox_execution_failure():
    # 4. A sandbox execution failure
    # We create a python script that does sys.exit(1) or has a syntax error
    content = b"import sys\nsys.exit(1)\n"
    filename = create_test_file("fail_script.py", content)
    
    try:
        with open(filename, "rb") as f:
            response = client.post("/api/sandbox/execute", files={"file": ("fail_script.py", f, "text/x-python")})
            
        assert response.status_code == 200 # Execution fails but sandbox handles it
        data = response.json()
        assert data["status"] == "success"
        assert data["execution"]["exit_code"] != 0
    finally:
        os.remove(filename)
