from pathlib import Path

from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingBox,
    DockingJob,
)

from app.pipeline.docking import GninaCommandBuilder


def test_gnina_command_builder_creates_correct_command():
    # Arrange
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

    builder = GninaCommandBuilder(gnina_binary="gnina")

    # Act
    command = builder.build(job)

    # Assert
    expected_command = [
        "gnina",
        "-r", str(Path("data/input/receptor.pdbqt")),
        "-l", str(Path("data/input/ligands.sdf")),

        "--center_x", "5.2422",
        "--center_y", "11.3665",
        "--center_z", "28.3128",

        "--size_x", "20.0",
        "--size_y", "20.0",
        "--size_z", "20.0",

        "-o", str(Path("data/output/docked_batch_1_pocket1.sdf")),

        "--seed", "0",
        "--exhaustiveness", "8",
    ]

    assert command == expected_command