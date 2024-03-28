import sys, os
import subprocess
from pathlib import Path


def main():
    # Path to your bash script
    p = Path(__file__).absolute()
    pp = str(p.parent)

    # script_path = 'parkit_pkg/scripts/parkit_folder2hpcdme'
    script_path = os.path.join(pp, "scripts", "parkit_folder2hpcdme")

    # Pass all arguments to the bash script
    subprocess.run([script_path] + sys.argv[1:])


if __name__ == "__main__":
    main()
