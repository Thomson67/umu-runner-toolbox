# UMU Runner Toolbox pour Batocera

[README in English](../README.md)

**UMU Runner Toolbox** est un outil communautaire permettant d'installer, gérer, vérifier, mettre à jour et partager des runners **GE-Proton + UMU** sous Batocera.

Version stable actuelle : **v0.7.0**  
Version de l'intégration runner : **v3.7.5**

L'objectif est de simplifier l'utilisation de Proton via UMU depuis Batocera tout en isolant les runners UMU du reste de l'environnement Wine. Les runners standards Batocera, Wine-TKG et Kron4ek ne sont pas modifiés.

## Fonctionnalités principales

- Installation et suppression contrôlée de runners GE-Proton-UMU.
- Installation et mise à jour de `umu-run` avec vérification SHA-512.
- Téléchargement de GE-Proton avec contrôle du checksum SHA-512 upstream.
- Vérification de l'intégrité des runners gérés grâce à un manifest.
- Protection automatique en lecture seule des runners `*-UMU` pendant un lancement UMU.
- Export d'un runner ou création d'un package autonome partageable.
- Diagnostic UMU et nettoyage sécurisé des données temporaires.
- Résolution automatique de `GAMEID` et `STORE` depuis le gamelist Windows de Batocera pour ProtonFixes.
- Mise à jour de la Toolbox depuis GitHub Releases avec contrôle SHA-256 et sauvegarde préalable.
- Support Pad2Key pour piloter la Toolbox directement depuis Ports.
- Prise en charge de `PROTON_SONY_HIDRAW_XINPUT=1` lorsque HIDRAW est activé et supporté.
- Compatibilité Batocera 41 avec les adaptations nécessaires à Steam Runtime / pressure-vessel.

> **Attention :** GE-Proton10-30 à GE-Proton10-34 sont volontairement bloqués. Ces versions ont été constatées incompatibles avec cette intégration Batocera + UMU et peuvent échouer au lancement avec un code de sortie 245. GE-Proton10-29 et les versions 11.x ne sont pas concernés par ce blocage spécifique.

## Installation rapide

Depuis un terminal Batocera ou une connexion SSH, en `root` :

```bash
curl -fsSL https://raw.githubusercontent.com/Thomson67/umu-runner-toolbox/main/install.sh | bash
```

L'installateur détecte la dernière release stable, télécharge le package et son SHA-256, vérifie son intégrité puis lance l'installateur contenu dans la release.

La Toolbox est ensuite disponible dans :

```text
Ports -> UMU Runner Toolbox
```

Fichiers de la Toolbox :

```text
/userdata/system/umu/toolbox
```

Exports :

```text
/userdata/system/umu/exports
```

## Installation locale

Après téléchargement et extraction d'une release :

```bash
chmod +x install.sh
./install.sh
```

L'installation doit être lancée en `root`.

## Installer un runner GE-Proton-UMU

Lancer **UMU Runner Toolbox** depuis Ports puis choisir l'installation d'un runner GE-Proton UMU. La Toolbox télécharge la version sélectionnée, contrôle son checksum upstream, ajoute l'intégration Batocera/UMU et crée son manifest d'intégrité.

Le runner obtenu peut ensuite être sélectionné dans les options avancées d'un jeu Windows dans EmulationStation.

## GAMEID, STORE et ProtonFixes

UMU peut transmettre à ProtonFixes l'identité du jeu grâce aux variables `GAMEID` et `STORE`. La Toolbox automatise leur résolution pour les jeux Windows Batocera.

Lors d'un lancement, le résolveur :

1. recherche le jeu dans `/userdata/roms/windows/gamelist.xml` ;
2. récupère son titre Batocera ;
3. recherche ce titre dans la base UMU fournie avec la Toolbox ;
4. détermine le `GAMEID` et le `STORE` correspondants ;
5. si plusieurs stores correspondent, examine les gamefixes ProtonFixes disponibles pour choisir le store pertinent lorsque cela est possible.

Si aucune correspondance suffisamment fiable n'est trouvée, il utilise :

```text
GAMEID=umu-default
```

Le jeu peut donc toujours être lancé, mais sans identification spécifique exploitable par ProtonFixes. Les conteneurs `.wine` et `.wsquashfs` portant le même nom sont reconnus comme des représentations équivalentes du même jeu lors de la recherche dans le gamelist.

Dans la majorité des cas, aucune configuration manuelle de `GAMEID` ou `STORE` n'est nécessaire.

## Intégrité et protection des runners

Les runners préparés par la Toolbox disposent d'un **manifest d'intégrité**. Il permet de vérifier que les fichiers gérés du runner n'ont pas été modifiés.

Ces contrôles sont notamment utilisés avant certaines opérations de maintenance, de migration ou d'export. Un runner modifié n'est pas silencieusement considéré comme sain.

Pendant un lancement UMU, les runners `*-UMU` gérés sont automatiquement protégés en lecture seule. **Le préfixe Wine du jeu reste modifiable normalement.**

