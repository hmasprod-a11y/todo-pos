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

## Validation de la release 1.1.0
La validation n'est pas figée sur un ancien numéro de commit dans ce document : le **commit de livraison est toujours le HEAD exact** pour lequel les trois workflows suivants sont tous en `success` :

- `Quick test build`;
- `ToDo tests`;
- `Windows build`.

Le workflow Windows réalise également un smoke test réel de l'installateur : installation silencieuse, présence de `ToDo.exe`, création de `%ProgramData%\ToDo POS`, contrôle de l'autorisation `Modify` du groupe Windows intégré `Users`, test d'écriture, désinstallation silencieuse et vérification que les données de ProgramData sont conservées.

Chaque artifact Windows contient `RELEASE_HEAD.txt` avec le SHA Git exact qui a produit le package et le numéro du workflow Windows. Ce fichier est la référence embarquée pour rattacher un installateur à son code source précis.

Une release n'est donc considérée comme automatisément validée que si le SHA de `RELEASE_HEAD.txt` correspond au commit examiné et que les trois workflows GitHub de ce même SHA sont verts.

Cette validation automatisée ne remplace pas les contrôles physiques en magasin : scanner, imprimante, tiroir, afficheur client, balance, RFID, ports COM et rendu arabe doivent encore être testés sur le matériel cible avant déploiement réel.
