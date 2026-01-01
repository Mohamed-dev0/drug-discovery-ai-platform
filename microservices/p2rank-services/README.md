# P2Rank Microservice

This microservice exposes a **FastAPI** interface to run **P2Rank** for automated
binding pocket detection on protein structures.

It acts as a lightweight wrapper around the P2Rank CLI, enabling integration
with a web frontend and other services.

---

## 🧠 What this service does

- Accepts a protein structure identifier (PDB ID or UniProt ID)
- Retrieves the corresponding 3D structure:
  - From RCSB PDB (experimental)
  - Fallback to AlphaFold DB (predicted)
- Runs **P2Rank** to detect potential ligand-binding pockets
- Parses and returns:
  - Pocket metadata (rank, score, center coordinates)
  - Pocket surface points for 3D visualization

---

## 🧰 Tech Stack

- **Python 3.10+**
- **FastAPI**
- **Pandas**
- **P2Rank** (Java-based CLI tool)

---

## 📦 Requirements

### System
- **Java JDK** (v11 or later) — required by P2Rank
- **P2Rank** installed locally
- **Git Bash** (recommended on Windows to execute the P2Rank CLI)

### Python
- Python 3.10 or later
- `pip`

---

## ⚙️ Installation

### 1. Create a virtual environment

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install P2Rank

Download P2Rank from the official repository:
https://github.com/rdk/p2rank

Extract the archive locally (e.g. p2rank/distro/).

Verify Java installation:
```bash
java -version
```
### 4. Environment configuration
Create a .env file in this directory (not tracked by Git):
```env
# P2Rank configuration
P2RANK_DISTRO=./p2rank/distro
P2RANK_BIN=./p2rank/distro/prank
GIT_BASH="C:\Program Files\Git\bin\bash.exe"

# CORS
ALLOWED_ORIGINS=http://localhost:5173
```

### 🚀 Running the service

From this directory:
```bash
uvicorn main:app --reload
```

The API will be available at:
```arduino
http://localhost:8000
```

Interactive API documentation:

- Swagger UI: http://localhost:8000/docs

### 🔌 API Overview
**POST /run_p2rank**

Runs P2Rank on a protein structure and returns predicted binding pockets.

**Input**

- clean_id (query parameter): PDB ID or UniProt ID

**Output**

- JSON containing:

  - **pockets**: list of predicted pockets (rank, score, center)

  - **points_by_rank**: surface points grouped by pocket rank

## 📄 License

This microservice is part of the Drug Discovery AI Platform and is licensed under the MIT License.
