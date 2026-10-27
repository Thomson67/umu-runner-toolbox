# UMU Runner Toolbox pour Batocera

[README in English](../README.md)

**UMU Runner Toolbox** est un outil communautaire permettant d'installer, gérer, vérifier, mettre à jour et partager des runners **GE-Proton, GDK-Proton, CachyOS Proton, Proton-EM et DW-Proton via UMU** sous Batocera.

Version stable actuelle : **v0.13.13**
Version de l'intégration runner : **v3.10.10**

## Manettes Sony : GE-Proton recommandé

Pour les manettes **DualShock 4 et DualSense**, utiliser de préférence **GE-Proton 11-8 ou supérieur** avec UMU. Depuis GE-Proton 11-8, le repli automatique vers XInput est normalement disponible sans ajouter `PROTON_SONY_HIDRAW_XINPUT=1` manuellement. La Toolbox ne force aucune de ces variables : le fonctionnement natif du runner et les exceptions définies dans `autorun.cmd` sont respectés. Les runners antérieurs restent disponibles. Le conseil apparaît dans **Paramètres > Manettes Sony** et lors du choix d'un GE-Proton.

L'intégration **3.10.9** exclut de la copie du préfixe `.wine` l'ancien dossier de jeu conservé par une mise à jour Ultimate Wine Toolbox en cours. L'état actif et son journal doivent correspondre exactement au préfixe et au dossier de secours. Ce dossier est également préservé pendant la synchronisation au retour du jeu. Les autres dossiers `.bak` et les lancements sans journal correspondant gardent leur comportement habituel. Installer cette intégration après la fin de la session UMU actuelle : elle ne modifie pas un wrapper déjà lancé.

L'intégration **3.10.10** répare aussi les liens vers un ancien runner disparu en utilisant le runner explicitement sélectionné. Les modules PE Wine, notamment DLL, exécutables, pilotes et thèmes, exigent le même nom de fichier et une architecture PE correspondante. Une copie privée remplace le lien dans le préfixe ; les runners restent protégés. Les liens de polices déjà cassés sous Windows/Fonts sont remplacés depuis le runner sélectionné si la police existe, ou retirés pour laisser Wine utiliser ses polices de remplacement. Les autres entrées non résolues sont toutes signalées avant modification. Le contrôle préalable tient lui aussi compte du runner choisi pour le jeu dans Batocera.

L'intégration **3.10.9** supprime automatiquement les préfixes matérialisés après synchronisation réussie et libération des montages. Les changements reviennent dans le `.wine` d'origine ou dans la bouteille Batocera accessible par l'OverlayFS du jeu compressé. L'archive et le dossier externe du jeu restent intacts. La synchronisation des sauvegardes du mode direct doit aussi réussir avant suppression. Avant copie, l'espace nécessaire est estimé sans le jeu ni son ancien dossier UWT identifié, avec une réserve de 256 Mio.

Un verrou partagé avec le nettoyage manuel protège la session. Un journal suit le processus (démarrage et identité du boot), la préparation et la synchronisation. Les préparations interrompues peuvent être nettoyées au prochain lancement. Une session de jeu non synchronisée est conservée pour récupération. Au lancement suivant, une copie complète identifiée avec la même version source vérifiée, la même identité de runner, le même mode direct et le même dossier de jeu est reprise sans nouvelle copie, y compris après Hotkey + Start. Une identité différente ou invérifiable bloque la reprise et l’écrasement. Les anciennes copies sans journal sont conservées une fois sous `.legacy-*` lors de leur réutilisation : elles nécessitent une vérification. Le menu **Maintenance > Copies UMU conservées** affiche le jeu, l'espace occupé, la date du dernier état, le runner et le journal de lancement lorsqu'ils sont connus. Il explique comment reprendre une copie identifiée en relançant le même jeu depuis EmulationStation, ou permet d'abandonner une seule copie après confirmation. Une copie locale sans journal, ou avec un journal ordinaire invalide, peut etre abandonnee apres confirmation et verification des sessions et montages ; un journal redirige reste refuse. Le nettoyage global est bloqué tant que des récupérations restent conservées. Une copie modifiée depuis sa sélection invalide l'ancienne confirmation de suppression. Les nouveaux échecs de synchronisation enregistrent leur motif et demandent une notification ES ; les interruptions brutales sont signalées à la prochaine ouverture de la Toolbox. Le nettoyage automatique vise uniquement les copies identifiées comme supprimables, sans montage actif, y compris dans un conteneur encore vivant. Il ne purge pas automatiquement les compatdata, caches graphiques, runners ou sauvegardes persistantes.

