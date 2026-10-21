import sys
from pathlib import Path
import pandas as pd

# ---------- 定位项目根目录，导入 config ----------
root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import (
    ANNUALIZED_LOADED_PATH,
    G_PATENT_PATH,
    G_ABSTRACT_PATH,
    G_CPC_AT_ISSUE_PATH,
    G_CPC_TITLE_PATH,
    G_ASSIGNEE_DISAMBIGUATED_PATH,
    G_PATENT_COLUMNS,
    G_ABSTRACT_COLUMNS,
    G_CPC_AT_ISSUE_COLUMNS,
    EXTRA_KEY_COLUMN,
    SORT_COLUMN,
    PRIORITY_COLUMN,
    PRIORITY_VALUE,
    CHUNK_SIZE,
    G_ASSIGNEE_DISAMBIGUATED_COLUMNS,
    schema_raw,
    )

from db import get_engine, save_to_sql

# ============================================================
# 读取
# ============================================================
def load_chunks(inputdir: Path, select_cols, semi_ids: set, key_col=EXTRA_KEY_COLUMN):

    if select_cols is not None and key_col not in select_cols:
        raise ValueError(f"{inputdir} 的 select_cols 必须包含 {key_col}")
    
    usecols = list(select_cols.keys())
    dtype = dict(select_cols)

    semi_ids_str = {str(x) for x in semi_ids}

    """分块筛选读取"""
    chunks = []
    for chunk in pd.read_csv(
        inputdir,
        sep="\t",
        chunksize=CHUNK_SIZE,
        usecols = usecols,
        dtype=dtype,
    ):
        chunks.append(chunk[chunk[key_col].isin(semi_ids_str)])

    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    print(f"{inputdir}（筛选后）：{len(df)} 行")
    return df

# ============================================================
# 含优先值列的指定列排序
# ============================================================
def column_sort(df, sort_col=SORT_COLUMN, priority_col=PRIORITY_COLUMN, priority_value=PRIORITY_VALUE, key_col=EXTRA_KEY_COLUMN):

    inventional = df[df[priority_col] == priority_value]
    inventional = inventional.sort_values([key_col,sort_col])

    no_inventional = df[~df[key_col].isin(inventional[key_col])]
    no_inventional = no_inventional.sort_values([key_col,sort_col])

    cpc_main_df = pd.concat(
        [inventional, no_inventional.drop_duplicates(key_col)],
        ignore_index=True,
    )

    return cpc_main_df

# ============================================================
# 主程序
# ===========================================================
def load_all_path(semi_ids):

    # 专利描述相关补充列
    g_patent_df = load_chunks(G_PATENT_PATH, select_cols=G_PATENT_COLUMNS, semi_ids=semi_ids)
    g_abstract_df = load_chunks(G_ABSTRACT_PATH, select_cols=G_ABSTRACT_COLUMNS, semi_ids=semi_ids)
    g_cpc_at_issue_df = load_chunks(G_CPC_AT_ISSUE_PATH, select_cols=G_CPC_AT_ISSUE_COLUMNS, semi_ids=semi_ids)
    raw_cpc_dict = pd.read_csv(G_CPC_TITLE_PATH, sep="\t")
    main_cpc_df = column_sort(g_cpc_at_issue_df)
    all_cpc_df = g_cpc_at_issue_df.drop(columns=SORT_COLUMN)

    # 企业名归一化消歧补充列
    g_assignee_disambiguated_df = load_chunks(
        G_ASSIGNEE_DISAMBIGUATED_PATH,
        select_cols=G_ASSIGNEE_DISAMBIGUATED_COLUMNS,
        semi_ids=semi_ids,
    )

    return g_patent_df, g_abstract_df, raw_cpc_dict, main_cpc_df, all_cpc_df, g_assignee_disambiguated_df

# ============================================================
# 主程序
# ===========================================================
if __name__ == "__main__":

    engine = get_engine()

    raw_patent = pd.read_parquet(ANNUALIZED_LOADED_PATH)

    # 取所有半导体编号raw_
    semi_ids = set(raw_patent[EXTRA_KEY_COLUMN].dropna())

    g_patent_df, g_abstract_df, raw_cpc_dict, main_cpc_df, all_cpc_df, g_assignee_disambiguated_df = load_all_path(semi_ids)

    # ---- 合并进 patent ----
    raw_patent[EXTRA_KEY_COLUMN] = raw_patent[EXTRA_KEY_COLUMN].astype("string")
    raw_patent_df = raw_patent.merge(
        g_patent_df,
        on=EXTRA_KEY_COLUMN,
        how="left",
    )
    raw_patent_df = raw_patent_df.merge(
        g_abstract_df,
        on=EXTRA_KEY_COLUMN,
        how="left",
    )
    raw_patent_df = raw_patent_df.merge(
        main_cpc_df,
        on=EXTRA_KEY_COLUMN,
        how="left",
    )

    # --------- 落盘 ---------
    save_to_sql(raw_patent_df, "raw_patent", engine, schema_raw)
    save_to_sql(g_assignee_disambiguated_df, "bridge_patent_organization", engine, schema_raw)
    save_to_sql(all_cpc_df, "bridge_patent_technology", engine, schema_raw)
    save_to_sql(raw_cpc_dict, "raw_cpc_dict", engine, schema_raw)

    print("\n完成：")
    print(f"  raw_patent         {len(raw_patent_df)} 行, {raw_patent_df.shape[1]} 列")
    print(f"  bridge_patent_organization     {len(g_assignee_disambiguated_df)} 行, {g_assignee_disambiguated_df.shape[1]} 列")
    print(f"  bridge_patent_technology       {len(all_cpc_df)} 行, {all_cpc_df.shape[1]} 列")
    print(f"  raw_cpc_dict      {len(raw_cpc_dict)} 行, {raw_cpc_dict.shape[1]} 列")

    engine.dispose()