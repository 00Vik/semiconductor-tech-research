import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text

root = Path(__file__).resolve()
while not (root / "config.py").exists() and root != root.parent:
    root = root.parent
sys.path.append(str(root))

from db import get_engine

from config import FIGURES_DIR


def query(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ============================================================
# 趋势分析图表
# ============================================================
def plot_year_trend(engine):
    """1. 年度专利总量与 YoY 增速双轴图"""
    df = query(engine, "SELECT * FROM trends.v_year_total")
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(df["grant_year"], df["patent_count"], color="steelblue", alpha=0.7, label="Patent Count")
    ax1.set_xlabel("Grant Year")
    ax1.set_ylabel("Patent Count", color="steelblue")
    
    ax2 = ax1.twinx()
    ax2.plot(df["grant_year"], df["yoy"], color="darkred", marker="o", label="YoY Growth")
    ax2.set_ylabel("YoY Growth", color="darkred")
    ax2.axhline(0, color="gray", linestyle="--", alpha=0.5)
    
    fig.suptitle("Annual Patent Count and YoY Growth")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "trend_year_total.png", dpi=150)
    plt.close(fig)


def plot_subclass_share(engine):
    """2. Top 8 技术方向（subclass）的份额演变堆叠面积图"""
    # 取总量前 8 的 subclass
    top8 = query(engine, """
        SELECT cpc_subclass, tech_label 
        FROM trends.v_subclass_trend 
        GROUP BY cpc_subclass, tech_label 
        ORDER BY SUM(patent_count) DESC LIMIT 8
    """)["cpc_subclass"].tolist()
    
    df = query(engine, f"""
        SELECT grant_year, tech_label, share 
        FROM trends.v_subclass_trend 
        WHERE cpc_subclass IN {tuple(top8)}
    """)
    
    pivot_df = df.pivot(index="grant_year", columns="tech_label", values="share").fillna(0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot_df.plot(kind="area", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("Top 8 Subclass Technology Share Evolution")
    ax.set_xlabel("Grant Year")
    ax.set_ylabel("Share")
    
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "trend_subclass_share.png", dpi=150)
    plt.close(fig)


def plot_h01l_main_group_trend(engine):
    """3. H01L 主组 Top 6 的年度专利量走势"""
    top6 = query(engine, """
        SELECT cpc_code FROM trends.v_h01l_trend 
        GROUP BY cpc_code ORDER BY SUM(patent_count) DESC LIMIT 6
    """)["cpc_code"].tolist()
    
    df = query(engine, f"""
        SELECT grant_year, cpc_code, tech_label, patent_count 
        FROM trends.v_h01l_trend 
        WHERE cpc_code IN {tuple(top6)}
    """)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    for label, group in df.groupby("cpc_code"):
        ax.plot(group["grant_year"], group["patent_count"], marker="o", label=group["tech_label"].iloc[0][:30] + "...")
        
    ax.set_title("H01L Main Group Trends (Top 6)")
    ax.set_xlabel("Grant Year")
    ax.set_ylabel("Patent Count")
    ax.legend()
    
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "trend_h01l_main_group.png", dpi=150)
    plt.close(fig)


# ============================================================
# 企业布局图表
# ============================================================
def plot_company_matrix(engine):
    """4. Top 15 企业 × Top 10 技术的布局矩阵热力图"""
    df = query(engine, """
        SELECT company_name, tech_label, patent_count 
        FROM trends.v_company_tech_matrix
        WHERE assignee_id IN (
            SELECT assignee_id FROM trends.v_company_tech_matrix 
            GROUP BY assignee_id ORDER BY SUM(patent_count) DESC LIMIT 15
        )
        AND tech_label IN (
            SELECT tech_label FROM trends.v_company_tech_matrix
            GROUP BY tech_label ORDER BY SUM(patent_count) DESC LIMIT 10
        )
    """)
    
    pivot_df = df.pivot(index="company_name", columns="tech_label", values="patent_count").fillna(0)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    im = ax.imshow(pivot_df.values, cmap="YlOrRd", aspect="auto")
    
    ax.set_xticks(range(len(pivot_df.columns)))
    ax.set_xticklabels([c[:15] + "..." for c in pivot_df.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot_df.index)))
    ax.set_yticklabels(pivot_df.index)
    ax.set_title("Company x Technology Matrix (Top 15 x Top 10)")
    fig.colorbar(im, ax=ax, label="Patent Count")
    
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "company_tech_matrix.png", dpi=150)
    plt.close(fig)


def plot_company_concentration(engine):
    """5. 企业技术集中度（HHI）散点/条形图"""
    df = query(engine, """
        SELECT company_name, total_patents, hhi 
        FROM trends.v_company_concentration 
        ORDER BY hhi DESC LIMIT 20
    """)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["company_name"], df["hhi"], color="coral")
    ax.invert_yaxis()
    ax.set_title("Top 20 Companies by Tech Concentration (HHI)")
    ax.set_xlabel("HHI Index")
    
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "company_concentration.png", dpi=150)
    plt.close(fig)


def plot_company_activity(engine):
    """6. 年度活跃企业数与新进入者折线图"""
    df = query(engine, "SELECT * FROM trends.v_company_activity")
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["grant_year"], df["active_companies"], marker="o", label="Active Companies")
    ax.plot(df["grant_year"], df["new_entrants"], marker="s", label="New Entrants")
    
    ax.set_title("Active Companies and New Entrants by Year")
    ax.set_xlabel("Grant Year")
    ax.set_ylabel("Count")
    ax.legend()
    
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "company_activity.png", dpi=150)
    plt.close(fig)


# ============================================================
# 主程序
# ============================================================
def run():
    engine = get_engine()
    
    plot_year_trend(engine)
    plot_subclass_share(engine)
    plot_h01l_main_group_trend(engine)
    
    plot_company_matrix(engine)
    plot_company_concentration(engine)
    plot_company_activity(engine)
    
    print(f"全部图表已生成并保存至：{FIGURES_DIR}")
    return engine


if __name__ == "__main__":
    engine = run()
    engine.dispose()