L'objectif est de simplifier l'utilisation de Proton via UMU depuis Batocera tout en isolant les runners UMU du reste de l'environnement Wine. Les runners standards Batocera, Wine-TKG et Kron4ek ne sont pas modifiés.

## Fonctionnalités principales

- Installation et suppression contrôlée de runners GE-Proton-UMU, GDK-Proton-UMU, CachyOS Proton UMU, Proton-EM-UMU et DW-Proton-UMU.
- Installation et mise à jour de `umu-run` avec vérification SHA-512.
- Téléchargement de GE-Proton avec contrôle du checksum SHA-512 upstream.
- Téléchargement de GDK-Proton avec vérification des digests SHA-256 GitHub lorsqu'ils sont disponibles.
- Installation des releases CachyOS Proton Steam Linux Runtime (SLR) prises en charge via le même système UMU géré.
- Installation des releases officielles Proton-EM de BananaWorks07/Proton avec vérification SHA-256 upstream obligatoire. Les releases sans checksum restent visibles mais sont clairement indiquées comme non installables.
- Installation des releases DW-Proton x86_64 de dawn-winery/dwproton-mirror avec vérification SHA-512 upstream obligatoire.
- Vérification de l'intégrité des runners gérés grâce à un manifest.
- Protection automatique en lecture seule des runners `*-UMU` pendant un lancement UMU.
- Export d'un runner ou création d'un package autonome partageable.
- Diagnostic UMU et nettoyage sécurisé des données temporaires.
- Résolution automatique de `GAMEID` et `STORE` depuis le gamelist Windows de Batocera pour ProtonFixes.
- Mise à jour de la Toolbox depuis GitHub Releases avec contrôle SHA-256 et sauvegarde préalable.
- Support Pad2Key pour piloter la Toolbox directement depuis Ports.
- Conservation du mode Sony HIDRAW natif, de la détection PlayStation et des fonctions DualSense prises en charge ; respect des options explicites et des correctifs par jeu de Proton.
- Compatibilité Batocera 41 avec les adaptations nécessaires à Steam Runtime / pressure-vessel.

> **v0.13.2 :** ajoute de courtes descriptions dans les menus et des explications sur les familles de runners. L'analyse GAMEID charge ses sources une seule fois, et les propositions donnent la priorité au titre principal plutôt qu'aux mentions d'édition, en distinguant les numéros de suites. Lors d'un test utilisateur sur 1 265 jeux, l'analyse a pris environ 50 secondes contre plus de deux minutes auparavant ; le temps dépend du matériel et des sources de correspondances disponibles.

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

## Installer un runner Proton-UMU

Le menu d’installation propose cinq familles : **GE-Proton**, **GDK-Proton**, **CachyOS Proton**, **Proton-EM** et **DW-Proton**. Chaque version est installée dans son propre dossier `*-UMU` et n’écrase jamais un runner existant.

Lancer **UMU Runner Toolbox** depuis Ports puis choisir la famille et la version du runner souhaité. La Toolbox télécharge la version sélectionnée, applique les contrôles disponibles, ajoute l'intégration Batocera/UMU et crée son manifest d'intégrité.

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

Le jeu peut donc toujours être lancé, mais sans identification spécifique exploitable par ProtonFixes. Les formats `.pc`, `.wine` et `.wsquashfs` sont pris en charge par le resolver pour retrouver le jeu Batocera et appliquer les informations GAMEID/STORE.

Dans la majorité des cas, aucune configuration manuelle de `GAMEID` ou `STORE` n'est nécessaire.

## Résolution automatique via les ProtonFixes Steam

Lorsqu'un titre est absent de la base UMU, le resolver peut désormais examiner les `gamefixes-steam/*.py` de ProtonFixes installés localement. Il lit uniquement la docstring du module, sans exécuter le fix pendant la détection, puis n'accepte automatiquement un AppID Steam que si **un seul** titre de ProtonFix correspond exactement après normalisation au titre Batocera. En cas d'absence ou d'ambiguïté, aucun AppID n'est forcé. Une détection sûre est journalisée sous `AUTO_STEAM_MATCH`.

## Associations manuelles GAMEID / STORE

Le menu principal **Compatibilité des jeux** permet d'analyser les correspondances ambiguës, de choisir un jeu depuis `gamelist.xml`, puis de sélectionner une proposition classée issue de la base UMU ou des ProtonFixes Steam installés. Le `GAMEID` et le `STORE` peuvent également être renseignés manuellement. Le GAMEID peut être un identifiant `umu-*` ou un **AppID Steam numérique** ; un identifiant numérique permet à ProtonFixes de rechercher directement un fix dans `gamefixes-steam`.

