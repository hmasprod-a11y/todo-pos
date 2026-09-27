# ToDo POS — Validation

## État automatisé
La CI exécute les tests métier, les tests Tk, la compilation et le build Windows. Les fonctions critiques disposent de tests de régression : ventes, paiements, stock, retours, achats, sauvegardes, fidélité, commandes, devis, imprimantes, e-mail, balance, RFID, afficheur série et permissions.

## Performance catalogue
La CI contient un test avec 20 000 produits et codes-barres couvrant recherche FTS, SKU exact et scan code-barres, avec garde-fous de temps destinés à détecter les régressions lourdes.

Des mesures historiques sur 100 000 produits sont conservées dans les résultats de benchmark du dépôt lorsqu'ils sont disponibles. Les performances réelles varient selon le PC, le stockage, SQLite et les périphériques.

## Ce que l'automatisation ne remplace pas
Avant installation magasin, tester physiquement :
- scanner;
- imprimante ticket;
- tiroir;
- afficheur client HDMI/série;
- balance;
- RFID;
- ports COM;
- rendu arabe sur l'imprimante réellement utilisée.

Le statut de livraison d'un commit dépend des trois workflows GitHub verts sur ce commit précis.
