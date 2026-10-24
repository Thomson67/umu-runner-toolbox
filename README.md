# UMU Runner Toolbox for Batocera

[Documentation française](docs/README_FR.md)

**UMU Runner Toolbox** is a community tool for installing, managing, validating, updating and sharing **GE-Proton / GDK-Proton / CachyOS Proton / Proton-EM / DW-Proton + UMU** runners on Batocera.

Current stable version: **v0.13.13**
Runner integration version: **v3.10.10**

It is designed to make UMU-based Proton runners easy to use from Batocera while keeping the existing Batocera Wine environment isolated. Standard Batocera runners, Wine-TKG and Kron4ek runners are not modified.

## Sony controllers: recommended GE-Proton version

For DualShock 4 and DualSense, **GE-Proton 11-8 or newer is recommended**. Starting with GE-Proton 11-8, native automatic PlayStation-to-XInput fallback is normally available without setting `PROTON_SONY_HIDRAW_XINPUT=1` manually. UMU Runner Toolbox does not force these compatibility variables, preserving the runner default and existing per-game `autorun.cmd` overrides. Older runners are still usable, but may require game-specific configuration. The recommendation appears under Settings > Sony controllers and in the GE-Proton installation picker.

## Features

- Install and safely remove GE-Proton-UMU, GDK-Proton-UMU, CachyOS Proton UMU, Proton-EM-UMU and DW-Proton-UMU runners.
- Install and update `umu-run` with SHA-512 verification.
- Download GE-Proton releases and verify upstream checksums before installation.
- Download GDK-Proton releases and verify GitHub SHA-256 digests when available, including support for the historical GDK-Proton10-25 archive naming.
- Install supported CachyOS Proton Steam Linux Runtime (SLR) releases through the same managed UMU workflow.
- Install official Proton-EM releases from BananaWorks07/Proton with mandatory upstream SHA-256 verification. Releases without an upstream checksum remain visible but are explicitly marked non-installable.
- Install DW-Proton x86_64 releases from dawn-winery/dwproton-mirror with mandatory upstream SHA-512 verification.
- Validate managed runners with integrity manifests.
- Automatically protect all `*-UMU` runners as read-only while an UMU game is running.
- Export a runner or build a self-contained package for sharing.
- Run UMU diagnostics and safely clean UMU runtime data, including materialized prefixes and game views.
- Automatically resolve `GAMEID` and `STORE` from the Batocera Windows gamelist for ProtonFixes. 
- Game Compatibility menu with assisted matching, global ambiguity scan and persistent manual associations.
- Update the Toolbox directly from GitHub Releases with SHA-256 verification and automatic backup.
- Native Batocera Pad2Key support, so the Toolbox can be controlled directly from Ports.
- Preserve native Sony HIDRAW input, PlayStation detection and supported DualSense features; respect explicit compatibility options and Proton game presets.
- Batocera 41 compatibility workarounds for the missing Python `_lzma` module and the `ldconfig` cache required by Steam Runtime / pressure-vessel.

> **v0.13.2:** adds short explanations throughout the menus and introduces runner families for beginners. GAMEID scans load their sources once, and assisted matching prioritizes the main title over edition labels and distinguishes sequel numbers. A user-reported test on 1,265 games took about 50 seconds, down from over two minutes; timings depend on hardware and the available candidate sources.

## How GAMEID and STORE work

UMU can expose game-specific information to ProtonFixes through the `GAMEID` and `STORE` environment variables. The Toolbox integration resolves these values automatically for Batocera Windows games.

The resolver:

1. Finds the launched game in `/userdata/roms/windows/gamelist.xml`.
2. Uses the Batocera game title to search the bundled UMU database.
3. Resolves the corresponding UMU game ID and store.
4. When a title exists for several stores, checks the available ProtonFixes gamefixes to select the appropriate store when possible.
5. Falls back to `GAMEID=umu-default` when no reliable match is found.

This allows ProtonFixes to load game-specific fixes when available without requiring users to manually maintain `GAMEID` or `STORE` values.

`.pc`, `.wine` and `.wsquashfs` containers are supported by the resolver when matching Batocera games and applying GAMEID/STORE information.

