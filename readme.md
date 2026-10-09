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

Le script lit les GTFS, rapproche les stations de métro des gares situées à moins de 300 mètres et recrée `correspondance.json`.

## Barème par défaut

- correspondance métro : **2 points** ;
- gare desservie : **3 points** ;
- correspondance tram : **1 point** ;
- ligne de bus : **0,1 point**.
