# 🧊 STELLIO - STL Library Manager

**STELLIO** est une station de gestion de fichiers 3D moderne et intuitive. Inspirée par l'esthétique de l'écosystème **Mainsail/Klipper**, elle centralise tous vos modèles STL dans une interface unique, fluide et ultra-performante.

---

## ✨ Points Forts & Fonctionnalités

### 🖥️ Interface "Mainsail" Native
Profitez d'un design professionnel conçu pour les passionnés d'impression 3D.
* **Mode Sombre (Dark Mode)** : Un confort visuel optimal pour vos sessions de préparation.
* **Design Responsive** : Une navigation organisée, pensée pour la productivité.
* **Thèmes Personnalisables** : Adaptez l'interface aux couleurs de votre marque préférée (Bambu Lab, Prusa, Voron, Creality, etc.).

### 🔍 Visionneuse 3D & Aperçus
* **Aperçu Interactif** : Visualisez vos STL en temps réel directement dans l'application grâce à l'intégration de Three.js.
* **Génération de Miniatures** : Un moteur de rendu interne (**Trimesh / Matplotlib**) crée automatiquement des vignettes pour chaque fichier afin d'explorer votre bibliothèque d'un seul coup d'œil.

### 📂 Gestion de Bibliothèque Hybride
* **Multi-Sources** : Connectez vos dossiers locaux, disques externes ou **partages réseau (NAS / SMB / Samba)** en quelques secondes.
* **Scan Récursif Profond** : Un moteur d'indexation performant qui explore intelligemment tous vos sous-dossiers avec barre de progression.
* **Performance Nomade** : Architecture optimisée pour fonctionner sur **clé USB** (gestion dynamique des chemins relatifs).

### 🚀 Workflow de Fabrication
* **Envoi vers Slicer** : Ouvrez vos fichiers directement dans votre logiciel de découpe préféré (PrusaSlicer, Bambu Studio, OrcaSlicer, etc.) via les protocoles natifs.
* **Multi-comptes** : Chaque utilisateur possède sa propre configuration de sources et ses préférences isolées.

---

## 🛠️ Architecture Technique

Stellio repose sur une structure robuste pour garantir stabilité et rapidité, même avec des milliers de fichiers :

* **Backend FastAPI (Python 3.11)** : Une API asynchrone ultra-rapide gère la logique de scan et l'accès aux fichiers.
* **Système Multi-Thread** : 
    * `Thread API` : Serveur Uvicorn gérant les requêtes.
    * `Thread Worker` : Génération des miniatures en arrière-plan (ne bloque pas l'UI).
    * `Thread UI` : Interface native gérée par PyWebView.
* **Zéro Configuration** : Serveur web intégré, aucune installation de serveur tiers (Apache/Nginx) n'est requise.

---

## 📂 Structure du Projet

```text
STELLIO/
├── backend/
│   ├── main.py            # Cœur du système (API & Logique)
│   └── stellio-data/      # Stockage local (JSON, Miniatures, Logs)
└── frontend/
    ├── index.html         # Interface utilisateur (HTML5)
    ├── script.js          # Logique client & Interactions
    └── style.css          # Design Mainsail-like & Thèmes
