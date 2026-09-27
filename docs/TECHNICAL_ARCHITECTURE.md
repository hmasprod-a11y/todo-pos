# ToDo POS — Documentation technique

## 1. Architecture générale

ToDo POS est une application de bureau Windows, locale et hors ligne. La pile cible est :

- Python 3.10+ ;
- Tkinter/ttk pour l'interface ;
- SQLite pour la base locale ;
- PyInstaller pour la version Windows portable ;
- Inno Setup pour l'installateur ;
- GitHub Actions pour les tests et le packaging Release.

Le point d'entrée est `ToDo.pyw`. Le code applicatif est sous `todo/`.

## 2. Organisation du code

- `todo/screens/` : écrans Tkinter et interactions utilisateur.
- `todo/services/` : logique métier, transactions, impression, sauvegarde et périphériques.
- `todo/database.py` : schéma, migrations, connexion SQLite et paramètres.
- `tests/` : régressions métier, sécurité, exports et périphériques simulés.
- `tools/` : utilitaires de développement/livraison.
- `docs/` : documentation utilisateur et technique.

La logique métier sensible doit rester dans les services plutôt que dans les écrans.

## 3. Base de données

Moteur : SQLite.

Caractéristiques principales :

- `PRAGMA foreign_keys=ON`;
- journal WAL ;
- transactions `BEGIN IMMEDIATE` pour les écritures sensibles ;
- montants stockés en centimes entiers ;
- migrations incrémentales via `PRAGMA user_version`;
- sauvegarde pré-migration avant changement de schéma important ;
- indexes pour recherche catalogue et relations critiques.

La base active est résolue par `database.DB_PATH`. La variable d'environnement `TODO_DB_PATH` peut fournir un chemin alternatif.

## 4. Transactions critiques

Les opérations suivantes sont protégées par transaction :

- finalisation de vente ;
- paiements et paiements mixtes ;
- mouvements de stock ;
- retours ;
- fidélité liée à la vente ;
- conversion devis/commande vers vente ;
- import de tables autorisées ;
- opérations fournisseur sensibles.

Une erreur déclenche un rollback afin d'éviter les écritures partielles.

## 5. Modules fonctionnels

Les six modules principaux sont :

1. Vente
2. Stock
3. Journal
4. Gestion
5. Paramètres
6. Statistiques

Des écrans complémentaires couvrent notamment retours, fournisseurs, fidélité, commandes clients, devis, promotions, inventaires, rendez-vous et crédits.

## 6. Périphériques

Périphériques pris en charge :

- scanner code-barres HID/clavier ;
- imprimantes Windows et ESC/POS ;
- tiroir-caisse ESC/POS ;
- imprimantes dédiées Rapport / Ticket / Addition / C1 à C4 ;
- écran client HDMI ;
- afficheur client série ;
- balance série ;
- RFID HID/série.

Les périphériques série utilisent `pyserial` et des paramètres COM/BaudRate configurables.

## 7. Dépendances principales

Les dépendances runtime sont déclarées dans `requirements.txt`.

Principales bibliothèques :

- Pillow : images produit ;
- ReportLab : PDF ;
- pywin32 : impression Windows et spooler ;
- openpyxl : Excel ;
- screeninfo : détection multi-écrans ;
- OpenCV headless : média/vidéo écran client ;
- pyserial : périphériques série ;
- cryptography : signatures Ed25519 pour la licence optionnelle.

## 8. Sécurité

- authentification utilisateur par PIN hashé ;
- droits granulaires par utilisateur ;
- verrouillage rapide du poste ;
- audit des opérations sensibles ;
- poste de caisse enregistré avec les sessions et ventes ;
- licence machine signée Ed25519 disponible en mode opt-in ;
- clé privée de signature non incluse dans l'application.

## 9. Sauvegarde et restauration

Deux usages sont distingués :

- sauvegarde SQLite opérationnelle ;
- sauvegarde complète pour migration appareil avec données et médias.

La restauration complète valide le paquet avant remplacement et utilise un rollback de sécurité en cas d'échec.

Voir `BACKUP_RESTORE.md`.

## 10. Export et reprise de données

L'écran Base de Données permet :

- inventaire des tables ;
- export CSV table par table ;
- import limité aux tables de référence autorisées ;
- export du schéma SQL ;
- export complet ZIP contenant `schema.sql`, `manifest.json` et les CSV.

Les tables transactionnelles ne sont pas importées directement par CSV.

## 11. Recherche et performance

Le catalogue utilise des indexes SQLite et une recherche FTS. Les tests de charge du dépôt valident les recherches principales avec un catalogue de 20 000 produits.

## 12. Build Windows

Le workflow `.github/workflows/windows-build.yml` :

1. installe les dépendances ;
2. exécute les tests métier ;
3. exécute les smoke/acceptance tests Tk ;
4. compile les sources ;
5. construit `ToDo.exe` avec PyInstaller ;
6. construit `ImporterToDo.exe` ;
7. inclut la documentation ;
8. construit l'installateur Inno Setup ;
9. produit le ZIP Windows ;
10. génère les SHA256 ;
11. publie l'artifact Release.

## 13. Validation avant production

Avant installation en magasin :

- vérifier les trois workflows CI verts ;
- tester scanner réel ;
- tester imprimante ticket ;
- tester tiroir ;
- tester écran client ;
- tester balance/RFID/afficheur série si utilisés ;
- effectuer un backup complet puis une restauration de contrôle ;
- changer le PIN administrateur initial ;
- vérifier le poste de caisse et les permissions.

Voir `RELEASE_CHECKLIST.md`.

## 14. Procédure d'installation

Voir `INSTALLATION_WINDOWS.md`.

## 15. Maintenance

Toute évolution du schéma doit :

- rester idempotente ;
- conserver les anciennes données ;
- ajouter un test de migration ;
- incrémenter `PRAGMA user_version` si nécessaire.

Toute évolution métier sensible doit être couverte par un test avant livraison.
