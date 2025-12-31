import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


if os.name == 'nt': # Windows
    LAUNCHER = os.getenv("GIT_BASH", r"C:\Program Files\Git\bin\bash.exe")
else: # Linux / Mac
    LAUNCHER = "sh"
P2RANK_DISTRO = Path(os.getenv("P2RANK_DISTRO", r".\p2rank\distro")).resolve()
P2RANK_BIN = Path(os.getenv("P2RANK_BIN", str(P2RANK_DISTRO / "prank"))).resolve()


def run_p2rank_cli(pdb_path: Path, output_dir: Path):
    pdb_path = Path(pdb_path).resolve()
    output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        LAUNCHER,
        str(P2RANK_BIN),   # prank
        "predict",
        "-f", str(pdb_path),
        "-o", str(output_dir),
    ]

    subprocess.run(cmd, check=True, cwd=str(P2RANK_DISTRO))


if __name__ == "__main__":
    import sys

    # Usage: python run_p2rank.py <pdb_path> <output_dir>
    if len(sys.argv) != 3:
        print("Usage: python run_p2rank.py <pdb_path> <output_dir>")
        print("Optional env vars: LAUNCHER, P2RANK_DISTRO, P2RANK_BIN")
        raise SystemExit(2)

    pdb_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    run_p2rank_cli(pdb_path, output_dir)
    print("Done.")
