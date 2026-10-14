## Français

- **v0.13.10 — intégration runner 3.10.7** : chemin Windows du dossier du jeu conservé entre runners classiques et UMU, notamment `C:\game`.
- Le dossier du jeu est exposé dans le préfixe Proton par montage, sans recopier ses fichiers ni fusionner le préfixe Proton avec celui du runner classique.
- Prise en charge des dossiers `.wine`, des `.wsquashfs` et du mode `UMU_DIRECT_GAME=1`. En mode direct, le chemin de lancement existant est conservé et la vue `C:\game` est ajoutée.
- Démontage de la vue du jeu avant synchronisation du préfixe, avec protection des données et maintien de la synchronisation des sauvegardes du mode direct.
- **Paramètres → partage des caches graphiques** : activation/désactivation du partage automatique des caches Batocera pour comparer les performances. Activé par défaut ; aucun fichier cache supprimé.
- Réglage par jeu possible avec `UMU_GRAPHICS_CACHE_SHARING=0/1`. Retour à l’ancienne exposition du jeu possible avec `UMU_C_GAME_PATH=0`.
- Validation : 48 tests automatisés ; GoW3 en `.wine` normal/direct et `.wsquashfs` normal, Forza/Azimuth en `.wsquashfs` direct sur deux sessions avec synchronisation des sauvegardes réussie.

## English

- **v0.13.10 — runner integration 3.10.7**: preserve the Windows game directory path across classic and UMU runners, including `C:\game`.
- Bind the game directory into the Proton prefix without copying game data or merging the Proton and classic runner prefixes.
- Supports `.wine`, `.wsquashfs`, and `UMU_DIRECT_GAME=1`. Direct mode preserves its existing launch path and adds the `C:\game` view.
- Unmount the game view before prefix synchronization, protecting game data and preserving direct-mode save synchronization.
- **Settings → graphics cache sharing**: enable or disable automatic Batocera cache sharing for performance comparisons. Enabled by default; no cache files are deleted.
- Per-game override: `UMU_GRAPHICS_CACHE_SHARING=0/1`. Opt out of the C-drive game view with `UMU_C_GAME_PATH=0`.
- Validation: 48 automated tests; GoW3 in normal/direct `.wine` and normal `.wsquashfs`, plus Forza/Azimuth in direct `.wsquashfs` across two sessions with successful save synchronization.