L'association manuelle est prioritaire sur la détection automatique. Elle peut être supprimée à tout moment pour revenir au fonctionnement automatique. Les associations sont conservées dans `config/gameid-overrides.csv`, dossier déjà préservé lors des mises à jour de la Toolbox.

L'interface prend en compte les entrées `.wsquashfs`, `.wine`, `.pc` et `.wtgz`. Les entrées `.exe` sont ignorées pour éviter les exécutables techniques de Wine. L'analyse lit `gamelist.xml` sans parcourir récursivement le contenu des préfixes `.wine` ni les dossiers de médias. Les sources de correspondances sont chargées une seule fois par analyse.

Le classement privilégie le titre principal. Les mentions « Definitive Edition », « Deluxe » ou « Remastered » permettent de départager des variantes d'un même jeu, sans rendre probable un jeu sans rapport. Les numéros de suites différents sont pénalisés ; les chiffres romains et arabes en fin de titre sont rapprochés. Les sous-titres restent pris en compte. Si l'édition exacte est absente, une proposition pour le jeu de base reste à vérifier manuellement.

Le bilan compte aussi les jeux sans correspondance, mais la liste de contrôle global présente uniquement les cas ambigus. Après une association, elle reste ouverte pour traiter plusieurs jeux à la suite. Cette analyse ne crée aucune association automatiquement et ne modifie pas les associations déjà enregistrées.

Le menu de maintenance permet également de nettoyer séparément les logs UMU Runner et Toolbox, avec affichage de l'espace occupé et conservation du log Toolbox de la session en cours.

## Intégrité et protection des runners

Les runners préparés par la Toolbox disposent d'un **manifest d'intégrité**. Il permet de vérifier que les fichiers gérés du runner n'ont pas été modifiés.

Ces contrôles sont notamment utilisés avant certaines opérations de maintenance, de migration ou d'export. Un runner modifié n'est pas silencieusement considéré comme sain.

Pendant un lancement UMU, les runners `*-UMU` gérés sont automatiquement protégés en lecture seule. **Le préfixe Wine du jeu reste modifiable normalement.**

Cette protection permet notamment de tester plusieurs runners Proton-UMU sur un même préfixe sans qu'un lancement puisse modifier accidentellement un autre runner.

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

L'intégration ne force plus `PROTON_SONY_HIDRAW_XINPUT=1` lorsque HIDRAW est activé. Laisser cette option absente pour la prise en charge Sony native. Utiliser `ENV=PROTON_SONY_HIDRAW_XINPUT=1` dans l'autorun du jeu uniquement si une compatibilité XInput est nécessaire, ou `0` pour un test explicite du mode natif. Proton peut toujours appliquer ses propres correctifs par jeu. Il n'est pas utile d'activer HIDRAW systématiquement si le jeu fonctionne déjà correctement.

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

Le script `uninstall.sh` retire uniquement la Toolbox : son dossier, son lanceur Ports et une éventuelle ancienne installation pré-v0.5.2b. Il conserve volontairement les runners Proton-UMU gérés déjà installés, UMU, les jeux, les Wine bottles et les sauvegardes.

## À retenir

La Toolbox automatise volontairement l'essentiel de l'intégration UMU : installation, contrôles d'intégrité, protection des runners, résolution `GAMEID` / `STORE`, mises à jour et diagnostics.

Pour une utilisation normale, il n'est pas nécessaire de modifier manuellement les fichiers des runners ou les variables UMU.

## Documentation complémentaire

### Chemin du jeu conservé sur C:

L’intégration 3.10.7 monte temporairement le dossier réel du jeu sous drive_c dans le préfixe Proton actif. Avec un dossier d’origine drive_c/game, le jeu et ses sélecteurs de fichiers retrouvent C:\game. Un autre nom d’origine reste conservé. Les formats .wine et .wsquashfs utilisent cette vue, sans copier les données du jeu dans le préfixe matérialisé ; pour une archive, la source reste la vue fusionnée de Batocera.

Le lancement normal utilise aussi cette vue pour l’exécutable et son répertoire courant. Le mode UMU_DIRECT_GAME=1 garde ses chemins de lancement actuels, avec l’accès C: disponible en complément. La vue est démontée avant la synchronisation du préfixe et avant son montage parent. Les fichiers du jeu restent exclus de la copie du préfixe.

