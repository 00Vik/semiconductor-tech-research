import sys
import numpy as np
import pandas as pd
from pathlib import Path
from pandas.api.types import is_object_dtype, is_categorical_dtype

# ---------- 定位项目根目录，导入 config ----------
root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import (
    KEEP_COLUMNS,
    NUMERIC_COLUMNS,
    STRING_COLUMNS,
    CODE_COLUMNS,
    FAKE_MISSING,
    ASSIGNEE_COLUMN,
    PATENT_DUP_COLUMNS,
    PATENT_ASSIGNEE_DUP_COLUMNS,
    PATENT_CPC_COLUMNS,
    CPC_DICT_COLUMNS,
    schema_clean,
    schema_dirty,
    )

from db import get_engine, save_to_sql

# ============================================================
# 合并 + 选列
# ============================================================
def select_columns(df, keep_columns = KEEP_COLUMNS):
    
    missing = [c for c in keep_columns if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列：{missing}")

    df = df[keep_columns].copy()
    print(f"筛选完成：{len(df)} 行, {df.shape[1]} 列")
    return df

# ============================================================
# 全列空值检查
# ============================================================
def check_empty_columns(df, columns):
    """检查指定列是否整列为空，有空列则抛错中断。"""

    empty_cols = []

    for col in columns:
        if col not in df.columns:
            continue
        # 整列全是 NaN / 空串
        if df[col].isna().all() or(df[col] == '').all():
            empty_cols.append(col)

    if empty_cols:
        raise ValueError(
            f"以下列整列为空，无法继续：{empty_cols}"
        )

# ============================================================
# 提取脏数字行
# ============================================================

def extract_dirty_numeric(df, columns=NUMERIC_COLUMNS):
    """
    找出数字列里"空值、无法转成数字、负值"的行。

    返回:
        dirty_df   : 脏数据明细（每行标明哪列、原值是什么）
        dirty_mask : 布尔 Series，True 表示该行是脏的
    """

    dirty_mask = pd.Series(False, index=df.index)
    records = []

    for col in columns:

        s = df[col]
        converted = pd.to_numeric(s, errors="coerce")

        # 三类脏数据类型
        is_missing = s.isna()                          # 原本就空
        is_non_numeric = s.notna() & converted.isna()  # 有值但转不了
        is_negative = converted.notna() & (converted < 0)  # 负值

        bad_mask = is_missing | is_non_numeric | is_negative


        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            bad_df["bad_type"] = np.select(
                [
                    is_negative.loc[bad_mask],
                    is_non_numeric.loc[bad_mask],
                    is_missing.loc[bad_mask],
                ],
                [
                    "negative",
                    "non_numeric",
                    "is_missing",
                ],
                default="unknown",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 提取脏代码行
# ============================================================
def extract_dirty_code(df, columns=CODE_COLUMNS):

    dirty_mask = pd.Series(False, index=df.index)
    records = []

    for col in columns:

        s = df[col]

        # 统一转字符串、去缺失值、转小写
        s_str = s.astype(str)
        s_stripped = s_str.str.strip()
        s_lowered = s_stripped.str.lower()


        # 各类脏数据
        is_missing = s.isna()                                                    # 缺失值标记
        is_fake_missing = s.notna() & s_lowered.isin(FAKE_MISSING)               # 伪缺失标记
        has_dot_zero = s_stripped.str.contains(r"\.0$", regex=True, na=False)    # float格式标记


        bad_mask = (
            is_missing
            | is_fake_missing
            | has_dot_zero
        )

        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            bad_df["bad_type"] = np.select(
                [
                    is_missing.loc[bad_mask],
                    is_fake_missing.loc[bad_mask],
                    has_dot_zero.loc[bad_mask],
                ],
                [
                    "is_missing",
                    "fake_missing",
                    "has_dot_zero",
                ],
                default="unknown",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 提取脏字符串行
# ============================================================

def extract_dirty_string(df, columns=STRING_COLUMNS):
    """
    处理字符串前后多余空白。
    找出字符串列里"空字符串、常见伪缺失标记、常见伪缺失标记"的行

    返回:
        dirty_df   : 脏数据明细（每行标明哪列、原值是什么）
        dirty_mask : 布尔 Series，True 表示该行是脏的
    """

    dirty_mask = pd.Series(False, index=df.index)
    records = []


    for col in columns:

        s = df[col]

        # 只处理字符串/object/category 列
        if not (is_object_dtype(s)
            or isinstance(s.dtype, pd.StringDtype)
            or is_categorical_dtype(s)):
            continue

        # 统一转字符串、去缺失值、转小写
        s_str = s.astype("string")                     
        s_stripped = s_str.str.strip()
        s_lowered = s_stripped.str.lower()

        # 缺失值标记
        is_missing = s.isna()
        
        # 伪缺失标记
        is_fake_missing = s.notna() & s_lowered.isin(FAKE_MISSING)

        bad_mask = is_missing | is_fake_missing

        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            # 标记脏数据类型
            bad_df["bad_type"] = np.where(
                is_missing.loc[bad_mask],
                "is_missing",
                "fake_missing",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 去重
# ============================================================
def deduplicate (df, columns):

    subset_columns = [
        col for col in columns
        if col in df.columns
    ]

    if subset_columns:
        df = df.drop_duplicates(
            subset=subset_columns
        )

    return df 

    
# ============================================================
# 生成 df_patent（专利粒度）
# ============================================================
def build_patent_table(df: pd.DataFrame, duplicate_columns = PATENT_DUP_COLUMNS):
    """
    - 按 patent_number 去重
    - 保留空 assignee 的专利
    """
    df = deduplicate(df, duplicate_columns)

    print(f"patent_df：{len(df)} 行")
    return df


# ============================================================
# 生成 df_patent_assignee（专利 × 企业）
# ============================================================
def build_patent_assignee_table(df: pd.DataFrame, remove_column = ASSIGNEE_COLUMN, duplicate_columns = PATENT_ASSIGNEE_DUP_COLUMNS):
    """
    - 剔除 assignee 为空
    - 不去重
    """
    assignee_dirty_df, assignee_dirty_mask = extract_dirty_string(df, remove_column)
    # 标记脏数据生成源
    assignee_dirty_df["source"] = "assignee"

    df = df[~assignee_dirty_mask].copy()
    df = deduplicate(df, duplicate_columns)

    print(f"patent_assignee_df：{len(df)} 行")
    return assignee_dirty_df, df

# ============================================================
# 基础清洗程序
# ============================================================
def basic_clean(df: pd.DataFrame):

    check_empty_columns(df,KEEP_COLUMNS)

    # 代码挑脏
    dirty_code_df, dirty_code_mask = extract_dirty_code(df)
    # 数字挑脏
    dirty_num_df, dirty_num_mask = extract_dirty_numeric(df)
    # 字符串挑脏
    dirty_str_df, dirty_str_mask = extract_dirty_string(df)
    # 生成脏数据总表
    basic_dirty_df = pd.concat(
        [dirty_num_df, dirty_str_df, dirty_code_df],
        ignore_index=True,
    )

    # 标记脏数据生成源
    basic_dirty_df["source"] = "basic"

    # 三类 mask 合并，一次性剔行
    dirty_mask = dirty_code_mask | dirty_num_mask | dirty_str_mask
    df = df[~dirty_mask].copy()

    return basic_dirty_df, df

# ============================================================
# 最终清洗程序
# ============================================================
def final_clean(df):

    engine = get_engine()

    df = df.copy()

    # 清洗
    basic_dirty_df, df = basic_clean(df)

    # 生成专利粒度表和企业布局表
    patent_df = build_patent_table(df)
    assignee_dirty_df, patent_assignee_df = build_patent_assignee_table(df)

    dirty_all_df = pd.concat([assignee_dirty_df, basic_dirty_df],ignore_index=True)

    save_to_sql(patent_df, "patent", engine, schema_clean)
    save_to_sql(patent_assignee_df, "patent_assignee", engine, schema_clean)
    save_to_sql(dirty_all_df, "dirty_all", engine, schema_dirty)
    print(f"dirty_all_df：{len(dirty_all_df)} 行")

# ============================================================
# 执行
# ============================================================
if __name__ == "__main__":

    engine = get_engine()

    raw_patent_df = pd.read_sql("SELECT * FROM raw.raw_patent", engine)
    # 全cpc表（patent_id 和技术分类）
    raw_patent_cpc_df = pd.read_sql("SELECT * FROM raw.bridge_patent_technology", engine)
    raw_cpc_dict = pd.read_sql("SELECT * FROM raw.raw_cpc_dict", engine)
    
    raw_patent_df=select_columns(raw_patent_df)

    print(f"开始清洗......")
    final_clean(raw_patent_df)
    print(f"patent.parquet清洗完成")
    print(f"patent_assignee.parquet清洗完成")

    dirty_patent_cpc_df, dirty_patent_cpc_mask = extract_dirty_string(raw_patent_cpc_df, PATENT_CPC_COLUMNS)
    patent_cpc_df = raw_patent_cpc_df[~dirty_patent_cpc_mask].copy()
    save_to_sql(patent_cpc_df, "patent_cpc", engine, schema_clean)
    save_to_sql(dirty_patent_cpc_df, "dirty_patent_cpc", engine, schema_dirty)
    print(f"patent_cpc_df：{len(patent_cpc_df)} 行")
    print(f"dirty_patent_cpc_df：{len(dirty_patent_cpc_df)} 行")
    print(f"patent_cpc.parquet清洗完成")

    dirty_cpc_dict, dirty_cpc_dict_mask = extract_dirty_string(raw_cpc_dict, CPC_DICT_COLUMNS)
    cpc_dict = raw_cpc_dict[~dirty_cpc_dict_mask].copy()
    save_to_sql(cpc_dict, "cpc_dict", engine, schema_clean)
    save_to_sql(dirty_cpc_dict, "dirty_cpc_dict", engine, schema_dirty)
    print(f"cpc_dict：{len(cpc_dict)} 行")
    print(f"dirty_cpc_dict:{len(dirty_cpc_dict)} 行")
    print(f"cpc_dict.parquet清洗完成")

    engine.dispose()
