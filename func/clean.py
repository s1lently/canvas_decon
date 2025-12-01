"""
Clean utility - Remove all generated files except account_config.json
Supports interactive exclusion of specific items before cleaning.
"""
import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Files/dirs that should NEVER be deleted (core project files)
PROTECTED = {
    # Config
    'account_config.json',
    'account_info.json',

    # Git
    '.git',
    '.gitignore',

    # Claude
    '.claude',
    'CLAUDE.md',

    # Project files
    'requirements.txt',
    'README.md',

    # Source directories
    'func',
    'gui',
    'login',
    'misc',  # Keep misc/ but clean misc/jsons/
}

# Directories to clean entirely
CLEAN_DIRS = [
    config.TODO_DIR,           # todo/
    config.COURSES_DIR,        # Courses/
]

# Files to clean (specific paths)
CLEAN_FILES = [
    config.COOKIES_FILE,       # misc/jsons/cookies.json
    config.TODOS_FILE,         # misc/jsons/todos.json
    config.COURSE_FILE,        # misc/jsons/course.json
    config.HIS_TODO_FILE,      # misc/jsons/his_todo.json
]

# Patterns to clean (anywhere in project)
CLEAN_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '.DS_Store',
]


def scan_items():
    """Scan for items to clean, returns list of (path, type, size_str)"""
    items = []

    # Directories to clean entirely
    for dir_path in CLEAN_DIRS:
        if os.path.exists(dir_path):
            size = _get_dir_size(dir_path)
            items.append((dir_path, 'dir', _format_size(size)))

    # Specific files
    for file_path in CLEAN_FILES:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            items.append((file_path, 'file', _format_size(size)))

    # Pattern-based cleaning
    for pattern in CLEAN_PATTERNS:
        for item in Path(config.ROOT_DIR).rglob(pattern):
            if item.exists() and not _is_protected(item):
                if item.is_dir():
                    size = _get_dir_size(str(item))
                    items.append((str(item), 'dir', _format_size(size)))
                else:
                    size = item.stat().st_size
                    items.append((str(item), 'file', _format_size(size)))

    # Remove duplicates and sort
    seen = set()
    unique = []
    for item in items:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)

    return sorted(unique, key=lambda x: x[0])


def _get_dir_size(path):
    """Get total size of directory"""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except:
                pass
    return total


def _format_size(size):
    """Format size in human readable form"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _is_protected(path):
    """Check if path is protected"""
    path = Path(path)
    try:
        rel = path.relative_to(config.ROOT_DIR)
        parts = rel.parts
        if parts and parts[0] in PROTECTED:
            # Special case: allow cleaning inside misc/jsons
            if parts[0] == 'misc' and len(parts) > 1 and parts[1] == 'jsons':
                return False
            return True
        return path.name in PROTECTED
    except:
        return False


def clean_items(items, exclude_indices=None):
    """
    Clean specified items.

    Args:
        items: List from scan_items()
        exclude_indices: Set of indices to exclude from cleaning

    Returns:
        (deleted_count, skipped_count)
    """
    exclude_indices = exclude_indices or set()
    deleted = 0
    skipped = 0

    for i, (path, item_type, _) in enumerate(items):
        if i in exclude_indices:
            skipped += 1
            continue

        try:
            if item_type == 'dir':
                shutil.rmtree(path)
                print(f"  ✓ Deleted dir: {_rel_path(path)}")
            else:
                os.remove(path)
                print(f"  ✓ Deleted file: {_rel_path(path)}")
            deleted += 1
        except Exception as e:
            print(f"  ✗ Failed: {_rel_path(path)} ({e})")

    return deleted, skipped


def _rel_path(path):
    """Get path relative to ROOT_DIR"""
    try:
        return str(Path(path).relative_to(config.ROOT_DIR))
    except:
        return path


def preview_deletion():
    """Preview what will be deleted (for GUI compatibility)"""
    return [_rel_path(item[0]) for item in scan_items()]


def build_tree(paths):
    """Build tree structure for display (for GUI compatibility)"""
    tree = {}
    for path in paths:
        cur = tree
        for part in Path(path).parts:
            cur = cur.setdefault(part, {})
    return tree


def print_tree(tree, prefix=""):
    """Print tree structure"""
    items = sorted(tree.items())
    for i, (name, sub) in enumerate(items):
        is_last = i == len(items) - 1
        print(f"{prefix}{'└── ' if is_last else '├── '}{name}")
        if sub:
            print_tree(sub, prefix + ('    ' if is_last else '│   '))


def clean_directory(to_delete):
    """Clean by path list (for GUI compatibility)"""
    items = scan_items()
    path_to_idx = {_rel_path(item[0]): i for i, item in enumerate(items)}

    # Find indices of items in to_delete
    indices_to_clean = set()
    for path in to_delete:
        if path in path_to_idx:
            indices_to_clean.add(path_to_idx[path])

    # Clean all except those not in to_delete
    exclude = set(range(len(items))) - indices_to_clean
    deleted, _ = clean_items(items, exclude)
    print(f"\n✓ 清理完成: {deleted} items deleted")


def interactive_clean():
    """Interactive cleaning with exclusion support"""
    items = scan_items()

    if not items:
        print("✓ Nothing to clean!")
        return

    # Display items with numbers
    print(f"\nFound {len(items)} items to clean:\n")
    total_size = 0
    for i, (path, item_type, size_str) in enumerate(items):
        marker = '📁' if item_type == 'dir' else '📄'
        print(f"  [{i:2d}] {marker} {_rel_path(path)} ({size_str})")
        # Parse size for total
        try:
            val, unit = size_str.split()
            val = float(val)
            mult = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
            total_size += val * mult.get(unit, 1)
        except:
            pass

    print(f"\n  Total: {_format_size(total_size)}")

    # Ask for exclusions
    print("\n📋 Enter indices to EXCLUDE (comma-separated), or press Enter to clean all:")
    print("   Example: 0,2,5 to exclude items 0, 2, and 5")

    try:
        exclude_input = input("\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    exclude_indices = set()
    if exclude_input:
        try:
            exclude_indices = {int(x.strip()) for x in exclude_input.split(',') if x.strip()}
        except ValueError:
            print("Invalid input. Cancelled.")
            return

    # Show what will be cleaned
    to_clean = [item for i, item in enumerate(items) if i not in exclude_indices]

    if not to_clean:
        print("\nNothing selected for cleaning.")
        return

    print(f"\n⚠️  Will clean {len(to_clean)} items" +
          (f" (excluding {len(exclude_indices)})" if exclude_indices else "") + ":")

    for path, item_type, size_str in to_clean:
        print(f"  - {_rel_path(path)}")

    # Confirm
    try:
        confirm = input("\nConfirm? (yes/no): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if confirm in ['yes', 'y']:
        print("\nCleaning...")
        deleted, skipped = clean_items(items, exclude_indices)
        print(f"\n✓ Done: {deleted} deleted, {skipped} skipped")
    else:
        print("Cancelled.")


if __name__ == '__main__':
    interactive_clean()
