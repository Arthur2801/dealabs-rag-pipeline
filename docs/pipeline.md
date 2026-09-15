# Pipeline de données

## 1. Extraire

Après avoir renseigné `DEALABS_CLIENT_KEY` et `DEALABS_CLIENT_SECRET` dans `.env`, installer le projet avec `pip install -e ".[pipeline]"`, puis lancer :

```bash
python scripts/extract_deals.py --limit 500 --workers 10
```

Les exports sont enregistrés dans `data/raw/`. `--limit` borne le nombre de deals récupérés et `--workers` le nombre de requêtes parallèles pour leurs commentaires.

## 2. Indexer

Renseigner `MONGO_URI` et installer l’extra `pipeline`. Le script lit tous les fichiers JSON de `data/raw/`, construit un texte à partir du titre, de la description, de la catégorie, du prix et d’un commentaire, puis produit des vecteurs de 384 dimensions avec `paraphrase-multilingual-MiniLM-L12-v2`.

```bash
python scripts/index_deals.py --create-index
```

Les documents sont insérés dans `deals_db.deals`. `--create-index` crée l’index Atlas `vector_index` pour la recherche vectorielle ; l’index existant est remplacé. `--reset` supprime et recrée la collection avant l’insertion. Sans `--reset`, les identifiants déjà présents sont conservés et les doublons sont comptés parmi les échecs d’insertion.

Si le modèle d’embedding change, relancer l’indexation avec `--reset --create-index` pour recalculer tous les vecteurs avec le même modèle que l’application.

## 3. Rechercher

`martial_app/rag_logic.py` transforme la requête avec **le même modèle d’embedding**, puis interroge MongoDB Atlas avec `$vectorSearch` et un filtre de prix. L’interface affiche les deals retournés et peut demander à Groq une synthèse fondée sur ces résultats.

La base `deals_db`, la collection `deals`, le champ `embedding` et le nom de l’index `vector_index` doivent correspondre à la configuration du pipeline.
