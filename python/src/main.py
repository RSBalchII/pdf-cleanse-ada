from __future__ import annotations
import argparse
import shlex
import subprocess
import sys
from pathlib import Path

COMMANDS = {
    "ada-auto": "../adobe_auto.py",
    "adobe-api": "../adobe_autotag_api.py",
    "batch-tag-acrobat": "../batch_auto_tag_acrobat.py",
    "pdf-fix-single": "../pdf_fix_single.py",
    "pipeline": "../pipeline.py",
    "compliance-checker": "../compliance_checker.py",
    "vision-alt-text": "../vision_alt_text.py",
    "ada-compliance-processor": "../ada_compliance_processor.py"
}

def dispatch(subcommand, script_rel_path, sub_args, dry_run):
    base_dir = Path(__file__).resolve().parent
    script_abs = (base_dir / script_rel_path).resolve()
    if not script_abs.is_file():
        raise FileNotFoundError(f"Target script for '{subcommand}' not found: {script_rel_path}")
    cmd_line = [sys.executable, str(script_abs)] + sub_args
    if dry_run:
        # Fixed: Added the missing closing brace '}' for the f-string expression
        print(f"[DRY-RUN] Dispatching '{subcommand}' -> {' '.join(shlex.quote(arg) for arg in cmd_line)}")
    else:
        subprocess.run(cmd_line, check=True)

def main():
    parser = argparse.ArgumentParser(description="pdf-ada PyInstaller entry point", add_help=True)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed without running")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    for name, rel_path in COMMANDS.items():
        sp = subparsers.add_parser(name, help=f"Run the '{name}' tool")
        sp.add_argument("sub_args", nargs=argparse.REMAINDER, help="Arguments passed to the underlying tool")
    args = parser.parse_args()
    if not getattr(args, "subcommand", None):
        parser.print_help(); sys.exit(1)
    _dispatch(args.subcommand, COMMANDS[args.subcommand], list(args.sub_args or []), dry_run=args.dry_run)

if __name__ == "__main__":
    main()