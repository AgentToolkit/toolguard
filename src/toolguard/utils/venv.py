import os
import subprocess
import venv
# import sys
# import ensurepip

def run(venv_dir: str, packages: list[str]):
    # Bootstrap pip if not present
    # try:
    #     import pip
    # except ImportError:
    #     ensurepip.bootstrap(upgrade=True)

    # subprocess.run([sys.executable, "-m", "pip", "install"] + packages, check=True)


    # Create the virtual environment
    venv.create(venv_dir, with_pip=True)
    #
    # #install packages
    pip_executable = os.path.join(venv_dir, "bin", "pip")
    subprocess.run([pip_executable, "install"] + packages, check=True)