from pathlib import Path
import os

# ============================================================
# 项目路径
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


#data
DATA_DIR = BASE_DIR / "data"

## database
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "semiconductor.duckdb"

## raw
RAW_DIR = DATA_DIR / "raw"

ANNUALIZED_DIR = RAW_DIR / "annualized_data"
ANNUALIZED_LOADED_PATH = ANNUALIZED_DIR / "annualized_data.parquet"
G_PATENT_PATH = RAW_DIR / "g_patent.tsv" / "g_patent.tsv"
G_ABSTRACT_PATH = RAW_DIR / "g_patent_abstract.tsv" / "g_patent_abstract.tsv"
G_CPC_AT_ISSUE_PATH = RAW_DIR / "g_cpc_at_issue.tsv"  / "g_cpc_at_issue.tsv"
G_CPC_TITLE_PATH = RAW_DIR / "g_cpc_title.tsv" / "g_cpc_title.tsv"
G_ASSIGNEE_DISAMBIGUATED_PATH = RAW_DIR / "g_assignee_disambiguated.tsv" / "g_assignee_disambiguated.tsv"

## processed
PROCESSED_DIR = DATA_DIR / "processed"

# eda
EDA_REPORTS_DIR =BASE_DIR / "eda_reports"

# figures
FIGURES_DIR = BASE_DIR / "figures"

for directory in [RAW_DIR, PROCESSED_DIR, FIGURES_DIR, DB_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# db组名
schema_raw = "raw"
schema_clean = "clean"
schema_dirty = "dirty"
schema_features = "features"
schema_trends ="trends"
# ============================================================
# 研究对象
# ============================================================
SELECT_COLUMN = "first_wipo_field_title"
INDUSTRY = "Semiconductors"

# ============================================================
# 分块读取参数
# ============================================================
ANNUALIZED_KEY_COLUMN = "patent_number"
EXTRA_KEY_COLUMN = "patent_id"
CHUNK_SIZE = 500_000


# ============================================================
# 补充材料里提取的列
# ============================================================
G_PATENT_COLUMNS = {
    "patent_id": "string", 
    "patent_title": "string"
    }

G_ABSTRACT_COLUMNS = {
    "patent_id": "string", 
    "patent_abstract": "string"
    }

G_CPC_AT_ISSUE_COLUMNS = {
    "patent_id": "string",
    "cpc_sequence": "Int64",
    "cpc_section": "string",
    "cpc_class": "string",
    "cpc_subclass": "string",
    "cpc_group": "string",
    "cpc_type": "string",
    }

G_ASSIGNEE_DISAMBIGUATED_COLUMNS = {
    "patent_id": "string",
    "assignee_id": "string",
    "disambig_assignee_organization": "string",
}

#主 CPC 表排序参数（优先 primary，无则取 sequence 最小）
SORT_COLUMN ="cpc_sequence"
PRIORITY_COLUMN = "cpc_type"
PRIORITY_VALUE = "inventional"

# ============================================================
# 保留列
# ============================================================
KEEP_COLUMNS = [
    "patent_id",
    "application_number",
    "grant_year",
    "application_year",
    "year",
    "assignee",
    "assignee_sequence",
    "first_wipo_field_title",
    "first_wipo_sector_title",
    "cpc_sections",
    "n_cpc",
    "country",
    "team_size",
    "patent_title",
    "patent_abstract",
    "cpc_sequence",
    "cpc_section",
    "cpc_class",
    "cpc_subclass",
    "cpc_group",
    "cpc_type",
] 

# ============================================================
# patent清洗列分类
# ============================================================
# 数字列
NUMERIC_COLUMNS = [
    "application_number",
    "grant_year",
    "application_year",
    "n_cpc",
    "team_size",
    "cpc_sequence",
]

# 字符串列
STRING_COLUMNS = [
    "patent_id",
    "first_wipo_field_title",
    "first_wipo_sector_title",
    "cpc_sections",
    "patent_title",
    "patent_abstract",
    "cpc_section",
    "cpc_class",
    "cpc_subclass",
    "cpc_group",
    "cpc_type",
] 

# 标识符代码列
CODE_COLUMNS = []


# ============================================================
# patent_cpc清洗列分类
# ============================================================
PATENT_CPC_COLUMNS={
    "patent_id": "string",
    "cpc_section": "string",
    "cpc_class": "string",
    "cpc_subclass": "string",
    "cpc_group": "string",
    "cpc_type": "string",
}

# ============================================================
# cpc_ict清洗列分类
# ============================================================
CPC_DICT_COLUMNS={
    "cpc_subclass": "string",
    "cpc_subclass_title": "string",
    "cpc_group": "string",
    "cpc_group_title": "string",
    "cpc_class": "string",
    "cpc_class_title": "string",
    }


# 视为"伪缺失"的字符串（不区分大小写）
FAKE_MISSING = {
    "", "n/a", "na", "-", "--",
    "null", "none", "nan",
    "unknown", "#", "?",}

# 单独处理assignee
ASSIGNEE_COLUMN = ["assignee"]

# 去重列
PATENT_DUP_COLUMNS = ["patent_id"]
PATENT_ASSIGNEE_DUP_COLUMNS = ["patent_id", "assignee"]

# ============================================================
# 文本标签参数
# ============================================================
MIN_PATENT = 1000