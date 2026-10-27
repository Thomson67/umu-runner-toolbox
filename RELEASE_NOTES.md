## Français

**UMU Runner Toolbox v0.13.14 — intégration 3.10.16**

### Synchronisation et copies de travail

- Correction de l’ordre de fermeture : le nettoyage natif Batocera attend la fin du wrapper UMU, le retour du préfixe et des sauvegardes directes, puis la libération des montages.
- Correction du retour des préfixes compressés : gestion du montage original déjà retiré via un alias vérifié, chemins avec espaces et synchronisation des dossiers sur place sans supprimer leur racine.
- Les copies de travail sont supprimées après synchronisation réussie et libération des montages. Un échec ou un arrêt brutal conserve les changements non rapatriés pour récupération.
- La reprise vérifie la version source, le runner et le mode de lancement. Remplacer un WSquashFS au même emplacement ou revenir à une ancienne version ne réinjecte plus silencieusement les données d’une autre version.
- En mode direct, les chemins de sauvegardes sont journalisés avant modification. Les sauvegardes locales récentes d’une session interrompue sont reprises uniquement lorsque l’identité de la source et l’état le permettent. Le lien déjà restauré par Batocera est reconnu.
- Maintenance permet d’abandonner explicitement une copie locale sans journal valide, après confirmation et contrôles d’activité/montage ; le motif d’un refus est affiché.

### Documentation intégrée

- Nouveau guide pour débutants dans **Documentation / À propos**, disponible hors ligne en français et en anglais.
- Sommaire de 11 chapitres : premiers pas, vocabulaire, cinq familles de runners, menus, compatibilité GAMEID, manettes et caches, sauvegardes et récupération, mode direct, maintenance, mises à jour et partage, dépannage.
- Lecture par chapitre avec défilement ; guides du dépôt actualisés.

### Validation et installation

- 124 tests de régression, incluant SIGKILL d’un groupe de processus et coordination du nettoyage natif.
- Test réel FH2/Azimuth sous Batocera : course, sauvegarde et relancement avec progression conservée, sans avertissement de synchronisation.
- Fermer les jeux et la Toolbox avant installation. Les runners gérés sains sont migrés vers l’intégration 3.10.16.
- Les anciennes copies de récupération restent à examiner séparément dans Maintenance ; la mise à jour ne les supprime pas automatiquement.

## English

**UMU Runner Toolbox v0.13.14 — integration 3.10.16**

### Synchronization and working copies

- Coordinate native Batocera shutdown with UMU wrapper completion, prefix/direct-save return and mount cleanup.
- Fix compressed-prefix return through a verified surviving alias, paths containing spaces and in-place directory synchronization.
- Remove working copies after successful synchronization and mount release. Failed or abruptly interrupted sessions retain unreturned changes for recovery.
- Verify source generation, runner and launch mode before reuse. Archive replacement or rollback no longer silently reuses changes from another source version.
- Journal direct-save paths before modification and resume newer local saves only for verified matching state. Recognize save links already restored by native Batocera preparation.
- Allow explicit discard of local copies without a valid journal after confirmation and activity/mount checks; report the actual refusal reason.

### Built-in documentation

- New offline beginner guide under **Documentation / About**, in French and English.
- Eleven scrollable chapters covering setup, terminology, runner families, menus, game identification, controllers/caches, saves/recovery, direct mode, maintenance, updates/sharing and troubleshooting.
- Updated repository reading guides.

### Validation and installation

- 124 regression tests, including process-group SIGKILL and native cleanup coordination.
- Real FH2/Azimuth validation on Batocera: race, save and relaunch with progress retained and no synchronization warning.
- Close games and the Toolbox before installing. Healthy managed runners migrate to integration 3.10.16.
- Existing recovery copies remain available for separate review in Maintenance; upgrading does not automatically discard them.
