from pathlib import Path
import subprocess
from app.pipeline.models import Pocket
import pandas as pd



class P2RankRunner:
    """Exécute P2Rank sur une protéine propre."""

    def __init__(self, p2rank_executable, work_dir):
        self.p2rank_executable = Path(p2rank_executable)
        self.work_dir = Path(work_dir)

    def run(self, pdb_file):
        pdb_file = Path(pdb_file)

        if not pdb_file.exists():
            raise FileNotFoundError(f"PDB file not found: {pdb_file}")

        self.work_dir.mkdir(parents=True, exist_ok=True)

        output_dir = self.work_dir / f"{pdb_file.stem}_p2rank"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.p2rank_executable),
            "predict",
            "-f",
            str(pdb_file),
            "-o",
            str(output_dir),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"P2Rank failed (code {result.returncode}).\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        return output_dir

class P2RankResultParser:
    """Parse les résultats CSV de P2Rank en objets Pocket."""

    def parse(self, output_dir):
        output_dir = Path(output_dir)

        csv_files = list(output_dir.glob("*_predictions.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No *_predictions.csv found in {output_dir}")

        predictions_csv = csv_files[0]
        df = pd.read_csv(predictions_csv)
        df.columns = df.columns.str.strip()

        pockets = []

        for _, row in df.iterrows():
            pocket = Pocket(
                pocket_id=str(row["name"].strip()),
                rank=int(row["rank"]),
                score=float(row["score"]),
                center_x=float(row["center_x"]),
                center_y=float(row["center_y"]),
                center_z=float(row["center_z"]),
                sas_points=int(row["sas_points"]) if "sas_points" in df.columns and pd.notna(row["sas_points"]) else None,
            )
            pockets.append(pocket)

        return pockets

class PocketSelector:
    """Sélectionne les top poches."""

    def select_top_5(self, pockets):
        if not pockets:
            return []

        pockets_sorted = sorted(pockets, key=lambda p: p.rank)
        return pockets_sorted[:5]


class PocketDetector:
    """Orchestre la détection de poches avec P2Rank."""

    def __init__(self, runner, parser, selector):
        self.runner = runner
        self.parser = parser
        self.selector = selector

    def detect_top_5(self, pdb_file):
        output_dir = self.runner.run(pdb_file)
        pockets = self.parser.parse(output_dir)
        top_5 = self.selector.select_top_5(pockets)
        return top_5