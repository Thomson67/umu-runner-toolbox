# UMU Runner Toolbox for Batocera

[Documentation française](docs/README_FR.md)

**UMU Runner Toolbox** is a community tool for installing, managing, validating, updating and sharing **GE-Proton / GDK-Proton / CachyOS Proton / Proton-EM + UMU** runners on Batocera.

Current stable version: **v0.11.0**  
Runner integration version: **v3.9.3**

It is designed to make UMU-based Proton runners easy to use from Batocera while keeping the existing Batocera Wine environment isolated. Standard Batocera runners, Wine-TKG and Kron4ek runners are not modified.

## Features

- Install and safely remove GE-Proton-UMU, GDK-Proton-UMU, CachyOS Proton UMU and Proton-EM-UMU runners.
- Install and update `umu-run` with SHA-512 verification.
- Download GE-Proton releases and verify upstream checksums before installation.
- Download GDK-Proton releases and verify GitHub SHA-256 digests when available, including support for the historical GDK-Proton10-25 archive naming.
- Install supported CachyOS Proton Steam Linux Runtime (SLR) releases through the same managed UMU workflow.
- Install official Proton-EM releases from BananaWorks07/Proton with mandatory upstream SHA-256 verification. Releases without an upstream checksum remain visible but are explicitly marked non-installable.
- Validate managed runners with integrity manifests.
- Automatically protect all `*-UMU` runners as read-only while an UMU game is running.
- Export a runner or build a self-contained package for sharing.
- Run UMU diagnostics and safely clean UMU runtime data, including materialized prefixes and game views.
- Automatically resolve `GAMEID` and `STORE` from the Batocera Windows gamelist for ProtonFixes. 
- Game Compatibility menu with assisted matching, global ambiguity scan and persistent manual associations.
- Update the Toolbox directly from GitHub Releases with SHA-256 verification and automatic backup.
- Native Batocera Pad2Key support, so the Toolbox can be controlled directly from Ports.
- Support `PROTON_SONY_HIDRAW_XINPUT=1` when HIDRAW is enabled and supported by the runner winebus.
- Batocera 41 compatibility workarounds for the missing Python `_lzma` module and the `ldconfig` cache required by Steam Runtime / pressure-vessel.

> **v0.11.0:** adds managed Proton-EM support while retaining the validated integration v3.9.3. CachyOS Proton SLR support introduced in v0.10.0 remains available. The validated integration supports Batocera `.pc`, `.wine` and `.wsquashfs` launches, GAMEID/STORE resolution with ProtonFixes, runner integrity protection and Batocera stop/hotkey handling for materialized sessions.

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

## Automatic Steam ProtonFix fallback

When a title is absent from the UMU database, the resolver can inspect the locally installed `gamefixes-steam/*.py` ProtonFixes. It reads only the module docstring, never executes the fix during detection, and accepts an automatic Steam AppID only when exactly one ProtonFix title matches the normalized Batocera title. Ambiguous or missing matches remain on the safe fallback. Successful detections are logged as `AUTO_STEAM_MATCH`.

## Manual GAMEID / STORE overrides

The main menu now includes **Game Compatibility**. It can scan the Windows gamelist for ambiguous matches, propose ranked candidates from the bundled UMU database and installed Steam ProtonFixes, then offer the stores linked to the selected candidate. Manual associations take priority over automatic detection and can be removed at any time to return to automatic resolution. They are stored in `config/gameid-overrides.csv` and preserved across Toolbox updates.

The compatibility UI considers `.wsquashfs`, `.wine`, `.pc` and `.wtgz` game entries. Raw `.exe` entries are ignored to avoid indexing technical Wine executables. Global scans count unmatched games in the summary but only present ambiguous matches for review; after saving an association, the same scan result remains open so several ambiguous games can be processed in sequence.

The maintenance menu can also clean UMU Runner and Toolbox logs while preserving the current Toolbox session log.

## Runner integrity and protection

Managed GE-Proton-UMU, GDK-Proton-UMU, CachyOS Proton UMU and Proton-EM-UMU runners receive an integrity manifest when they are prepared by the Toolbox.

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

Open **UMU Runner Toolbox** from Batocera Ports and choose the supported GE-Proton, GDK-Proton, CachyOS Proton or Proton-EM installation option.

The Toolbox downloads the selected Proton release, verifies the available upstream checksum/digest, adds the Batocera/UMU integration and creates the integrity manifest.

The resulting runner can then be selected from the advanced options of a Windows game in EmulationStation.

## Updating

The Toolbox can update itself from GitHub Releases. The update package and SHA-256 checksum are downloaded and verified before replacement. The current Toolbox is backed up first, and the local `config/` directory is preserved.

`umu-run` can also be updated independently from the Toolbox, with SHA-512 verification when the upstream checksum is available.

Runner integration upgrades are applied only to managed runners that pass the required integrity checks.

Installing or updating Toolbox v0.11.0 also migrates the integration of existing healthy managed runners to v3.9.3. Modified runners that fail their integrity manifest are left untouched. If a live UMU/Wine process is detected, migration is safely deferred; Maintenance can also identify and remove orphaned read-only runner protections left after a forced termination.

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

UMU Runner Toolbox is a community project built to integrate the UMU ecosystem and GE-Proton, GDK-Proton and CachyOS Proton runners with Batocera.

It relies on and is intended to work alongside the upstream projects that make this possible, including **UMU Launcher**, **GE-Proton**, **GDK-Proton**, **CachyOS Proton**, **Proton-EM**, **ProtonFixes**, **Steam Runtime** and **Batocera**. All trademarks and project names belong to their respective owners.

## License

This project is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE).