For `.wsquashfs` games, integration v3.9.3 keeps the game payload on Batocera's merged OverlayFS view but materializes the Proton/Wine PFX on a real filesystem under `/userdata/system/umu/materialized-prefixes`. The external game view is exposed under `/userdata/system/umu/gameviews`. Compressed-game compatdata identities are runner-specific to prevent unwanted cross-migrations between managed runners.

Integration 3.10.9 excludes the old game directory retained by an active Ultimate Wine Toolbox update from `.wine` prefix materialization. It verifies the active UWT state and update journal against the exact prefix and backup path, then preserves that backup during return persistence as well. Unrelated `.bak` directories and launches without a matching update journal keep their existing behavior. Install integration updates only after the current UMU session has ended; it does not change a running wrapper.

Integration **3.10.10** also repairs stale links to a removed runner using the explicitly selected runner. Wine PE modules, including DLLs, executables, drivers and themes, require the same filename and matching PE architecture. Replacements become private prefix files; runners remain protected. Missing font links under Windows/Fonts are replaced from the selected runner when available, or removed when already dangling so Wine can use its font fallbacks. Other unresolved entries are all reported before changing prefix files. The pre-launch guard uses Batocera's per-game runner selection as well.

Integration **3.10.9** automatically removes materialized prefixes after prefix changes are successfully synchronized and runtime mounts are released. `.wine` changes return to the original prefix; compressed-game changes return to Batocera's writable merged bottle, leaving the archive and external game directory untouched. Saves handled by direct mode must also synchronize successfully before removal. The copy preflight excludes the game and validated UWT backup, checks available space and reserves 256 MiB.

Sessions share a runtime lock with manual cleanup. A journal tracks the process identity (including boot and start time), preparation and synchronization. Interrupted preparation copies can be reclaimed automatically at the next launch. Unsynchronized game sessions remain available for recovery. At the next launch, a complete owned copy with the same source, runner identity and game directory is reused without another copy, including after Hotkey + Start. If the identity cannot be verified, reuse and overwrite are refused. Old copies without a journal are retained once under `.legacy-*` on first reuse; they require review rather than automatic deletion. The Toolbox offers **Maintenance > Retained UMU copies**, with game, occupied space, last recorded state, runner and launch log when available. It explains how to resume a verified copy through the same game in EmulationStation, or allows discarding one copy after confirmation. Unknown journals require manual review. Bulk runtime cleanup refuses to proceed while recovery copies remain. A changed copy invalidates an earlier discard selection. New synchronization failures retain their cause in the journal and request an ES notification; abrupt interruptions are reported when the Toolbox next opens. Automatic cleanup only removes owned, disposable copies and refuses active mounts, including mounts in surviving containers. Compatdata, shader caches, runners and persistent saves are not automatically purged.

## Automatic Steam ProtonFix fallback

When a title is absent from the UMU database, the resolver can inspect the locally installed `gamefixes-steam/*.py` ProtonFixes. It reads only the module docstring, never executes the fix during detection, and accepts an automatic Steam AppID only when exactly one ProtonFix title matches the normalized Batocera title. Ambiguous or missing matches remain on the safe fallback. Successful detections are logged as `AUTO_STEAM_MATCH`.

## Manual GAMEID / STORE overrides

The main menu now includes **Game Compatibility**. It can scan the Windows gamelist for ambiguous matches, propose ranked candidates from the bundled UMU database and installed Steam ProtonFixes, then offer the stores linked to the selected candidate. Manual associations take priority over automatic detection and can be removed at any time to return to automatic resolution. They are stored in `config/gameid-overrides.csv` and preserved across Toolbox updates.

The compatibility UI considers `.wsquashfs`, `.wine`, `.pc` and `.wtgz` game entries. Raw `.exe` entries are ignored to avoid indexing technical Wine executables. Global scans count unmatched games in the summary but only present ambiguous matches for review; after saving an association, the same scan result remains open so several ambiguous games can be processed in sequence.

The scan reads game entries from `gamelist.xml`; it does not recursively explore the contents of `.wine` prefixes or media directories. The candidate database and installed Steam ProtonFix titles are loaded once per scan.

Assisted matching gives priority to the main title. Labels such as “Definitive Edition”, “Deluxe” or “Remastered” help distinguish related variants but cannot make an unrelated game a probable match on their own. Different sequel numbers are penalized, and trailing Roman and Arabic sequel numbers are treated consistently. Subtitles remain part of the title. When the exact edition is unavailable, a suggestion for the base game still requires manual review.

