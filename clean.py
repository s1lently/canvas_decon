#!/usr/bin/env python3
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
KEEP_EXTS = {'.py'}

def load_whitelist():
    wl = ROOT_DIR / 'clean_whitelist.txt'
    if not wl.exists():
        return {'account_info.json', 'personal_info.json', 'CLAUDE.md', 'README.md',
                'requirements.txt', 'cookies.json', '.gitignore'}, {'.git', '.claude', 'todo_files', 'misc'}
    files, dirs = set(), set()
    for line in wl.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            (dirs.add(line.rstrip('/')) if line.endswith('/') else files.add(line))
    return files, dirs

KEEP_FILES, KEEP_DIRS = load_whitelist()

def is_whitelisted(p): return p.suffix in KEEP_EXTS or p.name in KEEP_FILES
def is_protected(p):
    try: return (p.relative_to(ROOT_DIR).parts[0] if p != ROOT_DIR else '') in KEEP_DIRS
    except: return False

def build_tree(paths):
    tree = {}
    for path in paths:
        cur = tree
        for part in Path(path).parts:
            cur = cur.setdefault(part, {})
    return tree

def print_tree(tree, prefix=""):
    items = sorted(tree.items())
    for i, (name, sub) in enumerate(items):
        print(f"{prefix}{'└── ' if i == len(items)-1 else '├── '}{name}")
        if sub: print_tree(sub, prefix + ('    ' if i == len(items)-1 else '│   '))


def preview_deletion():
    to_delete = []
    for item in ROOT_DIR.rglob('*'):
        if item.is_file() and item.name not in ('clean.py', 'clean_whitelist.txt') \
           and not is_protected(item.parent) and not is_whitelisted(item):
            to_delete.append(str(item.relative_to(ROOT_DIR)))
    return to_delete

def clean_directory(to_delete):
    deleted_files, deleted_dirs = 0, 0
    for path_str in to_delete:
        try: (ROOT_DIR / path_str).unlink(); deleted_files += 1
        except: pass
    for _ in range(10):
        dirs = sorted([d for d in ROOT_DIR.rglob('*') if d.is_dir()], key=lambda p: len(p.parts), reverse=True)
        deleted_round = False
        for d in dirs:
            if not is_protected(d):
                try:
                    if not any(d.iterdir()): d.rmdir(); deleted_dirs += 1; deleted_round = True
                except: pass
        if not deleted_round: break
    print(f"\n✓ 清理完成: {deleted_files} 文件, {deleted_dirs} 文件夹")

if __name__ == '__main__':
    to_delete = preview_deletion()
    if not to_delete:
        print("✓ 无需清理")
    else:
        print(f"将删除以下 {len(to_delete)} 个文件:\n")
        print_tree(build_tree(to_delete))
        if input("\n⚠️  确认清理？(yes/no): ").lower() in ['yes', 'y']:
            clean_directory(to_delete)
        else:
            print("已取消")
