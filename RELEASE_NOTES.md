## Français

- Nouveau mode de compatibilité par jeu : `ENV=UMU_DIRECT_GAME=1` contourne la vue `gameviews` supplémentaire sans extraire le jeu complet. Désactivé par défaut.
- Pour les jeux refusant les liens de sauvegardes, les dossiers `SAVEDIR` à l’intérieur du jeu sont présentés comme de vrais dossiers, puis synchronisés à la fermeture. Les modifications et suppressions sont répercutées ; le lien Batocera est ensuite restauré.
- Une seule copie de secours reste dans le dossier de sauvegardes du jeu, sous `.umu-direct-previous`, sans accumulation récursive.
- Intégration **3.10.4** : Steam Runtime, isolation des préfixes et protection des runners conservés. La mise à jour migre les runners gérés dont le manifeste est valide ; les jeux doivent être fermés.
- Validation utilisateur sur Batocera avec Azimuth / Forza Horizon 2 et GE-Proton11-7-UMU : lancement, sauvegarde et reprise de progression en `.wine` et `.wsquashfs`.

Le mode direct vise des incompatibilités de chemins et ne corrige pas tous les crashs. Les copies de sauvegardes nécessitent de l’espace libre et ajoutent un délai ; une interruption forcée peut demander une récupération manuelle. Le nom du jeu détermine le dossier de sauvegardes Batocera : le conserver ou transférer les sauvegardes lors d’un renommage.

## English

- New per-game compatibility mode: `ENV=UMU_DIRECT_GAME=1` bypasses the extra `gameviews` view without extracting the full game. Disabled by default.
- For games rejecting save symlinks, `SAVEDIR` directories inside the game are presented as real directories and synchronized on exit. Changes and deletions are propagated, then the Batocera link is restored.
- One recovery snapshot remains inside the game's save directory as `.umu-direct-previous`, without recursive accumulation.
- Integration **3.10.4** retains Steam Runtime, prefix isolation and runner protection. Updating migrates managed runners with valid manifests; close games first.
- User validation on Batocera with Azimuth / Forza Horizon 2 and GE-Proton11-7-UMU: launch, save and restored progress in `.wine` and `.wsquashfs`.

Direct mode targets path incompatibilities and does not fix every crash. Save copies require free space and add latency; forced termination may require manual recovery. The game name determines Batocera's save directory: keep it or transfer saves when renaming.