These ranking changes concern the compatibility menu's suggestions; they do not make new automatic GAMEID assignments during a scan.

The maintenance menu can also clean UMU Runner and Toolbox logs while preserving the current Toolbox session log.

## Runner integrity and protection

Managed GE-Proton-UMU, GDK-Proton-UMU, CachyOS Proton UMU, Proton-EM-UMU and DW-Proton-UMU runners receive an integrity manifest when they are prepared by the Toolbox.

Before sensitive maintenance, migration or export operations, the Toolbox can verify that manifest. A runner whose managed files no longer match its reference manifest is treated as modified rather than silently trusted.

During an UMU game launch, all managed `*-UMU` runners are protected as read-only. The game's Wine prefix remains writable. This prevents a prefix reused with several Proton versions from accidentally altering another runner.

## Installation

Run the following command as `root` on Batocera:

```bash
curl -fsSL https://raw.githubusercontent.com/Thomson67/umu-runner-toolbox/main/install.sh | bash
```

The bootstrap installer detects the latest stable GitHub release, downloads the release package and SHA-256 checksum, verifies it, then runs the packaged installer locally.

After installation, the Toolbox is available from:

```text
Ports -> UMU Runner Toolbox
```

Toolbox files are installed under:

```text
/userdata/system/umu/toolbox
```

Exports are stored under:

```text
/userdata/system/umu/exports
```

## Local installation

Download a release archive, extract it, then run as `root`:

```bash
chmod +x install.sh
./install.sh
```

## Installing a Proton-UMU runner

Open **UMU Runner Toolbox** from Batocera Ports and choose the supported GE-Proton, GDK-Proton, CachyOS Proton, Proton-EM or DW-Proton installation option.

The Toolbox downloads the selected Proton release, verifies the available upstream checksum/digest, adds the Batocera/UMU integration and creates the integrity manifest.

The resulting runner can then be selected from the advanced options of a Windows game in EmulationStation.

## Updating

The Toolbox can update itself from GitHub Releases. The update package and SHA-256 checksum are downloaded and verified before replacement. The current Toolbox is backed up first, and the local `config/` directory is preserved.

`umu-run` can also be updated independently from the Toolbox, with SHA-512 verification when the upstream checksum is available.

Runner integration upgrades are applied only to managed runners that pass the required integrity checks.

Installing or updating Toolbox v0.12.0 also migrates the integration of existing healthy managed runners to v3.9.3. Modified runners that fail their integrity manifest are left untouched. If a live UMU/Wine process is detected, migration is safely deferred; Maintenance can also identify and remove orphaned read-only runner protections left after a forced termination.

## Compatibility

The project supports Batocera Windows game formats including:

- `.pc`
- `.wine`
- `.wsquashfs`
- Wine bottles

Batocera 41 requires additional compatibility handling for Steam Runtime / pressure-vessel. The Toolbox provides the required workaround while preserving the native UMU path on Batocera versions that already provide the necessary host components.

Earlier compatibility work was successfully tested on Batocera 41 with:

- `GE-Proton10-25-UMU`
- `GE-Proton11-5-UMU`

Compatibility can still vary depending on the game, Proton version, GPU driver and Batocera version.

### DualShock / DualSense

Some games using Sony controllers may require HIDRAW. If a DualShock or DualSense controller is not detected correctly, enable HIDRAW in the game's advanced settings and try again. Do not enable it systematically when the game already works correctly.

The integration no longer forces `PROTON_SONY_HIDRAW_XINPUT=1` when HIDRAW is enabled. Leave this option unset for native Sony support. Use `ENV=PROTON_SONY_HIDRAW_XINPUT=1` in the game autorun only when XInput compatibility is needed, or `0` for an explicit native-mode test. Proton may still apply its own per-game presets.

## Diagnostics and logs

The **Maintenance and diagnostics** menu provides runner integrity checks, protection status, integration repair/upgrade tools and a complete UMU diagnostic.

Logs are stored in:

```text
Runner wrapper: /userdata/system/logs/umu-runner/
Toolbox:        /userdata/system/logs/umu-toolbox/
```

