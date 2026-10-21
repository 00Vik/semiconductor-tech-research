import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import (
    ANNUALIZED_DIR,
    ANNUALIZED_LOADED_PATH,
    SELECT_COLUMN,
    ANNUALIZED_KEY_COLUMN,
    EXTRA_KEY_COLUMN,
    INDUSTRY,
)


def _iter_year_dirs(inputdir: Path):
    """扫描 RAW_DIR 下所有 4 位数字命名的子目录，按年份升序返回。"""
    for path in sorted(inputdir.iterdir()):
        if path.is_dir() and path.name.isdigit() and len(path.name) == 4:
            yield int(path.name), path


def load_one_year(year: int, inputdir: Path):
    """读取单年 CSV，加一列 year。失败返回空 DataFrame。"""
    csv_path = inputdir / str(year) / f"{year}.csv"
    if not csv_path.exists():
        print(f"[{year}] 文件不存在: {csv_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            csv_path,
            encoding="utf-8",
            low_memory=False,
            dtype={"cpc_sections": "string", "assignee": "string"},
        )
    except Exception as e:
        print(f"[{year}] 读取失败: {e}")
        return pd.DataFrame()

    df["year"] = year
    print(f"[{year}] 读取成功: {len(df)} 行, {df.shape[1]} 列")
    return df


def load_all_years(inputdir):
    """返回 {year: df}，按年份升序。读取失败的年份会被跳过。"""
    results = {}
    for year, _ in _iter_year_dirs(inputdir):
        df = load_one_year(year, inputdir)
        if not df.empty:
            results[year] = df
    return results


if __name__ == "__main__":

    data = load_all_years(ANNUALIZED_DIR)
    df = pd.concat(data.values(), ignore_index=True)
    df = df[df[SELECT_COLUMN] == INDUSTRY]
    df = df.rename(columns={ANNUALIZED_KEY_COLUMN: EXTRA_KEY_COLUMN})

    df.to_parquet(ANNUALIZED_LOADED_PATH, index=False)
    print(f"Saved: {ANNUALIZED_LOADED_PATH}  ({len(df)} 行)")

    print(f"\n共读取 {len(data)} 个年份: {sorted(data.keys())}")