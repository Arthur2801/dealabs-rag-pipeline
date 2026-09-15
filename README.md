# Dealabs · pipeline data & recherche sémantique

![Python](https://img.shields.io/badge/Python-3.11%2B-306998?style=flat-square) ![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20Vector%20Search-47A248?style=flat-square) ![Streamlit](https://img.shields.io/badge/Streamlit-interface-FF4B4B?style=flat-square) ![Sentence Transformers](https://img.shields.io/badge/Sentence%20Transformers-embeddings-4B5563?style=flat-square) ![Groq](https://img.shields.io/badge/Groq-r%C3%A9ponse%20LLM-EA580C?style=flat-square)

Un projet de bout en bout : **collecter des bons plans, les transformer en vecteurs, puis les retrouver par leur sens**. Le dépôt contient aussi une interface Streamlit pour la recherche en langage naturel et la synthèse des résultats.

```text
API Dealabs → exports JSON → préparation + embeddings → MongoDB Atlas → Streamlit
                                                             ↘ réponse via Groq
```

## Ce que contient le dépôt

| Dossier | Rôle |
| --- | --- |
| `scripts/` | Extraction par lots et chargement dans MongoDB Atlas. |
| `src/dealabs_pipeline/` | Préparation des documents, embeddings et index vectoriel. |
| `src/dealabs/` | Client de l’API Dealabs, adapté de [IDerr/dealabs-api](https://github.com/IDerr/dealabs-api). |
| `data/raw/` | Six exports JSON du projet (13 799 entrées avant dédoublonnage). |
| `martial_app/` | Code de l’interface Streamlit et de la recherche. |

## Lancer en local

Pour lancer le projet en local, il faut Python 3.11+, un cluster MongoDB Atlas et une clé Groq pour la synthèse. La commande d’indexation crée l’index `vector_index` sur `embedding` (384 dimensions) :

```bash
python -m pip install -e ".[app,pipeline]"
cp .env.example .env      # renseigner MONGO_URI et GROQ_API_KEY
python scripts/index_deals.py --create-index
streamlit run martial_app/app.py
```

Le chargement lit `data/raw/` par défaut. L’option `--reset` efface la collection avant l’insertion ; elle doit être demandée explicitement. Pour les options d’extraction et d’indexation, voir [le guide du pipeline](docs/pipeline.md).

**Équipe :** [Arthur](https://github.com/Arthur2801), [Martial](https://github.com/GuyMartial24) et [Yassine](https://github.com/yassine-571).
