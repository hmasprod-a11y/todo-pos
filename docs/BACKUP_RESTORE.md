# ToDo POS — Sauvegarde et restauration

## Sauvegarde quotidienne
La base SQLite reste locale. Utilisez la sauvegarde automatique ou manuelle depuis Paramètres. Conservez au moins une copie hors de l'appareil de caisse.

## Sauvegarde complète
La sauvegarde complète est le format recommandé pour changer de PC/tablette. Elle inclut la base de données et les médias gérés par ToDo.

Procédure :
1. Fermer les ventes en cours ou les mettre en attente.
2. Ouvrir Paramètres > Données.
3. Créer une sauvegarde complète.
4. Copier le fichier obtenu vers un support externe.
5. Sur le nouvel appareil, installer ToDo.
6. Avant de reprendre les ventes, restaurer la sauvegarde complète.
7. Vérifier produits, stock, utilisateurs, clients, fournisseurs et dernière journée.
8. Effectuer une vente test avant ouverture réelle.

## Restauration
La restauration valide le fichier avant remplacement. Une sauvegarde de sécurité locale est créée autour des migrations/restaurations critiques.

Ne jamais écraser manuellement `todo.db` pendant que ToDo est ouvert.

## Échange catalogue entre magasins
Pour transférer uniquement le catalogue, utilisez Export/Import produits. Les conflits de codes-barres sont présentés explicitement afin de conserver, ignorer ou partager selon le cas.
