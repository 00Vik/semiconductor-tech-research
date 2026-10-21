import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# ============================================================
# 环境与配置加载
# ============================================================
root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql
from config import schema_trends

def query(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ============================================================
# 1. 年度专利量总表 (基于专利主表去重)
# ============================================================
SQL_YEAR_TOTAL = """
WITH base AS (
    SELECT
        grant_year,
        COUNT(DISTINCT patent_id) AS patent_count
    FROM clean.patent
    GROUP BY grant_year
)
SELECT
    grant_year,
    patent_count,
    LAG(patent_count) OVER (ORDER BY grant_year) AS prev_count,
    ROUND((patent_count - LAG(patent_count) OVER (ORDER BY grant_year)) * 1.0 / LAG(patent_count) OVER (ORDER BY grant_year), 4) AS yoy
FROM base
ORDER BY grant_year
"""


# ============================================================
# 2. subclass 年度趋势 (基于全 CPC 表，按专利去重)
# 逻辑：使用全 CPC 表确保副分类被统计，按专利去重避免一专利多分类重复计数
# ============================================================
SQL_SUBCLASS_TREND = """
WITH labeled AS (
    SELECT DISTINCT
        p.grant_year,
        p.patent_id,
        CASE
            WHEN c.cpc_subclass IN (SELECT cpc_code FROM features.subclass_label)
                THEN c.cpc_subclass
            ELSE 'Other'
        END AS cpc_subclass
    FROM clean.patent p
    JOIN clean.patent_cpc c ON p.patent_id = c.patent_id
),
base AS (
    SELECT
        grant_year,
        cpc_subclass,
        COUNT(patent_id) AS patent_count
    FROM labeled
    GROUP BY grant_year, cpc_subclass
),
calc AS (
    SELECT
        grant_year,
        cpc_subclass,
        patent_count,
        LAG(patent_count) OVER (PARTITION BY cpc_subclass ORDER BY grant_year) AS prev_count,
        SUM(patent_count) OVER (PARTITION BY grant_year) AS year_total
    FROM base
)
SELECT
    c.grant_year,
    c.cpc_subclass,
    COALESCE(t.tech_label, 'Other') AS tech_label,
    c.patent_count,
    ROUND(c.patent_count * 1.0 / c.year_total, 4) AS share,
    c.prev_count,
    ROUND((c.patent_count - c.prev_count) * 1.0 / c.prev_count, 4) AS yoy
FROM calc c
LEFT JOIN features.subclass_label t ON c.cpc_subclass = t.cpc_code
ORDER BY c.cpc_subclass, c.grant_year
"""


# ============================================================
# 3. H01L 主组年度趋势 (基于全 CPC 表，按专利去重)
# 逻辑：提取 H01L 下所有主组，全表扫描并去重
# ============================================================
SQL_H01L_TREND = """
WITH labeled AS (
    SELECT DISTINCT
        p.grant_year,
        p.patent_id,
        SPLIT_PART(c.cpc_group, '/', 1) AS cpc_code
    FROM clean.patent p
    JOIN clean.patent_cpc c ON p.patent_id = c.patent_id
    WHERE c.cpc_subclass = 'H01L'
),
base AS (
    SELECT
        grant_year,
        cpc_code,
        COUNT(patent_id) AS patent_count
    FROM labeled
    GROUP BY grant_year, cpc_code
),
calc AS (
    SELECT
        grant_year,
        cpc_code,
        patent_count,
        LAG(patent_count) OVER (PARTITION BY cpc_code ORDER BY grant_year) AS prev_count,
        SUM(patent_count) OVER (PARTITION BY grant_year) AS year_total
    FROM base
)
SELECT
    c.grant_year,
    c.cpc_code,
    t.tech_label,
    t.note,
    c.patent_count,
    ROUND(c.patent_count * 1.0 / c.year_total, 4) AS share,
    c.prev_count,
    ROUND((c.patent_count - c.prev_count) * 1.0 / c.prev_count, 4) AS yoy
FROM calc c
LEFT JOIN features.h01l_label t ON c.cpc_code = t.cpc_code
ORDER BY c.cpc_code, c.grant_year
"""


# ============================================================
# 4. H10K group 年度趋势 (基于全 CPC 表，按专利去重)
# 逻辑：针对细分 group，全表扫描并去重
# ============================================================
SQL_H10K_TREND = """
WITH labeled AS (
    SELECT DISTINCT
        p.grant_year,
        p.patent_id,
        c.cpc_group AS cpc_code
    FROM clean.patent p
    JOIN clean.patent_cpc c ON p.patent_id = c.patent_id
    WHERE c.cpc_group IN (SELECT cpc_code FROM features.h10k_label)
),
base AS (
    SELECT
        grant_year,
        cpc_code,
        COUNT(patent_id) AS patent_count
    FROM labeled
    GROUP BY grant_year, cpc_code
)
SELECT
    b.grant_year,
    b.cpc_code,
    t.tech_label,
    b.patent_count,
    LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year) AS prev_count,
    ROUND((b.patent_count - LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year)) * 1.0 / LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year), 4) AS yoy
FROM base b
LEFT JOIN features.h10k_label t ON b.cpc_code = t.cpc_code
ORDER BY b.cpc_code, b.grant_year
"""


# ============================================================
# 5. H05K group 年度趋势 (基于全 CPC 表，按专利去重)
# 逻辑：针对细分 group，全表扫描并去重
# ============================================================
SQL_H05K_TREND = """
WITH labeled AS (
    SELECT DISTINCT
        p.grant_year,
        p.patent_id,
        c.cpc_group AS cpc_code
    FROM clean.patent p
    JOIN clean.patent_cpc c ON p.patent_id = c.patent_id
    WHERE c.cpc_group IN (SELECT cpc_code FROM features.h05k_label)
),
base AS (
    SELECT
        grant_year,
        cpc_code,
        COUNT(patent_id) AS patent_count
    FROM labeled
    GROUP BY grant_year, cpc_code
)
SELECT
    b.grant_year,
    b.cpc_code,
    t.tech_label,
    b.patent_count,
    LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year) AS prev_count,
    ROUND((b.patent_count - LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year)) * 1.0 / LAG(b.patent_count) OVER (PARTITION BY b.cpc_code ORDER BY b.grant_year), 4) AS yoy
FROM base b
LEFT JOIN features.h05k_label t ON b.cpc_code = t.cpc_code
ORDER BY b.cpc_code, b.grant_year
"""


# ============================================================
# 主程序
# ============================================================
def run():
    engine = get_engine()

    print("开始执行趋势分析 SQL ...")

    year_total = query(engine, SQL_YEAR_TOTAL)
    subclass_trend = query(engine, SQL_SUBCLASS_TREND)
    h01l_trend = query(engine, SQL_H01L_TREND)
    h10k_trend = query(engine, SQL_H10K_TREND)
    h05k_trend = query(engine, SQL_H05K_TREND)

    save_to_sql(year_total, "year_total", engine, schema_trends)
    save_to_sql(subclass_trend, "subclass_trend", engine, schema_trends)
    save_to_sql(h01l_trend, "h01l_main_group_trend", engine, schema_trends)
    save_to_sql(h10k_trend, "h10k_group_trend", engine, schema_trends)
    save_to_sql(h05k_trend, "h05k_group_trend", engine, schema_trends)

    return engine, year_total, subclass_trend, h01l_trend, h10k_trend, h05k_trend


if __name__ == "__main__":
    engine, _, _, _, _, _ = run()
    engine.dispose()