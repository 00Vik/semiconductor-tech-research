import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from config import DB_DIR, DB_PATH


def get_engine():
    """返回 DuckDB 数据库引擎，必要时建目录。"""
    return create_engine(f"duckdb:///{DB_PATH}")


def save_to_sql(df: pd.DataFrame, table_name: str, engine, schema: str = "main"):
    """写入 DuckDB 表，整表替换。table_name 支持 'schema.table' 写法。"""
    if "." in table_name:
        schema, table = table_name.split(".", 1)
    else:
        table = table_name

    with engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        # 1. 落表
        conn.connection.register("df_tmp", df)
        conn.exec_driver_sql(
            f'CREATE OR REPLACE TABLE "{schema}"."{table_name}" AS SELECT * FROM df_tmp'
        )
        conn.connection.unregister("df_tmp")
        print(f"Saved Table: {schema}.{table_name}  ({len(df)} 行)")

        # 2. 顺手建视图
        conn.exec_driver_sql(
            f'CREATE OR REPLACE VIEW "{schema}"."v_{table_name}" AS SELECT * FROM "{schema}"."{table_name}"'
        )

    print(f"Saved: {schema}.{table}  ({len(df)} 行)")