# NebulaVerse API Foundation

This is the API foundation for connecting the NebulaVerse frontend, sandbox, and smart contracts.

## Getting Started

1. Set up a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Run the API:
   ```bash
   uvicorn app.main:app --reload
   ```
