## Français

**UMU Runner Toolbox v0.13.17 · intégration 3.10.18**

- L’option `UMU_CPU_AFFINITY` limite les CPU logiques pour un jeu avant le démarrage d’UMU et de Proton. Ajoutez `UMU_CPU_AFFINITY=0-14` à la ligne `ENV=` de son `autorun.cmd`. Le réglage est conservé lors de la compression en `.wsquashfs`.
- Le journal du runner indique les CPU demandés et ceux effectivement utilisés. Si le réglage est invalide ou qu’aucun CPU demandé n’est disponible, le lancement se poursuit avec l’affinité héritée.
- Le lancement de Bionic Commando Rearmed avec `UMU_CPU_AFFINITY=0-14` a été validé sur Batocera.

## English

**UMU Runner Toolbox v0.13.17 · integration 3.10.18**

- Use `UMU_CPU_AFFINITY` to restrict a game to selected logical CPUs before UMU and Proton start. Add `UMU_CPU_AFFINITY=0-14` to the `ENV=` line in the game's `autorun.cmd`. This setting is carried into `.wsquashfs` archives.
- The runner log records the requested and effective CPU lists. If the setting is invalid or none of the requested CPUs are available, the game launches with the inherited affinity.
- Bionic Commando Rearmed was verified on Batocera with `UMU_CPU_AFFINITY=0-14`.
