from pathlib import Path
import json

from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingBox,
    DockingJob,
)

from app.pipeline.payload import docking_job_to_payload


def test_docking_job_to_payload_returns_json_serializable_dict():
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

    expected_payload = {
        "job_id": "batch_1__pocket1",
        "receptor_pdbqt_path": str(Path("data/input/receptor.pdbqt")),
        "ligand_sdf_path": str(Path("data/input/ligands.sdf")),
        "output_sdf_path": str(Path("data/output/docked_batch_1_pocket1.sdf")),
        "batch_id": "batch_1",
        "pocket_id": "pocket1",
        "center_x": 5.2422,
        "center_y": 11.3665,
        "center_z": 28.3128,
        "size_x": 20.0,
        "size_y": 20.0,
        "size_z": 20.0,
        "exhaustiveness": 8,
        "seed": 0,
    }

    assert payload == expected_payload

    # Test très important : vérifie que Celery/JSON peut transporter ce payload
    json.dumps(payload)