"""One-time reorganization of downloaded NISR files into data/raw/ layout.
Run once from anywhere, doesn't need to be inside the repo.
"""
import shutil
from pathlib import Path

SRC_ROOT = Path("/mnt/Hackathon/nisr/nisr/Data")   # <- set this
DEST_ROOT = Path("/mnt/Hackathon/nisr/agritwin")      # <- your repo root

SAS_YEARS = ["SAS 2019", "SAS 2020", "SAS 2021", "SAS 2022", "SAS 2023", "SAS 2024", "SAS 2025"]
KEEP_EXTS = {".dta", ".sav"}

def year_from_folder(name: str) -> str:
    return name.split()[-1]  # "SAS 2024" -> "2024"

def is_season_c(path: Path) -> bool:
    return "seasonc" in path.name.lower() or "season c" in str(path).lower()

for year_folder_name in SAS_YEARS:
    src_year_dir = SRC_ROOT / "Seasonal Agriculture Survey" / year_folder_name
    if not src_year_dir.exists():
        print(f"MISSING: {src_year_dir}")
        continue

    year = year_from_folder(year_folder_name)
    dest_dir = DEST_ROOT / "data" / "raw" / "sas" / year
    dest_dir.mkdir(parents=True, exist_ok=True)

    # collect every candidate file, grouped by its base name (ignoring extension and subfolder)
    candidates: dict[str, dict[str, Path]] = {}
    for f in src_year_dir.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in KEEP_EXTS:
            continue
        if is_season_c(f):
            continue
        base = f.stem.lower()
        candidates.setdefault(base, {})[f.suffix.lower()] = f

    copied = 0
    for by_ext in candidates.values():
        chosen = by_ext.get(".dta") or by_ext.get(".sav")
        dest_path = dest_dir / chosen.name
        shutil.copy2(chosen, dest_path)
        copied += 1

    print(f"{year}: copied {copied} files -> {dest_dir}")

# AHS 2024 only
src_ahs = SRC_ROOT / "Agriculture Household Survey 2024"
dest_ahs = DEST_ROOT / "data" / "raw" / "ahs" / "2024"
dest_ahs.mkdir(parents=True, exist_ok=True)
count = 0
for f in src_ahs.glob("*.dta"):
    shutil.copy2(f, dest_ahs / f.name)
    count += 1
print(f"AHS 2024: copied {count} files -> {dest_ahs}")