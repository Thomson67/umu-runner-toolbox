# UMU Runner Toolbox v0.9.0

UMU Runner Toolbox est un outil communautaire pour Batocera x86_64 permettant d'installer, gerer, diagnostiquer et partager des runners Proton via UMU.

## Runners geres

- GE-Proton (GloriousEggroll/proton-ge-custom)
- GDK-Proton (Weather-OS/GDK-Proton)

Les runners Batocera standards, Wine-TKG et Kron4ek ne sont pas modifies.

## Nouveautes v0.9.0

- Provider GDK-Proton avec verification SHA-256 des assets GitHub quand le digest est disponible.
- Support de l'archive historique GDK-Proton10-25 publiee sous le nom `GE-Proton10-25.tar.gz`.
- GE-Proton10-30 a 10-34 de nouveau installables.
- Compatibilite `.wsquashfs` : le jeu reste sur la vue OverlayFS fusionnee de Batocera, tandis que le PFX Proton est materialise sur un vrai systeme de fichiers.
- Compatdata des jeux compresses isole par runner afin d'eviter les migrations croisees GE/GDK.
- Resolver `.wine` corrige : le chemin complet du jeu est transmis au resolver GAMEID.
- Maintenance, export, integrite, protection, suppression et desinstallation adaptes aux runners GE-Proton-UMU et GDK-Proton-UMU.
- Nettoyage des nouveaux repertoires runtime `materialized-prefixes` et `gameviews`, avec nettoyage des anciens repertoires TEST7 si presents.
- Migration de l'integration des runners geres existants apres installation/mise a jour, uniquement si leur manifest d'integrite est sain.

## Installation

Le package local contient son propre `install.sh`. L'installation sauvegarde la Toolbox precedente, conserve `config/`, synchronise le Port/Pad2Key puis met a niveau l'integration des runners UMU geres et intacts.

L'installation publique depuis GitHub reste assuree par le `install.sh` bootstrap du depot une fois la release publiee.

## Securite

La Toolbox applique une politique immutable aux runners : une version deja installee n'est pas ecrasee. Les runners geres sont controles par manifest SHA-256 et proteges en lecture seule pendant les lancements UMU.

La suppression d'un runner ne supprime pas les jeux, les `.wine`/`.wsquashfs`, les wine-bottles ni les sauvegardes. La desinstallation complete est une action distincte et explicite dans le menu Maintenance.
