# Score des correspondances métro

Petite application Streamlit qui compare les correspondances des réseaux de métro Tisséo, Ilévia, RTM et STAR.

Le score est calculé à partir des correspondances métro, tram, gare et bus de chaque station. Le barème peut être modifié directement dans l’application.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l’application

Le fichier `correspondance.json` est déjà généré : les fichiers GTFS ne sont donc pas nécessaires pour simplement lancer l’application.

```bash
streamlit run streamlit.py
```

## Télécharger les GTFS

Les archives GTFS ne sont pas versionnées dans le dépôt. Téléchargez les données statiques depuis les sources officielles, puis placez-les dans `gtfs/` avec les noms suivants :

| Réseau | Source officielle | Nom du fichier attendu |
|---|---|---|
| Tisséo — Toulouse | [Tisséo : réseau transport urbain toulousain](https://data.toulouse-metropole.fr/explore/dataset/tisseo-gtfs/information/) | `tisseo_gtfs_v2.zip` |
| Ilévia — Lille | [Page du jeu de données](https://transport.data.gouv.fr/datasets/ilevia-localisation-des-arrets-bus-metro-et-tram-gtfs) · [téléchargement direct](https://media.ilevia.fr/opendata/gtfs.zip) | `lille_gtfs.zip` |
| RTM — Marseille | [Réseaux urbains de la Métropole Aix-Marseille-Provence](https://transport.data.gouv.fr/datasets/reseaux-de-transports-en-commun-de-la-metropole-daix-marseille-provence-et-des-bouches-du-rhone) — choisir la ressource **GTFS RTM** | `mamp-rtm.gtfs.zip` |
| STAR — Rennes | [Horaires GTFS du réseau STAR](https://data.explore.star.fr/explore/dataset/tco-busmetro-horaires-gtfs-versions-td/information/) | `rennes_gtfs.zip` |

Arborescence attendue :

```text
gtfs/
├── lille_gtfs.zip
├── mamp-rtm.gtfs.zip
├── rennes_gtfs.zip
└── tisseo_gtfs_v2.zip
```

## Régénérer les correspondances

Après avoir téléchargé ou actualisé les quatre archives :

```bash
python generate_json.py
```

Le script lit les GTFS, rapproche les stations de métro des gares situées à moins de 300 mètres et recrée `correspondance.json`. Chaque station contient aussi son identifiant GTFS et sa position `[longitude, latitude]` : ce fichier est ainsi la source unique des correspondances et des coordonnées.

## Générer le GeoJSON pour QGIS

```bash
python generate_qgis_geojson.py
```

Le script lit uniquement `correspondance.json` et crée `metro_qgis.geojson` en WGS 84. Il ne relit pas les GTFS et ne recalcule pas les correspondances. Il faut donc exécuter `generate_json.py` avant lui après chaque mise à jour des GTFS.

Le fichier contient deux types d'entités, distingués par le champ `feature_type` :

- `station` : un point par station de métro, avec les lignes de métro, tram et bus, les gares proches, des compteurs et des champs booléens tels que `has_train_station` ;
- `metro_line` : une ligne par ligne de métro, construite avec des segments droits reliant toutes les stations dans leur ordre de desserte GTFS.

Chaque station expose aussi le score par défaut dans `score`, sa décomposition dans `points_metro`, `points_gare`, `points_tram` et `points_bus`, ainsi que le barème unitaire dans les champs `weight_*`. Les lignes possèdent la somme des scores de leurs stations. La formule et le barème sont définis une seule fois dans `scoring.py`, partagé avec l'application Streamlit.

Le script n'utilise pas `shapes.txt`. Les coordonnées des lignes sont exactement celles des stations successives enregistrées dans `correspondance.json`. Les listes de correspondances utilisent le séparateur ` | ` afin de rester faciles à lire et à filtrer dans QGIS.

Pour créer deux couches séparées dans QGIS, ajoutez deux fois le même GeoJSON puis appliquez les filtres suivants :

```text
"feature_type" = 'station'
"feature_type" = 'metro_line'
```

Un autre chemin de sortie peut être choisi avec :

```bash
python generate_qgis_geojson.py --input correspondance.json --output chemin/metro.geojson
```

## Barème par défaut

- correspondance métro : **2 points** ;
- gare desservie : **3 points** ;
- correspondance tram : **1 point** ;
- ligne de bus : **0,1 point**.
