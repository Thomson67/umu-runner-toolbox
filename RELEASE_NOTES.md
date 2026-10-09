## Français

Cette mise à jour renforce la protection des runners lors des changements de version de Wine/Proton et évite qu’un ancien runner altéré bloque les autres jeux.

- Le runner sélectionné reste contrôlé : un manifeste invalide refuse son lancement. Un autre runner altéré produit une alerte sans bloquer le runner sain.
- Protection en lecture seule des runners UMU au lancement des jeux Windows depuis EmulationStation, y compris avec Wine classique. Les montages occupés restent protégés.
- Isolation des fichiers Windows de préfixe liés aux runners, par copies privées atomiques, sans modifier les liens de sauvegarde. Les liens de répertoire dangereux sont refusés.
- Protection également pendant les appels de maintenance des wrappers ; attente du wineserver avant le retrait des protections.
- Compatibilité avec les versions de Batocera sans commande `mountpoint`.
- Helper de réparation manuelle de DW-Proton avec vérification de l’archive officielle, sauvegarde des DLL et conservation du manifeste d’intégrité.
- Le comportement Sony HIDRAW habituel est conservé : activation de `PROTON_SONY_HIDRAW_XINPUT=1` sur les runners compatibles lorsque HIDRAW est activé. Les essais spécifiques à Resonance ne sont pas intégrés.

La mise à jour installe le hook et migre les runners sains. Elle ne répare pas automatiquement les runners déjà altérés. Fermez les jeux Windows avant installation.

Validation : tests automatisés d’isolation/réparation et contrôles de syntaxe ; fonctionnement des jeux rétabli confirmé sur Batocera. Le défaut de navigation à la manette signalé après mise à jour de la Toolbox reste à reproduire et n’est pas annoncé comme corrigé. Les binaires Wine réels appelés directement hors wrappers et hors EmulationStation ne sont pas interceptés ; un échec du hook ne garantit pas l’annulation du lancement par EmulationStation.

## English

This update strengthens runner protection across Wine/Proton changes and prevents an unrelated damaged runner from blocking healthy ones.

- Integrity checks still reject a damaged selected runner; unrelated damaged runners warn without blocking healthy runners.
- Read-only protection covers Windows launches from EmulationStation, including classic Wine. Busy mounts retain their protection.
- Atomic private copies isolate Windows prefix files linked to runners, preserving save symlinks; unsafe directory aliases are rejected.
- Wrapper maintenance calls also apply isolation and wait for wineserver shutdown before releasing protection.
- Compatibility with Batocera builds without `mountpoint`.
- Manual DW-Proton repair helper verifies the official archive, backs up DLLs and preserves the integrity manifest.
- Existing Sony HIDRAW behavior is retained: `PROTON_SONY_HIDRAW_XINPUT=1` for compatible runners with HIDRAW enabled. Resonance-specific experiments are excluded.

Updating installs the guard and migrates healthy runners; it does not automatically repair damaged runners. Close Windows games before installing.

Validation includes automated isolation/repair tests, syntax checks and user-confirmed restored game operation on Batocera. The reported Toolbox controller navigation issue after updating remains unconfirmed and is not claimed fixed. Direct real-Wine binary calls outside wrappers/EmulationStation are not intercepted, and hook failure cannot guarantee that EmulationStation cancels launch.
