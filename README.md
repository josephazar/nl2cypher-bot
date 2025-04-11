# Badevel Living Lab Assistant

Une interface conversationnelle (chatbot) qui permet d'interroger la base de données du village intelligent de Badevel en langage naturel, avec visualisation graphique des résultats.

![Badevel Living Lab](logo-femto.png)

## Fonctionnalités

- 🗣️ **Interface conversationnelle** en français et en anglais
- 🔊 **Reconnaissance vocale** pour les requêtes orales
- 📊 **Visualisation graphique** des relations entre éléments
- 📈 **Tableaux et graphiques** pour présenter les données
- 🔍 **Requêtes intelligentes** vers la base de données Neo4j

## Prérequis

- Python 3.9+
- Neo4j Database
- Compte Azure OpenAI avec un accès aux API
- Configuration des variables d'environnement

## Installation

1. Clonez ce dépôt :
```bash
git clone https://github.com/votre-nom/badevel-living-lab-assistant.git
cd badevel-living-lab-assistant
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Copiez le fichier `.env.example` en `.env` et configurez vos variables d'environnement :
```bash
cp .env.example .env
nano .env  # ou utilisez votre éditeur préféré
```

4. Créez l'assistant OpenAI (à faire une seule fois) :
```bash
python create_assistant.py
```
   - Notez l'ID de l'assistant généré et ajoutez-le à votre fichier `.env`

## Lancement de l'application

```bash
chainlit run app.py
```

L'application sera disponible à l'adresse : [http://localhost:8000](http://localhost:8000)

## Structure de la base de données

La base de données Neo4j contient les nœuds suivants :
- `Thing` : Les capteurs et appareils du village
- `Location` : Les bâtiments et emplacements
- `Sensor` : Types de capteurs disponibles
- `Power` : Sources d'énergie
- `Network` : Types de réseaux de communication
- `Application` : Applications utilisant les données
- `ThingType` : Types d'objets intelligents
- `Manufacturer` : Fabricants des appareils
- `Vendor` : Fournisseurs des appareils

## Exemples d'utilisation

- "Quelle est la température actuelle à l'école maternelle ?"
- "Montre-moi tous les capteurs de la mairie"
- "Quel est le chemin de connexion entre le capteur de température et l'application de monitoring ?"
- "Quels sont les bâtiments avec la meilleure efficacité énergétique ?"

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.