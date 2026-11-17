import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))  # el paquete vive en src/
from phishguard.training import train
if __name__ == "__main__":
    train()
