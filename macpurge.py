#!/usr/bin/env python3
"""MacPurge CLI — lightweight macOS maintenance tool."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ANSI colors
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"

HOME = Path.home()

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def fmt_size(nbytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def dir_size(path: Path) -> int:
    """Total size of all files under *path* (follows no symlinks)."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if not entry.is_symlink() and entry.is_file():
                try:
                    total += os.lstat(entry).st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
    return total


def confirm(prompt: str) -> bool:
    """Ask for Y/n confirmation."""
    try:
        answer = input(f"{YELLOW}{prompt} [Y/n]{RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes")


def delete_contents(path: Path, use_sudo: bool = False) -> int:
    """Delete contents of a directory, return bytes freed.

    If *use_sudo* is True, removal is done via ``sudo rm -rf``.
    """
    if not path.exists():
        return 0
    freed = 0
    try:
        for child in list(path.iterdir()):
            try:
                size = os.lstat(child).st_size if (not child.is_symlink() and child.is_file()) else dir_size(child)
            except (PermissionError, OSError):
                size = 0

            try:
                if use_sudo:
                    subprocess.run(
                        ["sudo", "rm", "-rf", str(child)],
                        check=True,
                        capture_output=True,
                    )
                    freed += size
                else:
                    if not child.is_symlink() and child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
                    freed += size
            except (PermissionError, OSError) as exc:
                print(f"  {DIM}skip: {child.name} ({exc}){RESET}")
    except PermissionError:
        print(f"  {DIM}cannot list {path}{RESET}")
    return freed


# ---------------------------------------------------------------------------
# SIP-protected paths to never touch
# ---------------------------------------------------------------------------

SIP_PROTECTED = {
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/Applications",
}


def is_sip_protected(path: Path) -> bool:
    resolved = str(path.resolve())
    return any(resolved == p or resolved.startswith(p + "/") for p in SIP_PROTECTED)


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

def clean_logs(dry_run: bool = True) -> int:
    """Delete files in ~/Library/Logs and /private/var/log."""
    print(f"\n{BOLD}{'[DRY RUN] ' if dry_run else ''}Clean Logs{RESET}")
    targets = [
        (HOME / "Library" / "Logs", False),
        (Path("/private/var/log"), True),
    ]
    total = 0
    for path, needs_sudo in targets:
        if is_sip_protected(path):
            print(f"  {RED}skip SIP-protected: {path}{RESET}")
            continue
        size = dir_size(path)
        total += size
        print(f"  {path}: {GREEN}{fmt_size(size)}{RESET}")

    if dry_run:
        print(f"  Total reclaimable: {CYAN}{fmt_size(total)}{RESET}")
        return total

    if total == 0:
        print(f"  {DIM}Nothing to clean.{RESET}")
        return 0

    if not confirm("Delete these log files?"):
        print("  Skipped.")
        return 0

    freed = 0
    for path, needs_sudo in targets:
        if is_sip_protected(path):
            continue
        freed += delete_contents(path, use_sudo=needs_sudo)
    print(f"  Freed: {GREEN}{fmt_size(freed)}{RESET}")
    return freed


def clean_cache(dry_run: bool = True) -> int:
    """Delete files in ~/Library/Caches and /Library/Caches."""
    print(f"\n{BOLD}{'[DRY RUN] ' if dry_run else ''}Clean Caches{RESET}")
    targets = [
        (HOME / "Library" / "Caches", False),
        (Path("/Library/Caches"), True),
    ]
    total = 0
    for path, needs_sudo in targets:
        if is_sip_protected(path):
            print(f"  {RED}skip SIP-protected: {path}{RESET}")
            continue
        size = dir_size(path)
        total += size
        print(f"  {path}: {GREEN}{fmt_size(size)}{RESET}")

    if dry_run:
        print(f"  Total reclaimable: {CYAN}{fmt_size(total)}{RESET}")
        return total

    if total == 0:
        print(f"  {DIM}Nothing to clean.{RESET}")
        return 0

    if not confirm("Delete these cache files?"):
        print("  Skipped.")
        return 0

    freed = 0
    for path, needs_sudo in targets:
        if is_sip_protected(path):
            continue
        freed += delete_contents(path, use_sudo=needs_sudo)
    print(f"  Freed: {GREEN}{fmt_size(freed)}{RESET}")
    return freed


