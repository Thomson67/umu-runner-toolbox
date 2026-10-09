# Correctif d'isolation — version de test

Le log du 9 octobre 2026 confirme qu'un manifeste défectueux de DW-Proton
interrompt le lancement de GE-Proton, car l'ancien wrapper vérifie tous les
runners et refuse la session dès la première erreur.

Les logs de Maid of Salvation montrent une fin normale des sessions et le retrait
des protections à 00:00:12. Les douze DLL de DW-Proton ont ensuite été modifiées
à 00:00:25–29. Ces logs ne contiennent pas l'identité du processus qui écrit.
Le remplacement de DLL à travers des liens d'un préfixe vers un ancien runner
reste une hypothèse à confirmer avec les empreintes et les liens présents.
Le hook DXVK d'Ultimate Wine Toolbox modifie le lien vers le bundle graphique;
son code ne copie pas les douze DLL système concernées.

## Changements

- Le wrapper refuse un runner sélectionné altéré. Un runner historique altéré
  produit une alerte et reste protégé en lecture seule sans bloquer les autres.
- Un hook protège tous les runners UMU dès `gameStart` pour les jeux Windows,
  y compris les lancements avec Wine classique, avant la préparation Batocera.
  `gameStop` contrôle les manifestes et retire uniquement les montages créés
  par ce hook. Un montage occupé reste protégé et son état est conservé.
- Le helper détache les liens de fichiers Windows vers les runners et les
  fichiers partagés par liens physiques; il crée des copies privées atomiques.
  Les liens de sauvegardes restent en place. Un lien de répertoire Windows
  vers un runner nécessite une réparation manuelle et refuse le lancement UMU.
- `findmnt -M` remplace la dépendance à la commande `mountpoint`, absente sur
  certaines installations Batocera.
- Les appels de maintenance du wrapper (`wineboot`, `regedit`, `winecfg`)
  protègent et détachent également les fichiers du préfixe. Le wrapper attend
  la fin du wineserver de ce préfixe avant de retirer ses propres protections.
  Les appels purement informatifs `--version` et `--help` restent directs.
- La réparation compare les DLL actuelles aux autres distributions installées,
  conserve une sauvegarde, vérifie toutes les DLL de l'archive contre le
  manifeste existant avant toute écriture et conserve ce manifeste.

## Installation et réparation sur Batocera

Fermer tout jeu Windows. Depuis le dossier extrait de cette branche :

```bash
bash toolbox/helpers/repair-dwproton.sh --apply
bash packaging/install.sh
```

La première commande télécharge l'archive officielle indiquée dans les
métadonnées du runner. Prévoir environ 2 Go libres sur `/userdata` pour le
téléchargement et la sauvegarde. La réparation refuse un runner monté ou un
processus Wine actif. Une réparation peut être simulée sans `--apply`.
L'installation migre ensuite l'intégration des runners dont le manifeste est
valide. Les runners encore altérés restent exclus de la migration.

## Vérification sur la machine

1. Lancer Maid of Salvation avec DW-Proton puis GE-Proton10-25.
2. Relancer BlazBlue Entropy Effect avec Wine-proton-9.0-4 et les bundles voulus.
3. Comparer les manifestes et lire `runner-guard.log` ainsi que le log de réparation.
   Une ligne `matching_source=` identifie une distribution dont la DLL est
   identique à la DLL altérée; elle ne prouve pas à elle seule quel processus
   a effectué la copie.

Les tests automatisés vérifient l'isolation des liens et liens physiques, le
refus des répertoires dangereux, le comportement face à un runner historique
altéré et la validation de l'archive avant réparation. Le montage réel,
SteamRT et les jeux nécessitent un test sur Batocera. Le hook Batocera ne peut
pas garantir qu'EmulationStation annule un lancement si le hook retourne une
erreur; les erreurs de montage sont journalisées. Les lancements hors
EmulationStation avec un Wine classique ne passent pas par ce hook.
Les appels directs aux wrappers UMU bénéficient aussi de la protection lors
des opérations de maintenance. Les binaires réels de Wine appelés directement
hors des wrappers ne sont pas interceptés.

Les journaux se trouvent dans `/userdata/system/logs/umu-runner/`. Le guard
conserve le journal courant et une rotation d'environ 1 Mio. Les sauvegardes
de DLL se trouvent dans `/userdata/system/wine/runner-repair-backups/`.
