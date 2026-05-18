from __future__ import annotations

from pathlib import Path


API_DIR = Path(__file__).resolve().parent


def iter_migration_files() -> list[Path]:
    files: list[Path] = []
    for migrations_dir in API_DIR.rglob("migrations"):
        if not migrations_dir.is_dir():
            continue
        for child in migrations_dir.iterdir():
            if not child.is_file():
                continue
            if child.name == "__init__.py":
                continue
            files.append(child)
    return sorted(files)


def main() -> None:
    files = iter_migration_files()
    if not files:
        print("No migration files to delete.")
        return

    for file_path in files:
        file_path.unlink()
        print(f"Deleted {file_path.relative_to(API_DIR)}")


if __name__ == "__main__":
    main()