def flush_dns() -> None:
    """Flush the macOS DNS cache."""
    print(f"\n{BOLD}Flush DNS Cache{RESET}")
    try:
        subprocess.run(
            ["sudo", "dscacheutil", "-flushcache"],
            check=True,
        )
        subprocess.run(
            ["sudo", "killall", "-HUP", "mDNSResponder"],
            check=True,
        )
        print(f"  {GREEN}DNS cache flushed.{RESET}")
    except subprocess.CalledProcessError as exc:
        print(f"  {RED}Failed: {exc}{RESET}")


def purge_mem() -> None:
    """Purge inactive RAM."""
    print(f"\n{BOLD}Purge Inactive Memory{RESET}")
    try:
        subprocess.run(["sudo", "purge"], check=True)
        print(f"  {GREEN}Inactive memory purged.{RESET}")
    except subprocess.CalledProcessError as exc:
        print(f"  {RED}Failed: {exc}{RESET}")


def run_scripts() -> None:
    """Run macOS periodic maintenance scripts."""
    print(f"\n{BOLD}Run Periodic Maintenance Scripts{RESET}")
    try:
        subprocess.run(
            ["sudo", "periodic", "daily", "weekly", "monthly"],
            check=True,
        )
        print(f"  {GREEN}Periodic scripts completed.{RESET}")
    except subprocess.CalledProcessError as exc:
        print(f"  {RED}Failed: {exc}{RESET}")


def find_large(min_mb: int = 500) -> None:
    """List the top 10 largest files in the home directory (>min_mb MB)."""
    print(f"\n{BOLD}Large Files (>{min_mb} MB) in {HOME}{RESET}")
    threshold = min_mb * 1024 * 1024
    large_files: list[tuple[int, Path]] = []

    # Top-level dirs to skip entirely
    skip_top = {".Trash", "Library", ".cache", "node_modules", ".git"}
    # Directory names to skip at any depth during traversal
    skip_any = {"node_modules", ".git", ".cache", "__pycache__", ".venv",
                "venv", ".tox", ".mypy_cache", ".pytest_cache", "Pods",
                ".bundle", "vendor", ".gradle", "build", "DerivedData"}

    scanned = 0
    for entry in HOME.iterdir():
        if entry.name in skip_top or entry.is_symlink():
            continue
        if entry.is_dir():
            print(f"  {DIM}Scanning ~/{entry.name} ...{RESET}", end="\r", flush=True)
            try:
                for f in entry.rglob("*"):
                    if f.is_dir() and f.name in skip_any:
                        continue
                    if not f.is_symlink() and f.is_file():
                        scanned += 1
                        if scanned % 50_000 == 0:
                            print(f"  {DIM}Scanned {scanned:,} files ...{RESET}",
                                  end="\r", flush=True)
                        try:
                            sz = os.lstat(f).st_size
                            if sz >= threshold:
                                large_files.append((sz, f))
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
        elif not entry.is_symlink() and entry.is_file():
            scanned += 1
            try:
                sz = os.lstat(entry).st_size
                if sz >= threshold:
                    large_files.append((sz, entry))
            except (PermissionError, OSError):
                pass

    # Clear progress line
    print(" " * 60, end="\r", flush=True)

    large_files.sort(key=lambda x: x[0], reverse=True)

    if not large_files:
        print(f"  {DIM}No files larger than {min_mb} MB found ({scanned:,} files scanned).{RESET}")
        return

    for size, path in large_files[:10]:
        rel = path.relative_to(HOME)
        print(f"  {GREEN}{fmt_size(size):>10}{RESET}  ~/{rel}")
    total = sum(s for s, _ in large_files[:10])
    print(f"\n  Top {min(10, len(large_files))} total: {CYAN}{fmt_size(total)}{RESET}")
    print(f"  {DIM}({scanned:,} files scanned){RESET}")


