import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql

from src.eda.structure_check import load_tables

def load_all():
    
    engine, patent_df, patent_assignee_df, patent_cpc_df, cpc_dict = load_tables()

    dirty_all = pd.read_sql("SELECT * FROM dirty.dirty_all", engine)
    dirty_patent_cpc = pd.read_sql("SELECT * FROM dirty.dirty_patent_cpc", engine)
    dirty_cpc_dict = pd.read_sql("SELECT * FROM dirty.dirty_cpc_dict", engine)

    return (
        engine, 
        patent_df, 
        patent_assignee_df, 
        patent_cpc_df, 
        cpc_dict,
        dirty_all,
        dirty_patent_cpc,
        dirty_cpc_dict,
    )


# ============================================================
# 检查 1：patent 脏数据分布
# ============================================================
def check_patent_dirty(patent_df, dirty_all):
    print("===== 检查 1：patent 脏数据分布 =====")
    print(f"清洗后 patent 行数: {len(patent_df)}")
    print(f"脏数据行数: {len(dirty_all)}")
    print(f"脏数据占比: {len(dirty_all) / (len(patent_df) + len(dirty_all)):.4f}")

    print("\n-- bad_column 分布 --")
    print(dirty_all["bad_column"].value_counts())

    print("\n-- bad_type 分布 --")
    print(dirty_all["bad_type"].value_counts())

    print("\n-- source 分布 --")
    print(dirty_all["source"].value_counts())

    print("\n-- grant_year 分布 --")
    print(dirty_all["grant_year"].value_counts().sort_index())
    print()


# ============================================================
# 检查 2：patent 剔行后，年份是否失真
# ============================================================
def check_year_loss(patent_df, dirty_all):
    print("===== 检查 2：patent 剔行后年份失真 =====")
    clean = patent_df["grant_year"].value_counts().sort_index()
    dirty = dirty_all["grant_year"].value_counts().sort_index()
    total = clean.add(dirty, fill_value=0).sort_index()

    df = pd.DataFrame({
        "clean": clean,
        "dirty": dirty,
        "total": total,
        "dirty_ratio": (dirty / total).round(4),
    })
    print(df)
    print()


# ============================================================
# 检查 3：patent_assignee 剔除比例
# ============================================================
def check_assignee_loss(patent_df, patent_assignee_df, dirty_all):
    print("===== 检查 3：patent_assignee 剔除比例 =====")
    dirty_assignee = dirty_all[dirty_all["bad_column"] == "assignee"]

    print(f"patent 行数: {len(patent_df)}")
    print(f"patent_assignee 行数: {len(patent_assignee_df)}")
    print(f"assignee 脏数据行数: {len(dirty_assignee)}")
    print(f"assignee 缺失占 patent 比例: {len(dirty_assignee) / len(patent_df):.4f}")

    print("\n-- assignee 缺失的年份分布 --")
    print(dirty_assignee["grant_year"].value_counts().sort_index())
    print()


# ============================================================
# 检查 4：patent_cpc 和 patent 的对应
# ============================================================
def check_cpc_coverage(patent_df, patent_cpc_df):
    print("===== 检查 4：patent_cpc 覆盖率 =====")
    patent_ids = set(patent_df["patent_id"].astype(str))
    cpc_ids = set(patent_cpc_df["patent_id"].astype(str))

    only_patent = patent_ids - cpc_ids
    only_cpc = cpc_ids - patent_ids

    print(f"patent 专利数: {len(patent_ids)}")
    print(f"patent_cpc 专利数: {len(cpc_ids)}")
    print(f"只在 patent 中: {len(only_patent)}")
    print(f"只在 patent_cpc 中: {len(only_cpc)}")

    if only_patent:
        no_cpc_df = patent_df[
            patent_df["patent_number"].astype(str).isin(only_patent)
        ]
        print("\n-- 无 CPC 的专利年份分布 --")
        print(no_cpc_df["grant_year"].value_counts().sort_index())
    print()


# ============================================================
# 检查 5：CPC join 未匹配部分
# ============================================================
def check_cpc_join(patent_cpc_df, cpc_dict):
    print("===== 检查 5：CPC join 未匹配 =====")
    for col in ["cpc_subclass", "cpc_group", "cpc_class"]:
        if col in patent_cpc_df.columns and col in cpc_dict.columns:
            matched = patent_cpc_df[col].isin(cpc_dict[col])
            unmatched = patent_cpc_df.loc[~matched, col].value_counts()
            print(f"\n-- {col} 未匹配 --")
            print(f"未匹配行数: {(~matched).sum()}")
            print(unmatched.head(20))
    print()


