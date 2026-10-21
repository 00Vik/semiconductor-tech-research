import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql
from config import (
    MIN_PATENT,
    schema_features,
)


# ============================================================
# 工具
# ============================================================
def patent_count(df, key_col):
    """按 patent_id × key_col 去重后计数。"""
    return (
        df.drop_duplicates(["patent_id", key_col])[key_col]
        .value_counts()
    )


def is_indexing(main_group: str) -> bool:
    """子类后接 4 位数字且首位为 2，视为 2000 系列索引码。"""
    suffix = main_group[4:]
    return len(suffix) == 4 and suffix.isdigit() and suffix[0] == "2"


# ============================================================
# 母级：subclass
# ============================================================
def build_subclass_label(patent_cpc_df, cpc_dict):
    counts = patent_count(patent_cpc_df, "cpc_subclass")
    keep = counts[counts > MIN_PATENT].index

    title = (
        cpc_dict[["cpc_subclass", "cpc_subclass_title"]]
        .drop_duplicates("cpc_subclass")
        .set_index("cpc_subclass")["cpc_subclass_title"]
    )

    records = [
        {"cpc_code": code, "tech_label": title.get(code, "")}
        for code in keep
    ]
    return pd.DataFrame(records)


# ============================================================
# H01L 主组
# ============================================================
def build_h01l_main_group_label(patent_cpc_df, cpc_dict):
    h01l = patent_cpc_df[patent_cpc_df["cpc_subclass"] == "H01L"].copy()
    h01l["cpc_main_group"] = h01l["cpc_group"].str.split("/").str[0]

    counts = patent_count(h01l, "cpc_main_group")
    keep = counts[counts > MIN_PATENT].index

    main_group_00 = {g + "/00" for g in keep}
    title = (
        cpc_dict[cpc_dict["cpc_group"].isin(main_group_00)]
        .drop_duplicates("cpc_group")
        .set_index("cpc_group")["cpc_group_title"]
    )

    records = []
    for code in keep:
        records.append({
            "cpc_code": code,
            "tech_label": title.get(code + "/00", ""),
            "note": "indexing" if is_indexing(code) else "",
        })
    return pd.DataFrame(records)


# ============================================================
# H10K group
# ============================================================
def build_h10k_group_label(patent_cpc_df, cpc_dict):
    title = (
        cpc_dict[["cpc_group", "cpc_group_title"]]
        .drop_duplicates("cpc_group")
        .set_index("cpc_group")["cpc_group_title"]
    )

    h10k = patent_cpc_df[patent_cpc_df["cpc_subclass"] == "H10K"]
    counts = patent_count(h10k, "cpc_group")
    keep = counts[counts > MIN_PATENT].index

    records = [
        {"cpc_code": code, "tech_label": title.get(code, ""), "note": ""}
        for code in keep
    ]
    return pd.DataFrame(records)


# ============================================================
# H05K group
# ============================================================
def build_h05k_group_label(patent_cpc_df, cpc_dict):
    title = (
        cpc_dict[["cpc_group", "cpc_group_title"]]
        .drop_duplicates("cpc_group")
        .set_index("cpc_group")["cpc_group_title"]
    )

    h05k = patent_cpc_df[patent_cpc_df["cpc_subclass"] == "H05K"]
    counts = patent_count(h05k, "cpc_group")

    records = []
    if not counts.empty:
        code = counts.index[0]
        records.append({
            "cpc_code": code,
            "tech_label": title.get(code, ""),
            "note": "",
        })
    return pd.DataFrame(records)


# ============================================================
# 输出空值明细
# ============================================================
def print_empty_labels(name, df):
    empty = df[df["tech_label"] == ""]
    print(f"\n{name} 空值行数：{len(empty)}")
    if not empty.empty:
        print(empty.to_string(index=False))


# ============================================================
# 主程序
# ============================================================
def run():
    engine = get_engine()
    print("开始读取 patent_cpc ...")
    patent_cpc_df = pd.read_sql("SELECT * FROM clean.patent_cpc", engine)
    print(f"patent_cpc 读取完成：{len(patent_cpc_df)} 行")

    print("开始读取 cpc_dict ...")
    cpc_dict = pd.read_sql("SELECT * FROM clean.cpc_dict", engine)
    print(f"cpc_dict 读取完成：{len(cpc_dict)} 行")

    subclass_label = build_subclass_label(patent_cpc_df, cpc_dict)
    h01l_label = build_h01l_main_group_label(patent_cpc_df, cpc_dict)
    h10k_label = build_h10k_group_label(patent_cpc_df, cpc_dict)
    h05k_label = build_h05k_group_label(patent_cpc_df, cpc_dict)

    save_to_sql(subclass_label, "subclass_label", engine, schema_features)
    save_to_sql(h01l_label, "h01l_label", engine, schema_features)
    save_to_sql(h10k_label, "h10k_label", engine, schema_features)
    save_to_sql(h05k_label, "h05k_label", engine, schema_features)

    print_empty_labels("subclass", subclass_label)
    print_empty_labels("H01L main_group", h01l_label)
    print_empty_labels("H10K group", h10k_label)
    print_empty_labels("H05K group", h05k_label)

    return engine, subclass_label, h01l_label, h10k_label, h05k_label


if __name__ == "__main__":
    engine, _, _, _, _ = run()
    engine.dispose()