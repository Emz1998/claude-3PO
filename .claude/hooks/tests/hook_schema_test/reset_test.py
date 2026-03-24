from pathlib import Path
import shutil


def main() -> None:
    folder = Path("input-schemas")
    for item in folder.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


if __name__ == "__main__":
    main()