Cette protection permet notamment de tester plusieurs versions de GE-Proton-UMU sur un même préfixe sans qu'un lancement puisse modifier accidentellement un autre runner.

## Mises à jour

### Toolbox

La Toolbox peut se mettre à jour depuis GitHub Releases. Le package et son SHA-256 sont vérifiés avant remplacement. La version actuelle est sauvegardée et le dossier local `config/` est conservé.

### UMU

`umu-run` peut être mis à jour indépendamment depuis la Toolbox, avec vérification SHA-512 lorsque le checksum upstream est disponible.

### Intégration des runners

Les mises à niveau de l'intégration sont appliquées aux runners gérés qui passent les contrôles d'intégrité requis. Les runners non gérés ou modifiés sont ignorés afin d'éviter d'écraser une installation personnalisée.

## Compatibilité

La Toolbox est prévue pour les principaux formats Windows utilisés sous Batocera :

- `.pc` ;
- `.wine` ;
- `.wsquashfs` ;
- Wine bottles.

### Batocera 41

Batocera 41 nécessite des adaptations supplémentaires pour Steam Runtime / pressure-vessel, notamment autour du module Python `_lzma` absent dans l'environnement concerné et du cache `ldconfig`. La Toolbox fournit ce contournement tout en conservant le chemin UMU natif sur les versions plus récentes qui disposent déjà des composants nécessaires.

La base de compatibilité introduite avec la v0.6.5 a été testée avec succès sous Batocera 41 avec `GE-Proton10-25-UMU` et `GE-Proton11-5-UMU`.

La compatibilité peut naturellement varier selon le jeu, la version de Proton, les pilotes graphiques et la version de Batocera.

## DualShock / DualSense et HIDRAW

Certains jeux utilisant une manette Sony peuvent nécessiter HIDRAW. Si une DualShock ou DualSense n'est pas reconnue correctement, activer **HIDRAW** dans les paramètres avancés du jeu puis relancer celui-ci.

Lorsque les conditions sont réunies, l'intégration peut utiliser `PROTON_SONY_HIDRAW_XINPUT=1`. Il n'est pas utile d'activer HIDRAW systématiquement si le jeu fonctionne déjà correctement.

## Maintenance et diagnostic

Le menu **Maintenance et diagnostic** regroupe notamment le contrôle d'intégrité, l'état de la protection, la réparation/mise à niveau de l'intégration, le diagnostic UMU complet et le nettoyage sécurisé de certaines données temporaires.

Le nettoyage n'est effectué que lorsqu'aucun lancement UMU n'est actif. Les caches Mesa/RADV sont proposés séparément et restent facultatifs. Cette opération ne supprime pas `umu-run`, Steam Runtime UMU, ProtonFixes, les runners, les sauvegardes UMU ni les données des jeux Batocera.

## Logs

En cas de problème, le **Diagnostic UMU complet** constitue un bon point de départ.

```text
Wrapper runner : /userdata/system/logs/umu-runner/
Toolbox        : /userdata/system/logs/umu-toolbox/
```

## Exporter ou partager un runner

Deux méthodes sont proposées :

**Package autonome / partageable**  
Recommandé pour une installation Batocera qui ne dispose pas encore de l'infrastructure UMU. Le package contient le runner, ses informations d'intégrité, un installateur et les contrôles nécessaires.

**Archive du runner uniquement**  
Destinée plutôt à une sauvegarde ou au transfert vers une installation Batocera déjà préparée pour UMU.

Un runner modifié qui échoue au contrôle d'intégrité n'est pas considéré comme fiable pour un export géré normal.

## Suppression et désinstallation

La suppression d'un runner depuis la Toolbox ne supprime pas les jeux ni leurs sauvegardes.

Le script `uninstall.sh` retire uniquement la Toolbox : son dossier, son lanceur Ports et une éventuelle ancienne installation pré-v0.5.2b. Il conserve volontairement les runners GE-Proton-UMU déjà installés, UMU, les jeux, les Wine bottles et les sauvegardes.

## À retenir

La Toolbox automatise volontairement l'essentiel de l'intégration UMU : installation, contrôles d'intégrité, protection des runners, résolution `GAMEID` / `STORE`, mises à jour et diagnostics.

Pour une utilisation normale, il n'est pas nécessaire de modifier manuellement les fichiers des runners ou les variables UMU.

## Documentation complémentaire

L'ancien guide détaillé d'installation et de partage reste disponible dans [GUIDE_PARTAGE_ET_INSTALLATION.txt](GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Crédits

UMU Runner Toolbox est un projet communautaire destiné à intégrer l'écosystème UMU et les runners GE-Proton à Batocera. Il s'appuie notamment sur **UMU Launcher**, **GE-Proton**, **ProtonFixes**, **Steam Runtime** et **Batocera**. Les marques et noms de projets appartiennent à leurs propriétaires respectifs.

## Licence

Le projet est distribué sous licence **GNU General Public License v3.0 (GPL-3.0)**. Voir [LICENSE](../LICENSE).
