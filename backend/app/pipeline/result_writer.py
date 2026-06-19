from pathlib import Path
import csv
from app.pipeline.models import DockingResult

class DockingResultWriter:
    """Écrit les résultats de docking en CSV."""

    def write_csv(self, results: list[DockingResult], output_csv_path: str | Path) -> Path:
        output_csv_path = Path(output_csv_path)
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ligand_id",
                    "batch_id",
                    "pocket_id",
                    "vina_affinity",
                    "cnn_pose_score",
                    "cnn_affinity",
                    "source_sdf",
                ],
            )
            writer.writeheader()
            for r in results:
                writer.writerow(
                    {
                        "ligand_id": r.ligand_id,
                        "batch_id": r.batch_id,
                        "pocket_id": r.pocket_id,
                        "vina_affinity": r.vina_affinity,
                        "cnn_pose_score": r.cnn_pose_score,
                        "cnn_affinity": r.cnn_affinity,
                        "source_sdf": str(r.source_sdf) if r.source_sdf else "",
                    }
                )

        return output_csv_path