def clean_xcode(dry_run: bool = True) -> int:
    """Delete Xcode DerivedData."""
    derived = HOME / "Library" / "Developer" / "Xcode" / "DerivedData"
    print(f"\n{BOLD}{'[DRY RUN] ' if dry_run else ''}Clean Xcode DerivedData{RESET}")

    if not derived.exists():
        print(f"  {DIM}DerivedData not found — skipping.{RESET}")
        return 0

    size = dir_size(derived)
    print(f"  {derived}: {GREEN}{fmt_size(size)}{RESET}")

    if dry_run:
        print(f"  Total reclaimable: {CYAN}{fmt_size(size)}{RESET}")
        return size

    if size == 0:
        print(f"  {DIM}Nothing to clean.{RESET}")
        return 0

    if not confirm("Delete DerivedData?"):
        print("  Skipped.")
        return 0

    freed = delete_contents(derived)
    print(f"  Freed: {GREEN}{fmt_size(freed)}{RESET}")
    return freed


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

MENU = f"""
{BOLD}╔══════════════════════════════════════╗
║         {CYAN}MacPurge CLI{RESET}{BOLD}                ║
║   macOS Maintenance Tool             ║
╚══════════════════════════════════════╝{RESET}

  {BOLD}1{RESET}  Clean Logs          {DIM}~/Library/Logs, /var/log{RESET}
  {BOLD}2{RESET}  Clean Caches        {DIM}~/Library/Caches, /Library/Caches{RESET}
  {BOLD}3{RESET}  Flush DNS Cache
  {BOLD}4{RESET}  Purge Inactive RAM
  {BOLD}5{RESET}  Run Maintenance Scripts
  {BOLD}6{RESET}  Find Large Files     {DIM}(>500 MB in ~){RESET}
  {BOLD}7{RESET}  Clean Xcode Data     {DIM}~/…/DerivedData{RESET}
  {BOLD}A{RESET}  Run All Cleanups
  {BOLD}Q{RESET}  Quit
"""


