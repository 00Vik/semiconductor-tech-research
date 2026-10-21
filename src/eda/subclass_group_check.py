import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql

from src.eda.structure_check import load_tables

# ============================================================
# 单个 subclass 的 group 分布
# ============================================================
def group_distribution_of_subclass(patent_cpc_df, subclass, topn=20):
    print(f"===== {subclass} 的 group 分布 =====")

    df = patent_cpc_df[patent_cpc_df["cpc_subclass"] == subclass]
    df = df.drop_duplicates(["patent_id", "cpc_group"])

    total_patent = df["patent_id"].nunique()
    counts = df["cpc_group"].value_counts()

    print(f"专利数: {total_patent}")
    print(f"group 类别数: {counts.shape[0]}")

    print(f"\n-- Top {topn} group --")
    print(counts.head(topn))

    top10_share = counts.head(10).sum() / counts.sum()
    top20_share = counts.head(20).sum() / counts.sum()
    print(f"\nTop 10 group 占 {top10_share:.4f}")
    print(f"Top 20 group 占 {top20_share:.4f}")

    print(f"\n量 < 1000 的 group 数: {(counts < 1000).sum()}")
    print(f"量 < 100 的 group 数: {(counts < 100).sum()}")
    print(f"量 < 10 的 group 数: {(counts < 10).sum()}")
    print()

    return counts

# ============================================================
# 单个 subclass 的主组分布
# ============================================================
def main_group_distribution_of_subclass(patent_cpc_df, subclass, topn=20):
    print(f"===== {subclass} 的主组分布 =====")

    df = patent_cpc_df[patent_cpc_df["cpc_subclass"] == subclass].copy()
    df["cpc_main_group"] = df["cpc_group"].str.split("/").str[0]
    df = df.drop_duplicates(["patent_id", "cpc_main_group"])

    total_patent = df["patent_id"].nunique()
    counts = df["cpc_main_group"].value_counts()

    print(f"专利数: {total_patent}")
    print(f"主组类别数: {counts.shape[0]}")

    print(f"\n-- Top {topn} 主组 --")
    print(counts.head(topn))

    top10_share = counts.head(10).sum() / counts.sum()
    top20_share = counts.head(20).sum() / counts.sum()
    print(f"\nTop 10 主组占 {top10_share:.4f}")
    print(f"Top 20 主组占 {top20_share:.4f}")

    print(f"\n量 < 10000 的主组数: {(counts < 10000).sum()}")
    print(f"量 < 1000 的主组数: {(counts < 1000).sum()}")
    print(f"量 < 100 的主组数: {(counts < 100).sum()}")
    print(f"量 < 10 的主组数: {(counts < 10).sum()}")
    print()

    return counts
    
# ============================================================
# 主程序
# ============================================================
def run():

    for subclass in ["H01L", "H10K", "H05K"]:
        group_distribution_of_subclass(patent_cpc_df, subclass)

    
if __name__ == "__main__":

    engine, _, _, patent_cpc_df, _ = load_tables()
    run()
    engine.dispose()