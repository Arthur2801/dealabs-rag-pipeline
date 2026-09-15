"""
Module d'indexation vectorielle des deals dans MongoDB Atlas.

Ce module permet de :
    1. Charger les deals depuis des fichiers JSON
    2. Générer des embeddings vectoriels avec sentence-transformers
    3. Insérer les deals avec leurs embeddings dans MongoDB Atlas
    4. Créer un index de recherche vectorielle Atlas pour les requêtes RAG

Architecture:
    - SentenceTransformer pour la vectorisation (paraphrase-multilingual-MiniLM-L12-v2)
    - MongoDB Atlas comme base de données vectorielle
    - Search Index pour la recherche par similarité cosine
    - Traitement par batches pour optimiser les performances

Auteur: Projet Master Big Data
Date: Janvier 2026
"""

import json
import time
import os
import glob
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from pymongo.operations import SearchIndexModel
from sentence_transformers import SentenceTransformer

# Configuration du chemin racine du projet (3 niveaux au-dessus du fichier actuel)
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class MongoDBConnectionError(Exception):
    """Exception levée lors d'une erreur de connexion à MongoDB."""

    pass


class EmbeddingError(Exception):
    """Exception levée lors d'une erreur de génération d'embedding."""

    pass


@dataclass
class Config:
    """
    Configuration pour l'indexation vectorielle.

    Attributes:
        model_id (str): Identifiant du modèle SentenceTransformer
        embedding_dims (int): Dimension des vecteurs d'embedding (384 pour MiniLM-L12-v2)
        mongo_uri (str): URI de connexion MongoDB Atlas
        db_name (str): Nom de la base de données
        collection_name (str): Nom de la collection
        index_name (str): Nom de l'index de recherche vectorielle
        data_dir (str): Répertoire contenant les fichiers JSON de deals
        batch_size (int): Taille des batches pour l'insertion
    """

    model_id: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dims: int = 384
    mongo_uri: str = os.getenv("MONGO_URI", "")
    db_name: str = "deals_db"
    collection_name: str = "deals"
    index_name: str = "vector_index"
    data_dir: str = str(PROJECT_ROOT / "data" / "raw")
    batch_size: int = 50


class EmbeddingService:
    """
    Gère la génération d'embeddings vectoriels via SentenceTransformer.

    Ce service charge un modèle pré-entraîné et génère des vecteurs
    d'embedding pour du texte, permettant la recherche sémantique.

    Attributes:
        embedding_dims (int): Dimension des vecteurs produits
        model (SentenceTransformer): Modèle de génération d'embeddings
    """

    def __init__(self, model_id: str, embedding_dims: int):
        """
        Initialise le service d'embedding avec un modèle spécifique.

        Args:
            model_id (str): Identifiant du modèle HuggingFace
            embedding_dims (int): Dimension attendue des vecteurs
        """
        self.embedding_dims = embedding_dims
        print(f"Chargement du modèle {model_id}...")
        self.model = SentenceTransformer(model_id)
        print("Modèle chargé")

    def embed(self, text: str) -> list[float]:
        """
        Génère un vecteur d'embedding pour un texte donné.

        Args:
            text (str): Texte à vectoriser

        Returns:
            list[float]: Vecteur d'embedding

        Raises:
            EmbeddingError: Si la génération d'embedding échoue
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            raise EmbeddingError(f"Echec de l'embedding: {e}")


class MongoDBClient:
    """
    Gère la connexion et les opérations sur MongoDB Atlas.

    Ce client permet de :
        - Se connecter à MongoDB Atlas
        - Réinitialiser/créer des collections
        - Insérer des documents par batches
        - Créer des index de recherche vectorielle

    Attributes:
        config (Config): Configuration de connexion
        client (MongoClient): Client MongoDB
        db (Database): Base de données active
        collection (Collection): Collection active
    """

    def __init__(self, config: Config):
        """
        Initialise et connecte le client MongoDB.

        Args:
            config (Config): Configuration contenant URI et noms de DB/collection
        """
        self.config = config
        self._connect()

    def _connect(self):
        """
        Établit la connexion à MongoDB Atlas.

        Raises:
            MongoDBConnectionError: Si la connexion échoue
        """
        try:
            self.client = MongoClient(self.config.mongo_uri)
            self.db = self.client[self.config.db_name]
            self.collection = self.db[self.config.collection_name]
            self.client.admin.command("ping")
            print("Connecté à MongoDB Atlas")
        except Exception as e:
            raise MongoDBConnectionError(f"Impossible de se connecter: {e}")

    def reset_collection(self):
        """
        Supprime et recrée la collection (RAZ complète).
        """
        if self.config.collection_name in self.db.list_collection_names():
            self.collection.drop()
            print(f"Collection '{self.config.collection_name}' supprimée")
        else:
            print(f"Collection '{self.config.collection_name}' inexistante, création...")

    def insert_batch(self, documents: list[dict]) -> tuple[int, int]:
        """
        Insère un batch de documents dans la collection.

        Utilise insert_many avec ordered=False pour continuer même en cas d'erreur
        sur certains documents (ex: doublons).

        Args:
            documents (list[dict]): Liste de documents à insérer

        Returns:
            tuple[int, int]: (nombre_insérés, nombre_échoués)
        """
        if not documents:
            return 0, 0

        try:
            result = self.collection.insert_many(documents, ordered=False)
            return len(result.inserted_ids), 0
        except BulkWriteError as bwe:
            inserted = bwe.details["nInserted"]
            return inserted, len(documents) - inserted
        except Exception as e:
            print(f"Erreur batch: {e}")
            return 0, len(documents)

    def count_documents(self) -> int:
        return self.collection.count_documents({})

    def create_vector_index(self):
        print(f"Connexion établie à {self.config.db_name}.{self.config.collection_name}")

        try:
            self.collection.drop_search_index(self.config.index_name)
            print(f"Ancien index '{self.config.index_name}' supprimé")
        except Exception:
            pass

        index_definition = {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": self.config.embedding_dims,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "group_display_summary"},
                {"type": "filter", "path": "price"},
            ]
        }

        search_index_model = SearchIndexModel(
            definition=index_definition,
            name=self.config.index_name,
            type="vectorSearch",
        )

        print("Création de l'index en cours...")
        result = self.collection.create_search_index(search_index_model)
        print(f"Index créé: {result}")
        print("L'indexation peut prendre quelques minutes.")


class DealProcessor:
    """Transforme les deals en documents MongoDB avec embeddings."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    @staticmethod
    def pick_best_comment(deal: dict) -> Optional[str]:
        comments = deal.get("comments", [])
        if not comments:
            return None

        max_likes = max(c.get("reaction_counters", {}).get("like", 0) for c in comments)
        best_comment = next(
            c for c in comments if c.get("reaction_counters", {}).get("like", 0) == max_likes
        )
        return best_comment.get("content_unformatted")

    @staticmethod
    def parse_price(price) -> Optional[float]:
        if price is None:
            return None
        try:
            return float(price)
        except (ValueError, TypeError):
            return None

    def build_embedding_text(self, deal: dict) -> str:
        parts = []

        if title := deal.get("title"):
            parts.append(f"Titre : {title}.")
        if category := deal.get("group_display_summary"):
            parts.append(f"Catégorie : {category}.")
        if description := deal.get("html_stripped_description"):
            parts.append(f"Description : {description[:500]}.")
        if (price := deal.get("price")) is not None:
            parts.append(f"Prix : {price} euros.")
        if temp := deal.get("temperature_level"):
            parts.append(f"Niveau d'attractivité : {temp}.")
        if best_comment := self.pick_best_comment(deal):
            parts.append(f"Commentaire populaire : {best_comment[:200]}.")

        return " ".join(parts)

    def prepare_document(self, deal_id: str, deal: dict) -> Optional[dict]:
        text = self.build_embedding_text(deal)

        try:
            embedding = self.embedding_service.embed(text)
        except EmbeddingError:
            return None

        if len(embedding) != self.embedding_service.embedding_dims:
            return None

        return {
            "_id": deal_id,
            "title": deal.get("title"),
            "text": text,
            "html_stripped_description": deal.get("html_stripped_description"),
            "group_display_summary": deal.get("group_display_summary"),
            "price": self.parse_price(deal.get("price")),
            "url": deal.get("deal_uri"),
            "embedding": embedding,
        }