def interactive_menu() -> None:
    """Run the interactive menu loop."""
    while True:
        print(MENU)
        try:
            choice = input(f"{YELLOW}Choose an option: {RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        total_freed = 0
        if choice == "1":
            size = clean_logs(dry_run=True)
            if size and confirm("\nProceed with deletion?"):
                total_freed += clean_logs(dry_run=False)
        elif choice == "2":
            size = clean_cache(dry_run=True)
            if size and confirm("\nProceed with deletion?"):
                total_freed += clean_cache(dry_run=False)
        elif choice == "3":
            flush_dns()
        elif choice == "4":
            purge_mem()
        elif choice == "5":
            run_scripts()
        elif choice == "6":
            find_large()
        elif choice == "7":
            size = clean_xcode(dry_run=True)
            if size and confirm("\nProceed with deletion?"):
                total_freed += clean_xcode(dry_run=False)
        elif choice == "a":
            # Dry run everything first
            total_reclaimable = 0
            total_reclaimable += clean_logs(dry_run=True)
            total_reclaimable += clean_cache(dry_run=True)
            total_reclaimable += clean_xcode(dry_run=True)
            find_large()
            print(f"\n{BOLD}Total reclaimable: {CYAN}{fmt_size(total_reclaimable)}{RESET}")
            if total_reclaimable and confirm("\nProceed with ALL deletions?"):
                total_freed += clean_logs(dry_run=False)
                total_freed += clean_cache(dry_run=False)
                total_freed += clean_xcode(dry_run=False)
                flush_dns()
                purge_mem()
                run_scripts()
        elif choice == "q":
            print("Bye!")
            break
        else:
            print(f"{RED}Invalid option.{RESET}")
            continue

        if total_freed:
            print(f"\n{BOLD}Successfully cleared {GREEN}{fmt_size(total_freed)}{RESET}{BOLD} of space.{RESET}")


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macpurge",
        description="MacPurge CLI — lightweight macOS maintenance tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
examples:
  %(prog)s                     Interactive menu
  %(prog)s --clean-logs        Dry-run log cleanup
  %(prog)s --clean-cache -y    Delete caches without confirmation
  %(prog)s --all -y            Run every cleanup module
  %(prog)s --find-large 200    Find files >200 MB
""",
    )
    parser.add_argument("--clean-logs", action="store_true", help="Clean log files")
    parser.add_argument("--clean-cache", action="store_true", help="Clean cache files")
    parser.add_argument("--flush-dns", action="store_true", help="Flush DNS cache")
    parser.add_argument("--purge-mem", action="store_true", help="Purge inactive RAM")
    parser.add_argument("--run-scripts", action="store_true", help="Run periodic maintenance scripts")
    parser.add_argument("--find-large", nargs="?", const=500, type=int, metavar="MB", help="Find large files (default >500 MB)")
    parser.add_argument("--clean-xcode", action="store_true", help="Clean Xcode DerivedData")
    parser.add_argument("--all", action="store_true", help="Run all cleanup modules")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Show what would be deleted (default for interactive)")
    return parser


def run_cli(args: argparse.Namespace) -> None:
    """Execute CLI-mode operations."""
    total_freed = 0

    # Determine dry-run: default True unless -y is passed
    dry_run = not args.yes

    targets = {
        "clean_logs": args.clean_logs or args.all,
        "clean_cache": args.clean_cache or args.all,
        "flush_dns": args.flush_dns or args.all,
        "purge_mem": args.purge_mem or args.all,
        "run_scripts": args.run_scripts or args.all,
        "find_large": args.find_large is not None or args.all,
        "clean_xcode": args.clean_xcode or args.all,
    }

    # Force dry-run if --dry-run explicitly set
    if args.dry_run:
        dry_run = True

    if targets["clean_logs"]:
        result = clean_logs(dry_run=dry_run)
        if not dry_run:
            total_freed += result

    if targets["clean_cache"]:
        result = clean_cache(dry_run=dry_run)
        if not dry_run:
            total_freed += result

    if targets["flush_dns"] and not dry_run:
        flush_dns()
    elif targets["flush_dns"]:
        print(f"\n{BOLD}[DRY RUN] Flush DNS Cache{RESET}")
        print(f"  Would run: sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder")

    if targets["purge_mem"] and not dry_run:
        purge_mem()
    elif targets["purge_mem"]:
        print(f"\n{BOLD}[DRY RUN] Purge Inactive Memory{RESET}")
        print(f"  Would run: sudo purge")

    if targets["run_scripts"] and not dry_run:
        run_scripts()
    elif targets["run_scripts"]:
        print(f"\n{BOLD}[DRY RUN] Run Periodic Maintenance Scripts{RESET}")
        print(f"  Would run: sudo periodic daily weekly monthly")

    if targets["find_large"]:
        min_mb = args.find_large if args.find_large is not None else 500
        find_large(min_mb)

    if targets["clean_xcode"]:
        result = clean_xcode(dry_run=dry_run)
        if not dry_run:
            total_freed += result

    if total_freed:
        print(f"\n{BOLD}Successfully cleared {GREEN}{fmt_size(total_freed)}{RESET}{BOLD} of space.{RESET}")
    elif dry_run and any(targets.values()):
        print(f"\n{DIM}Dry run complete. Add -y to execute deletions.{RESET}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    if sys.platform != "darwin":
        print(f"{RED}MacPurge is designed for macOS only.{RESET}")
        sys.exit(1)

    parser = build_parser()
    args = parser.parse_args()

    # If no flags given, launch interactive menu
    has_action = any([
        args.clean_logs, args.clean_cache, args.flush_dns,
        args.purge_mem, args.run_scripts, args.find_large is not None,
        args.clean_xcode, args.all,
    ])

    if not has_action:
        interactive_menu()
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
