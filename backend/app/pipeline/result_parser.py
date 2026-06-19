from __future__ import annotations
from pathlib import Path
from typing import Optional
from rdkit import Chem
from app.pipeline.models import (
    LigandBatch,
    Pocket,
    DockingResult,
)

class GninaResultParser:
    """
    Parse un SDF GNINA.
    Tolérant sur les noms de propriétés, car ils peuvent varier selon la sortie.
    """

    VINA_KEYS = ["minimizedAffinity", "Affinity", "VINA_Affinity", "vina_affinity"]
    CNN_POSE_KEYS = ["CNNscore", "CNN_pose_score", "cnn_pose_score"]
    CNN_AFF_KEYS = ["CNNaffinity", "CNN_affinity", "cnn_affinity"]

    def _get_first_float(self, mol: Chem.Mol, candidate_keys: list[str]) -> Optional[float]:
        for key in candidate_keys:
            if mol.HasProp(key):
                try:
                    return float(mol.GetProp(key))
                except ValueError:
                    continue
        return None

    def parse(self, sdf_path: str | Path, batch: LigandBatch, pocket: Pocket) -> list[DockingResult]:
        sdf_path = Path(sdf_path)

        if not sdf_path.exists():
            raise FileNotFoundError(f"SDF file not found: {sdf_path}")

        suppl = Chem.SDMolSupplier(str(sdf_path), removeHs=False)
        results: list[DockingResult] = []

        fallback_index = 0

        for mol in suppl:
            if mol is None:
                continue

            ligand_id = mol.GetProp("_Name") if mol.HasProp("_Name") else None

            if not ligand_id:
                if fallback_index < len(batch.ligands):
                    ligand_id = batch.ligands[fallback_index].ligand_id
                else:
                    ligand_id = f"{batch.batch_id}_lig_{fallback_index + 1}"

            result = DockingResult(
                ligand_id=ligand_id,
                batch_id=batch.batch_id,
                pocket_id=pocket.pocket_id,
                vina_affinity=self._get_first_float(mol, self.VINA_KEYS),
                cnn_pose_score=self._get_first_float(mol, self.CNN_POSE_KEYS),
                cnn_affinity=self._get_first_float(mol, self.CNN_AFF_KEYS),
                source_sdf=sdf_path,
            )
            results.append(result)
            fallback_index += 1

        return results