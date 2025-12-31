import os
import logging
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from script_p2Rank import run_p2rank_cli
from pathlib import Path
import tempfile
import shutil
import requests
import gzip
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run_p2rank/")
def run_p2rank_endpoint(clean_id: str):
    result = download_structure(clean_id)

    if result is None or "pdb" not in result:
        raise HTTPException(status_code=404, detail="Structure not found for this id")

    pdb_text = result["pdb"]
    temp_dir = Path(tempfile.mkdtemp(prefix="p2rank_"))

    try:
        pdb_path = temp_dir / "input.pdb"
        output_dir = temp_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        pdb_path.write_text(pdb_text, encoding="utf-8")

        run_p2rank_cli(pdb_path, output_dir)

        prediction_csv = output_dir / "input.pdb_predictions.csv"
        if not prediction_csv.exists():
            raise HTTPException(status_code=500, detail="P2Rank did not generate the _predictions.csv file.")

        df = pd.read_csv(prediction_csv)
        if df.empty:
            return {"pockets": [], "points_by_rank": {}}

        df.columns = df.columns.str.strip()

        cols = ['name', 'rank', 'score', 'sas_points', 'center_x', 'center_y', 'center_z']
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise HTTPException(status_code=500, detail=f"Missing columns in P2Rank CSV: {missing}")

        df_clean = df[cols].copy().rename(columns={
            "name": "pocket_name",
            "rank": "pocket_rank",
            "sas_points": "surface_points"
        })

        # faster than apply(axis=1)
        df_clean["center"] = [
            {"x": float(x), "y": float(y), "z": float(z)}
            for x, y, z in zip(df_clean["center_x"], df_clean["center_y"], df_clean["center_z"])
        ]
        df_clean = df_clean.drop(columns=["center_x", "center_y", "center_z"])
        pockets = df_clean.to_dict(orient="records")

        points_path = output_dir / "visualizations/data/input.pdb_points.pdb.gz"
        if not points_path.exists():
            raise HTTPException(status_code=500, detail="P2Rank did not generate _points.pdb.gz")

        points_by_rank = {}
        with gzip.open(points_path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.startswith("HETATM"):
                    continue

                # WARNING: fragile parsing — verify P2Rank format
                rank_str = line[21].strip()
                if not rank_str:
                    continue

                try:
                    rank = int(rank_str)
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                except ValueError:
                    continue

                points_by_rank.setdefault(rank, []).append({"x": x, "y": y, "z": z})

        return {"pockets": pockets, "points_by_rank": points_by_rank}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Internal error in /run_p2rank/")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/get_structure")
def download_structure(clean_id: str):
    clean_id = clean_id.strip().upper()
    if not clean_id:
        raise HTTPException(status_code=400, detail="clean_id is required")

    # 1) RCSB
    try:
        rcsb_url = f"https://files.rcsb.org/download/{clean_id}.pdb"
        rcsb_resp = requests.get(rcsb_url, timeout=10)
        if rcsb_resp.ok and rcsb_resp.text.strip():
            return {"pdb": rcsb_resp.text, "source": "RCSB PDB (Experimental)"}
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="RCSB timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"RCSB request failed: {e}")

    # 2) AlphaFold fallback (clean_id should likely be a UniProt ID)
    try:
        af_api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{clean_id}"
        af_resp = requests.get(af_api_url, timeout=10)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AlphaFold API timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"AlphaFold API request failed: {e}")

    if not af_resp.ok:
        raise HTTPException(status_code=404, detail="Structure not found (RCSB) and AlphaFold API not available")

    try:
        data = af_resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="AlphaFold API returned invalid JSON")

    if not data:
        raise HTTPException(status_code=404, detail="No AlphaFold model for this ID")

    pdb_url = data[0].get("pdbUrl")
    if not pdb_url:
        raise HTTPException(status_code=502, detail="AlphaFold response missing pdbUrl")

    try:
        pdb_resp = requests.get(pdb_url, timeout=10)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AlphaFold PDB download timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"AlphaFold PDB download failed: {e}")

    if not (pdb_resp.ok and pdb_resp.text.strip()):
        raise HTTPException(status_code=404, detail="AlphaFold PDB file not available")

    return {"pdb": pdb_resp.text, "source": "AlphaFold DB (AI PREDICTION)"}
