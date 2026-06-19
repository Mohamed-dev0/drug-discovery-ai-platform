from pathlib import Path


from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingBox,
    DockingJob,
    Ligand
)
from app.pipeline.virtual_screening_session import VirtualScreeningSession


def make_ligands(n: int) -> list[Ligand]:
    return [
        Ligand(
            ligand_id=f"lig_{i}",
            smiles="CCO",
        )
        for i in range(1, n + 1)
    ]


def make_session(ligand_batches: list[LigandBatch], probe_ligand_count: int = 10, seed: int = 0):
    return VirtualScreeningSession(
        receptor_pdbqt_path=Path("data/input/receptor.pdbqt"),
        ligand_batches=ligand_batches,
        pockets=[],
        ligand_batch_to_sdf={},
        gnina_runner=None,
        result_parser=None,
        result_writer=None,
        probe_evaluator=None,
        ligand_preparator=None,
        work_dir=Path("data/output"),
        gnina_binary="gnina",
        probe_ligand_count=probe_ligand_count,
        box_size=20.0,
        exhaustiveness=8,
        seed=seed,
    )


def test_select_probe_batch_returns_correct_number_of_ligands():
    ligands = make_ligands(100)

    batches = [
        LigandBatch(
            batch_id="batch_1",
            ligands=ligands,
        )
    ]

    session = make_session(
        ligand_batches=batches,
        probe_ligand_count=10,
        seed=0,
    )

    probe_batch = session._select_probe_batch()

    assert probe_batch.batch_id == "probe_random_10"
    assert len(probe_batch.ligands) == 10


def test_select_probe_batch_is_reproducible_with_same_seed():
    ligands = make_ligands(100)

    batches = [
        LigandBatch(
            batch_id="batch_1",
            ligands=ligands,
        )
    ]

    session_1 = make_session(
        ligand_batches=batches,
        probe_ligand_count=10,
        seed=0,
    )

    session_2 = make_session(
        ligand_batches=batches,
        probe_ligand_count=10,
        seed=0,
    )

    probe_batch_1 = session_1._select_probe_batch()
    probe_batch_2 = session_2._select_probe_batch()

    ids_1 = [ligand.ligand_id for ligand in probe_batch_1.ligands]
    ids_2 = [ligand.ligand_id for ligand in probe_batch_2.ligands]

    assert ids_1 == ids_2


def test_select_probe_batch_samples_across_multiple_batches():
    batch_1 = LigandBatch(
        batch_id="batch_1",
        ligands=make_ligands(50),
    )

    batch_2 = LigandBatch(
        batch_id="batch_2",
        ligands=[
            Ligand(
                ligand_id=f"lig_{i}",
                smiles="CCO",
            )
            for i in range(51, 101)
        ],
    )

    session = make_session(
        ligand_batches=[batch_1, batch_2],
        probe_ligand_count=20,
        seed=0,
    )

    probe_batch = session._select_probe_batch()

    assert len(probe_batch.ligands) == 20

    selected_ids = [ligand.ligand_id for ligand in probe_batch.ligands]

    assert len(selected_ids) == len(set(selected_ids))


def test_select_probe_batch_uses_all_ligands_if_probe_count_is_larger_than_library():
    ligands = make_ligands(5)

    batches = [
        LigandBatch(
            batch_id="batch_1",
            ligands=ligands,
        )
    ]

    session = make_session(
        ligand_batches=batches,
        probe_ligand_count=100,
        seed=0,
    )

    probe_batch = session._select_probe_batch()

    assert probe_batch.batch_id == "probe_random_5"
    assert len(probe_batch.ligands) == 5


def test_job_to_payload():
    ligands = make_ligands(5)

    batch = LigandBatch(
        batch_id="batch_1",
        ligands=ligands,
    )

    session = make_session(
        ligand_batches=[batch],
        probe_ligand_count=100,
        seed=0,
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

    payload = session._job_to_payload(job)

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

        "gnina_binary": "gnina",
    }

    assert payload == expected_payload

def test_get_original_ligand_id_removes_variant_suffix():
    session = make_session(
        ligand_batches=[],
        probe_ligand_count=100,
        seed=0,
    )

    assert session._get_original_ligand_id("lig_12_i0") == "lig_12"
    assert session._get_original_ligand_id("lig_12_i1") == "lig_12"
    assert session._get_original_ligand_id("lig_12_i5") == "lig_12"


def test_get_original_ligand_id_keeps_normal_id_unchanged():
    session = make_session(
        ligand_batches=[],
        probe_ligand_count=100,
        seed=0,
    )

    assert session._get_original_ligand_id("lig_13") == "lig_13"
    assert session._get_original_ligand_id("mol_ABC123") == "mol_ABC123"


