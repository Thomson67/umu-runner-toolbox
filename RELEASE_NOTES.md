## Français

**UMU Runner Toolbox v0.13.20 · intégration 3.10.20**

- À la fermeture d’un jeu, la synchronisation du préfixe Wine réutilise les fichiers dont le contenu et les métadonnées sont identiques. Cela évite de recopier des dépendances comme .NET et le cache d’installation Windows dans les couches privées des bottles.
- Les fichiers ajoutés ou modifiés restent synchronisés. Le journal UMU indique le nombre de fichiers et le volume de données dont la recopie a été évitée.

## English

**UMU Runner Toolbox v0.13.20 · integration 3.10.20**

- When a game exits, Wine prefix synchronization reuses files with identical contents and metadata. This avoids copying dependencies such as .NET and the Windows installer cache into private bottle layers.
- Added and modified files are still synchronized. The UMU log reports how many files and bytes were skipped.
