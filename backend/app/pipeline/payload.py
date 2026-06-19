from .models import DockingJob


def docking_job_to_payload(job: DockingJob) -> dict:
    """
    Converts a Python DockingJob into a simple Celery/JSON-compatible dictionary.

    """

    return {
        "job_id": job.job_id,

        "receptor_pdbqt_path": str(job.receptor_pdbqt_path),
        "ligand_sdf_path": str(job.ligand_sdf_path),
        "output_sdf_path": str(job.output_sdf_path),

        "batch_id": job.batch.batch_id,
        "pocket_id": job.pocket.pocket_id,

        "center_x": job.docking_box.center_x,
        "center_y": job.docking_box.center_y,
        "center_z": job.docking_box.center_z,

        "size_x": job.docking_box.size_x,
        "size_y": job.docking_box.size_y,
        "size_z": job.docking_box.size_z,

        "exhaustiveness": job.exhaustiveness,
        "seed": job.seed,
    }