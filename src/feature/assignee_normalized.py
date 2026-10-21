import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql

from config import (
    schema_features,
)


# 归一化
def build_normalized():
    engine = get_engine()

    patent_assignee = pd.read_sql("SELECT * FROM clean.patent_assignee", engine)
    assignee_disambig = pd.read_sql("SELECT * FROM raw.bridge_patent_organization", engine)

    normalized_df = patent_assignee.merge(
        assignee_disambig[
            ["patent_id", "assignee_id", "disambig_assignee_organization"]
        ],
        on="patent_id",
        how="left",
    )

    print(f"未匹配：{normalized_df['assignee_id'].isna().sum()} 行")
    save_to_sql(normalized_df, "patent_assignee_normalized", engine, schema_features)

    return engine, normalized_df


# 企业分布
def assignee_distribution(normalized_df, topn=30):
    counts = (
        normalized_df
        .dropna(subset=["assignee_id"])
        .drop_duplicates(["patent_id", "assignee_id"])
        .groupby(["assignee_id", "disambig_assignee_organization"])["patent_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    total_patent = normalized_df["patent_id"].nunique()
    total_assignee = counts.shape[0]

    print(f"企业数：{total_assignee}")
    print(f"专利数：{total_patent}")
    print()

    print(f"===== Top {topn} 企业专利数 =====")
    print(counts.head(topn))

    print("\n===== 累计占比 =====")
    for n in [10, 50, 100, 200, 500, 1000]:
        top_n = counts.head(n).sum()
        print(f"Top {n:>4}: 专利 {top_n:>7}，占 {top_n / total_patent:.4f}")

    print("\n===== 专利数分布 =====")
    bins = [0, 1, 5, 10, 50, 100, 500, 1000, 10000, 100000]
    labels = ["1", "2-5", "6-10", "11-50", "51-100", "101-500", "501-1000", "1001-10000", "10000+"]
    dist = pd.cut(counts, bins=bins, labels=labels, right=True)
    print(dist.value_counts().sort_index())

    return counts


# 主程序
def run():
    engine, normalized_df = build_normalized()
    counts = assignee_distribution(normalized_df)
    return engine, normalized_df, counts


if __name__ == "__main__":
    engine, _, _ = run()
    engine.dispose()