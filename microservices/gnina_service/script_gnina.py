from pdbfixer import PDBFixer
from openmm.app import PDBFile
import os
import subprocess
from rdkit import Chem
import pandas as pd
from pathlib import Path
from fastapi import HTTPException
import numpy as np
from microservices.p2rank_services.script_p2Rank import run_p2rank_cli


def prepare_protein(protein_filepath: str, pH: float = 7.0) -> Path:
    """
    Prepare a protein for docking (PDB -> cleaned PDB -> PDBQT).

    Assumptions used in this preparation:
    - pH assumed to be physiological (~7.0)
    - Protein treated as rigid (no relaxation/minimization)
    - Standard residue protonation states (no local pKa effects)
    - All heterogens removed (including waters, ligands, ions/cofactors)
    """

    docking_file = Path("docking_file")
    receptor_dir = docking_file / "receptor"
    receptor_dir.mkdir(parents=True, exist_ok=True)


    if not os.path.exists(protein_filepath):
        raise FileNotFoundError(f"PDB file not found: {protein_filepath}")

    # Initialize PDBFixer
    fixer = PDBFixer(filename=protein_filepath)

    # Identify missing residues (information step)
    fixer.findMissingResidues()

    # Replace non-standard residues (compatibility assumption)
    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()

    # Remove waters + other heterogens (strong assumption)
    fixer.removeHeterogens(keepWater=False)

    # Add missing heavy atoms / terminals
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()

    # Re-check missing atoms after fix
    fixer.findMissingAtoms()
    if fixer.missingAtoms or fixer.missingTerminals:
        raise ValueError(
            f"Missing atoms/terminals remain after addMissingAtoms(): "
            f"missingAtoms={len(fixer.missingAtoms)}, missingTerminals={len(fixer.missingTerminals)}"
        )

    # Add hydrogens with assumed pH
    fixer.addMissingHydrogens(pH=pH)

    # Write cleaned PDB
    protein_name = Path(protein_filepath).stem
    clean_path = receptor_dir / f"{protein_name}_clean.pdb"
    with open(clean_path, "w") as f:
        PDBFile.writeFile(fixer.topology, fixer.positions, f, keepIds=True)

    # Convert to PDBQT using OpenBabel
    receptor_pdbqt_path = receptor_dir / f"{protein_name}.pdbqt"
    cmd = ["obabel", "-ipdb", clean_path, "-opdbqt", "-O", receptor_pdbqt_path]
    result = subprocess.run(cmd, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"OpenBabel failed (code {result.returncode}).\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    if not os.path.exists(receptor_pdbqt_path) or os.path.getsize(receptor_pdbqt_path) == 0:
        raise RuntimeError(f"PDBQT output missing or empty: {receptor_pdbqt_path}")

    return receptor_pdbqt_path, clean_path



def prepare_ligand(ligands_input):

  docking_file = Path("docking_file")
  ligand_directory = docking_file / "ligands_structures"
  ligand_directory.mkdir(parents=True, exist_ok=True)

  input_path = Path(ligands_input)
  ext = input_path.suffix.lower()

  if ext == ".csv":
    #first case : Multiple ligands from smiles strings
    smiles_supplier = Chem.SmilesMolSupplier(str(input_path), delimiter=",")

    mols = []
    for mol in smiles_supplier:
      if mol is None:
        continue
      mols.append(mol)

    if not mols:
       raise ValueError("No valid SMILES found in the CSV.")

    # Write out our molecules
    ligands_to_dock_dirty = ligand_directory / "ligands_to_dock_dirty.sdf"
    writer = Chem.SDWriter(ligands_to_dock_dirty)
    for m in mols:
      writer.write(m)
    writer.close()

    #Scrubber to clean the ligands
    ligands_clean = ligand_directory /"ligands_to_dock.sdf"

    scrub_cmd = ["scrub.py", str(ligands_to_dock_dirty), "-o", str(ligands_clean)]
    subprocess.run(scrub_cmd, check=True)

    return str(ligands_clean)


  # -------- Case 2: Single ligand file (sdf/mol2/pdb/...) --------
  else:
      ligand_clean = ligand_directory / "ligand_clean.sdf"
      scrub_cmd = ["scrub.py", str(input_path), "-o", str(ligand_clean)]
      subprocess.run(scrub_cmd, check=True)

      ligand_pdbqt = ligand_directory / "ligand.pdbqt"
      obabel_cmd = ["obabel", str(ligand_clean), "-O", str(ligand_pdbqt), "-xh"]
      subprocess.run(obabel_cmd, check=True)

      return str(ligand_pdbqt)


def run_gnina(receptor_pdbqt_path, clean_path, ligand_pdbqt_path):

  output_dir = Path("output_dir")
  output_dir.mkdir(parents=True, exist_ok=True)

  receptor_filename = os.path.basename(receptor_pdbqt_path)
  ligand_filename = os.path.basename(ligand_pdbqt_path)


  run_p2rank_cli(clean_path, output_dir)



  input_name = Path(clean_path).stem
  predictions_csv = output_dir / f"{input_name}.pdb_predictions.csv"
  if not predictions_csv.exists():
      raise HTTPException(status_code=500, detail="P2Rank did not generate the _predictions.csv file.")

  df = pd.read_csv(predictions_csv)
  df.columns = df.columns.str.strip()

  df_first_pocket = df.head(1)

  center_x = df_first_pocket.loc[0,"center_x"].astype(np.float64)
  center_y = df_first_pocket.loc[0,"center_y"].astype(np.float64)
  center_z = df_first_pocket.loc[0,"center_z"].astype(np.float64)

  size = 40

  abs_path_docking_file = os.path.abspath("./docking_file")

  gnina_cmd = ["docker", "run", "--rm",
               "--gpus", "all",
               "-v", f"{abs_path_docking_file}:/data",
               "gnina/gnina",
               "gnina",
               "-r", f"/data/receptor/{receptor_filename}",
               "-l", f"/data/ligands_structures/{ligand_filename}",
               "--center_x", str(center_x),
               "--size_x", str(size),
               "--center_y", str(center_y),
               "--size_y", str(size),
               "--center_z", str(center_z),
               "--size_z", str(size),
               "-o", f"/data/docked_{receptor_filename.split('.')[0]}.sdf",
               "--seed", "0",
               "--exhaustiveness", "16"]

  out_sdf = Path(abs_path_docking_file) / f"docked_{receptor_filename.split('.')[0]}.sdf"



  try:
      # Capture output explicitly to print it on error
      gnina_results = subprocess.run(gnina_cmd, text=True, check=True)
  except subprocess.CalledProcessError as e:
      print("--- GNINA STDOUT ---")
      print(e.stdout)
      print("--- GNINA STDERR ---")
      print(e.stderr)
      raise

  if not out_sdf.exists():
      raise HTTPException(status_code=500, detail="GNINA did not generate output SDF.")

  return gnina_results.stdout