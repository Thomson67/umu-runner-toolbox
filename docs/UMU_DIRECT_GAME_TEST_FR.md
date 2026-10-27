# Compatibilité UMU : chemin direct

Option facultative dans autorun.cmd : `ENV=UMU_DIRECT_GAME=1`.
Si ENV existe déjà, ajouter UMU_DIRECT_GAME=1 sur cette ligne.
Le mode standard reste la valeur par défaut ; supprimer la variable pour revenir au comportement standard.

UMU Runner Toolbox 0.13.7 et Ultimate Wine Toolbox 0.5.4 ou plus sont nécessaires pour le workflow. Après installation de UMU Runner Toolbox, lancer Maintenance > Réparer / mettre à niveau l’intégration UMU afin de mettre à jour les wrappers des runners sains et leurs manifests. Ne pas remplacer directement bin/wine dans un runner protégé.

Dans Ultimate Wine Toolbox : création WSquashFS > premier essai > options par jeu > Compatibilité UMU : lancement direct, puis relancer. Le choix est conservé dans l’archive finale et peut aussi être retiré dans ce menu.

Le mode direct conserve le préfixe matérialisé, sa persistance, la protection des runners et le Steam Runtime. Pour .wine, il utilise le répertoire original. Pour .wsquashfs/.wtgz, il utilise le montage merged-prefixes existant (OverlayFS complet et inscriptible) sans monter de gameviews supplémentaire. Aucune extraction du jeu au lancement.

## Contrôles après installation

1. Azimuth .wine + GE-Proton11-7-UMU, option activée : launcher, jeu, arrêt et relancement.
2. Azimuth .wsquashfs, même runner : launcher, jeu, écritures/sauvegardes et relancement.
3. Un jeu connu sans option : lancement, sauvegardes et relancement identiques.
4. Désactiver l’option : vérifier le retour au mode standard.

Les logs doivent indiquer umu_direct_game=1, runtime_gameview_bypassed=1 et runtime_gameview_bind=0. Pour les archives, runtime_game_source doit rester sous merged-prefixes, jamais le lowerdir SquashFS seul.

Validation utilisateur obtenue sur Batocera avec GE-Proton11-7-UMU : lancement, sauvegarde et reprise de progression en .wine et .wsquashfs.

## Sauvegardes refusant les liens et points de montage

Quand UMU_DIRECT_GAME=1 est actif, le wrapper remplace temporairement le lien du SAVEDIR déclaré dans autorun.cmd par un vrai dossier contenant une copie de sa cible sous /userdata/saves/windows. Aucun montage bind n’est utilisé pour ce dossier de sauvegardes : Wine peut signaler un changement de système de fichiers comme point de réanalyse, refusé par certains jeux. Ce traitement est limité aux sauvegardes à l’intérieur du répertoire du jeu ; les dossiers réels et les sauvegardes hors du jeu ne sont pas convertis.

À la fermeture, une copie complète des sauvegardes du jeu est préparée à côté de la cible persistante, avant de remplacer celle-ci. L’état précédent est conservé temporairement sous <cible>.umu-direct-previous jusqu’à la synchronisation et la restauration du lien, puis déplacé dans <cible>/.umu-direct-previous. Une seule génération est conservée. Ce sous-dossier réservé est exclu de la copie au lancement et de la synchronisation afin de ne pas accumuler des sauvegardes imbriquées. Les suppressions de fichiers effectuées par le jeu sont ainsi répercutées. Le lien original, conservé sous <dossier>.umu-direct-link pendant la session, est restauré seulement après synchronisation réussie. Sans UMU_DIRECT_GAME=1, aucun de ces traitements ne s’exécute.

Logs attendus : direct_save_copy=1, direct_save_path=..., direct_save_source=..., puis direct_save_sync=ok et direct_save_link_restored=... à la fermeture.

