# UMU Runner Toolbox for Batocera

UMU Runner Toolbox facilite l'installation, la gestion, le diagnostic et le partage de runners **GE-Proton + UMU** sous Batocera.

Version stable actuelle : **v0.6.5**  
Integration runner : **v3.7.4**

## Fonctionnalites principales

- installation et suppression controlee de runners GE-Proton-UMU ;
- installation/mise a jour de `umu-run` avec verification SHA512 ;
- verification d'integrite par manifest ;
- protection en lecture seule des runners `*-UMU` pendant les lancements UMU ;
- export d'un runner ou creation d'un package partageable ;
- diagnostic, maintenance et nettoyage securise des donnees temporaires UMU ;
- Pad2Key natif Batocera pour piloter la Toolbox depuis Ports ;
- prise en charge de `PROTON_SONY_HIDRAW_XINPUT=1` lorsque HIDRAW est active et que le winebus du runner le supporte ;
- compatibilite Batocera 41 : contournement de l'absence de `_lzma` pour Steam Runtime et generation automatique du cache `ldconfig` requis par pressure-vessel.

La Toolbox ne modifie pas les runners standards Batocera, Wine-TKG ou Kron4ek.

## Compatibilite validee

La v0.6.5 a ete testee avec succes sur **Batocera v41** apres redemarrage avec :

- `GE-Proton10-25-UMU` ;
- `GE-Proton11-5-UMU`.

Elle conserve le chemin UMU natif lorsque l'hote fournit deja les composants requis, afin de ne pas modifier inutilement les versions plus recentes de Batocera.

## Installation en une commande

En root sur Batocera :

```bash
curl -fsSL https://raw.githubusercontent.com/Thomson67/umu-runner-toolbox/main/install.sh | bash
```

Le bootstrap telecharge la derniere release stable, verifie son SHA-256, extrait le package puis lance son installateur local.

La Toolbox est ensuite disponible dans :

```text
Ports -> UMU Runner Toolbox
```

Elle est installee sous :

```text
/userdata/system/umu/toolbox
```

Les exports sont ranges sous :

```text
/userdata/system/umu/exports
```

## Installation locale

Telecharger l'archive de release, l'extraire puis lancer en root :

```bash
chmod +x install.sh
./install.sh
```

## Documentation

Le guide detaille est disponible dans [`docs/GUIDE_PARTAGE_ET_INSTALLATION.txt`](docs/GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Logs

```text
Wrapper : /userdata/system/logs/umu-runner/
Toolbox : /userdata/system/logs/umu-toolbox/
```

## Licence

Ce projet est distribue sous licence **GNU General Public License v3.0 (GPL-3.0)**. Voir [`LICENSE`](LICENSE).
