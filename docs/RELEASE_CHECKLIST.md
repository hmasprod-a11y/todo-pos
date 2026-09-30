# Checklist de livraison

Avant déploiement magasin :
- [ ] Les trois workflows CI sont verts sur le commit livré.
- [ ] Le ZIP Windows et l'installateur sont générés.
- [ ] SHA256SUMS.txt correspond aux fichiers livrés.
- [ ] PIN admin par défaut changé.
- [ ] Sauvegarde complète testée puis copiée hors appareil.
- [ ] Scanner code-barres testé.
- [ ] Imprimante ticket et tiroir testés.
- [ ] Écran/afficheur client testé si utilisé.
- [ ] Balance et RFID testés si utilisés.
- [ ] Vente espèces, carte, mixte et retour testés.
- [ ] Export PDF/Excel/CSV testé.
- [ ] Restauration sur base de test vérifiée avant migration réelle.

## Microsoft Store / MSIX

Avant une soumission Store :
- [ ] L'identité et le Publisher proviennent de Partner Center (aucune valeur devinée).
- [ ] Les trois assets PNG officiels requis par MSIX sont fournis.
- [ ] Le package MSIX est construit depuis le même artefact Windows testé.
- [ ] Le MSIX est signé/soumis selon le flux Microsoft Store, sans certificat privé dans le dépôt.
- [ ] Installation propre, lancement initial et migration/backup sont vérifiés.
- [ ] Les textes Store EN, FR et AR correspondent aux fonctions effectivement disponibles.
- [ ] Privacy Policy, Terms of Use et Support/data sont accessibles dans l'application.
