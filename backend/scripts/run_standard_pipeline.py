from pathlib import Path

from app.pipeline.docking import GninaRunner, GninaCommandBuilder
from app.pipeline.result_parser import  GninaResultParser
from app.pipeline.result_writer import DockingResultWriter
from app.pipeline.probe_evaluator import ProbePocketEvaluator

from app.pipeline.ligand_preparation import (
    CSVLigandReader,
    BatchBuilder,
    LigandPreparator,
    LigandScrubber,
    Ligand3DConverter)

from app.pipeline.protein_preparation import (
    ProteinDownloader,
    ProteinCleaner,
    PDBQTConverter,
    ProteinPreparator)

from app.pipeline.pocket_detection import (
    P2RankRunner,
    P2RankResultParser,
    PocketSelector,
    PocketDetector
)
from app.pipeline.virtual_screening_session import  VirtualScreeningSession


def main():
    # =========================
    # CONFIGURATION
    # =========================

    project_dir = Path("/home/ubuntu/drug-discovery").resolve()

    data_dir = project_dir / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = project_dir / "outputs"
    tmp_dir = project_dir / "tmp"
    tools_dir = project_dir / "tools"

    ligands_csv = inputs_dir / "ligands" / "lipinski_admet_results.csv"
    receptor_work_dir = inputs_dir / "receptor"
    prepared_ligands_dir = tmp_dir / "ligands_prepared"

    p2rank_executable = tools_dir / "p2rank_2.5.1" / "prank"


    pdb_id = "7LME"
    batch_size = 10
    smiles_column = "smiles"
    max_ligands_for_test = 30


    # =========================
    # 1) LIRE LA LIBRAIRIE
    # =========================
    reader = CSVLigandReader(smiles_column=smiles_column)
    ligands = reader.read(ligands_csv)
    ligands = ligands[:max_ligands_for_test]
    print(f"[1] Ligands lus: {len(ligands)}")


    # =========================
    # 2) CONSTRUIRE LES BATCHES
    # =========================
    builder = BatchBuilder()
    batches = builder.build(ligands, batch_size)

    print(f"[2] Nombre de batches: {len(batches)}")
    # =========================
    # 3) PREPARER LES LIGANDS BATCHS
    # =========================
    converter = Ligand3DConverter()
    scrubber = LigandScrubber()

    ligands_preparator = LigandPreparator(
        converter=converter,
        scrubber=scrubber,
        work_dir= prepared_ligands_dir
    )

    ligand_batch_to_sdf = {}

    for batch in batches:
        clean_sdf = ligands_preparator.prepare_batch(batch)
        ligand_batch_to_sdf[batch.batch_id] = clean_sdf
        print(f"[3] Batch préparé: {batch.batch_id} -> {clean_sdf}")


    # =========================
    # 4) PREPARER LA PROTEINE
    # =========================

    downloader = ProteinDownloader()
    cleaner = ProteinCleaner()
    protein_converter = PDBQTConverter()

    protein_preparator = ProteinPreparator(
        downloader=downloader,
        cleaner=cleaner,
        converter=protein_converter,
        work_dir = receptor_work_dir
    )

    receptor_pdbqt_path, clean_pdb_path = protein_preparator.prepare(pdb_id, 7.4)
    print(f"[4] Clean PDB: {clean_pdb_path}")
    print(f"[4] Receptor PDBQT: {receptor_pdbqt_path}")

    # =========================
    # 5) DETECTER LES POCHES
    # =========================

    runner = P2RankRunner(p2rank_executable, work_dir=outputs_dir / "p2rank" / pdb_id)
    parser = P2RankResultParser()
    selector = PocketSelector()

    pocket_detector = PocketDetector(
        runner=runner,
        parser=parser,
        selector=selector,
    )

    top_5_pockets = pocket_detector.detect_top_5(clean_pdb_path)
    print(f"[5] Nombre de poches sélectionnées: {len(top_5_pockets)}")

    # =========================
    # 6) LANCER LA SESSION
    # =========================
    cmd_builder = GninaCommandBuilder()
    gnina_runner = GninaRunner(command_builder=cmd_builder)
    result_parser = GninaResultParser()
    result_writer = DockingResultWriter()
    probe_evaluator = ProbePocketEvaluator()


    session = VirtualScreeningSession(
        receptor_pdbqt_path=receptor_pdbqt_path,
        ligand_batches=batches,
        pockets=top_5_pockets,
        ligand_batch_to_sdf=ligand_batch_to_sdf,
        gnina_runner=gnina_runner,
        result_parser=result_parser,
        result_writer=result_writer,
        probe_evaluator=probe_evaluator,
        ligand_preparator=ligands_preparator,
        work_dir=outputs_dir / "gnina" / "gnina_session",
        probe_ligand_count=10,
        box_size=20,
        exhaustiveness=4,
        seed=0
    )

    results = session.run_standard()
    print(f"[DONE] Nombre de résultats finaux: {len(results)}")


if __name__ == "__main__":
    main()