from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Ligand:
    """Represent a ligand."""
    ligand_id: str
    smiles: str


@dataclass
class LigandBatch:
    """Represent a group of ligands."""
    batch_id: str
    ligands: list[Ligand]

    def __len__(self) -> int:
        return len(self.ligands)


@dataclass
class Protein:
    """Represent a protein identified by a PDB ID."""
    pdb_id: str
    pdb_file: Optional[Path] = None


@dataclass
class Pocket:
    """Represent a pocket predicted by P2Rank."""
    pocket_id: str
    rank: int
    score: float
    center_x: float
    center_y: float
    center_z: float
    sas_points: Optional[int] = None


@dataclass
class DockingBox:
    """Represent the 3D search box used by GNINA."""
    center_x: float
    center_y: float
    center_z: float
    size_x: float = 20.0
    size_y: float = 20.0
    size_z: float = 20.0


@dataclass
class DockingJob:
    """Represent one task GNINA docking job."""
    job_id: str
    receptor_pdbqt_path: Path
    ligand_sdf_path: Path
    batch: LigandBatch
    pocket: Pocket
    docking_box: DockingBox
    output_sdf_path: Path
    exhaustiveness: int = 16
    seed: int = 0


@dataclass
class DockingResult:
    """Represent one parsed GNINA docking result."""
    ligand_id: str
    batch_id: str
    pocket_id: str
    vina_affinity: Optional[float] = None
    cnn_pose_score: Optional[float] = None
    cnn_affinity: Optional[float] = None
    source_sdf: Optional[Path] = None