# Test de compatibilité UMU : chemin direct

Option facultative dans autorun.cmd : `ENV=UMU_DIRECT_GAME=1`.
Si ENV existe déjà, ajouter UMU_DIRECT_GAME=1 sur cette ligne.
Le mode standard reste la valeur par défaut ; supprimer la variable pour revenir au comportement standard.

La version test des deux toolboxes est nécessaire pour le workflow. Après installation de UMU Runner Toolbox, lancer Maintenance > Réparer / mettre à niveau l’intégration UMU afin de mettre à jour les wrappers des runners sains et leurs manifests. Ne pas remplacer directement bin/wine dans un runner protégé.

Dans Ultimate Wine Toolbox : création WSquashFS > premier essai > options par jeu > Compatibilité UMU : lancement direct (expérimental), puis relancer. Le choix est conservé dans l’archive finale et peut aussi être retiré dans ce menu.

Le mode direct conserve le préfixe matérialisé, sa persistance, la protection des runners et le Steam Runtime. Pour .wine, il utilise le répertoire original. Pour .wsquashfs/.wtgz, il utilise le montage merged-prefixes existant (OverlayFS complet et inscriptible) sans monter de gameviews supplémentaire. Aucune extraction du jeu au lancement.

## Validation Batocera encore nécessaire

1. Azimuth .wine + GE-Proton11-7-UMU, option activée : launcher, jeu, arrêt et relancement.
2. Azimuth .wsquashfs, même runner : launcher, jeu, écritures/sauvegardes et relancement.
3. Un jeu connu sans option : lancement, sauvegardes et relancement identiques.
4. Désactiver l’option : vérifier le retour au mode standard.

Les logs doivent indiquer umu_direct_game=1, runtime_gameview_bypassed=1 et runtime_gameview_bind=0. Pour les archives, runtime_game_source doit rester sous merged-prefixes, jamais le lowerdir SquashFS seul.

Les tests statiques et simulés ne valident pas le comportement d’Azimuth dans pressure-vessel : le montage compressed doit être testé sur Batocera avant toute release.

## Sauvegardes refusant les liens symboliques

Quand UMU_DIRECT_GAME=1 est actif, le wrapper remplace temporairement le lien du SAVEDIR déclaré dans autorun.cmd par un montage bind de sa cible existante sous /userdata/saves/windows. Cette conversion est limitée aux dossiers de sauvegardes à l’intérieur du répertoire du jeu ; les dossiers réels, les sauvegardes hors du jeu et SAVEFILES ne sont pas convertis. Le lien original est conservé sous le nom <dossier>.umu-direct-link puis restauré après démontage à la fermeture. Les données persistantes ne sont ni déplacées ni copiées. Sans UMU_DIRECT_GAME=1, ce traitement ne s’exécute pas.

Logs attendus : direct_save_bind=1, direct_save_path=..., direct_save_source=..., puis direct_save_link_restored=... à la fermeture. Un échec de montage refuse le lancement et restaure le lien. Si le démontage reste occupé, le montage et le lien de secours sont conservés : ne pas supprimer leurs données ; examiner le journal avant de relancer. Un arrêt forcé (SIGKILL, coupure) peut nécessiter une récupération manuelle.

Validation Batocera : relancer Azimuth .wine avec SAVEDIR et vérifier jeu, sauvegarde, fermeture, restauration du lien et relancement ; valider ensuite le même comportement en .wsquashfs avant toute release.
