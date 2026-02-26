# MacPurge CLI

A lightweight macOS maintenance CLI tool that replaces subscription-based cleaning apps. Zero dependencies, dry-run by default.

## Features

| Module | Description |
|--------|-------------|
| **Clean Logs** | `~/Library/Logs`, `/private/var/log` |
| **Clean Caches** | `~/Library/Caches`, `/Library/Caches` |
| **Flush DNS** | Resets macOS DNS resolver cache |
| **Purge RAM** | Clears inactive memory |
| **Maintenance Scripts** | Runs `periodic daily weekly monthly` |
| **Find Large Files** | Lists top 10 files >500 MB in home directory |
| **Clean Xcode** | Removes `DerivedData` |

## Requirements

- macOS (Darwin)
- Python 3.10+
- No external dependencies

## Installation

```bash
git clone https://github.com/yourusername/MacPurge.git
cd MacPurge
chmod +x macpurge.py
```

## Usage

### Interactive Menu

```bash
python3 macpurge.py
```

### CLI Flags

```bash
# Dry-run (default) — shows what would be deleted
python3 macpurge.py --clean-logs
python3 macpurge.py --clean-cache
python3 macpurge.py --all

# Execute deletions (requires confirmation)
python3 macpurge.py --clean-logs -y
python3 macpurge.py --all -y

# Find large files with custom threshold
python3 macpurge.py --find-large 200
```

### All Options

```
--clean-logs       Clean log files
--clean-cache      Clean cache files
--flush-dns        Flush DNS cache
--purge-mem        Purge inactive RAM
--run-scripts      Run periodic maintenance scripts
--find-large [MB]  Find large files (default >500 MB)
--clean-xcode      Clean Xcode DerivedData
--all              Run all cleanup modules
-y, --yes          Skip confirmation prompts
--dry-run          Show what would be deleted without deleting
```

## Safety

MacPurge is designed with safety as a priority:

- **Dry-run by default** — every destructive operation shows exactly what will be deleted and how much space will be reclaimed _before_ anything is removed. Files are only deleted after explicit `[Y/n]` confirmation (or the `-y` flag).
- **SIP-aware** — System Integrity Protection paths (`/System`, `/usr`, `/bin`, `/sbin`, `/Applications`) are excluded and cannot be targeted.
- **No symlink following** — all file operations use `os.lstat()` and check `is_symlink()` to avoid following symbolic links to unintended locations.
- **Sudo scoping** — elevated permissions are only used for system-level directories (`/Library/Caches`, `/private/var/log`) and macOS maintenance commands. User-level cleanup never invokes `sudo`.

### Recommended Practice

- **Always dry-run first.** Run without `-y` to review what will be deleted.
- **Don't clear caches daily.** Caches help apps load faster. Only clear them when low on disk space or troubleshooting a misbehaving application.
- **Review large file results** before deleting anything manually.

## Disclaimer

**USE AT YOUR OWN RISK.**

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

This tool deletes files from your system. While it includes safety mechanisms (dry-run defaults, SIP protection, confirmation prompts), **you are solely responsible for reviewing what will be deleted before confirming any operation.** The author(s) accept no responsibility for data loss, system instability, or any other damage resulting from the use of this tool.

Always ensure you have adequate backups before running any system cleanup utility.

## License

MIT
