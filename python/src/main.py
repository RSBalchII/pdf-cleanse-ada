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

    print(f"DEBUG DISPATCH: received subcommand={subcommand}, script_rel_path={script_rel_path}")

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

    print(f"DEBUG DISPATCH: all_args={all_args}, remaining_param={remaining}")
    
    cmd_line = [sys.executable, str(script_abs)] + all_args
    
    # For Node.js server.js, we already handled --dry-run in main() so no stripping needed there
    if dry_run:
        print(f"DEBUG DISPATCH: dry_run=True, full_cmd={cmd_line}")
        # Fixed: Added the missing closing brace '}' for the f-string expression
        print(f"[DRY-RUN] Dispatching '{subcommand}' -> {' '.join(shlex.quote(arg) for arg in cmd_line)}")
    else:
        print(f"DEBUG DISPATCH: subprocess.run(cmd_line={cmd_line}, check=True)")
        
        import shlex
        for i, arg in enumerate(cmd_line):
            print(f"  [subprocess arg {i}]: {shlex.quote(arg)}")
            
        subprocess.run(cmd_line, check=True)

def main():
    # DEBUG MAIN at startup - show what argv looks like
    import sys as _sys
    print(f"DEBUG ENTRY: len(sys.argv)={len(_sys.argv)}", file=_sys.stderr, flush=True)
    for i, arg in enumerate(_sys.argv):
        print(f"DEBUG ENTRY: sys.argv[{i}]='{arg}'", file=_sys.stderr, flush=True)

    parser = argparse.ArgumentParser(description="pdf-ada PyInstaller entry point", add_help=True)

    # Check if first argument is a full file path (from PATH pollution) - default to server
    # A path typically has '/' or '\' in it and contains 'server.js' for the special case, 
    # but we should check more generally for any path-like string that's not a valid subcommand key
    import os.path as _os_path
    
    # If first argument is a full file path (e.g., from PATH pollution), default to server
    if len(_sys.argv) > 1:
        first_arg = _sys.argv[1]
        has_slash = '/' in first_arg or '\\' in first_arg
        # It's a file-like path - likely PATH pollution, default to server
        if has_slash and ('server.js' in first_arg):
            subcommand = "server"
    
    # If the first argument starts with '--', it's a flag, not a tool name
    if subcommand.startswith('--'):
        actual_subcommand = "server"
    else:
        actual_subcommand = subcommand

    print(f"DEBUG MAIN: After setting subcommand - subcommand={subcommand}, actual_subcommand={actual_subcommand}", file=_sys.stderr)

    # Parse just the help flag, pass all other arguments through
    # But filter out any file paths that might be in PATH (e.g., server.js from parent dir)
    args, remaining = parser.parse_known_args()

    print(f"DEBUG MAIN: after parse_known_args - args={args}, remaining={remaining}", file=_sys.stderr, flush=True)
    filtered_remaining = []
    for arg in remaining:
        slash_found = '/' in arg or '\\' in arg
        print(f"DEBUG MAIN: checking arg='{arg}', type={type(arg)}, has_slash={slash_found}", file=_sys.stderr)
        if isinstance(arg, str) and ('/' in arg or '\\' in arg):
            # It's a path, skip it (it came from PATH environment variable)
            continue
        filtered_remaining.append(arg)

    print(f"DEBUG MAIN: filtered_remaining={filtered_remaining}, remaining={remaining}")
    # Debug output to see what's being passed
    print(f"DEBUG: sys.argv={sys.argv}")
    print(f"DEBUG: subcommand={subcommand}, actual={actual_subcommand}, remaining_before_filter={remaining}")

    # Run the selected command with all arguments passed through
    cmd_args = list(filtered_remaining) if len(filtered_remaining) > 0 else []
    
    # Debug after dispatch call - show what's being passed to subprocess
    print(f"DEBUG: dispatch called with subcommand={actual_subcommand}, script_rel_path={COMMANDS[actual_subcommand]}, cmd_args={cmd_args}")

    # Determine dry-run mode from command line arguments passed through dispatch
    dry_run = False
    for arg in cmd_args:
        if isinstance(arg, str) and '--dry-run' in arg:
            dry_run = True
    
    dispatch(actual_subcommand, COMMANDS[actual_subcommand], cmd_args, dry_run=dry_run, remaining=remaining)

if __name__ == "__main__":
    main()