En cas d’échec de la copie initiale, le lien et les sauvegardes persistantes restent inchangés et le lancement est refusé. En cas d’échec de synchronisation, le vrai dossier de sauvegardes et son lien de secours restent présents pour récupération. Depuis l’intégration 3.10.11 (test), leur association est journalisée avant toute modification. Après Hotkey + Start ou SIGKILL, une session de la même version vérifiée peut reprendre ces sauvegardes locales sans les écraser par les anciennes sauvegardes externes. Si l’archive, le runner, le mode, l’autorun ou le préfixe source a changé, ou si le journal et les chemins ne correspondent plus, la reprise des sauvegardes est refusée. Une interruption au milieu du retour transactionnel peut encore demander une récupération manuelle. Ne pas supprimer ces dossiers ou refaire le packaging avant récupération. Le mode copie nécessite de l’espace libre sur les systèmes de fichiers du jeu et des sauvegardes et ajoute un délai proportionnel à leur taille.

Validation Batocera : relancer Azimuth .wine avec SAVEDIR et vérifier jeu, sauvegarde, fermeture, restauration du lien et relancement ; vérifier ensuite le même comportement en .wsquashfs.

## Vérification du correctif 3.10.11

Tests locaux : arrêt normal avec suppression du préfixe après synchronisation, SIGKILL du groupe de processus avant retour et entre retour du préfixe et retour des sauvegardes, reprise des sauvegardes les plus récentes, refus après changement de source et conservation après échec de retour. Les opérations de copie/journalisation sont réelles ; les montages OverlayFS sont modélisés.

À confirmer sur Batocera : Forza Horizon 2/Azimuth en WSquashFS avec `SAVEDIR=drive_c/game/data/saves` et `UMU_DIRECT_GAME=1`, sortie normale puis Hotkey + Start et relancement. Vérifier la progression et `direct_save_reused_after_interruption` lorsque le wrapper a réellement été tué avant son nettoyage. Un Hotkey + Start qui laisse le wrapper synchroniser peut produire un nettoyage normal à la place. Les données que le jeu n'avait pas encore écrites au moment du kill ne peuvent pas être récupérées.

Tester séparément le retour à une autre version de l'archive : l'ancienne copie doit être conservée sous `.retained-*`, jamais réutilisée silencieusement. Si des sauvegardes directes non synchronisées sont encore présentes dans le dossier du jeu, le lancement est refusé pour examen manuel. Abandonner une copie dans Maintenance ne supprime pas ces fichiers du jeu. La sauvegarde de secours `.umu-direct-previous` reste limitée à une génération.

## Retour après retrait du montage Batocera (3.10.12)

Un essai FH2 avec intégration 3.10.11 a montré `wine_persistence_rc=3` avant copie du préfixe, alors que `direct_save_sync=ok` et `direct_save_link_restored` confirmaient le retour des sauvegardes par l'alias. Le contrôle OverlayFS du chemin original était refusé. Avec 3.10.12, le wrapper vérifie alors son propre alias (montage OverlayFS exact, inscriptible, mêmes upperdir/lowerdir) avant d'y synchroniser le préfixe. Le checkpoint lit aussi cette vue. Le journal doit indiquer `wine_persistence_overlay_alias_fallback` si le montage original a disparu, puis `wine_persistence_result=success`, `direct_save_sync=ok` et `runtime_removed`. Un alias absent, en lecture seule ou associé à d'autres couches reste refusé. La nouvelle correction reste à valider sur Batocera ; ne pas confondre une ancienne récupération séparée avec une copie nouvellement conservée par cet essai.

### Chemins contenant des espaces (3.10.13)

Le journal FH2 en 3.10.12 montrait un alias OverlayFS encore valide, mais `refused-alias-upperdir`. La commande findmnt avec `--raw` encodait les espaces en `\x20`, contrairement aux valeurs décodées enregistrées au lancement. La 3.10.13 lit OPTIONS sans `--raw`, sans troncature, puis conserve les mêmes contrôles stricts. Un test avec le vrai formateur findmnt reproduit exactement le refus avant correction. Les sauvegardes directes étaient déjà synchronisées dans cet essai ; la correction concerne le retour du préfixe et son nettoyage.

### Retour du contenu de dosdevices (3.10.14)

