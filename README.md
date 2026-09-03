# Hympyr Brand OS

Application Streamlit autonome construite à partir de la charte graphique Hympyr Energies `HYM-CHG-001`, version `0.1` du 27 juillet 2026.

## Fonctions incluses

- tableau de bord ;
- ADN de marque avec distinction entre informations documentées et éléments à valider ;
- charte interactive : logo, couleurs, typographie et contrôle WCAG ;
- bibliothèque des gabarits décrits dans la charte ;
- studio de contenu sans génération de faits non fournis ;
- calendrier éditorial ;
- banque d'idées ;
- grille de conformité ;
- export JSON des données ;
- protection facultative par mot de passe.

## Lancement local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement Streamlit Community Cloud

1. Décompresser le livrable et publier son contenu dans un dépôt GitHub.
2. Créer l'application dans Streamlit Community Cloud.
3. Choisir `app.py` comme **Main file path**.
4. Déployer.

Pour protéger l'application, ajouter dans les secrets Streamlit :

```toml
APP_PASSWORD = "un-mot-de-passe-fort"
```

Ne jamais inscrire un mot de passe, une clé API ou une donnée sensible directement dans `app.py`.

## Données

La V1 enregistre les idées et contenus dans `data/brand_os.db`. Le stockage local de Streamlit Community Cloud peut être réinitialisé lors d'un redéploiement. L'écran **Administration** permet donc d'exporter une sauvegarde JSON.

Une base PostgreSQL pourra remplacer SQLite dans une version ultérieure si une conservation permanente et multi-utilisateur est nécessaire.

## Sources et limites

- Les données graphiques sont directement intégrées dans `app.py` : l'application ne dépend d'aucun fichier `brand.yml`.
- Le PDF source est conservé dans `reference/charte_graphique_hympyr.pdf` et peut être téléchargé depuis l'application.
- Les fichiers vectoriels officiels du logo n'ont pas été fournis. L'application ne recrée donc pas le logo et ne distribue pas de faux fichier source.
- Les conversions CMJN sont reproduites comme indicatives, conformément à la charte.
- La plateforme de marque reste partielle tant que la mission, la vision, les valeurs, les audiences et les preuves commerciales n'ont pas été validées.
