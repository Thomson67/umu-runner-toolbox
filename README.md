# UMU Runner Toolbox for Batocera

UMU Runner Toolbox facilite l'installation, la gestion, le diagnostic et le partage de runners **GE-Proton + UMU** sous Batocera.

Version stable actuelle : **v0.5.2b**  
Integration runner : **v3.7.1**

## Fonctionnalites principales

- installation de runners GE-Proton-UMU ;
- suppression controlee des runners UMU ;
- verification d'integrite par manifest ;
- protection en lecture seule des runners `*-UMU` pendant les lancements UMU ;
- export d'un runner ou creation d'un package partageable ;
- diagnostic et maintenance UMU ;
- nettoyage securise des donnees temporaires de tests UMU ;
- prise en charge de `PROTON_SONY_HIDRAW_XINPUT=1` avec les versions recentes de GE-Proton lorsque Batocera active HIDRAW et que le winebus du runner le supporte.

La Toolbox ne modifie pas les runners standards Batocera, Wine-TKG ou Kron4ek.

## Compatibilite

L'integration a ete concue pour les jeux Batocera Windows utilisant notamment :

- `.pc` ;
- `.wine` ;
- `.wsquashfs` et les overlays Batocera ;
- `wine-bottles` ;
- les sauvegardes externes sous `/userdata/saves`.

## Installation locale

Copier ou extraire le projet sur Batocera, puis en root :

```bash
chmod +x install.sh
./install.sh
```

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

## Installation distante

L'installation en une commande sera ajoutee apres validation du mecanisme de publication GitHub Releases. Aucune URL distante n'est volontairement figee dans cette premiere publication du depot.

## Documentation

Le guide detaille est disponible dans [`docs/GUIDE_PARTAGE_ET_INSTALLATION.txt`](docs/GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Logs

```text
Wrapper : /userdata/system/logs/umu-runner/
Toolbox : /userdata/system/logs/umu-toolbox/
```

## Licence

Ce projet est distribue sous licence **GNU General Public License v3.0 (GPL-3.0)**. Voir [`LICENSE`](LICENSE).
