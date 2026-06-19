from pathlib import Path, PurePosixPath
import subprocess

from .celery_app import celery_app


HOST_PROJECT_DIR = Path("/home/ubuntu/drug-discovery").resolve()
CONTAINER_PROJECT_DIR = PurePosixPath("/work")


def to_host_path(path: str | Path) -> Path:
    """
    Convertit un chemin relatif ou absolu en chemin host absolu.
    Exemple :
    data/inputs/x.sdf
    -> /home/ubuntu/drug-discovery/data/inputs/x.sdf
    """
    path = Path(path)

    if not path.is_absolute():
        path = HOST_PROJECT_DIR / path

    return path.resolve()


def to_container_path(host_path: str | Path) -> str:
    """
    Convertit un chemin host en chemin visible depuis Docker.

    Exemple :
    /home/ubuntu/drug-discovery/data/inputs/x.sdf
    -> /work/data/inputs/x.sdf
    """
    host_path = Path(host_path).resolve()

    relative_path = host_path.relative_to(HOST_PROJECT_DIR)

    container_path = PurePosixPath(
        CONTAINER_PROJECT_DIR,
        *relative_path.parts,
    )

    return str(container_path)


@celery_app.task
def run_real_gnina_job(payload: dict) -> dict:
    """
    Lance GNINA via Docker à partir d'un payload JSON-compatible.
    """

    required_keys = [
        "job_id",
        "receptor_pdbqt_path",
        "ligand_sdf_path",
        "output_sdf_path",
        "center_x",
        "center_y",
        "center_z",
        "size_x",
        "size_y",
        "size_z",
        "exhaustiveness",
        "seed",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in payload
    ]

    if missing_keys:
        return {
            "status": "error",
            "job_id": payload.get("job_id"),
            "message": "Missing required keys",
            "missing_keys": missing_keys,
        }

    try:
        receptor_host_path = to_host_path(payload["receptor_pdbqt_path"])
        ligand_host_path = to_host_path(payload["ligand_sdf_path"])
        output_host_path = to_host_path(payload["output_sdf_path"])

        receptor_container_path = to_container_path(receptor_host_path)
        ligand_container_path = to_container_path(ligand_host_path)
        output_container_path = to_container_path(output_host_path)

    except Exception as exc:
        return {
            "status": "error",
            "job_id": payload["job_id"],
            "message": f"Path conversion failed: {exc}",
        }

    if not receptor_host_path.exists():
        return {
            "status": "error",
            "job_id": payload["job_id"],
            "message": f"Receptor file not found: {receptor_host_path}",
        }

    if not ligand_host_path.exists():
        return {
            "status": "error",
            "job_id": payload["job_id"],
            "message": f"Ligand file not found: {ligand_host_path}",
        }

    output_host_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "docker", "run", "--rm",
        "--gpus", "all",
        "-v", f"{HOST_PROJECT_DIR}:/work",
        "gnina/gnina",
        "gnina",

        "-r", receptor_container_path,
        "-l", ligand_container_path,

        "--center_x", str(payload["center_x"]),
        "--center_y", str(payload["center_y"]),
        "--center_z", str(payload["center_z"]),

        "--size_x", str(payload["size_x"]),
        "--size_y", str(payload["size_y"]),
        "--size_z", str(payload["size_z"]),

        "--exhaustiveness", str(payload["exhaustiveness"]),
        "--seed", str(payload["seed"]),

        "-o", output_container_path,
    ]

    completed_process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    output_exists = output_host_path.exists()
    output_size = output_host_path.stat().st_size if output_exists else 0

    if completed_process.returncode != 0:
        return {
            "status": "error",
            "job_id": payload["job_id"],
            "message": "Docker GNINA command failed",
            "return_code": completed_process.returncode,
            "command": command,
            "stdout_tail": completed_process.stdout[-2000:],
            "stderr_tail": completed_process.stderr[-2000:],
            "output_exists": output_exists,
            "output_size": output_size,
        }

    if not output_exists or output_size == 0:
        return {
            "status": "error",
            "job_id": payload["job_id"],
            "message": "GNINA output file missing or empty",
            "return_code": completed_process.returncode,
            "command": command,
            "stdout_tail": completed_process.stdout[-2000:],
            "stderr_tail": completed_process.stderr[-2000:],
            "output_exists": output_exists,
            "output_size": output_size,
        }

    return {
        "status": "success",
        "job_id": payload["job_id"],
        "output_sdf_path": str(output_host_path),
        "output_exists": output_exists,
        "output_size": output_size,
        "return_code": completed_process.returncode,
        "stdout_tail": completed_process.stdout[-2000:],
        "stderr_tail": completed_process.stderr[-2000:],
    }