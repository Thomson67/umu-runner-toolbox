# UMU Runner Toolbox — le guide pour débuter

Un parcours simple pour installer un runner, jouer et entretenir son installation. Le même guide est disponible hors ligne dans **Documentation / À propos** de la Toolbox.

[English guide](GUIDE_EN.md) · [Projet / détails techniques](../README.md)

- [Bien démarrer : installer et lancer un jeu](#start)
- [Wine, Proton, UMU : comprendre les mots](#basics)
- [Les cinq familles : quel runner choisir ?](#runners)
- [Les menus : à quoi sert chaque fonction ?](#menus)
- [Compatibilité des jeux : GAMEID et correctifs](#compat)
- [Manettes, affichage et caches graphiques](#controllers)
- [Sauvegardes et copies de travail : que conserve UMU ?](#saves)
- [Mode direct : pour certains jeux particuliers](#direct)
- [Maintenance : vérifier, réparer, nettoyer](#maintenance)
- [Mises à jour, export et partage](#sharing)
- [Dépannage : les bons réflexes et les journaux](#help)

<a id="start"></a>

## Bien démarrer : installer et lancer un jeu

UMU RUNNER TOOLBOX — VOTRE PREMIER LANCEMENT

Vous avez un jeu Windows dans Batocera ? La Toolbox prépare des runners
Proton compatibles avec UMU. Vous lancez ensuite le jeu depuis EmulationStation,
comme d'habitude. Il n'est pas nécessaire de garder la Toolbox ouverte.

1. Ouvrez Ports > UMU Runner Toolbox.
2. Choisissez Installer un runner, puis une famille et une version.
   Pour commencer, GE-Proton est un choix généraliste.
3. Laissez le téléchargement et la préparation se terminer.
4. Revenez à votre jeu Windows dans EmulationStation et ouvrez ses options
   avancées. Sélectionnez le runner installé, dont le nom se termine par -UMU.
5. Lancez le jeu. Au premier démarrage, la préparation peut être plus longue.
6. Faites une sauvegarde en jeu, quittez puis relancez pour vérifier le résultat.

Installer un runner ne l'affecte pas automatiquement à tous vos jeux. Vous
pouvez conserver plusieurs versions et choisir celle qui convient à chaque jeu.

À prévoir : une connexion Internet pour les téléchargements et suffisamment
d'espace pour le runner, le runtime et les données de travail. La taille varie
selon les versions et les jeux. Fermez les jeux avant installation ou maintenance.

Pour installer la Toolbox elle-même depuis un terminal Batocera :
https://github.com/Thomson67/umu-runner-toolbox
Le README du projet donne la commande d'installation de la version stable.

<a id="basics"></a>

## Wine, Proton, UMU : comprendre les mots

LE PETIT LEXIQUE

Wine : permet à des programmes Windows de fonctionner sous Linux.

Proton : s'appuie sur Wine et d'autres composants destinés aux jeux, notamment
pour traduire leurs appels graphiques. Ce n'est pas une installation de Windows.

Runner : la version de Wine/Proton choisie pour lancer votre jeu. Deux runners
peuvent donner des résultats différents sur un même jeu.

UMU : lance Proton hors de Steam avec l'environnement Linux prévu pour lui.
La Toolbox installe et relie ces éléments à Batocera.

Runtime Steam : ensemble de bibliothèques Linux utilisé par Proton via UMU.
Il ne s'agit pas du client Steam ; vous n'avez pas à ouvrir Steam pour jouer.

Préfixe Wine : petit environnement Windows propre au jeu : registre, disque C:,
composants et paramètres. Il peut aussi contenir des sauvegardes.

Bouteille : espace de modifications utilisé par Batocera, notamment pour les
jeux compressés. L'archive reste compressée, les changements sont stockés à côté.

Shader/cache graphique : données préparées pour afficher le jeu. Les conserver
peut éviter de répéter une partie de la compilation aux lancements suivants.

La UMU Runner Toolbox gère les runners et leur intégration. Pour préparer,
modifier ou recompresser vos jeux, Ultimate Wine Toolbox est un outil distinct.

<a id="runners"></a>

## Les cinq familles : quel runner choisir ?

CHOISIR SANS SE PERDRE

GE-Proton
Le point de départ généraliste du menu : correctifs de compatibilité et de
lecture vidéo. Si vous découvrez UMU, commencez par cette famille.

GDK-Proton
Une variante orientée WineGDK et les jeux utilisant Microsoft GDK. À essayer
pour ce besoin particulier. Cela ne garantit pas le fonctionnement du Microsoft
Store, des abonnements ou des services de connexion Microsoft.

Proton-CachyOS
Une autre famille avec ses propres changements et options. La Toolbox propose
les versions Steam Linux Runtime prises en charge. À comparer pour un jeu
précis ; le nom ne garantit pas de meilleures performances sur votre machine.

Proton-EM
Une variante proposant ses propres adaptations, notamment autour de l'affichage
selon la version. Les possibilités Wayland/HDR dépendent aussi de Batocera,
des pilotes et de votre écran. Choisir ce runner n'active pas tout à lui seul.

DW-Proton
Une alternative communautaire avec ses propres modifications. À tester si
vous cherchez une autre combinaison pour un jeu difficile.

LA BONNE MÉTHODE

- Gardez le runner avec lequel votre jeu fonctionne déjà.
- Testez une autre version si vous avez un problème concret.
- Changez un seul réglage à la fois et notez le résultat.
- Conservez l'ancien runner tant que le nouveau n'est pas validé.

Une version plus récente peut corriger un jeu et en perturber un autre.
Les numéros ne se comparent pas directement entre familles. Changer de runner
peut modifier le préfixe du jeu : pour un jeu important, sauvegardez d'abord
ses données persistantes. Revenir à l'ancien runner ne restaure pas ces données.

Projets sources et notes de versions :
GE-Proton : https://github.com/GloriousEggroll/proton-ge-custom
GDK-Proton : https://github.com/Weather-OS/GDK-Proton
CachyOS : https://github.com/CachyOS/proton-cachyos
Proton-EM : https://github.com/BananaWorks07/Proton
DW-Proton : https://github.com/dawn-winery/dwproton-mirror

<a id="menus"></a>

## Les menus : à quoi sert chaque fonction ?

LE TOUR DE LA TOOLBOX

Installer un runner
Choisissez une famille, puis une version. La Toolbox télécharge les composants,
contrôle les fichiers et prépare l'intégration. Les versions sont séparées ;
une nouvelle version n'écrase pas automatiquement l'ancienne.

Supprimer un runner
Libère la place occupée par ce runner. Vos jeux et leurs sauvegardes ne sont
pas supprimés. Les jeux qui l'utilisaient doivent recevoir un autre runner.

Exporter / partager
Crée une archive du runner ou un package avec son environnement et installateur.
Le chapitre Partager explique lequel choisir.

Compatibilité des jeux
Permet de vérifier ou corriger l'identité d'un jeu pour ses correctifs ProtonFixes.
Ce n'est pas une liste garantissant que les jeux vont fonctionner.

Maintenance et diagnostic
Vérifie l'installation, répare l'intégration, examine les copies conservées,
nettoie les données temporaires, les journaux ou les protections orphelines.

Mettre à jour la Toolbox
Recherche une release publiée. La mise à jour conserve la configuration locale
et sauvegarde l'ancienne Toolbox. Elle ne remplace pas vos jeux.

Documentation / À propos
Le guide que vous lisez : choisissez un chapitre et faites défiler son texte.

Paramètres
Choix de la langue, taille de police et affichage de la Toolbox, partage des
caches graphiques et conseils pour les manettes Sony. La langue et la police
concernent la Toolbox, pas les jeux. Certains changements d'affichage prennent
leur effet à la prochaine ouverture du terminal.

<a id="compat"></a>

## Compatibilité des jeux : GAMEID et correctifs

IDENTIFIER LE BON JEU

ProtonFixes peut appliquer des adaptations prévues pour un jeu : composants,
options ou réglages de compatibilité. Pour choisir les bons correctifs, UMU
utilise une identité appelée GAMEID et parfois la boutique d'origine, STORE.
Cela ne télécharge pas le jeu et ne donne pas accès à une boutique.

Le fonctionnement normal est automatique. Le résolveur utilise le titre dans
la liste de jeux Windows de Batocera, la base UMU et, lorsque la correspondance
est sûre, les correctifs Steam installés localement. Soignez le titre du jeu
dans EmulationStation ; un nom erroné peut empêcher une bonne identification.

Si aucun jeu n'est identifié, umu-default permet quand même de tenter le
lancement, sans identification spécifique pour les correctifs.

QUAND UTILISER LE MENU COMPATIBILITÉ ?

1. Analysez les correspondances pour repérer les cas ambigus.
2. Choisissez un jeu et vérifiez les propositions : titre, suite, édition,
   boutique. Ne validez pas un autre jeu simplement parce que le nom ressemble.
3. Enregistrez l'association adaptée. Elle passe avant la détection automatique.
4. Relancez le jeu pour tester.

Un utilisateur averti peut saisir un GAMEID umu-* ou un AppID Steam numérique.
Si vous ne connaissez pas l'identifiant, utilisez les propositions vérifiées.
L'analyse seule n'enregistre aucune association. Vous pouvez consulter ou
supprimer une association pour revenir à la détection automatique.

Un correctif peut améliorer la compatibilité, sans garantir qu'un jeu ou ses
services en ligne fonctionnent. N'associez pas toute votre bibliothèque au
hasard : un jeu qui fonctionne ne demande généralement aucune intervention.

<a id="controllers"></a>

## Manettes, affichage et caches graphiques

MANETTES

Commencez avec les réglages habituels du jeu. Pour une DualShock 4 ou DualSense
mal reconnue, essayez HIDRAW dans les options avancées du jeu puis relancez.
Le menu Paramètres > Manettes Sony conseille GE-Proton 11-8 ou supérieur.

La Toolbox respecte le comportement du runner et les variables explicites de
l'autorun. Certains jeux prennent directement en charge les manettes Sony,
d'autres attendent une manette Xbox/XInput. Les fonctions haptiques et les
icônes affichées dépendent aussi du jeu, du runner et du mode de connexion.
Il n'est pas nécessaire d'ajouter systématiquement des variables Sony.

AFFICHAGE

La taille de police et le plein écran de Paramètres servent à rendre la Toolbox
plus lisible. Pour la résolution, le plein écran ou les performances d'un jeu,
utilisez ses options et celles de Batocera. Le runner peut aussi influencer
le résultat ; changer plusieurs réglages en même temps complique le diagnostic.

CACHES GRAPHIQUES

Le partage des caches rend les dossiers configurés par Batocera accessibles à
l'environnement UMU. Laissez-le activé pour l'usage normal. Le premier lancement
peut compiler des shaders ; les suivants peuvent profiter des données conservées.

Le réglage de partage permet une comparaison de performances. Il s'applique
au prochain lancement et ne supprime aucun cache. Ce n'est pas un interrupteur
qui désactive tous les caches de Proton ou de Mesa.

Le nettoyage des caches Mesa/RADV est proposé séparément dans Maintenance.
Ils peuvent se reconstruire, avec un coût en temps de préparation et parfois
des saccades temporaires. Ce n'est pas un entretien nécessaire après chaque jeu.

<a id="saves"></a>

## Sauvegardes et copies de travail : que conserve UMU ?

COMPRENDRE OÙ VONT LES CHANGEMENTS

La Toolbox prend notamment en charge les jeux .pc, .wine et .wsquashfs intégrés
au lancement Wine de Batocera. Le détail du stockage dépend du format et de
la configuration du jeu.

Pour les préfixes .wine et les jeux compressés, l'intégration peut préparer
une copie de travail du petit environnement Windows. Le dossier du jeu est
présenté séparément : il n'est pas recopié intégralement à chaque lancement.

À la fermeture, les modifications du préfixe reviennent dans le .wine d'origine
ou la bouteille du jeu compressé. Quand les retours nécessaires ont réussi
et les montages ont été libérés, la copie temporaire est supprimée.
Une sauvegarde externe configurée par Batocera reste distincte de cette copie.

POURQUOI UNE COPIE RESTE-T-ELLE PARFOIS ?

Une coupure, un arrêt brutal ou un échec de synchronisation peut laisser des
changements uniquement dans la copie. Elle est conservée pour éviter de les
perdre. Une copie conservée n'est donc pas une simple poubelle à vider.

Dans Maintenance > Copies UMU conservées, examinez le jeu, le runner, la date,
la place occupée et le journal. Pour reprendre une session récupérable, relancez
le même jeu avec la même version source et le même runner. L'intégration vérifie
que les données correspondent avant de les réutiliser.

Si vous avez remplacé le WSquashFS, changé de runner ou réinstallé l'intégration,
une ancienne copie peut rester séparée. Son avertissement ne prouve pas que
la nouvelle session a échoué. Vérifiez la progression et le dernier journal.

Abandonner une copie supprime ses modifications non rapatriées. Faites-le
seulement après avoir vérifié ce que vous souhaitez conserver. Une copie active
ou encore montée ne peut pas être supprimée par ce menu. Ne forcez pas son
retrait à la main pour contourner un refus : consultez le diagnostic.

HOTKEY + START

Ce raccourci peut interrompre les processus avant leur nettoyage. L'intégration
coordonne la fermeture avec Batocera lorsque le chemin normal est disponible ;
un arrêt forcé peut malgré tout laisser une récupération. Pour vérifier un jeu,
sauvegardez, quittez normalement si possible, puis contrôlez après relancement.

Ces copies ne remplacent pas une sauvegarde personnelle de vos jeux et données.

<a id="direct"></a>

## Mode direct : pour certains jeux particuliers

À ACTIVER SEULEMENT SI LE JEU EN A BESOIN

Certains jeux supportent mal les chemins de lancement redirigés ou les liens
symboliques de sauvegardes. Le mode direct est un réglage de compatibilité par
jeu, utilisé notamment dans notre essai Forza Horizon 2 / Azimuth.

Dans autorun.cmd, ajoutez UMU_DIRECT_GAME=1 à la ligne ENV= existante.
Si elle n'existe pas, créez une ligne :

ENV=UMU_DIRECT_GAME=1

S'il y a déjà des variables, conservez-les sur cette même ligne ENV= et ajoutez
la nouvelle, séparée par un espace. Ne créez pas plusieurs lignes concurrentes.
Pour revenir au fonctionnement normal, retirez uniquement UMU_DIRECT_GAME=1.
Fermez le jeu avant de modifier ce fichier.

Le mode direct conserve UMU et son environnement. Quand un SAVEDIR pris en charge
se trouve dans le dossier du jeu, il peut remplacer temporairement le lien de
sauvegarde par un vrai dossier, puis rapatrier son contenu et restaurer le lien.
Cela prend de l'espace et un peu de temps selon la taille des sauvegardes.

Une génération précédente peut être gardée dans .umu-direct-previous, dans le
dossier de sauvegardes externe. Elle est distincte des copies de préfixe.
Après une interruption, la reprise dépend des vérifications de la même source
et de l'état enregistré ; les situations incertaines sont conservées pour examen.

Le test FH2 de cette intégration a validé une course, une sauvegarde et un
relancement avec progression conservée, sans avertissement de synchronisation.
Cela ne constitue pas une validation de tous les jeux ni de tous les arrêts.

L'accès au dossier du jeu sur C: est également proposé par l'intégration pour
les formats concernés. Voir C:\game n'impose pas à lui seul le mode direct.

<a id="maintenance"></a>

## Maintenance : vérifier, réparer, nettoyer

LE BON ORDRE EN CAS DE DOUTE

1. Fermez les jeux UMU.
2. Lancez Maintenance > Diagnostic UMU complet.
3. Si le problème concerne l'intégration, utilisez Réparer / mettre à niveau
   l'intégration UMU, puis consultez le résultat.
4. Testez le jeu avant de supprimer des données.

INTÉGRITÉ ET PROTECTION

Les runners gérés possèdent une liste de contrôle de leurs fichiers importants.
Le diagnostic peut détecter une modification ou un fichier manquant. Pendant
les jeux, les runners sont protégés en lecture seule pour qu'un préfixe ne
modifie pas accidentellement leurs composants partagés.

Le préfixe du jeu reste modifiable. Une alerte d'intégrité n'indique pas à elle
seule un virus. Elle signifie que le runner ne correspond plus à l'état attendu.
La réparation de l'intégration n'est pas une restauration universelle de fichiers
altérés : un runner modifié peut être ignoré et nécessiter une réinstallation.

NETTOYAGE DES DONNÉES UMU

L'outil annonce les catégories et leur taille avant confirmation. Il peut
supprimer des données de travail, comme compatdata, les vues de préfixe et les
copies supprimables. Une nouvelle préparation peut être nécessaire au lancement.
Il conserve notamment les runners, UMU, son runtime et les données de jeu Batocera.
Le nettoyage global est bloqué tant que des copies de récupération restent à
examiner. Les caches graphiques facultatifs sont proposés à part.

NETTOYAGE DES JOURNAUX

Libère les anciens comptes rendus techniques. Exportez ceux d'un problème en
cours avant de les effacer. La Toolbox applique déjà une rotation des journaux.

PROTECTIONS RO ORPHELINES

Retire des protections en lecture seule restées sans session active. Utilisez
cette fonction lorsqu'une protection empêche une opération après un arrêt anormal.
Elle ne sert pas à désactiver durablement la protection des runners.

DÉSINSTALLATION

Les choix ont des portées différentes : Toolbox seule, UMU et ses runners,
ou ensemble complet. Lisez la liste affichée : les deux derniers choix retirent
aussi des données UMU, exports et récupérations. Ne les confondez pas avec la
simple suppression d'un runner. Sauvegardez les données utiles avant validation.

<a id="sharing"></a>

## Mises à jour, export et partage

TROIS CHOSES DIFFÉRENTES À METTRE À JOUR

La Toolbox : les menus et outils de gestion, via la fonction de mise à jour.
L'intégration : les scripts qui relient les runners à Batocera, via la réparation
ou la migration des runners gérés sains lors d'une installation.
Le runner : une nouvelle version de Proton, à installer séparément puis à choisir
pour le jeu. Actualiser la Toolbox ne choisit pas un nouveau Proton pour vos jeux.

UMU et son runtime sont aussi des composants distincts, préparés selon les besoins
de l'installation. Une première préparation peut nécessiter des téléchargements.
Installez les mises à jour avec les jeux fermés : un wrapper déjà lancé n'est
pas remplacé au milieu d'une session.

EXPORTER UN RUNNER SEUL

Archive destinée à une sauvegarde ou un autre Batocera déjà préparé pour UMU.
Elle ne contient pas tout l'environnement nécessaire à une machine vierge.

CRÉER UN PACKAGE AUTONOME / PARTAGEABLE

Inclut le runner, UMU, le runtime requis, un installateur et les contrôles prévus
pour préparer un autre Batocera, y compris hors ligne. La création peut être
longue : le téléchargement et la compression demandent du temps et de l'espace.

Le destinataire extrait le package puis lance son installateur sur Batocera.
Il sélectionne ensuite le runner pour son jeu dans EmulationStation.

Aucun des deux exports n'inclut vos jeux ni leurs sauvegardes. Un export de
runner n'est pas une sauvegarde complète de votre configuration Batocera.
Les fichiers du runner sont contrôlés avant un export géré.

<a id="help"></a>

## Dépannage : les bons réflexes et les journaux

LE JEU NE DÉMARRE PAS

Vérifiez qu'il utilise bien le runner -UMU voulu. Lancez le diagnostic, puis
comparez avec un runner déjà connu pour fonctionner. Notez le format du jeu,
la version Batocera et le runner exact. Une nouvelle version de jeu peut aussi
être à l'origine du changement de comportement.

LE PREMIER LANCEMENT EST LONG

Une préparation du runtime, du préfixe ou des shaders peut prendre du temps.
Consultez le journal pour voir si l'opération avance. N'effacez pas les caches
à chaque essai : cela peut justement provoquer de nouvelles compilations.

LES DONNÉES NE SONT PAS SYNCHRONISÉES

Gardez la copie de récupération. Vérifiez le journal du dernier lancement du
jeu avant de supprimer quoi que ce soit. En mode direct, le retour des sauvegardes
et le retour du préfixe sont deux opérations : l'une peut réussir et l'autre
échouer. Vérifiez votre progression après relancement si le jeu peut être repris.

QUELS FICHIERS FOURNIR POUR OBTENIR DE L'AIDE ?

- Le nom du jeu, son format et les étapes pour reproduire le problème.
- La version Batocera, celle de la Toolbox et le nom complet du runner.
- Le dernier journal du jeu et le journal Toolbox concerné.
- Pour un problème de fermeture : wineserver-stop.log, s'il existe.

Journaux des jeux : /userdata/system/logs/umu-runner/
Journaux Toolbox : /userdata/system/logs/umu-toolbox/
Le journal d'une partie s'appelle runner-AAAAMMJJ-HHMMSS-PID.log.
runner-guard.log sert à la protection : ce n'est pas le journal de votre partie.

Depuis un PC Windows, ouvrez le partage réseau Batocera puis system/logs.
Lisez les fichiers avant de les partager : ils peuvent contenir vos chemins
et des informations sur votre installation.

LES REPÈRES UTILES

Toolbox : /userdata/system/umu/toolbox
Runners : /userdata/system/wine/custom
Exports : /userdata/system/umu/exports
Copies de travail : /userdata/system/umu/materialized-prefixes
Sauvegardes Windows externalisées : /userdata/saves/windows
L'emplacement réel des sauvegardes dépend de la configuration de chaque jeu.

Projet et signalements : https://github.com/Thomson67/umu-runner-toolbox
Cet outil communautaire s'appuie sur Batocera, UMU et les projets de runners.
