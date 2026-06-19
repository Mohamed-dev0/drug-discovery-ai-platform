from celery_app import celery_app
import time
from pathlib import Path

@celery_app.task
def add(x, y):
    return x + y

@celery_app.task
def sleep_task(seconds):
    time.sleep(seconds)
    return f"Task finished after {seconds} seconds"

@celery_app.task
def check_file_exists(file_path):
    path = Path(file_path)

    return {
        "file_path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
    }

@celery_app.task
def run_fake_gnina_job(job_payload):
    required_keys = [
        "job_id",
        "receptor_pdbqt_path",
        "ligand_sdf_path",
        "output_sdf_path",
        "pocket_id",
        "center_x",
        "center_y",
        "center_z",
        "box_size",
        "exhaustiveness",
        "seed",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in job_payload
    ]

    if missing_keys:
        return {
            "status": "error",
            "message": "Missing required keys",
            "missing_keys": missing_keys,
        }

    job_id = job_payload["job_id"]
    pocket_id = job_payload["pocket_id"]

    return {
        "job_id": job_id,
        "status": "success",
        "message": "Fake GNINA job completed",
        "received_payload": job_payload,
        "n_results": 2,
        "results": [
            {
                "ligand_id": "lig_1",
                "pocket_id": pocket_id,
                "vina_affinity": -7.2,
                "cnn_pose_score": 0.84,
            },
            {
                "ligand_id": "lig_2",
                "pocket_id": pocket_id,
                "vina_affinity": -6.8,
                "cnn_pose_score": 0.79,
            },
        ],
    }
