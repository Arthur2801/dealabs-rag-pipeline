"""Charger les exports JSON dans MongoDB Atlas et créer l'index vectoriel."""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Dossier contenant les exports JSON (défaut : data/raw)",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprimer la collection MongoDB avant le chargement",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Créer ou remplacer l'index Atlas vector_index",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size doit être supérieur à zéro")
    if not args.data_dir.is_dir() or not any(args.data_dir.glob("*.json")):
        parser.error(f"Aucun export JSON dans {args.data_dir}")

    from dealabs_pipeline.indexing import Config, MigrationPipeline

    config = Config(data_dir=str(args.data_dir), batch_size=args.batch_size)
    if not config.mongo_uri:
        parser.error("MONGO_URI doit être renseigné dans .env")

    pipeline = MigrationPipeline(config)
    pipeline.run(reset=args.reset, create_index=args.create_index)


if __name__ == "__main__":
    main()