Sélectionner une fois C:\game dans l’application si elle avait enregistré un chemin S:\... ; aucun réglage applicatif n’est réécrit automatiquement. Pour comparer avec l’ancien fonctionnement, ajouter UMU_C_GAME_PATH=0 à la ligne ENV= de l’autorun. Le journal indique runtime_c_game_source, runtime_c_game_target, runtime_c_game_windows et le nettoyage runtime_c_game_unmounted. Cette version demande encore une validation réelle sur Batocera, notamment en .wsquashfs.

### Comparaison du partage des caches graphiques

Avec l’intégration 3.10.6, **Paramètres → Partage des caches graphiques (test performances)** permet de désactiver puis réactiver le partage automatique des dossiers de cache Batocera avec le conteneur UMU. Activé par défaut, ce choix s’applique aux prochains lancements et reste conservé après mise à jour.

Pour un seul jeu, ajouter `UMU_GRAPHICS_CACHE_SHARING=0` à sa ligne `ENV=` d’autorun ; `1` force l’activation. Ce réglage par jeu est prioritaire sur le choix global. Le journal du runner indique `graphics_cache_sharing=0` ou `1`.

Aucun cache n’est supprimé. Désactiver retrouve le comportement de partage antérieur au correctif : les autres caches de Proton/Mesa et les partages explicitement configurés restent possibles. La compilation peut reprendre si un chemin de cache Batocera redevient invisible. Comparer séparément le premier lancement et les suivants. Fermer le jeu entre chaque changement.

