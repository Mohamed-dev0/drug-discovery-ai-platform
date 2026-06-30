from pathlib import Path
import subprocess
import requests
from pdbfixer import PDBFixer
from openmm.app import PDBFile
from app.pipeline.models import Protein


class ProteinDownloader:
    """Télécharge le fichier PDB d'une protéine depuis la RCSB."""
    def download(self, protein, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{protein.pdb_id}.pdb"
        url = f"https://files.rcsb.org/download/{protein.pdb_id}.pdb"

        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as e:
            raise RuntimeError(f"Download request failed for {protein.pdb_id}: {e}") from e

        if response.status_code != 200:
            raise RuntimeError(
                f"Download failed for {protein.pdb_id} with status code {response.status_code}"
            )

        with open(output_path, "wb") as f:
            f.write(response.content)

        protein.pdb_file = output_path
        return output_path


class ProteinCleaner:
    """Nettoie un fichier PDB et produit un clean.pdb."""
    def clean(self, pdb_file, output_dir, pH: float = 7.4):
        pdb_file = Path(pdb_file)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not pdb_file.exists():
            raise FileNotFoundError(f"PDB file not found: {pdb_file}")

        fixer = PDBFixer(filename=str(pdb_file))

        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()

        fixer.removeHeterogens(keepWater=False)

        fixer.findMissingAtoms()
        fixer.addMissingAtoms()

        fixer.findMissingAtoms()
        if fixer.missingAtoms or fixer.missingTerminals:
            raise ValueError(
                "Missing atoms/terminals remain after addMissingAtoms(): "
                f"missingAtoms={len(fixer.missingAtoms)}, "
                f"missingTerminals={len(fixer.missingTerminals)}"
            )

        fixer.addMissingHydrogens(pH=pH)

        protein_name = pdb_file.stem
        clean_path = output_dir / f"{protein_name}_clean.pdb"

        with open(clean_path, "w") as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f, keepIds=True)

        return clean_path


class PDBQTConverter:
    """Convertit un clean.pdb en pdbqt via OpenBabel."""
    def convert(self, clean_pdb_path, output_dir):
        clean_pdb_path = Path(clean_pdb_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not clean_pdb_path.exists():
            raise FileNotFoundError(f"Clean PDB file not found: {clean_pdb_path}")

        protein_name = clean_pdb_path.stem.replace("_clean", "")
        receptor_pdbqt_path = output_dir / f"{protein_name}.pdbqt"

        cmd = [
            "obabel",
            "-ipdb",
            str(clean_pdb_path),
            "-opdbqt",
            "-O",
            str(receptor_pdbqt_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"OpenBabel failed (code {result.returncode}).\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        if not receptor_pdbqt_path.exists() or receptor_pdbqt_path.stat().st_size == 0:
            raise RuntimeError(f"PDBQT output missing or empty: {receptor_pdbqt_path}")

        return receptor_pdbqt_path


class ProteinPreparator:
    """Orchestre la préparation : téléchargement -> clean.pdb -> pdbqt."""
    def __init__(self, downloader, cleaner, converter, work_dir):
        self.downloader = downloader
        self.cleaner = cleaner
        self.converter = converter
        self.work_dir = Path(work_dir)

    def prepare(self, pdb_id: str, pH: float = 7.4):
        protein = Protein(pdb_id=pdb_id)

        self.work_dir.mkdir(parents=True, exist_ok=True)

        raw_dir = self.work_dir / "raw"
        receptor_dir = self.work_dir / "receptor"

        pdb_path = self.downloader.download(protein, raw_dir)

        clean_path = self.cleaner.clean(
            pdb_file=pdb_path,
            output_dir=receptor_dir,
            pH=pH,
        )

        if not clean_path.exists():
            raise RuntimeError(f"Clean PDB was not created: {clean_path}")

        receptor_pdbqt_path = self.converter.convert(
            clean_pdb_path=clean_path,
            output_dir=receptor_dir,
        )

        return receptor_pdbqt_path, clean_path
