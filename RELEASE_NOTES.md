## Français

**UMU Runner Toolbox v0.13.15 · intégration 3.10.17**

- Récupère au lancement un montage `compatdata/.../pfx` abandonné après une interruption. La récupération concerne les jeux utilisant un préfixe matérialisé.
- Vérifie le journal, l’ancien propriétaire et la correspondance exacte du montage avant un démontage normal. Les montages actifs, occupés ou ambigus restent protégés, et le journal du runner indique le motif du refus.
- Le journal indique aussi si le montage a été libéré lors de la fermeture du jeu.

Les tests automatisés couvrent la reprise et le refus des montages non vérifiables. Le scénario d’interruption reste à valider avec cette intégration sur Batocera.

## English

**UMU Runner Toolbox v0.13.15 · integration 3.10.17**

- Recover abandoned `compatdata/.../pfx` mounts on the next launch of a game using a materialized prefix.
- Verify the journal, former owner and exact mount identity before a normal unmount. Active, busy or ambiguous mounts stay protected, with a refusal reason in the runner log.
- Log whether the mount was released on game exit.

Automated tests cover recovery and refusal of unverifiable mounts. The interruption scenario still needs validation on Batocera with this integration.
