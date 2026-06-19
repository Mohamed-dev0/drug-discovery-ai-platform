from pathlib import Path

from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingBox,
    DockingJob,
)

from app.pipeline.payload import docking_job_to_payload
from app.workers.tasks import run_fake_gnina_job


def main():
    batch = LigandBatch(
        batch_id="batch_1",
        ligands=[],
    )

    pocket = Pocket(
        pocket_id="pocket1",
        rank=1,
        score=26.7,
        center_x=5.2422,
        center_y=11.3665,
        center_z=28.3128,
    )

    docking_box = DockingBox(
        center_x=5.2422,
        center_y=11.3665,
        center_z=28.3128,
        size_x=20.0,
        size_y=20.0,
        size_z=20.0,
    )

    job = DockingJob(
        job_id="batch_1__pocket1",
        receptor_pdbqt_path=Path("data/input/receptor.pdbqt"),
        ligand_sdf_path=Path("data/input/ligands.sdf"),
        batch=batch,
        pocket=pocket,
        docking_box=docking_box,
        output_sdf_path=Path("data/output/docked_batch_1_pocket1.sdf"),
        exhaustiveness=8,
        seed=0,
    )

    payload = docking_job_to_payload(job)

    task = run_fake_gnina_job.delay(payload)

    print(f"Task id: {task.id}")
    print("Waiting for result...")

    result = task.get(timeout=30)

    print(result)


if __name__ == "__main__":
    main()