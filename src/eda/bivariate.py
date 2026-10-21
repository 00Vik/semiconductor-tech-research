import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import EDA_REPORTS_DIR

from src.eda.structure_check import load_tables

def year_by_category(df, year_col, cat_col, name="patent", normalize=False):
    """年份 × 类别 交叉，保存堆叠面积图。"""
    ct = pd.crosstab(df[year_col], df[cat_col])
    if normalize:
        ct = ct.div(ct.sum(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(12, 5))
    ct.plot(kind="area", stacked=True, ax=ax, colormap="tab20")
    ax.set_title(f"{name}: {year_col} × {cat_col}")
    fig.tight_layout()
    fig.savefig(EDA_REPORTS_DIR / f"{name}_{year_col}_{cat_col}.png", dpi=150)
    plt.close(fig)
    return ct


def assignee_by_category(df, assignee_col, cat_col, topn=10, name="patent_assignee"):
    """Top 企业 × 类别 交叉。"""
    top = df[assignee_col].value_counts().head(topn).index
    sub = df[df[assignee_col].isin(top)]
    ct = pd.crosstab(sub[assignee_col], sub[cat_col])

    fig, ax = plt.subplots(figsize=(12, 6))
    ct.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title(f"{name}: Top{topn} {assignee_col} × {cat_col}")
    fig.tight_layout()
    fig.savefig(EDA_REPORTS_DIR / f"{name}_{assignee_col}_{cat_col}.png", dpi=150)
    plt.close(fig)
    return ct


def numeric_corr(df, name="patent"):
    """数值列相关性。"""
    num = df.select_dtypes("number")
    corr = num.corr()
    print(f"===== {name} 数值相关性 =====")
    print(corr)
    return corr


def run(patent_df, patent_assignee_df):
    
    year_by_category(patent_df, "grant_year", "cpc_section")
    year_by_category(patent_df, "grant_year", "cpc_section", normalize=True)

    if "assignee" in patent_assignee_df.columns and "cpc_section" in patent_assignee_df.columns:
        assignee_by_category(patent_assignee_df, "assignee", "cpc_section")

    numeric_corr(patent_df)


if __name__ == "__main__":

    engine, patent_df, patent_assignee_df, _, _ = load_tables()
    run(patent_df, patent_assignee_df)
    engine.dispose()