class DataLoader:
    """Charge les deals depuis des fichiers JSON."""

    @staticmethod
    def load_all_deals(data_dir: str) -> dict:
        all_deals = {}
        json_files = glob.glob(os.path.join(data_dir, "*.json"))

        print(f"Fichiers trouvés: {len(json_files)}")

        for filepath in sorted(json_files):
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_data = json.load(f)

                    if isinstance(file_data, list):
                        for i, deal in enumerate(file_data):
                            deal_id = deal.get("deal_id") or deal.get("id") or f"{filename}_{i}"
                            all_deals[str(deal_id)] = deal
                    elif isinstance(file_data, dict):
                        all_deals.update(file_data)

                print(f"  {filename} chargé")
            except json.JSONDecodeError as e:
                print(f"  Erreur JSON dans {filename}: {e}")
            except IOError as e:
                print(f"  Erreur lecture {filename}: {e}")

        return all_deals


class MigrationPipeline:
    """Orchestre la migration complète des deals vers MongoDB Atlas."""

    def __init__(self, config: Config):
        self.config = config
        self.embedding_service = EmbeddingService(config.model_id, config.embedding_dims)
        self.mongo_client = MongoDBClient(config)
        self.deal_processor = DealProcessor(self.embedding_service)

    def run(self, reset: bool = False, create_index: bool = False):
        print("Migration vers MongoDB Atlas")

        print(f"\nChargement des fichiers depuis {self.config.data_dir}...")
        data = DataLoader.load_all_deals(self.config.data_dir)
        print(f"Total: {len(data)} deals chargés")
        if not data:
            raise ValueError(f"Aucun deal trouvé dans {self.config.data_dir}")

        if reset:
            print("\nPréparation de la base de données...")
            self.mongo_client.reset_collection()

        print("\nInsertion en cours...")
        start_time = time.time()
        indexed, failed = self._index_deals(data)
        elapsed = time.time() - start_time

        print("\nRésumé:")
        print(f"  Documents insérés: {indexed}")
        print(f"  Echecs: {failed}")
        print(f"  Temps total: {elapsed:.1f}s")

        count = self.mongo_client.count_documents()
        print(f"\nTotal dans MongoDB Atlas: {count} documents")

        if create_index:
            print("\nCréation de l'index vectoriel...")
            self.mongo_client.create_vector_index()

    def _index_deals(self, data: dict) -> tuple[int, int]:
        total = len(data)
        indexed = 0
        failed = 0
        deals_list = list(data.items())

        for i in range(0, total, self.config.batch_size):
            batch = deals_list[i : i + self.config.batch_size]
            documents = []

            for deal_id, deal in batch:
                doc = self.deal_processor.prepare_document(deal_id, deal)
                if doc:
                    documents.append(doc)
                else:
                    failed += 1

            batch_indexed, batch_failed = self.mongo_client.insert_batch(documents)
            indexed += batch_indexed
            failed += batch_failed

            progress = min(i + self.config.batch_size, total)
            print(
                f"\rProgression: {progress}/{total} ({100 * progress // total}%)",
                end="",
                flush=True,
            )

        print()
        return indexed, failed
