import os
import sys
import multiprocessing
import uvicorn

os.environ["ROME_PROXY_API_KEY"] = "2556c1b210a01dfbd13890f570008950"

def base_dir():
    """Dossier de l'exe (mode gelé) ou du script (mode normal)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_api_key():
    key = os.environ.get("ROME_PROXY_API_KEY")
    if key:
        return key.strip()
    path = os.path.join(base_dir(), "api_key.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return None


if __name__ == "__main__":
    multiprocessing.freeze_support()

    key = load_api_key()
    if not key:
        print("Clé API absente : définissez ROME_PROXY_API_KEY "
              "ou créez un fichier api_key.txt à côté de l'exécutable.")
        input("Appuyez sur Entrée pour quitter...")
        sys.exit(1)

    # Doit être défini AVANT l'import de RomeProxy (la clé est lue à l'import)
    os.environ["ROME_PROXY_API_KEY"] = key

    from RomeProxy import app

    uvicorn.run(
        app,                  # objet, pas une chaîne
        host="127.0.0.1",     # localhost uniquement
        port=8000,
        reload=False,
    )
