# Dealabs · pipeline data & recherche sémantique

![Python](https://img.shields.io/badge/Python-3.11%2B-306998?style=flat-square) ![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20Vector%20Search-47A248?style=flat-square) ![Streamlit](https://img.shields.io/badge/Streamlit-interface-FF4B4B?style=flat-square) ![Sentence Transformers](https://img.shields.io/badge/Sentence%20Transformers-embeddings-4B5563?style=flat-square) ![Groq](https://img.shields.io/badge/Groq-LLM%20inference-EA580C?style=flat-square)

**[Dealabs](https://www.dealabs.com/)** est une plateforme communautaire où les membres publient, commentent et évaluent des bons plans. Ce projet extrait ces offres via l’API Dealabs, prépare les données et génère des **embeddings** multilingues, puis les indexe dans **MongoDB Atlas Vector Search** (vector DB).

Pour une recherche en langage naturel, le pipeline convertit la requête en embedding, retrouve les offres les plus proches et applique un filtre de prix. Le dépôt comprend une interface **Streamlit** pour consulter les résultats et poduit une synthèse **RAG** avec un LLM à partir des offres retrouvées.

```text
Ingestion  Dealabs API → JSON → préparation → embeddings → MongoDB Atlas Vector Search
Recherche requête + budget → embedding → vector search → offres pertinentes → Streamlit
Synthèse  offres retrouvées → Groq (LLM) → réponse
```

## Ce que contient le dépôt

| Dossier | Rôle |
| --- | --- |
| `scripts/` | Extraction par lots et chargement dans MongoDB Atlas. |
| `src/dealabs_pipeline/` | Préparation des documents, embeddings et index vectoriel. |
| `src/dealabs/` | Client de l’API Dealabs, adapté de [IDerr/dealabs-api](https://github.com/IDerr/dealabs-api). |
| `data/raw/` | Six exports JSON du projet (13 799 entrées avant dédoublonnage). |
| `martial_app/` | Code de l’interface Streamlit et de la recherche. |


```bash
python -m pip install -e ".[app,pipeline]"
cp .env.example .env      # renseigner MONGO_URI et GROQ_API_KEY
python scripts/index_deals.py --create-index
streamlit run martial_app/app.py
```

Le chargement lit `data/raw/` par défaut. L’option `--reset` efface la collection avant l’insertion ; elle doit être demandée explicitement. Pour les options d’extraction et d’indexation, voir [le guide du pipeline](docs/pipeline.md).

**Équipe :** [Arthur](https://github.com/Arthur2801), [Martial](https://github.com/GuyMartial24) et [Yassine](https://github.com/yassine-571).
