## Français

- Version de test **0.13.8-dev1**, intégration **3.10.5** : les dossiers de cache graphiques configurés et existants sont exposés en lecture/écriture dans Steam Runtime (VKD3D, DXVK, Mesa et NVIDIA).
- Conserve les chemins et caches existants, notamment `/userdata/system/cache` utilisé par Batocera. Les liens symboliques sont pris en charge et les montages déjà configurés sont conservés.
- Corrige le cas où VKD3D recevait un chemin invisible dans le conteneur UMU. Le test utilisateur avec un chemin visible a réduit « Preparing graphic pipelines » d'environ 15 secondes à moins d'une seconde sur Azimuth / Forza Horizon 2. La correction automatique reste à valider sur Batocera.
- Les chemins vides, désactivés (`0`), relatifs ou inexistants ne sont pas montés. Les décisions sont consignées dans le journal du runner.
- Fermer les jeux avant installation : les runners gérés dont le manifeste est valide sont migrés automatiquement.

## English

- Test version **0.13.8-dev1**, integration **3.10.5**: configured, existing graphics cache directories are shared read/write with Steam Runtime (VKD3D, DXVK, Mesa and NVIDIA).
- Preserves existing cache paths and contents, including Batocera's `/userdata/system/cache`. Supports symlinks and retains previously configured mounts.
- Fixes VKD3D receiving a cache path invisible inside the UMU container. A user test with a visible path reduced “Preparing graphic pipelines” from about 15 seconds to less than one second on Azimuth / Forza Horizon 2. Automatic sharing still needs validation on Batocera.
- Empty, disabled (`0`), relative and missing paths are not mounted. Decisions are recorded in the runner log.
- Close games before installation: managed runners with valid integrity manifests are migrated automatically.
