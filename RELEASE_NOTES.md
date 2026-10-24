## Français

**UMU Runner Toolbox v0.13.13 — intégration runner 3.10.10 (inchangée)**

- **Manettes Sony (DualSense / DualShock 4) :** recommandation d'utiliser **GE-Proton 11-8 ou plus récent** pour profiter du mode XInput automatique intégré.
- Le conseil apparaît dans **Paramètres → Conseil : manettes Sony** et lors du choix d'une version GE-Proton.
- **Aucune variable imposée** : GE-Proton conserve son fonctionnement natif. Les réglages propres aux jeux dans `autorun.cmd` restent prioritaires.
- Confirmation sous Batocera avec GE-Proton 11-11 via UMU : une DualSense est reconnue sans variable Sony sur l'ancienne version d'Azimuth ; avec `PROTON_SONY_AUTO_XINPUT=0`, elle ne l'est plus. Cette observation valide le rôle du mode automatique pour ce jeu.
- **Aucune modification du lanceur UMU ni des runners installés** : intégration 3.10.10 conservée. Aucun nouveau réglage manuel à configurer.

## English

**UMU Runner Toolbox v0.13.13 — runner integration 3.10.10 (unchanged)**

- **Sony controllers (DualSense / DualShock 4):** recommend **GE-Proton 11-8 or newer** for built-in automatic XInput compatibility.
- The tip is available in **Settings → Sony controller advice** and in the GE-Proton version picker.
- **No forced environment variables:** GE-Proton uses its native defaults. Existing per-game `autorun.cmd` overrides continue to apply.
- Confirmed on Batocera with GE-Proton 11-11 through UMU: a DualSense works without Sony variables on an older Azimuth build, and stops being detected with `PROTON_SONY_AUTO_XINPUT=0`. This demonstrates the automatic mode's impact for that game.
- **No runner or launcher changes**; integration 3.10.10 stays intact. No new per-game manual setting is required.
