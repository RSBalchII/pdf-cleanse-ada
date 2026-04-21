from __future__ import annotations
import argparse
import shlex
import subprocess
import sys
from pathlib import Path

COMMANDS = {
    "server": "../server.js",  # Default - starts web UI (from project root)
    "ada-auto": "../adobe_auto.py",
    "adobe-api": "../adobe_autotag_api.py",
    "batch-tag-acrobat": "../batch_auto_tag_acrobat.py",
    "pdf-fix-single": "../pdf_fix_single.py",
    "pipeline": "../pipeline.py",
    "compliance-checker": "../compliance_checker.py",
    "vision-alt-text": "../vision_alt_text.py",
    "ada-compliance-processor": "../ada_compliance_processor.py"
}

def dispatch(subcommand, script_rel_path, sub_args, dry_run, remaining=None):
    """Dispatch to a tool based on subcommand.
    
    The project root is determined dynamically from sys.executable's location,
    which works correctly when running from the PyInstaller bundle.
    """
    # Use dynamic path resolution instead of hardcoded absolute path
    import os.path
    
    # Get executable directory (where .exe/.app runs from)
    exec_dir = Path(sys.executable).parent
    
    # Project root is parent of python/src/
    project_root = exec_dir.parent.parent / "python" / "..".resolve()
    
    # Build the full path to the target script
    if subcommand == "server":
        script_abs = project_root / "server.js"
    else:
        # Other scripts are relative to python/
        script_abs = (project_root / "python" / script_rel_path).resolve()

    if not script_abs.is_file():
        raise FileNotFoundError(f"Target script for '{subcommand}' not found at {script_abs}")

    # Combine sub_args and remaining, then strip known flags from server.js execution
    all_args = list(sub_args) + (list(remaining) if remaining else [])
    
    # For Node.js server.js, we already handled --dry-run in main() so no stripping needed there
    
    cmd_line = [sys.executable, str(script_abs)] + all_args
    if dry_run:
        # Fixed: Added the missing closing brace '}' for the f-string expression
        print(f"[DRY-RUN] Dispatching '{subcommand}' -> {' '.join(shlex.quote(arg) for arg in cmd_line)}")
    else:
        subprocess.run(cmd_line, check=True)

def main():
    parser = argparse.ArgumentParser(description="pdf-ada PyInstaller entry point", add_help=True)

    # Check if server is explicitly requested (default to True unless --server flag given)
    subcommand = sys.argv[1] if len(sys.argv) > 1 else "server"

    # If the first argument starts with '--', it's a flag, not a tool name
    if subcommand.startswith('--'):
        actual_subcommand = "server"
    else:
        actual_subcommand = subcommand

    # Parse just the help flag, pass all other arguments through
    # But filter out any file paths that might be in PATH (e.g., server.js from parent dir)
    args, remaining = parser.parse_known_args()
    
    # Filter out any full file paths that shouldn't be passed as subcommands
    filtered_remaining = []
    for arg in remaining:
        if isinstance(arg, str) and ('/' in arg or '\\' in arg):
            # It's a path, skip it (it came from PATH environment variable)
            continue
        filtered_remaining.append(arg)

    # Debug output to see what's being passed
    print(f"DEBUG: subcommand={subcommand}, actual={actual_subcommand}, remaining={filtered_remaining}")

    # Run the selected command with all arguments passed through
    cmd_args = list(filtered_remaining) if len(filtered_remaining) > 0 else []

    # Determine dry-run mode from command line arguments passed through dispatch
    dry_run = False
    for arg in cmd_args:
        if isinstance(arg, str) and '--dry-run' in arg:
            dry_run = True
    
    dispatch(actual_subcommand, COMMANDS[actual_subcommand], cmd_args, dry_run=dry_run, remaining=remaining)

if __name__ == "__main__":
    main()