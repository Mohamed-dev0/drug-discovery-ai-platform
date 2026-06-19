from .models import DockingJob
from pathlib import Path
import subprocess


class GninaCommandBuilder:
    """Construit la commande GNINA à partir d'un DockingJob."""

    def __init__(self):
        self.gnina_image = "gnina/gnina"
        self.host_project_dir = Path("/home/ubuntu/drug-discovery").resolve()
        self.container_project_dir = Path("/work")

    def to_container_path(self, path: str | Path) -> str:
        path = Path(path)

        if not path.is_absolute():
            path = self.host_project_dir / path

        relative_path = path.resolve().relative_to(self.host_project_dir)

        return str(self.container_project_dir / relative_path)

    def build(self, job: DockingJob) -> list[str]:
        receptor = self.to_container_path(job.receptor_pdbqt_path)
        ligand = self.to_container_path(job.ligand_sdf_path)
        output = self.to_container_path(job.output_sdf_path)

        return [
            "docker", "run", "--rm",
            "--gpus", "all",
            "-v", f"{self.host_project_dir}:{self.container_project_dir}",
            self.gnina_image,
            "gnina",

            "-r", receptor,
            "-l", ligand,

            "--center_x", str(job.docking_box.center_x),
            "--center_y", str(job.docking_box.center_y),
            "--center_z", str(job.docking_box.center_z),

            "--size_x", str(job.docking_box.size_x),
            "--size_y", str(job.docking_box.size_y),
            "--size_z", str(job.docking_box.size_z),

            "-o", output,

            "--seed", str(job.seed),
            "--exhaustiveness", str(job.exhaustiveness),
        ]

class GninaRunner:
    """Exécute GNINA pour un DockingJob."""

    def __init__(self, command_builder: GninaCommandBuilder):
        self.command_builder = command_builder

    def run(self, job: DockingJob) -> Path:
        job.output_sdf_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self.command_builder.build(job)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"GNINA failed for job {job.job_id}\n"
                f"CMD: {' '.join(cmd)}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        if not job.output_sdf_path.exists() or job.output_sdf_path.stat().st_size == 0:
            raise RuntimeError(f"GNINA output missing or empty: {job.output_sdf_path}")

        return job.output_sdf_path

