import subprocess
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()



P2RANK_BIN = Path("/opt/p2rank/p2rank_2.5.1/prank")



def run_p2rank_cli(pdb_path: Path, output_dir: Path):
    pdb_path = Path(pdb_path).resolve()
    output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(P2RANK_BIN),   # prank
        "predict",
        "-f", str(pdb_path),
        "-o", str(output_dir),
    ]

    subprocess.run(cmd, check=True)



