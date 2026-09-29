# Hympyr Brand OS

Studio Streamlit pour gérer l'identité de marque et produire des visuels à partir de gabarits modifiables. Le projet remplace les données locales SQLite par Supabase Auth, Postgres et Storage. Les fichiers, contenus et ressources de chaque compte sont isolés par des règles RLS.

## Ce que l'on peut faire

- Modifier, ajouter ou retirer couleurs et familles Google Fonts ; les couleurs sont appelées par token dans les gabarits.
- Importer les logos, images et modèles sources (SVG, PDF compris), créer des fichiers texte/Markdown/HTML et les conserver dans Storage.
- Créer un gabarit de 200 à 4 000 px avec calques texte, formes et images ; importer un PNG/JPEG/WebP en fond et superposer des champs éditables.
- Écrire un contenu et une suite de diapositives, changer de gabarit, prévisualiser et exporter en PNG, ZIP de PNG ou PDF multipage.
- Planifier les contenus, gérer les idées et exporter les métadonnées JSON ou le calendrier CSV.
- Importer une sauvegarde JSON de la V1 si l'espace de contenus et d'idées est vide.

Les modèles source SVG/PDF sont conservés et téléchargeables. Leur conversion en gabarit éditable passe actuellement par une image de fond PNG/JPEG/WebP et des calques configurés dans l'outil. Pour un rendu de logo dans le visuel, importez une version PNG/WebP transparente. Le rendu Google Fonts requiert l'accès à fonts.googleapis.com et fonts.gstatic.com ; une police de substitution est signalée quand le téléchargement échoue.

## Mise en place Supabase

Le projet `hympyr-brand-os` est créé dans `quentindebrie-code's Org`, en région Paris (`eu-west-3`). Les migrations `supabase/migrations/20260929150605_brand_os.sql` et `20260929150758_add_foreign_key_indexes.sql` y sont appliquées. Elles créent les tables, index, politiques RLS et le bucket privé `brand-assets`.

La clé **publishable** et l'URL de ce projet sont dans `store.py` ; elles peuvent être incluses dans un client public, puisque chaque opération sur les données est protégée par Supabase Auth et RLS. Ne jamais ajouter de clé `service_role` au dépôt. Pour pointer vers un autre projet, remplacez ces paramètres par les secrets Streamlit :

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

Configurez les paramètres Supabase Auth (confirmation d'e-mail, domaine de redirection et politique d'inscription) selon les utilisateurs qui doivent accéder à l'outil. Déployez `app.py` sur Streamlit Community Cloud ou lancez localement :

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Le déploiement utilise les dépendances directes épinglées dans `requirements.txt`, que Streamlit Cloud résout pour sa version de Python. Un verrou complet pour les installations locales est conservé dans `requirements.lock` et se régénère avec `uv pip compile --python-version 3.10 requirements.in -o requirements.lock`.

La base et les fichiers sont persistants dans Supabase. Le serveur Streamlit ne conserve que la session de l'utilisateur et les aperçus en cours d'édition ; enregistrez les modifications avant de fermer l'onglet. Un compte neuf reçoit la palette et le premier gabarit Hympyr une seule fois. Les autres comptes sont isolés : cette version ne partage pas un espace commun entre utilisateurs.

## Architecture

- `app.py` : interface et parcours de création ;
- `store.py` : accès aux tables, stockage et initialisation du compte ;
- `rendering.py` : rendu de gabarits en images et PDF, ajustement du texte ;
- `supabase/migrations/` : structure SQL et règles de sécurité ;
- `tests/` : vérification des rendus et exports.

Les gabarits sont enregistrés comme JSON de calques. Les champs (`title`, `body`, `cta` ou vos propres noms) sont remplis pour chaque diapositive ; les couleurs par token sont relues à chaque rendu. Les positions, tailles et dimensions sont en pixels. Une couleur ou une variante typographique utilisée dans un gabarit doit être remplacée dans le gabarit avant sa suppression.

## Reprendre les données de la V1

Dans l'ancienne application, téléchargez **Administration → Exporter toutes les données**, puis utilisez **Administration → Importer un export de la V1** dans cette version. Les anciens contenus et idées sont copiés ; chaque contenu reçoit une première diapositive brouillon. La V1 ne sauvegardait aucun fichier de marque dans sa base. Aucun fichier local `data/brand_os.db` n'est présent dans le dépôt GitHub.

## Vérification locale

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app.py store.py rendering.py
```
