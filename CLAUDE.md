# MacPurge CLI - CLAUDE.md

## Quick Reference

| Resource     | Location                  |
|-------------|---------------------------|
| Main script | `macpurge.py`             |
| Language    | Python 3.12+              |
| Platform    | macOS only (`darwin`)      |

---

## Project Overview

MacPurge is a lightweight macOS maintenance CLI tool that replaces subscription-based cleaning apps. It provides dry-run-by-default safety, interactive menu and CLI flag modes, and handles sudo prompts gracefully.

## Architecture

Single-file Python script with no external dependencies. Modules:

| Module         | Function          | Targets                                          |
|---------------|-------------------|--------------------------------------------------|
| `clean_logs`  | Delete log files  | `~/Library/Logs`, `/private/var/log`             |
| `clean_cache` | Delete caches     | `~/Library/Caches`, `/Library/Caches`            |
| `flush_dns`   | Flush DNS cache   | `dscacheutil`, `mDNSResponder`                   |
| `purge_mem`   | Purge inactive RAM| `sudo purge`                                     |
| `find_large`  | Find large files  | Home directory, >500MB default                   |
| `clean_xcode` | Xcode cleanup     | `~/Library/Developer/Xcode/DerivedData`          |

## Key Patterns

- **Dry-run by default**: All destructive operations show size/targets first, require confirmation
- **SIP protection**: `SIP_PROTECTED` set prevents touching system-critical paths
- **Sudo handling**: System-level paths use `sudo rm -rf` via subprocess; user paths use `shutil`
- **No symlink following**: All file operations use `os.lstat()` and check `is_symlink()` first

## Commands

```bash
# Interactive menu
python3 macpurge.py

# CLI flags (dry-run by default)
python3 macpurge.py --clean-logs
python3 macpurge.py --clean-cache
python3 macpurge.py --all

# Execute deletions
python3 macpurge.py --all -y

# Find large files with custom threshold
python3 macpurge.py --find-large 200
```

## Conventions

- No external dependencies — stdlib only
- ANSI color output via escape codes
- Functions return bytes freed (int) for summary reporting
- `confirm()` helper for all user prompts with `[Y/n]` pattern
