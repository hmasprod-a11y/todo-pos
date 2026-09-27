# ToDo POS — Guide utilisateur

## 1. Démarrage

Lancez `ToDo.exe`, choisissez l'utilisateur et saisissez le PIN. L'administrateur initial doit changer le PIN par défaut avant utilisation réelle.

## 2. Module Vente

La caisse accepte le scanner code-barres, la recherche produit, les articles sans code-barres par photo, les packs/cartons, les quantités fractionnées autorisées et les grilles de prix.

Un même code-barres peut appartenir à plusieurs articles : ToDo affiche alors une fenêtre de choix.

Le ticket en cours permet :

- quantité ;
- remise ligne ;
- remise ticket ;
- modification de prix selon les droits ;
- choix client/vendeur si activé ;
- mise en attente et reprise ;
- Addition ;
- bons C1 à C4 ;
- Duplicata.

### Paiement

Les moyens Espèces et Carte sont fournis par défaut. L'administrateur peut ajouter d'autres moyens avec une icône associée.

Sont pris en charge :

- espèces ;
- carte ;
- paiement mixte ;
- crédit client ;
- dénominations monétaires ;
- calcul du rendu monnaie ;
- ticket avec ou sans impression selon configuration.

### Retours

Depuis Retours, recherchez le ticket, sélectionnez la ligne et la quantité. Le stock, le remboursement et la dette client sont mis à jour atomiquement.

## 3. Module Stock

Le module Stock couvre :

- articles et familles ;
- prix d'achat et de vente ;
- niveaux et alertes ;
- mouvements ;
- corrections manuelles selon droits ;
- inventaires ;
- sorties ;
- réapprovisionnement ;
- fournisseurs et fournisseur préféré ;
- bons de commande ;
- réceptions ;
- retours fournisseur ;
- promotions.

Les produits sans code-barres peuvent être sélectionnés par image.

## 4. Module Journal

Le Journal permet :

- période début/fin ;
- filtres caissier, vendeur et paiement ;
- Journal détaillé ;
- Rapport global ;
- Rapport caissiers ;
- Rapport vendeurs ;
- Rapport familles ;
- Rapport clients ;
- Par article ;
- Par jours ;
- Sans détails ;
- vues Entête, Paiements et Retours ;
- export CSV, Excel et PDF ;
- export cumulé ;
- impression ;
- envoi e-mail si configuré.

Le poste de caisse est conservé avec les ventes pour la traçabilité.

## 5. Module Gestion

Gestion regroupe notamment :

- Réceptions ;
- Sorties ;
- Inventaires ;
- Mouvements de stock ;
- Fournisseurs ;
- Règlements fournisseurs ;
- Crédits fournisseurs ;
- Retours fournisseurs ;
- Clients ;
- Règlements clients ;
- Crédits clients ;
- Fidélité ;
- Commandes clients ;
- Devis ;
- Promotions ;
- Dépenses ;
- Rendez-vous.

## 6. Module Paramètres

Paramètres permet de configurer :

- magasin, devise et langue ;
- poste de caisse ;
- comportement de vente et stock ;
- choix client/vendeur ;
- crédit ;
- clôture ;
- démarrage Windows et mode fenêtre ;
- grilles de prix ;
- vendeurs ;
- modes de paiement et icônes ;
- imprimantes Ticket / Rapport / Addition / C1-C4 ;
- modèles FR/AR ;
- contenu du ticket ;
- N° Ticket Client ;
- tiroir ;
- écran client HDMI ;
- afficheur série ;
- balance ;
- RFID ;
- Gmail ;
- backup/restore ;
- Base de Données ;
- utilisateurs et permissions ;
- licence optionnelle ;
- À propos - Aide.

## 7. Module Statistiques

Les Statistiques couvrent :

- évolution des ventes ;
- sélection d'année ;
- ventes mensuelles ;
- total ventes ;
- top mois ;
- caissiers ;
- Top articles ;
- Top clients ;
- évolution article ;
- filtre par période ;
- nombre de tickets ;
- retours remboursement ;
- retours avoir ;
- vue financière.

## 8. Matériel

ToDo supporte scanner clavier/USB, imprimante Windows/ESC-POS, tiroir, écran client HDMI, afficheur client série, balance série et RFID HID/série.

Les ports COM et BaudRate se configurent dans Paramètres.

## 9. Sauvegarde

Pour une migration vers un autre appareil, utilisez la sauvegarde complète. Voir `BACKUP_RESTORE.md`.

## 10. Sécurité

Les comptes ont un PIN et un rôle. L'administrateur peut attribuer des droits distincts : remises, modification prix, retours, stock, rapports, gestion et paramètres.

Le verrouillage du poste est disponible depuis Fonctions. La licence machine est optionnelle et doit être activée explicitement par l'administrateur.
