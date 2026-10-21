import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql


def load_tables():
    """加载 EDA 所需的四张表。"""
    engine = get_engine()
    patent_df = pd.read_sql("SELECT * FROM clean.patent", engine)
    patent_assignee_df = pd.read_sql("SELECT * FROM clean.patent_assignee", engine)
    patent_cpc_df = pd.read_sql("SELECT * FROM clean.patent_cpc", engine)
    cpc_dict = pd.read_sql("SELECT * FROM clean.cpc_dict", engine)
    return engine, patent_df, patent_assignee_df, patent_cpc_df, cpc_dict


def overview(df, name):
    """打印单表基本信息。"""
    print(f"===== {name} =====")
    print(f"shape: {df.shape}")
    print(f"memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    print("\ndtypes:")
    print(df.dtypes)
    print("\n缺失比例:")
    print(df.isna().mean().sort_values(ascending=False).head(20))
    print()


def check_primary_key(df, columns, name):
    """检查主键唯一性。"""
    dup = df.duplicated(subset=columns).sum()
    print(f"{name} 主键 {columns} 重复行数: {dup}")
    return dup


def run(patent_df, patent_assignee_df, patent_cpc_df, cpc_dict):

    overview(patent_df, "patent")
    overview(patent_assignee_df, "patent_assignee")
    overview(patent_cpc_df, "patent_cpc")
    overview(cpc_dict, "cpc_dict")

    check_primary_key(patent_df, ["patent_id"], "patent")
    check_primary_key(
        patent_assignee_df, ["patent_id", "assignee"], "patent_assignee"
    )
    check_primary_key(
        patent_cpc_df, ["patent_id", "cpc_group"], "patent_cpc"
    )
    
    return patent_df, patent_assignee_df, patent_cpc_df, cpc_dict


if __name__ == "__main__":

    engine, patent_df, patent_assignee_df, patent_cpc_df, cpc_dict = load_tables()
    run(patent_df, patent_assignee_df, patent_cpc_df, cpc_dict)
    engine.dispose()
    