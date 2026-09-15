# Données brutes

`raw/` contient six exports JSON de Dealabs réalisés pour ce projet. Chaque fichier associe un identifiant de deal à ses champs d’origine et, lorsque disponibles, à ses commentaires. Les fichiers totalisent 13 799 entrées avant dédoublonnage ; le chargeur les fusionne par identifiant avant l’indexation.

Les exports sont un instantané, pas un flux actualisé. `scripts/extract_deals.py` écrit les nouvelles extractions dans ce dossier.
