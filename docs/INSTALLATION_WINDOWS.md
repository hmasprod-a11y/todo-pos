# Installation Windows — ToDo POS

## Version portable
1. Télécharger l'artifact Windows réussi.
2. Décompresser tout le dossier.
3. Conserver `ToDo.exe`, `_internal` et les autres fichiers ensemble.
4. Lancer `ToDo.exe`.

## Installateur
Le fichier `ToDo-POS-1.1.0-Setup.exe` installe l'application et peut créer un raccourci Bureau.

## Premier démarrage
- Administrateur initial : `admin`
- PIN initial : `1234`
- Changer immédiatement le PIN.
- Configurer magasin, langue, imprimantes, sauvegardes et périphériques nécessaires.

## Périphériques
Les lecteurs USB-HID se comportent généralement comme un clavier. Les périphériques série nécessitent le bon port COM et BaudRate. Tester chaque périphérique depuis Paramètres avant ouverture du magasin.

## Données
La version portable doit rester dans un emplacement où l'application peut écrire ses données. Ne pas déplacer partiellement les sous-dossiers après utilisation.

## Emplacement des données
La version installée conserve les fichiers programme dans `Program Files\ToDo POS`, mais toutes les données modifiables du magasin sont stockées dans `%ProgramData%\ToDo POS` : base SQLite, images produits, sauvegardes, médias client et licence.

Au premier lancement après une mise à niveau d'une ancienne installation, si aucune base n'existe encore dans ProgramData, ToDo copie automatiquement les données historiques présentes à côté de l'ancien exécutable. Une base déjà présente dans ProgramData n'est jamais fusionnée ou écrasée par cette migration.

La variable `TODO_DB_PATH` reste prioritaire pour les installations techniques et les tests.

La désinstallation du logiciel ne supprime pas automatiquement `%ProgramData%\ToDo POS`. Cette conservation est volontaire afin d'éviter la perte d'une base magasin lors d'une réinstallation.
