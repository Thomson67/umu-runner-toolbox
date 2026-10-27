## Français

**UMU Runner Toolbox v0.13.14-test2 — intégration 3.10.12 (test)**

- Correction du retour du préfixe si Batocera a déjà retiré le montage original : utilisation de l’alias encore monté, uniquement après validation des couches et de son accès en écriture. Les sauvegardes directes conservent leur traitement.
- Suppression explicite des copies locales sans journal depuis Maintenance, après confirmation et vérification des fichiers, sessions et montages.
- Affichage de la cause réelle d’un refus ; gestion des processus disparus pendant l’examen de leurs montages.
- Une archive remplacée au même emplacement ou une source non vérifiable ne réutilise plus silencieusement une ancienne copie UMU. L’ancienne copie reste disponible à l’examen.
- Prise en compte de Hotkey + Start / SIGKILL : aucune dépendance au nettoyage de sortie pour repérer une session interrompue.
- Mode direct : journal des chemins de sauvegardes avant remplacement du lien, reprise des sauvegardes locales récentes pour une même version vérifiée et nettoyage après synchronisation réussie.
- Une reprise non vérifiable ou un retour partiellement effectué conserve les données et demande un examen manuel. Abandonner le préfixe ne supprime pas les sauvegardes directes restées dans le jeu. La copie de secours `.umu-direct-previous` reste limitée à une génération.
- Tests locaux incluant SIGKILL d’un groupe de processus. Validation réelle Forza Horizon 2 sur Batocera encore requise.

## English

**UMU Runner Toolbox v0.13.14-test2 — integration 3.10.12 (test)**

- Fix prefix return after Batocera has released the original mount: use the still-mounted owned alias only after verifying its layers and writable state. Direct-save handling is preserved.
- Explicitly discard local copies without a valid regular journal after confirmation and fresh content/activity/mount checks.
- Display the actual discard error and handle processes disappearing during mount inspection.
- Do not silently reuse interrupted prefixes after archive replacement at the same path or when the source generation cannot be verified; retain previous changes separately.
- Account for Hotkey + Start / SIGKILL without relying on EXIT cleanup.
- Direct mode journals save paths before replacing the link and resumes newer game-side saves only for the same verified source. Successful synchronization removes the working prefix.
- Unverifiable or partially returned direct saves remain for manual review. Discarding the prefix does not delete game-side save leftovers. One `.umu-direct-previous` generation remains.
- Local regression tests include killing an entire process group. Actual Forza Horizon 2 validation on Batocera is still required.
