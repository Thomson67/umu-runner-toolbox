## Français

**UMU Runner Toolbox v0.13.17 · intégration 3.10.18**

- L’option `UMU_CPU_AFFINITY` fixe l’affinité CPU Linux du jeu avant le lancement d’UMU et de Proton. Les processus lancés héritent du masque. Ajoutez par exemple `ENV=UMU_CPU_AFFINITY=0-14` dans l’`autorun.cmd`, ou ajoutez la variable à la ligne `ENV=` existante.
- Les CPU logiques sont numérotés à partir de 0 et les plages sont inclusives. `0-3` sélectionne les quatre premiers CPU, `0,2,4,6` sélectionne quatre CPU précis et `0-3,8-11` combine deux plages. `0-14` sélectionne jusqu’à quinze CPU et a été validé pour Bionic Commando Rearmed sur Batocera.
- Le wrapper retient les CPU déjà autorisés par le lanceur. Le journal indique les listes demandée et appliquée dans `cpu_affinity_requested` et `cpu_affinity_effective`. Une valeur invalide ou une sélection sans CPU disponible déclenche un avertissement et conserve l’affinité héritée.
- Le réglage suit l’`autorun.cmd` dans un `.wsquashfs` et nécessite l’intégration 3.10.18 ou ultérieure. Pour revenir au comportement habituel, retirez la variable. [Guide français](https://github.com/Thomson67/umu-runner-toolbox/blob/main/docs/README_FR.md#affinité-cpu-par-jeu)

## English

**UMU Runner Toolbox v0.13.17 · integration 3.10.18**

- `UMU_CPU_AFFINITY` sets the game’s Linux CPU affinity before UMU and Proton start. The launched processes inherit the mask. Add `ENV=UMU_CPU_AFFINITY=0-14` to the game’s `autorun.cmd`, or append the variable to its existing `ENV=` line.
- Logical CPU IDs start at 0 and ranges are inclusive. `0-3` selects the first four CPUs, `0,2,4,6` selects four specific IDs, and `0-3,8-11` combines two ranges. `0-14` selects up to 15 logical CPUs and was verified with Bionic Commando Rearmed on Batocera.
- The wrapper keeps only CPUs already allowed for the launcher. The runner log records the requested and effective lists as `cpu_affinity_requested` and `cpu_affinity_effective`. An invalid value or a list with no available CPU produces a warning and preserves the inherited affinity.
- The setting travels with `autorun.cmd` in a `.wsquashfs` and requires integration 3.10.18 or later. Remove the variable to return to the usual behavior. [English guide](https://github.com/Thomson67/umu-runner-toolbox/blob/main/docs/GUIDE_EN.md#per-game-cpu-affinity)
