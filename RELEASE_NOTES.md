## Français

**UMU Runner Toolbox v0.13.11 — intégration runner 3.10.9**

- Correction des lancements bloqués par des liens DLL utilisant `<runner>/lib/wine/...` lorsque le runner Proton stocke la DLL sous `files/lib/wine/...`. La réparation utilise une copie privée du fichier exact, du même runner et de la même architecture ; la protection des runners reste active.
- Lors d'une mise à jour Ultimate Wine Toolbox, le dossier de secours de l'ancien jeu n'est plus recopié dans le préfixe temporaire UMU. L'exclusion est limitée au dossier identifié par le journal de mise à jour et le préfixe concerné ; ce dossier reste protégé lors de la synchronisation de retour.
- Nettoyage automatique des `materialized-prefixes` après synchronisation réussie et libération des montages. Les changements reviennent dans le `.wine` d'origine ou dans la bouteille Batocera du jeu compressé. Le jeu et son archive ne sont pas recopiés ou supprimés par ce nettoyage.
- Après une interruption, notamment Hotkey + Start, une copie complète et identifiée peut être reprise au lancement du même jeu avec le même runner et le même préfixe source, sans copie supplémentaire. Les données non synchronisées ne sont plus écrasées au lancement suivant. Le fichier `autorun.cmd` actuel reste préservé lors de la synchronisation.
- Un verrou partagé avec le nettoyage manuel, un journal de session et la vérification des montages encore actifs protègent les copies en cours d'utilisation, y compris dans les conteneurs survivants. Les préparations interrompues sans lancement de jeu peuvent être nettoyées automatiquement.
- Vérification de l'espace libre avant copie, avec une réserve de 256 Mio. Les anciennes copies sans journal restent conservées pour vérification ; la Toolbox indique leur présence et l'espace occupé. Les sauvegardes persistantes, runners, compatdata et caches graphiques ne sont pas purgés automatiquement.
- Validation : 74 tests automatisés et contrôles GitHub réussis. Sous Batocera v44, Resonance a été testé après fermeture normale, après Hotkey + Start et relance, avec confirmation de la synchronisation et de la suppression de la copie temporaire.

Installer la mise à jour une fois les jeux fermés pour appliquer l'intégration aux runners UMU gérés. Wine Mono n'est pas inclus dans cette release.

## English

**UMU Runner Toolbox v0.13.11 — runner integration 3.10.9**

- Fixed launches refused because prefix DLL links use `<runner>/lib/wine/...` while the Proton runner stores that DLL under `files/lib/wine/...`. Repair uses a private copy of the exact file from the same runner and architecture; runner protection remains active.
- During an Ultimate Wine Toolbox update, the old-game rollback directory is no longer copied into the temporary UMU prefix. The exclusion requires a matching update journal and prefix, and the backup remains protected during return synchronization.
- Materialized prefixes are automatically removed after successful synchronization and mount cleanup. Changes return to the original `.wine` or the compressed game's Batocera bottle. This cleanup does not copy or delete the game payload or its archive.
- After interruption, including Hotkey + Start, a complete owned copy can resume when the same game, runner and source prefix are launched again, without another copy. Unsynchronized data is no longer overwritten on the next launch. The current `autorun.cmd` is preserved during synchronization.
- A shared lock with manual cleanup, a session journal and checks for active mounts protect copies in use, including mounts inside surviving containers. Interrupted preparation copies that never launched the game can be reclaimed automatically.
- Free-space preflight reserves 256 MiB before copying. Older copies without a journal are retained for review; the Toolbox reports their presence and occupied space. Persistent saves, runners, compatdata and graphics caches are not automatically purged.
- Validation: 74 automated tests and successful GitHub checks. On Batocera v44, Resonance was tested after normal exit, after Hotkey + Start and relaunch, with successful synchronization and temporary-copy removal confirmed in the log.

Install after closing games so the integration can be applied to managed UMU runners. Wine Mono is not included in this release.
