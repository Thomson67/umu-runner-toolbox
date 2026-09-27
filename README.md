# UMU Runner Toolbox for Batocera

[Documentation française](docs/README_FR.md)\n\n**UMU Runner Toolbox** is a community tool for installing, managing, validating, updating and sharing **GE-Proton + UMU** runners on Batocera.

Current stable version: **v0.7.0**  
Runner integration version: **v3.7.5**

It is designed to make UMU-based Proton runners easy to use from Batocera while keeping the existing Batocera Wine environment isolated. Standard Batocera runners, Wine-TKG and Kron4ek runners are not modified.

## Features

- Install and safely remove GE-Proton-UMU runners.
- Install and update `umu-run` with SHA-512 verification.
- Download GE-Proton releases and verify upstream SHA-512 checksums before installation.
- Validate managed runners with integrity manifests.
- Automatically protect all `*-UMU` runners as read-only while an UMU game is running.
- Export a runner or build a self-contained package for sharing.
- Run UMU diagnostics and safely clean temporary UMU test data.
- Automatically resolve `GAMEID` and `STORE` from the Batocera Windows gamelist for ProtonFixes.
- Update the Toolbox directly from GitHub Releases with SHA-256 verification and automatic backup.
- Native Batocera Pad2Key support, so the Toolbox can be controlled directly from Ports.
- Support `PROTON_SONY_HIDRAW_XINPUT=1` when HIDRAW is enabled and supported by the runner winebus.
- Batocera 41 compatibility workarounds for the missing Python `_lzma` module and the `ldconfig` cache required by Steam Runtime / pressure-vessel.

> **Note:** GE-Proton10-30 through GE-Proton10-34 are intentionally blocked. These versions were found to be incompatible with this Batocera + UMU integration and can fail to launch with exit code 245. GE-Proton10-29 and 11.x are not affected by this specific block.

## How GAMEID and STORE work

UMU can expose game-specific information to ProtonFixes through the `GAMEID` and `STORE` environment variables. The Toolbox integration resolves these values automatically for Batocera Windows games.

The resolver:

1. Finds the launched game in `/userdata/roms/windows/gamelist.xml`.
2. Uses the Batocera game title to search the bundled UMU database.
3. Resolves the corresponding UMU game ID and store.
4. When a title exists for several stores, checks the available ProtonFixes gamefixes to select the appropriate store when possible.
5. Falls back to `GAMEID=umu-default` when no reliable match is found.

This allows ProtonFixes to load game-specific fixes when available without requiring users to manually maintain `GAMEID` or `STORE` values.

Both `.wine` and `.wsquashfs` containers are recognized as equivalent representations of the same Batocera game when resolving the gamelist entry.

## Runner integrity and protection

Managed GE-Proton-UMU runners receive an integrity manifest when they are prepared by the Toolbox.

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

## Installing a GE-Proton-UMU runner

Open **UMU Runner Toolbox** from Batocera Ports and choose the GE-Proton-UMU installation option.

The Toolbox downloads the selected GE-Proton release, verifies its upstream checksum, adds the Batocera/UMU integration and creates the integrity manifest.

The resulting runner can then be selected from the advanced options of a Windows game in EmulationStation.

## Updating

The Toolbox can update itself from GitHub Releases. The update package and SHA-256 checksum are downloaded and verified before replacement. The current Toolbox is backed up first, and the local `config/` directory is preserved.

`umu-run` can also be updated independently from the Toolbox, with SHA-512 verification when the upstream checksum is available.

Runner integration upgrades are applied only to managed runners that pass the required integrity checks.

## Compatibility

The project supports Batocera Windows game formats including:

- `.pc`
- `.wine`
- `.wsquashfs`
- Wine bottles

Batocera 41 requires additional compatibility handling for Steam Runtime / pressure-vessel. The Toolbox provides the required workaround while preserving the native UMU path on Batocera versions that already provide the necessary host components.

The v0.6.5 compatibility base was successfully tested on Batocera 41 with:

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

Temporary UMU test data can also be cleaned from the Toolbox when no UMU launch is active. Optional Mesa/RADV graphics caches are handled separately. This cleanup does not remove `umu-run`, Steam Runtime UMU, ProtonFixes, runners, Batocera game data or UMU saves.

## Exporting and sharing runners

The Toolbox supports two export modes:

**Self-contained/shareable package**  
Recommended when the destination Batocera system does not yet have the UMU infrastructure. The package contains the runner, its integrity information, an installer and checksum controls.

**Runner-only archive**  
Useful for backup or transfer to a Batocera installation that is already prepared for UMU.

Modified runners that fail integrity verification are not trusted for normal managed export.

## Uninstallation

To remove the Toolbox itself, run the provided `uninstall.sh` script as `root`.

The uninstaller removes the Toolbox directory, its Ports launcher and a legacy pre-v0.5.2b Toolbox directory if it still exists. It intentionally keeps installed GE-Proton-UMU runners, UMU, games, Wine bottles and saves.

## Documentation

The detailed installation and sharing guide is available in [docs/GUIDE_PARTAGE_ET_INSTALLATION.txt](docs/GUIDE_PARTAGE_ET_INSTALLATION.txt).

## Credits

UMU Runner Toolbox is a community project built to integrate the UMU ecosystem and GE-Proton runners with Batocera.

It relies on and is intended to work alongside the upstream projects that make this possible, including **UMU Launcher**, **GE-Proton**, **ProtonFixes**, **Steam Runtime** and **Batocera**. All trademarks and project names belong to their respective owners.

## License

This project is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE).