L'ancien guide détaillé d'installation et de partage reste disponible dans [GUIDE_PARTAGE_ET_INSTALLATION.txt](GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Crédits

UMU Runner Toolbox est un projet communautaire destiné à intégrer l'écosystème UMU et les runners GE-Proton, GDK-Proton, CachyOS Proton, Proton-EM et DW-Proton à Batocera. Il s'appuie notamment sur **UMU Launcher**, **GE-Proton**, **GDK-Proton**, **CachyOS Proton**, **Proton-EM**, **DW-Proton**, **ProtonFixes**, **Steam Runtime** et **Batocera**. Les marques et noms de projets appartiennent à leurs propriétaires respectifs.

## Licence

Le projet est distribué sous licence **GNU General Public License v3.0 (GPL-3.0)**. Voir [LICENSE](../LICENSE).


## Compatibilité par jeu : mode direct

Ajouter `UMU_DIRECT_GAME=1` à l’unique ligne `ENV=` de `autorun.cmd` pour les jeux refusant les chemins redirigés ou les liens de sauvegardes. Les autres jeux conservent leur mode de lancement. L’intégration 3.10.4 conserve Steam Runtime et les protections des runners. Les sauvegardes `SAVEDIR` situées dans le répertoire du jeu sont copiées dans un vrai dossier au lancement, synchronisées à la fermeture, puis le lien Batocera est restauré. Une seule copie de secours est conservée dans le dossier de sauvegardes du jeu sous `.umu-direct-previous`, et exclue des copies suivantes. Fermer normalement le jeu ; une interruption forcée peut nécessiter une récupération. Les copies demandent de l’espace libre et un délai proportionnel à la taille des sauvegardes.

## Correctif des copies de travail (version de test)

Toolbox **0.13.14-test6**, intégration **3.10.16** : la reprise vérifie la génération réelle de l'archive (fichier associé au périphérique loop, inode, taille et dates précises), les registres/autorun du préfixe, le runner et le mode direct. Le remplacement d'un WSquashFS au même emplacement, un retour à une ancienne version ou une origine non vérifiable déclenche une nouvelle copie ; les anciennes modifications sont conservées séparément, sans être injectées dans le nouveau jeu. Aucun hachage complet des grosses archives. Un montage d'archive non identifiable désactive la reprise automatique.

**Hotkey + Start** peut tuer le wrapper et ses enfants sans exécuter le nettoyage de sortie. La copie non synchronisée reste alors conservée. Avec `UMU_DIRECT_GAME=1`, le chemin des sauvegardes et leur cible externe sont journalisés avant remplacement du lien. Au prochain lancement de la même version vérifiée, les sauvegardes récentes restées dans le dossier du jeu sont reprises sans recopier les anciennes sauvegardes externes. Une version modifiée, un historique absent ou un retour des sauvegardes partiellement effectué bloque la reprise automatique et conserve les fichiers pour examen manuel. Après synchronisation réussie du préfixe et des sauvegardes directes, puis libération des montages, la copie de travail est supprimée. La génération de secours `.umu-direct-previous` reste distincte de ce préfixe temporaire.

Le menu Maintenance permet d'abandonner explicitement une copie locale sans journal. Il vérifie à nouveau les fichiers imbriqués, le journal, les sessions et les montages avant suppression, et affiche la cause précise d'un refus. Cette suppression ne nettoie pas les sauvegardes directes restées dans le dossier du jeu.

Les tests locaux tuent réellement un groupe de processus avec SIGKILL et couvrent l'arrêt normal, la reprise directe, une interruption entre retour du préfixe et retour des sauvegardes, le changement de version et l'échec de synchronisation. Ils modélisent les montages compressés ; le comportement de Forza Horizon 2 reste à confirmer sur Batocera avec ce correctif. Fermer les jeux avant installation ; l'installateur migre les runners gérés sains vers l'intégration 3.10.16.

L'intégration **3.10.12** traite aussi le retrait du montage original `/run/wine` avant le retour du préfixe. Si ce chemin n'est plus un OverlayFS, le retour peut utiliser l'alias encore monté par le wrapper, uniquement s'il est inscriptible et correspond aux mêmes upperdir/lowerdir enregistrés. Aucun retour direct dans le SquashFS ni dans un dossier de montage vide. L'identité de la source est vérifiée à travers cette vue encore vivante, tout en gardant le chemin source original dans le journal. Les refus précisent les types de systèmes de fichiers et le contrôle en échec. Une copie de récupération antérieure peut rester conservée séparément après cette mise à niveau ; l'examiner ou l'abandonner dans Maintenance après validation du jeu.

L'intégration **3.10.13** corrige un faux refus `refused-alias-upperdir` pour les chemins contenant des espaces : les options de l'alias sont lues sans l'échappement hexadécimal du mode raw de findmnt, comme lors de la détection initiale. L'option `--notruncate` conserve les valeurs complètes. Le test utilise le vrai findmnt util-linux, une table mountinfo isolée et le chemin FH2. Les contrôles de correspondance upperdir/lowerdir restent obligatoires.

L'intégration **3.10.14** synchronise le contenu des dossiers du préfixe sur place, au lieu de supprimer puis recréer leurs racines. Cela évite le refus FH2 `dosdevices: Directory not empty`, tout en retirant les entrées obsolètes et en préservant l'autorun courant, le dossier du jeu et le backup UWT validé. Chaque fichier est copié dans un espace temporaire du système de fichiers cible, puis remplacé individuellement : aucun fichier de runner lié au préfixe n'est modifié par écriture à travers un lien. Les dossiers communs conservent leur inode. Le retour complet n'est pas atomique ; un échec ou une interruption conserve toujours le préfixe de récupération. Les espaces réservés `.umu-prefix-sync-*` ne sont pas recopiés dans les préfixes de travail ; l'espace de la session courante est retiré à la fin normale du retour.

L'intégration **3.10.15** prépare chaque fichier/lien temporaire à côté de sa destination, au lieu de déplacer une entrée depuis un espace temporaire à la racine vers les sous-dossiers fusionnés. Cette adaptation suit le retour FH2 en ENOENT sur `drive_c/openxr/wineopenxr64.json`. Les remplacements restent privés et atomiques par entrée ; les racines de dossiers restent en place. Les candidats temporaires sont exclus du retour à tous les niveaux et retirés lors du retour normal ou d'une erreur gérée. Le diagnostic précise source, destination et présence du parent/candidat. Le test modélise le refus des déplacements entre dossiers ; une validation réelle Batocera reste nécessaire.

L'intégration **3.10.16** ajoute une attente à la fermeture native. Pour une session identifiée exactement par son préfixe d'origine, `bin/wineserver -w` attend Wine, puis la fin du wrapper hôte et de son nettoyage. Les attentes internes Proton et les associations par runner seul ne bloquent pas leur parent. Le journal de session contient l'identité de démarrage du processus ; un processus mort, zombie ou un PID réutilisé libère l'attente. Un arrêt forcé conserve toujours les données non rapatriées et le code d'erreur natif est préservé.

Cette correction traite la course de fermeture suggérée par le journal FH2 : Batocera supprime son workdir OverlayFS après l'attente wineserver, qui ne couvrait pas le retour du wrapper UMU. Le chemin `runtime_workdir` est journalisé ; s'il a déjà perdu son dossier interne `work`, le retour est refusé avec le code 14. Les tests modélisent le nettoyage natif après -w et vérifient qu'il attend le retour du préfixe, des sauvegardes directes et la fin du nettoyage du wrapper. L'essai sur le build Batocera de l'utilisateur reste nécessaire. Les marqueurs `runtime_wait_begin` et `runtime_wait_end` apparaissent dans wineserver-stop.log. Les anciennes sessions sans identité de processus gardent leur comportement antérieur. Installer uniquement avec les jeux fermés.
