import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine, save_to_sql
from config import schema_trends  # 统一存放在 trends schema 下


def query(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ============================================================
# 1. 企业 × 技术矩阵 (Top 100 企业，基于全 CPC)
# ============================================================
SQL_COMPANY_TECH_MATRIX = """
WITH top_companies AS (
    SELECT 
        assignee_id, 
        disambig_assignee_organization AS company_name, 
        COUNT(DISTINCT patent_id) AS total_patents
    FROM features.patent_assignee_normalized
    GROUP BY assignee_id, disambig_assignee_organization
    ORDER BY total_patents DESC
    LIMIT 100
),
company_tech AS (
    SELECT
        pa.assignee_id,
        pc.cpc_subclass,
        sl.tech_label,
        COUNT(DISTINCT pa.patent_id) AS patent_count
    FROM features.patent_assignee_normalized pa
    JOIN top_companies tc ON pa.assignee_id = tc.assignee_id
    JOIN clean.patent_cpc pc ON pa.patent_id = pc.patent_id
    JOIN features.subclass_label sl ON pc.cpc_subclass = sl.cpc_code
    GROUP BY pa.assignee_id, pc.cpc_subclass, sl.tech_label
)
SELECT
    ct.assignee_id,
    tc.company_name,
    ct.cpc_subclass,
    ct.tech_label,
    ct.patent_count,
    ROUND(ct.patent_count * 1.0 / tc.total_patents, 4) AS tech_share
FROM company_tech ct
JOIN top_companies tc ON ct.assignee_id = tc.assignee_id
ORDER BY ct.assignee_id, ct.patent_count DESC
"""


# ============================================================
# 2. 企业技术集中度 (HHI)
# ============================================================
SQL_COMPANY_CONCENTRATION = """
WITH matrix AS (
    -- 复用上面计算矩阵的底层逻辑
    SELECT
        pa.assignee_id,
        COUNT(DISTINCT pa.patent_id) AS total_patents,
        pc.cpc_subclass,
        COUNT(DISTINCT pa.patent_id) AS subclass_patents
    FROM features.patent_assignee_normalized pa
    JOIN clean.patent_cpc pc ON pa.patent_id = pc.patent_id
    JOIN features.subclass_label sl ON pc.cpc_subclass = sl.cpc_code
    GROUP BY pa.assignee_id, pc.cpc_subclass
),
shares AS (
    SELECT
        assignee_id,
        total_patents,
        subclass_patents * 1.0 / total_patents AS share
    FROM matrix
),
top_companies AS (
    SELECT assignee_id, disambig_assignee_organization AS company_name
    FROM features.patent_assignee_normalized
    GROUP BY assignee_id, disambig_assignee_organization
    ORDER BY COUNT(DISTINCT patent_id) DESC
    LIMIT 100
)
SELECT
    s.assignee_id,
    tc.company_name,
    MAX(s.total_patents) AS total_patents,
    ROUND(SUM(s.share * s.share), 4) AS hhi
FROM shares s
JOIN top_companies tc ON s.assignee_id = tc.assignee_id
GROUP BY s.assignee_id, tc.company_name
ORDER BY hhi DESC
"""


# ============================================================
# 3. 年度活跃企业数与新进入者
# ============================================================
SQL_COMPANY_ACTIVITY = """
WITH first_entry AS (
    SELECT
        pa.assignee_id,
        MIN(p.grant_year) AS first_year
    FROM features.patent_assignee_normalized pa
    JOIN clean.patent p ON pa.patent_id = p.patent_id
    GROUP BY pa.assignee_id
),
yearly_active AS (
    SELECT
        p.grant_year,
        COUNT(DISTINCT pa.assignee_id) AS active_companies
    FROM features.patent_assignee_normalized pa
    JOIN clean.patent p ON pa.patent_id = p.patent_id
    GROUP BY p.grant_year
)
SELECT
    ya.grant_year,
    ya.active_companies,
    COUNT(DISTINCT fe.assignee_id) AS new_entrants
FROM yearly_active ya
LEFT JOIN first_entry fe ON ya.grant_year = fe.first_year
GROUP BY ya.grant_year, ya.active_companies
ORDER BY ya.grant_year
"""


# ============================================================
# 主程序
# ============================================================
def run():
    engine = get_engine()

    print("开始执行企业布局 SQL ...")

    company_tech_matrix = query(engine, SQL_COMPANY_TECH_MATRIX)
    company_concentration = query(engine, SQL_COMPANY_CONCENTRATION)
    company_activity = query(engine, SQL_COMPANY_ACTIVITY)

    save_to_sql(company_tech_matrix, "company_tech_matrix", engine, schema_trends)
    save_to_sql(company_concentration, "company_concentration", engine, schema_trends)
    save_to_sql(company_activity, "company_activity", engine, schema_trends)

    return engine, company_tech_matrix, company_concentration, company_activity


if __name__ == "__main__":
    engine, _, _, _ = run()
    engine.dispose()