UMU runtime data can also be cleaned from the Toolbox when no UMU launch is active. Optional Mesa/RADV graphics caches are handled separately. This cleanup does not remove `umu-run`, Steam Runtime UMU, ProtonFixes, runners, Batocera game data or UMU saves.

## Exporting and sharing runners

The Toolbox supports two export modes:

**Self-contained/shareable package**  
Recommended when the destination Batocera system does not yet have the UMU infrastructure. The package contains the runner, its integrity information, an installer and checksum controls.

**Runner-only archive**  
Useful for backup or transfer to a Batocera installation that is already prepared for UMU.

Modified runners that fail integrity verification are not trusted for normal managed export.

## Uninstallation

To remove the Toolbox itself, run the provided `uninstall.sh` script as `root`.

The uninstaller removes the Toolbox directory, its Ports launcher and a legacy pre-v0.5.2b Toolbox directory if it still exists. It intentionally keeps installed managed Proton-UMU runners, UMU, games, Wine bottles and saves.

## Documentation

The detailed installation and sharing guide is available in [docs/GUIDE_PARTAGE_ET_INSTALLATION.txt](docs/GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Credits

UMU Runner Toolbox is a community project built to integrate the UMU ecosystem and GE-Proton, GDK-Proton, CachyOS Proton, Proton-EM and DW-Proton runners with Batocera.

It relies on and is intended to work alongside the upstream projects that make this possible, including **UMU Launcher**, **GE-Proton**, **GDK-Proton**, **CachyOS Proton**, **Proton-EM**, **DW-Proton**, **ProtonFixes**, **Steam Runtime** and **Batocera**. All trademarks and project names belong to their respective owners.

## License

This project is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE).


## Per-game compatibility: direct mode

Add `UMU_DIRECT_GAME=1` to the single `ENV=` line in `autorun.cmd` for games rejecting redirected paths or save symlinks. Other games retain their launch mode. Integration 3.10.5 preserves Steam Runtime and runner protection. `SAVEDIR` saves inside the game directory are copied into a real directory at launch, synchronized on exit, then the Batocera link is restored. One recovery snapshot is retained inside the game's save directory as `.umu-direct-previous` and excluded from subsequent copies. Close the game normally; forced termination may require recovery. Copies need free space and time proportional to save size.

### Stable game paths on C:

Integration 3.10.7 exposes the original top-level game directory inside Proton's active `pfx/drive_c` with a temporary directory bind. A source `drive_c/game` is thus available as `C:\game`, including files selected by launchers, without copying game data into the materialized prefix. A different original folder name is preserved. This applies to split `.wine` and merged `.wsquashfs` launches; `.pc` and standalone prefix layouts are unchanged.

Normal launches also use this view for the executable and working directory. `UMU_DIRECT_GAME=1` keeps its existing launch paths and gains the C: view as an additional access path. Original game files and save redirects remain the source of data. The temporary view is unmounted before `.wine` prefix persistence and before the parent pfx mount; game contents are excluded from prefix copying.

For comparison, `UMU_C_GAME_PATH=0` in the game's `ENV=` line restores the previous path behavior. Existing application settings containing `S:\...` are not rewritten: select the C: path once in the application. The runner log records `runtime_c_game_*`. Runtime validation on Batocera is required for this test version.

### Graphics cache visibility

Configured, existing VKD3D, DXVK, Mesa and NVIDIA cache directories are shared read/write with Steam Runtime. This preserves Batocera cache locations and avoids repeated compilation when an inherited cache path was invisible inside UMU. Cache sharing decisions are recorded in the runner log.

With integration 3.10.6, **Settings → Graphics cache sharing** enables or disables this automatic sharing for performance comparisons. It defaults to enabled and takes effect on the next launch. A game can override the global setting with `UMU_GRAPHICS_CACHE_SHARING=0` (off) or `1` (on) in its autorun `ENV=` line. The runner log records `graphics_cache_sharing=0` or `1`.

Disabling restores the mount behavior before the visibility fix; it does not delete caches or disable every Proton/Mesa cache. Existing user-provided mounts and default runtime shares remain available. Recompilation may return when Batocera's configured cache is no longer visible, so distinguish the first launch from subsequent launches when comparing performance.
