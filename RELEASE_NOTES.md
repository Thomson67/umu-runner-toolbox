## Français

Correction de la prise en charge native des manettes Sony avec HIDRAW, notamment sur GE-Proton11-5 à 11-7 via UMU.

- L'intégration ne force plus `PROTON_SONY_HIDRAW_XINPUT=1` lorsque HIDRAW est activé. Cette conversion de compatibilité en XInput pouvait empêcher la bonne détection PlayStation et les fonctions natives de la DualSense.
- Les valeurs explicitement définies dans la ligne `ENV=` de l'autorun sont conservées. Les correctifs spécifiques aux jeux appliqués par Proton restent actifs.
- Pour les jeux compatibles Sony nativement, laisser cette variable absente ou conserver `PROTON_SONY_HIDRAW_XINPUT=0`. Le mode `1` reste disponible pour les jeux nécessitant une conversion XInput.
- La mise à jour migre les runners gérés dont l'intégrité est valide vers l'intégration **3.10.3**, y compris le wrapper modifié par le script de test dont le manifeste a été mis à jour. Aucune modification des DLL amont ni des autorun des jeux.
- Les protections et contrôles d'intégrité des runners introduits en 0.13.5 sont conservés.

Validation utilisateur sur Batocera : DualSense avec fonctions haptiques opérationnelles dans **Gears of War: E-Day**, et fonctionnement HIDRAW rétabli dans **Resonance: A Plague Tale Legacy**, avec GE-Proton11-7-UMU et `PROTON_SONY_HIDRAW_XINPUT=0`. Ce résultat ne constitue pas une garantie pour tous les jeux.

Fermer les jeux et outils Wine avant la mise à jour. Le patch temporaire est remplacé par le wrapper officiel lors de la migration ; il n'est pas nécessaire de restaurer le patch avant la mise à jour. Ne pas utiliser son ancienne commande de restauration après migration. Les runners déjà altérés restent refusés et ne sont pas réparés automatiquement.

## English

Fix native Sony controller support with HIDRAW, particularly with GE-Proton11-5 through 11-7 under UMU.

- The integration no longer forces `PROTON_SONY_HIDRAW_XINPUT=1` when HIDRAW is enabled. This XInput compatibility conversion could interfere with PlayStation detection and native DualSense features.
- Explicit settings in the autorun `ENV=` line are preserved. Proton's own game-specific presets remain active.
- For games with native Sony support, leave this variable unset or keep `PROTON_SONY_HIDRAW_XINPUT=0`. Mode `1` remains available for games needing XInput conversion.
- The update migrates managed runners with valid integrity manifests to integration **3.10.3**, including the temporary test wrapper whose manifest was updated. Upstream DLLs and game autorun files are not modified.
- Runner protection and integrity checks from 0.13.5 are retained.

User validation on Batocera: DualSense haptic features working in **Gears of War: E-Day**, and HIDRAW input restored in **Resonance: A Plague Tale Legacy**, using GE-Proton11-7-UMU with `PROTON_SONY_HIDRAW_XINPUT=0`. This does not guarantee compatibility with every game.

Close games and Wine tools before updating. Migration replaces the temporary patch with the official wrapper; restoring the test patch beforehand is unnecessary. Do not run its old restore command after migration. Already damaged runners remain rejected and are not automatically repaired.
