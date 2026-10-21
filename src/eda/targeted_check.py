import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from src.eda.structure_check import load_tables

def check_assignee_normalization(patent_assignee_df, topn=50):
    """看企业名是否有明显同义写法。"""
    print("===== assignee 归一化检查 =====")
    print(patent_assignee_df["assignee"].value_counts().head(topn))
    print()


def check_cpc_dict_join(patent_cpc_df, cpc_dict):
    """CPC 与字典 join 匹配率。"""
    for col in ["cpc_subclass", "cpc_group", "cpc_class"]:
        if col in patent_cpc_df.columns and col in cpc_dict.columns:
            rate = patent_cpc_df[col].isin(cpc_dict[col]).mean()
            print(f"{col} 匹配率: {rate:.4f}")
    print()


def check_time_consistency(patent_df):
    """时间字段一致性。"""
    print("===== 时间字段一致性 =====")
    print(f"grant_year 范围: {patent_df['grant_year'].min()} ~ {patent_df['grant_year'].max()}")
    print(f"application_year 范围: {patent_df['application_year'].min()} ~ {patent_df['application_year'].max()}")

    bad = (patent_df["grant_year"] < patent_df["application_year"]).sum()
    print(f"grant_year < application_year 的行数: {bad}")

    if {"grant_year", "application_year"}.issubset(patent_df.columns):
        lag = patent_df["grant_year"] - patent_df["application_year"]
        print("审查周期 describe:")
        print(lag.describe())
    print()


def run(patent_df, patent_assignee_df, patent_cpc_df, cpc_dict):
    
    check_assignee_normalization(patent_assignee_df)
    check_cpc_dict_join(patent_cpc_df, cpc_dict)
    check_time_consistency(patent_df)


if __name__ == "__main__":

    engine,patent_df, patent_assignee_df, patent_cpc_df, cpc_dict = load_tables()
    run(patent_df, patent_assignee_df, patent_cpc_df, cpc_dict)
    engine.dispose()