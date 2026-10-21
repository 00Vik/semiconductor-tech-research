import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import EDA_REPORTS_DIR, NUMERIC_COLUMNS

from src.eda.structure_check import load_tables

def numeric_distribution(df, columns=None, name="patent"):
    """数值列描述统计。"""
    columns = columns or [c for c in NUMERIC_COLUMNS if c in df.columns]
    print(f"===== {name} 数值列 describe =====")
    print(df[columns].describe())
    print()


def year_distribution(df, column, name="patent"):
    """年份分布，返回年度计数并保存图。"""
    counts = df[column].value_counts().sort_index()
    print(f"===== {name}.{column} =====")
    print(f"范围: {counts.index.min()} ~ {counts.index.max()}")
    print(f"断档: {sorted(set(range(int(counts.index.min()), int(counts.index.max()) + 1)) - set(counts.index))}")
    print(counts)

    fig, ax = plt.subplots(figsize=(10, 4))
    counts.plot(kind="bar", ax=ax)
    ax.set_title(f"{name}.{column} Annual Distribution")
    ax.set_xlabel(column)
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(EDA_REPORTS_DIR / f"{name}_{column}_dist.png", dpi=150)
    plt.close(fig)
    return counts


def category_distribution(df, column, name="patent", topn=20):
    """类别列分布。"""
    counts = df[column].value_counts(dropna=False)
    print(f"===== {name}.{column} =====")
    print(f"类别数: {counts.shape[0]}")
    print(counts.head(topn))
    print()
    return counts


def text_length_distribution(df, column, name="patent"):
    """文本列长度分布并保存图。"""
    lengths = df[column].astype("string").str.len()
    print(f"===== {name}.{column} 长度 =====")
    print(lengths.describe())

    fig, ax = plt.subplots(figsize=(10, 4))
    lengths.plot(kind="hist", bins=50, ax=ax)
    ax.set_title(f"{name}.{column} Length Distribution")
    fig.tight_layout()
    fig.savefig(EDA_REPORTS_DIR / f"{name}_{column}_len.png", dpi=150)
    plt.close(fig)
    return lengths


def run(patent_df, patent_assignee_df):
    
    numeric_distribution(patent_df)
    year_distribution(patent_df, "grant_year")
    year_distribution(patent_df, "application_year")

    for col in ["cpc_section", "cpc_type", "country"]:
        if col in patent_df.columns:
            category_distribution(patent_df, col)

    category_distribution(patent_assignee_df, "assignee", name="patent_assignee", topn=50)

    if "patent_title" in patent_df.columns:
        text_length_distribution(patent_df, "patent_title")
    if "patent_abstract" in patent_df.columns:
        text_length_distribution(patent_df, "patent_abstract")


if __name__ == "__main__":
    
    engine, patent_df, patent_assignee_df, _, _ = load_tables()
    run(patent_df, patent_assignee_df)
    engine.dispose()