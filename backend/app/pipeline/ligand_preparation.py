import subprocess
from pathlib import Path

import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem

from app.pipeline.models import LigandBatch, Ligand


class Ligand3DConverter:
    """Convertit un ligand SMILES en molécule RDKit 3D."""

    def convert(self, ligand_id: str, smiles: str):
        if not smiles:
            return None

        mol = Chem.MolFromSmiles(str(smiles))

        if mol is None:
            return None

        # Ajouter les hydrogènes avant la génération 3D
        mol_h = Chem.AddHs(mol)

        # Important : définir le nom après AddHs
        mol_h.SetProp("_Name", str(ligand_id))

        # Génération 3D avec ETKDGv3
        params = AllChem.ETKDGv3()
        result = AllChem.EmbedMolecule(mol_h, params)

        if result == -1:
            return None

        # Optimisation géométrique
        try:
            AllChem.MMFFOptimizeMolecule(mol_h)
        except Exception:
            pass

        return mol_h


class LigandScrubber:
    """
    Nettoie un fichier SDF avec scrub.py.

    Entrée :
    - ligands_dirty_batch_x.sdf

    Sortie :
    - ligands_clean_batch_x.sdf
    """

    def __init__(self, scrub_command: str = "scrub.py"):
        self.scrub_command = scrub_command

    def scrub(self, input_file: str | Path, output_file: str | Path) -> Path:
        input_file = Path(input_file)
        output_file = Path(output_file)

        if not input_file.exists():
            raise FileNotFoundError(f"Input SDF file not found: {input_file}")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        command = [
            self.scrub_command,
            str(input_file),
            "-o",
            str(output_file),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Scrubbing failed for {input_file}\n"
                f"CMD: {' '.join(command)}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )

        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError(f"Scrubbed output missing or empty: {output_file}")

        return output_file


class BatchBuilder:
    """Découpe une librairie de ligands en batches."""

    def build(self, ligands: list[Ligand], batch_size: int) -> list[LigandBatch]:
        if len(ligands) == 0:
            raise ValueError("There are 0 ligands.")

        if batch_size <= 0:
            raise ValueError("Batch size must be greater than 0.")

        batches: list[LigandBatch] = []

        for batch_index, start in enumerate(range(0, len(ligands), batch_size), start=1):
            ligands_split = ligands[start:start + batch_size]

            batch = LigandBatch(
                batch_id=f"batch_{batch_index}",
                ligands=ligands_split,
            )

            batches.append(batch)

        return batches


class LigandPreparator:
    """
    Orchestre la préparation d'un batch :

    LigandBatch
    -> conversion 3D
    -> écriture dirty.sdf
    -> scrub.py
    -> clean.sdf
    """

    def __init__(
        self,
        converter: Ligand3DConverter,
        scrubber: LigandScrubber,
        work_dir: str | Path,
    ):
        self.converter = converter
        self.scrubber = scrubber
        self.work_dir = Path(work_dir)

    def prepare_batch(self, batch: LigandBatch) -> Path:
        self.work_dir.mkdir(parents=True, exist_ok=True)

        dirty_file = self.work_dir / f"ligands_dirty_{batch.batch_id}.sdf"
        clean_file = self.work_dir / f"ligands_clean_{batch.batch_id}.sdf"

        writer = Chem.SDWriter(str(dirty_file))
        written_count = 0

        try:
            for ligand in batch.ligands:
                ligand_3d = self.converter.convert(
                    ligand_id=ligand.ligand_id,
                    smiles=ligand.smiles,
                )

                if ligand_3d is None:
                    continue

                writer.write(ligand_3d)
                written_count += 1

        finally:
            writer.close()

        if written_count == 0:
            raise ValueError(
                f"No valid ligands could be prepared for {batch.batch_id}"
            )

        self.scrubber.scrub(dirty_file, clean_file)

        return clean_file


class CSVLigandReader:
    """Lit un CSV de ligands et transforme les lignes en objets Ligand."""

    def __init__(
        self,
        smiles_column: str = "smiles",
        id_column: str | None = "mol_id",
    ):
        self.smiles_column = smiles_column.lower()
        self.id_column = id_column.lower() if id_column else None

    def read(self, file_path: str | Path) -> list[Ligand]:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        df = pd.read_csv(file_path)

        df.columns = df.columns.str.lower().str.strip()

        if self.smiles_column not in df.columns:
            raise ValueError(
                f"Column '{self.smiles_column}' not found in {file_path.name}"
            )

        ligands: list[Ligand] = []

        for index, row in df.iterrows():
            smiles = row[self.smiles_column]

            if pd.isna(smiles):
                continue

            smiles = str(smiles).strip()

            if not smiles:
                continue

            if self.id_column and self.id_column in df.columns:
                raw_id = row[self.id_column]

                if pd.isna(raw_id) or str(raw_id).strip() == "":
                    ligand_id = f"lig_{index + 1}"
                else:
                    ligand_id = str(raw_id).strip()
            else:
                ligand_id = f"lig_{index + 1}"

            ligand = Ligand(
                ligand_id=ligand_id,
                smiles=smiles,
            )

            ligands.append(ligand)

        if len(ligands) == 0:
            raise ValueError(f"No valid ligands found in {file_path}")

        return ligands