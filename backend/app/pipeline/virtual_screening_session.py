import random
from pathlib import Path

from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingBox,
    DockingJob,
    DockingResult,
)

from app.pipeline.docking import GninaRunner
from app.pipeline.ligand_preparation import LigandPreparator
from app.pipeline.result_parser import GninaResultParser
from app.pipeline.result_writer import DockingResultWriter
from app.pipeline.probe_evaluator import ProbePocketEvaluator
from app.pipeline.payload import docking_job_to_payload
from app.workers.tasks import run_real_gnina_job



class VirtualScreeningSession:
    """
    Orchestre Tier Standard .
    Le principe:
    - Standard: probe docking sur les 100 ligands aléatoires à travers les top 5 poches,
      puis full docking de toute la librairie sur la poche gagnante.
    """

    def __init__(
            self,
            receptor_pdbqt_path: str | Path,
            ligand_batches: list[LigandBatch],
            pockets: list[Pocket],
            ligand_batch_to_sdf: dict[str, Path],
            gnina_runner: GninaRunner,
            result_parser: GninaResultParser,
            result_writer: DockingResultWriter,
            probe_evaluator: ProbePocketEvaluator,
            ligand_preparator: LigandPreparator,
            work_dir: str | Path,
            probe_ligand_count: int = 100,
            box_size: float = 20.0,
            exhaustiveness: int = 16,
            seed: int = 0,
    ):
        self.receptor_pdbqt_path = Path(receptor_pdbqt_path)
        self.ligand_batches = ligand_batches
        self.pockets = pockets
        self.ligand_batch_to_sdf = ligand_batch_to_sdf
        self.gnina_runner = gnina_runner
        self.result_parser = result_parser
        self.result_writer = result_writer
        self.probe_evaluator = probe_evaluator
        self.ligand_preparator = ligand_preparator
        self.work_dir = Path(work_dir)
        self.probe_ligand_count = probe_ligand_count
        self.box_size = box_size
        self.exhaustiveness = exhaustiveness
        self.seed = seed


    def _make_box(self, pocket: Pocket) -> DockingBox:
        return DockingBox(
            center_x=pocket.center_x,
            center_y=pocket.center_y,
            center_z=pocket.center_z,
            size_x=self.box_size,
            size_y=self.box_size,
            size_z=self.box_size,
        )

    def _make_job(self, batch: LigandBatch, pocket: Pocket) -> DockingJob:
        batch_sdf = self.ligand_batch_to_sdf[batch.batch_id]
        output_dir = self.work_dir / "gnina_outputs" / pocket.pocket_id
        output_sdf = output_dir / f"docked_{batch.batch_id}_{pocket.pocket_id}.sdf"

        return DockingJob(
            job_id=f"{batch.batch_id}__{pocket.pocket_id}",
            receptor_pdbqt_path=self.receptor_pdbqt_path,
            ligand_sdf_path=batch_sdf,
            batch=batch,
            pocket=pocket,
            docking_box=self._make_box(pocket),
            output_sdf_path=output_sdf,
            exhaustiveness=self.exhaustiveness,
            seed=self.seed,
        )

    def _run_job_and_parse(self, job: DockingJob) -> list[DockingResult]:
        sdf_path = self.gnina_runner.run(job)
        results = self.result_parser.parse(sdf_path, batch=job.batch, pocket=job.pocket)
        return results

    def _select_probe_batch(self) -> LigandBatch:
        """
        Sélectionne aléatoirement des ligands dans toute la librairie
        pour créer un batch probe unique.
        """

        all_ligands = [
            ligand
            for batch in self.ligand_batches
            for ligand in batch.ligands
        ]

        if not all_ligands:
            raise ValueError("No ligands available for probe selection.")

        sample_size = min(self.probe_ligand_count, len(all_ligands))

        rng = random.Random(self.seed)
        selected_ligands = rng.sample(all_ligands, sample_size)

        return LigandBatch(
            batch_id=f"probe_random_{sample_size}",
            ligands=selected_ligands,
        )

    def _job_to_payload(self, job: DockingJob) -> dict:
        payload = docking_job_to_payload(job)
        return payload

    def _run_jobs_celery(self, jobs: list[DockingJob]) -> list[DockingResult]:
        celery_tasks = []

        for job in jobs:
            payload = self._job_to_payload(job)
            task = run_real_gnina_job.delay(payload)
            celery_tasks.append((task, job))

        all_results: list[DockingResult] = []

        for task, job in celery_tasks:
            celery_response = task.get(timeout=3600)

            if celery_response["status"] != "success":
                print(f"[ERROR] Job failed: {job.job_id}")
                print(celery_response)
                continue

            output_sdf_path = Path(celery_response["output_sdf_path"])

            job_results = self.result_parser.parse(
                output_sdf_path,
                batch=job.batch,
                pocket=job.pocket,
            )

            all_results.extend(job_results)

            print(
                f"[OK] Job terminé : {job.job_id} | "
                f"{len(job_results)} résultats parsés"
            )

        return all_results

    def run_standard(self) -> list[DockingResult]:
        # 1. Sélection aléatoire des ligands probe
        probe_batch = self._select_probe_batch()

        # 2. Préparation du SDF probe
        probe_sdf_path = self.ligand_preparator.prepare_batch(probe_batch)

        # 3. Construire les probe jobs : même batch aléatoire sur chaque poche
        probe_jobs: list[DockingJob] = []

        for pocket in self.pockets:
            probe_job = DockingJob(
                job_id=f"{probe_batch.batch_id}__{pocket.pocket_id}",
                receptor_pdbqt_path=self.receptor_pdbqt_path,
                ligand_sdf_path=probe_sdf_path,
                batch=probe_batch,
                pocket=pocket,
                docking_box=self._make_box(pocket),
                output_sdf_path=(
                        self.work_dir
                        / "probe_outputs"
                        / pocket.pocket_id.strip()
                        / f"docked_{probe_batch.batch_id}_{pocket.pocket_id.strip()}.sdf"
                ),
                exhaustiveness=self.exhaustiveness,
                seed=self.seed,
            )

            probe_jobs.append(probe_job)

        # 4. Lancer les probe jobs avec Celery
        probe_results = self._run_jobs_celery(probe_jobs)

        if not probe_results:
            raise ValueError("No probe results returned. Cannot select best pocket.")

        # 5. Sélectionner la meilleure poche
        best_pocket_id = self.probe_evaluator.select_best_pocket(probe_results)

        best_pocket = next(
            pocket for pocket in self.pockets
            if pocket.pocket_id.strip() == best_pocket_id.strip()
        )

        print(f"[INFO] Best pocket selected for full docking: {best_pocket.pocket_id}")

        # 6. Construire les jobs finaux sur la meilleure poche
        final_jobs = [
            self._make_job(batch, best_pocket)
            for batch in self.ligand_batches
        ]

        # 7. Lancer les jobs finaux avec Celery
        all_results = self._run_jobs_celery(final_jobs)

        # 8. Garder le meilleur résultat par ligand
        best_by_ligand: dict[str, DockingResult] = {}

        for result in all_results:
            ligand_id = self._get_original_ligand_id(result.ligand_id)

            if ligand_id not in best_by_ligand:
                best_by_ligand[ligand_id] = result
                continue

            current = best_by_ligand[ligand_id]

            if result.cnn_pose_score is not None and current.cnn_pose_score is not None:
                if result.cnn_pose_score > current.cnn_pose_score:
                    best_by_ligand[ligand_id] = result

            elif result.cnn_pose_score is not None and current.cnn_pose_score is None:
                best_by_ligand[ligand_id] = result

        final_results = list(best_by_ligand.values())

        self.result_writer.write_csv(
            final_results,
            self.work_dir / "results_standard.csv",
        )

        return final_results

    def _get_original_ligand_id(self, ligand_id: str) -> str:
        """
        Convertit un ligand préparé en ligand original.

        Exemple :
        lig_12_i0 -> lig_12
        lig_12_i4 -> lig_12
        lig_13 -> lig_13
        """

        if "_i" in ligand_id:
            return ligand_id.split("_i")[0]

        return ligand_id