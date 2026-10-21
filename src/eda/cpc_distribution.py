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
# 第一层：class 分布
# ============================================================
def class_distribution(patent_cpc_df, topn=30):
    print("===== 第一层：class 分布 =====")
    df = patent_cpc_df.drop_duplicates(["patent_id", "cpc_class"])
    counts = df["cpc_class"].value_counts()
    print(f"class 类别数: {counts.shape[0]}")
    print(f"\n-- Top {topn} class（按专利数）--")
    print(counts.head(topn))
    print()
    return counts

# ============================================================
# 第一层：subclass 分布
# ============================================================
def subclass_distribution(patent_cpc_df, topn=50):
    print("===== 第二层：subclass 分布 =====")
    print(f"patent_cpc 总行数: {len(patent_cpc_df)}")
    print(f"subclass 类别数: {patent_cpc_df['cpc_subclass'].nunique()}")

    counts = patent_cpc_df["cpc_subclass"].value_counts()
    print(f"\n-- Top {topn} subclass --")
    print(counts.head(topn))

    print(f"\n-- 总行数量 < 1000 的 subclass 数 --")
    print(f"{(counts < 1000).sum()}")

    print(f"\n-- 总行数量 < 100 的 subclass 数 --")
    print(f"{(counts < 100).sum()}")

    print(f"\n-- 总行数量 < 10 的 subclass 数 --")
    print(f"{(counts < 10).sum()}")
    print()
    return counts


# ============================================================
# 第一层补充：专利粒度 × subclass 分布
# ============================================================
def subclass_patent_distribution(patent_cpc_df, topn=50):
    print("===== 第二层补充：专利粒度 × subclass 分布 =====")
    df = patent_cpc_df.drop_duplicates(["patent_id", "cpc_subclass"])
    counts = df["cpc_subclass"].value_counts()

    print(f"专利 × subclass 组合数: {len(df)}")
    print(f"subclass 类别数: {counts.shape[0]}")
    print(f"\n-- Top {topn} subclass（按专利数）--")
    print(counts.head(topn))

    print(f"\n-- 专利数量 < 1000 的 subclass 数 --")
    print(f"{(counts < 1000).sum()}")
    
    print(f"\n-- 专利数量 < 100 的 subclass 数 --")
    print(f"{(counts < 100).sum()}")
    
    print(f"\n-- 专利数量 < 10 的 subclass 数 --")
    print(f"{(counts < 10).sum()}")
    print()


# ============================================================
# 第二层补充：subclass 标题
# ============================================================
def subclass_titles(cpc_dict, top_subclass):
    print("===== 第二层补充：subclass 标题显示 =====")
    titles = (
        cpc_dict[cpc_dict["cpc_subclass"].isin(top_subclass)]
        [["cpc_subclass", "cpc_subclass_title"]]
        .drop_duplicates()
    )
    titles["__order"] = titles["cpc_subclass"].map(
        {s: i for i, s in enumerate(top_subclass)}
    )
    titles = titles.sort_values("__order").drop(columns="__order")
    print(titles.to_string(index=False))
    print()
    return titles

# ============================================================
# 第三层：group 分布
# ============================================================
def group_distribution(patent_cpc_df, topn=50):
    print("===== 第三层：group 分布 =====")
    df = patent_cpc_df.drop_duplicates(["patent_id", "cpc_group"])
    counts = df["cpc_group"].value_counts()

    print(f"专利 × group 组合数: {len(df)}")
    print(f"group 类别数: {counts.shape[0]}")

    print(f"\n-- Top {topn} group（按专利数）--")
    print(counts.head(topn))

    print(f"\n-- 量 < 1000 的 group 数 --")
    print(f"{(counts < 1000).sum()}")

    print(f"\n-- 量 < 100 的 group 数 --")
    print(f"{(counts < 100).sum()}")

    print(f"\n-- 量 < 10 的 group 数 --")
    print(f"{(counts < 10).sum()}")
    print()
    return counts


# ============================================================
# 第三层补充：group 的 subclass 归属
# ============================================================
def group_subclass_mapping(patent_cpc_df):
    print("===== 第三层补充：group 所属 subclass =====")
    df = patent_cpc_df.drop_duplicates(["cpc_group", "cpc_subclass"])
    mapping = df[["cpc_group", "cpc_subclass"]].copy()
    mapping["group_prefix"] = mapping["cpc_group"].str.split("/").str[0]
    mapping["subclass_from_group"] = mapping["group_prefix"].str[:4]

    mismatch = mapping[
        mapping["subclass_from_group"] != mapping["cpc_subclass"]
    ]
    print(f"group 与 subclass 前缀不一致的行数: {len(mismatch)}")
    print(mismatch.head(20).to_string(index=False))
    print()


# ============================================================
# 第三层补充：group 的 cpc_dict 覆盖率
# ============================================================
def group_dict_coverage(patent_cpc_df, cpc_dict):
    print("===== 第三层补充：group 字典覆盖率 =====")
    df = patent_cpc_df.drop_duplicates(["patent_id", "cpc_group"])
    total = len(df)
    matched = df["cpc_group"].isin(cpc_dict["cpc_group"]).sum()

    print(f"专利 × group 组合数: {total}")
    print(f"匹配数: {matched}")
    print(f"匹配率: {matched / total:.4f}")

    unmatched = (
        df.loc[~df["cpc_group"].isin(cpc_dict["cpc_group"]), "cpc_group"]
        .value_counts()
    )
    print(f"\n-- 未匹配 Top 20 --")
    print(unmatched.head(20))
    print()


# ============================================================
# 主程序
# ============================================================
def run(patent_cpc_df, cpc_dict):

    counts = subclass_distribution(patent_cpc_df)
    subclass_patent_distribution(patent_cpc_df)
    class_distribution(patent_cpc_df)

    top_subclass = counts.head(50).index.tolist()
    subclass_titles(cpc_dict, top_subclass)

    counts = subclass_distribution(patent_cpc_df)
    subclass_patent_distribution(patent_cpc_df)
    class_distribution(patent_cpc_df)
    group_distribution(patent_cpc_df)

    top_subclass = counts.head(50).index.tolist()
    subclass_titles(cpc_dict, top_subclass)

    group_subclass_mapping(patent_cpc_df)
    group_dict_coverage(patent_cpc_df, cpc_dict)

    

if __name__ == "__main__":

    engine, patent_cpc_df, cpc_dict, _, _ = load_tables()
    run(patent_cpc_df, cpc_dict)
    engine.dispose()