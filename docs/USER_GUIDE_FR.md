# ToDo POS — Guide utilisateur

## 1. Démarrage
Lancez `ToDo.exe`, choisissez votre utilisateur puis saisissez le PIN. L'administrateur initial doit changer le PIN par défaut avant utilisation réelle.

## 2. Vente
La caisse accepte le scanner code-barres, la recherche produit, les articles sans code-barres par photo, les packs/cartons, les quantités fractionnées autorisées et les grilles de prix. Un même code-barres peut appartenir à plusieurs articles : ToDo affiche alors un choix.

Le ticket en cours permet quantité, remise ligne, remise ticket et modification de prix selon les droits utilisateur. Les ventes peuvent être mises en attente puis reprises.

## 3. Paiement
Les moyens Espèces et Carte sont fournis par défaut. L'administrateur peut ajouter d'autres moyens dans Paramètres. Le paiement mixte, le crédit client et le rendu monnaie sont pris en charge.

## 4. Retours
Ouvrez Retours, recherchez le numéro du ticket, sélectionnez la ligne et la quantité. Le stock, le remboursement et la dette client sont mis à jour de façon atomique.

## 5. Stock et achats
Le stock comprend mouvements, corrections, inventaires, sorties, alertes, réapprovisionnement, fournisseurs, bons de commande, réceptions et retours fournisseur. Les corrections sensibles dépendent des droits utilisateur.

## 6. Gestion
Gestion regroupe notamment clients, fidélité, promotions, commandes clients, devis, fournisseurs, inventaires et fonctions de caisse complémentaires.

## 7. Journal et statistiques
Le Journal permet filtres, détails, exports CSV/Excel/PDF, impression et envoi e-mail si configuré. Les statistiques couvrent périodes, années, produits, clients, caissiers, retours et vue financière.

## 8. Matériel
ToDo supporte scanner clavier/USB, imprimante Windows/ESC-POS, tiroir, écran client HDMI, afficheur client série, balance série et RFID HID/série. Les ports COM et BaudRate se configurent dans Paramètres.

## 9. Sauvegarde
Utilisez la sauvegarde complète pour une migration vers un autre appareil. Voir `docs/BACKUP_RESTORE.md`.

## 10. Sécurité
Les comptes ont un PIN et un rôle. L'administrateur peut attribuer des droits distincts : remises, modification prix, retours, stock, rapports, gestion et paramètres.