L'essai FH2 en 3.10.13 a validé le retour par l'alias, mais échoué ensuite avec `phase=remove-root`, code 7 et `dosdevices: Directory not empty`. Les sauvegardes directes étaient encore synchronisées. La 3.10.14 conserve les dossiers communs et synchronise récursivement leurs entrées, sans supprimer la racine dosdevices. Les entrées obsolètes sont retirées et les fichiers remplacés individuellement, sans suivre les liens externes ni modifier les hardlinks vers les runners. Le jeu reste exclu. Un test impose le refus de suppression de dosdevices, puis vérifie le retour des mappings et sauvegardes ; les tests d'arrêt brutal et de préservation des backups UWT restent appliqués. Cette nouvelle étape reste à confirmer sur le montage réel Batocera.

### Fichier temporaire voisin de la destination (3.10.15)

Le ZIP FH2 test4 confirme le retour par l'alias et la synchronisation des sauvegardes directes, mais une erreur ENOENT lors du renommage de `.umu-prefix-sync-*/entry` vers `drive_c/openxr/wineopenxr64.json`. La test5 ne déplace plus de candidat depuis la racine : chaque remplacement utilise un nom temporaire unique dans le même dossier que sa destination. Les liens externes et hardlinks de runners restent protégés. Un test simule précisément ce refus de renommage entre dossiers ; il ne remplace pas l'essai sur le vrai OverlayFS. Un éventuel nouvel échec enregistre également la présence du parent et du candidat.

### Attendre la fin du retour avant le nettoyage natif (3.10.16)

Le ZIP test5 montre un échec dès la création d'un fichier dans openxr ; le renommage n'explique donc pas à lui seul le problème. Le code natif Batocera nettoie son WORKPOINT après `waitWineServer`, alors que le wrapper hôte UMU peut encore rapatrier ses données après l'arrêt réel de Wine. La test6 ajoute une attente de fin du wrapper pour les requêtes natives -w associées exactement à leur session. Le workdir doit rester disponible jusqu'au retour du préfixe, des sauvegardes directes et à la libération des montages. Un wrapper tué libère l'attente tout en conservant les copies non synchronisées.

Le test de concurrence échoue avec l'ancien wineserver et passe avec la nouvelle attente. Il modélise le nettoyage du workdir par le parent natif, sans prétendre reproduire le noyau du build cOPu. À confirmer sur Batocera : `runtime_workdir` dans le journal de lancement, `runtime_wait_begin` puis `runtime_wait_end` dans wineserver-stop.log, retour réussi puis suppression du runtime. Si le workdir disparaît malgré l'attente, l'erreur explicite est `refused-workdir-missing`, code 14 ; conserver la copie et joindre les deux journaux.

Références de l'analyse : script natif package/batocera/wine/batocera-wine/batocera-wine (waitWineServer, play_squashfs, cleanAndExit) dans batocera-linux/batocera.linux ; documentation noyau OverlayFS, section Changes to underlying filesystems. Le nettoyage natif effectue rm -rf sur WORKPOINT ; une vue bind survivante ne protège pas ce dossier contre cette suppression.

Le relancement natif après kill est également couvert : saveFilesToUserdata peut avoir déjà copié les sauvegardes locales vers leur cible externe et restauré le lien actif avant UMU. Si le lien actif et le lien de secours `.umu-direct-link` désignent exactement le même dossier externe existant, sans `.umu-direct-local` en attente, seul le lien de secours redondant est retiré avant la préparation normale. Un vrai dossier local, une cible différente ou une transaction partielle restent protégés. Le test modèle le cp/rm/ln natif après SIGKILL puis vérifie la progression, le lien et le nettoyage après retour réussi.

## Validation utilisateur — version 0.13.14

Le correctif de fermeture de l’intégration 3.10.16 a été validé sur FH2/Azimuth : une course, une sauvegarde et un relancement ont conservé la progression, sans avertissement de synchronisation. Ce résultat valide ce scénario ; les interruptions forcées restent traitées par la récupération lorsque le retour ne peut pas être terminé. La version stable inclut aussi le guide utilisateur hors ligne dans Documentation / À propos.