# ============================================================
# 检查 6：时间字段一致性
# ============================================================
def check_time(patent_df):
    print("===== 检查 6：时间字段一致性 =====")
    bad = (patent_df["grant_year"] < patent_df["application_year"]).sum()
    print(f"grant_year < application_year: {bad}")

    lag = patent_df["grant_year"] - patent_df["application_year"]
    print("\n-- 审查周期分布 --")
    print(lag.describe())

    print("\n-- 审查周期 > 10 年的行数 --")
    print(f"{(lag > 10).sum()}")
    print()


# ============================================================
# 检查 7：patent_cpc 脏数据对技术分类的影响
# ============================================================
def check_patent_cpc_dirty(patent_cpc_df, dirty_patent_cpc):
    print("===== 检查 7：patent_cpc 脏数据影响 =====")
    print(f"清洗后 patent_cpc 行数: {len(patent_cpc_df)}")
    print(f"脏数据行数: {len(dirty_patent_cpc)}")

    print("\n-- bad_column 分布 --")
    print(dirty_patent_cpc["bad_column"].value_counts())

    print("\n-- bad_type 分布 --")
    print(dirty_patent_cpc["bad_type"].value_counts())

    dirty_ids = set(dirty_patent_cpc["patent_id"].astype(str))
    clean_ids = set(patent_cpc_df["patent_id"].astype(str))

    only_dirty = dirty_ids - clean_ids
    print(f"\n脏数据涉及专利数: {len(dirty_ids)}")
    print(f"其中清洗后完全无 CPC 的专利数: {len(only_dirty)}")
    print()


# ============================================================
# 检查 8：cpc_dict 脏数据
# ============================================================
def check_cpc_dict_dirty(cpc_dict, dirty_cpc_dict):
    print("===== 检查 8：cpc_dict 脏数据影响 =====")
    print(f"清洗后 cpc_dict 行数: {len(cpc_dict)}")
    print(f"脏数据行数: {len(dirty_cpc_dict)}")

    print("\n-- bad_column 分布 --")
    print(dirty_cpc_dict["bad_column"].value_counts())

    print("\n-- bad_type 分布 --")
    print(dirty_cpc_dict["bad_type"].value_counts())

    print("\n-- 涉及 cpc_subclass --")
    print(dirty_cpc_dict["cpc_subclass"].value_counts())
    print()


# ============================================================
# 检查 9：join 未匹配与 cpc_dict 脏数据的关系
# ============================================================
def check_unmatched_vs_dirty(patent_cpc_df, cpc_dict, dirty_cpc_dict):
    print("===== 检查 9：join 未匹配 vs cpc_dict 脏数据 =====")
    matched = patent_cpc_df["cpc_subclass"].isin(cpc_dict["cpc_subclass"])
    unmatched_subclass = set(
        patent_cpc_df.loc[~matched, "cpc_subclass"].dropna().astype(str)
    )
    dirty_subclass = set(dirty_cpc_dict["cpc_subclass"].dropna().astype(str))

    print(f"未匹配 subclass 数: {len(unmatched_subclass)}")
    print(f"脏数据 subclass 数: {len(dirty_subclass)}")
    print(f"交集: {unmatched_subclass & dirty_subclass}")
    print(f"未匹配但不在脏数据里的: {unmatched_subclass - dirty_subclass}")
    print()


# ============================================================
# 主程序
# ============================================================
def run():

    check_patent_dirty(patent_df, dirty_all)
    check_year_loss(patent_df, dirty_all)
    check_assignee_loss(patent_df, patent_assignee_df, dirty_all)
    check_cpc_coverage(patent_df, patent_cpc_df)
    check_cpc_join(patent_cpc_df, cpc_dict)
    check_time(patent_df)
    check_patent_cpc_dirty(patent_cpc_df, dirty_patent_cpc)
    check_cpc_dict_dirty(cpc_dict, dirty_cpc_dict)
    check_unmatched_vs_dirty(patent_cpc_df, cpc_dict, dirty_cpc_dict)
    


if __name__ == "__main__":

    (
        engine, 
        patent_df, 
        patent_assignee_df, 
        patent_cpc_df, 
        cpc_dict,
        dirty_all,
        dirty_patent_cpc,
        dirty_cpc_dict,
    ) = load_all()
    
    run()

    engine.dispose()