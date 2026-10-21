# 半导体产业专利数据分析项目

## 项目简介
本项目基于美国专利商标局（USPTO）的授权专利数据，构建“技术方向—企业/机构—时间”的分析框架，对半导体产业的技术演进趋势与企业研发布局进行监测与分析。

## 数据来源与口径
- **数据源**：USPTO PatentsView Granted Patent Disambiguated Data (1976-2025)。
- **样本范围**：基于 WIPO 技术分类，筛选 `first_wipo_field_title == "Semiconductors"` 的相关专利，时间窗口为 2015-2025 年的授权专利。
- **统计粒度**：专利事实表（`clean.patent`）以 `patent_id` 为主键去重，避免重复计数。
- **技术口径**：`subclass` 及细分领域（H01L、H10K、H05K）趋势均基于全 CPC 表（`clean.patent_cpc`）按专利去重统计。
- **企业口径**：使用 PatentsView 官方机构消歧 ID（`assignee_id`），统一企业名称，剔除缺失样本。

## 技术栈
- **数据处理**：Python (Pandas)
- **数据库与查询**：DuckDB, SQL (SQLAlchemy)
- **可视化**：Power BI

## 项目结构与数据流转
项目采用分层架构设计：
1. **Raw (原始层)**：读取并合并年度专利主表、摘要、CPC 及机构消歧数据。
2. **Clean (清洗层)**：执行去重、脏数据剥离、剔除空企业名。
3. **Features (特征层)**：生成企业归一化大表及核心技术标签维度表。
4. **Trends (分析层)**：使用 SQL 计算年度趋势、YoY 增速、技术份额及企业技术矩阵。
5. **Views (视图层)**：基于所有落库表统一生成 `v_` 前缀直出视图，供 BI 工具调取。

## 运行说明
1. 安装依赖：`pip install -r requirements.txt`。
2. 按顺序运行数据管道：
   - `src/load/load_raw.py`
   - `src/load/load_extra.py`
   - `src/cleaning/clean.py`
   - `src/features/build_assignee_normalized.py`
   - `src/features/build_tech_labels.py`
   - `src/analysis/trend_analysis.py`
   - `src/analysis/company_landscape.py`
3. 打开 Power BI，连接 `data/db/semiconductor.duckdb` 中的 `views` 视图层，即可刷新并展示分析图表。详细业务结论见 `reports/final_report.md`。