## Français

**UMU Runner Toolbox v0.13.12 — intégration runner 3.10.10**

- Correction de lancements bloqués après un changement ou une suppression de runner : les liens cassés vers les fichiers Wine sont réparés avec les fichiers correspondants du runner sélectionné, en respectant leur architecture. Cela couvre aussi les exécutables, pilotes et thèmes.
- Prise en charge des anciennes références de polices : remplacement depuis le runner choisi lorsqu'elles sont disponibles, ou retrait des liens déjà cassés pour laisser Wine utiliser ses polices de remplacement.
- Nouveau menu **Maintenance → Copies UMU conservées** pour consulter le jeu, la taille, la date, le runner et le motif de conservation lorsqu'ils sont connus.
- Explications pour reprendre les modifications en relançant le même jeu depuis ES, ou abandon d'une seule copie avec confirmation. Le nettoyage global protège désormais les copies non synchronisées.
- Notification ES lorsqu'une copie doit être conservée, rappel à l'ouverture de la Toolbox et journal de récupération plus précis. Une copie modifiée depuis sa sélection ne peut pas être supprimée avec une ancienne confirmation.
- Validation : **96 tests automatisés**. Lancement de Warhammer sous Batocera v44 confirmé, avec synchronisation réussie et suppression du préfixe temporaire.

Installer la mise à jour avec les jeux fermés pour appliquer l'intégration aux runners UMU gérés.

## English

**UMU Runner Toolbox v0.13.12 — runner integration 3.10.10**

- Fixed launches blocked after switching or removing runners: stale Wine file links are repaired using matching files from the selected runner, with architecture checks. Executables, drivers and themes are covered too.
- Old font references are replaced from the selected runner when available; already dangling links are otherwise removed so Wine can use its font fallbacks.
- New **Maintenance → Retained UMU copies** menu shows each game's occupied space, date, runner and retention reason when known.
- Instructions explain how to resume changes by launching the same game from ES, or discard one copy after confirmation. Bulk runtime cleanup now protects unsynchronized copies.
- ES notification when a copy must be retained, a reminder when opening the Toolbox and more informative recovery journals. A copy changed since selection cannot be deleted using an old confirmation.
- Validation: **96 automated tests**. Warhammer launch confirmed on Batocera v44, with successful synchronization and temporary-prefix removal.

Install after closing games so the integration can be applied to managed UMU runners.
