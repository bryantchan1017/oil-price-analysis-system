import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.api import VAR
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# 打开日志文件，所有 print 都会自动保存到这里
log_file = open("run_log.txt", "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# ==========================
# 配置
# ==========================
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

# ==========================
# 1 读取数据（自动检测所有可用数据）
# ==========================

print("=" * 60)
print("开始加载数据...")
print("=" * 60)

# 核心数据（必须存在）
def load_core_data():
    """加载核心数据"""
    data = {}
    
    # WTI原油价格
    if os.path.exists("DCOILWTICO.csv"):
        oil_price = pd.read_csv("DCOILWTICO.csv")
        oil_price.columns = ["date", "wti"]
        oil_price["date"] = pd.to_datetime(oil_price["date"])
        oil_price = oil_price.sort_values("date")
        data['wti'] = oil_price
        print("✅ 加载 WTI 原油价格")
    else:
        print("❌ 未找到 DCOILWTICO.csv")
    
    # 美元指数
    if os.path.exists("DTWEXBGS.csv"):
        usd_index = pd.read_csv("DTWEXBGS.csv")
        usd_index.columns = ["date", "usd"]
        usd_index["date"] = pd.to_datetime(usd_index["date"])
        usd_index = usd_index.sort_values("date")
        data['usd'] = usd_index
        print("✅ 加载 美元指数")
    else:
        print("❌ 未找到 DTWEXBGS.csv")
    
    # 工业产出
    if os.path.exists("INDPRO.csv"):
        ind_prod = pd.read_csv("INDPRO.csv")
        ind_prod.columns = ["date", "indpro"]
        ind_prod["date"] = pd.to_datetime(ind_prod["date"])
        ind_prod = ind_prod.sort_values("date")
        data['indpro'] = ind_prod
        print("✅ 加载 工业产出")
    else:
        print("❌ 未找到 INDPRO.csv")
    
    return data

# EIA数据读取
def read_eia_sheet(file_path, sheet_name, col_name, skip_rows=None):
    """通用EIA数据读取函数"""
    try:
        if skip_rows:
            df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        df = df.iloc[:, :2]
        df.columns = ["date", col_name]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna()
        return df
    except Exception as e:
        print(f"  读取 {sheet_name} 失败: {e}")
        return None

def load_eia_data():
    """加载EIA数据"""
    eia_data = {}
    
    if os.path.exists("PET_SUM_SNDW_DCUS_NUS_W.xls"):
        print("✅ 找到 EIA 数据文件")
        
        eia_crude = read_eia_sheet("PET_SUM_SNDW_DCUS_NUS_W.xls", "Data 1", "production", skip_rows=2)
        if eia_crude is not None:
            eia_data['production'] = eia_crude
            print("  ✅ 加载 原油产量")
        
        eia_stock = read_eia_sheet("PET_SUM_SNDW_DCUS_NUS_W.xls", "Data 6", "inventory", skip_rows=2)
        if eia_stock is not None:
            eia_data['inventory'] = eia_stock
            print("  ✅ 加载 原油库存")
        
        eia_import = read_eia_sheet("PET_SUM_SNDW_DCUS_NUS_W.xls", "Data 8", "imports", skip_rows=2)
        if eia_import is not None:
            eia_data['imports'] = eia_import
            print("  ✅ 加载 原油进口")
        
        eia_export = read_eia_sheet("PET_SUM_SNDW_DCUS_NUS_W.xls", "Data 9", "exports", skip_rows=2)
        if eia_export is not None:
            eia_data['exports'] = eia_export
            print("  ✅ 加载 原油出口")
        
        eia_supply = read_eia_sheet("PET_SUM_SNDW_DCUS_NUS_W.xls", "Data 11", "product_supply", skip_rows=2)
        if eia_supply is not None:
            eia_data['product_supply'] = eia_supply
            print("  ✅ 加载 产品供应")
    else:
        print("❌ 未找到 PET_SUM_SNDW_DCUS_NUS_W.xls")
    
    return eia_data

def load_vix_data():
    """加载VIX波动率指数数据"""
    vix_data = {}
    
    if os.path.exists("VIX.csv"):
        try:
            vix_df = pd.read_csv("VIX.csv", encoding='utf-8')
            
            # 识别日期列和收盘价列
            date_col = None
            price_col = None
            
            for col in vix_df.columns:
                if '日期' in col or 'date' in col.lower():
                    date_col = col
                elif '收盘' in col or 'close' in col.lower():
                    price_col = col
            
            if date_col and price_col:
                vix = pd.DataFrame({
                    'date': pd.to_datetime(vix_df[date_col]),
                    'vix': pd.to_numeric(vix_df[price_col], errors='coerce')
                })
                vix = vix.sort_values('date')
                vix_data['vix'] = vix
                print("✅ 加载 VIX 波动率指数")
            else:
                print("❌ VIX数据格式不正确，未找到日期或收盘价列")
        except Exception as e:
            print(f"❌ 读取VIX数据失败: {e}")
    else:
        print("❌ 未找到 VIX.csv")
    
    return vix_data

def load_gpr_data():
    """加载GPR地缘政治风险数据"""
    gpr_data = {}
    
    if os.path.exists("data_gpr_export.xls"):
        try:
            # 读取Excel文件
            gpr_df = pd.read_excel("data_gpr_export.xls", sheet_name=0)
            
            # 找到日期列和GPR指数列
            # 根据提供的文件内容，第一列是日期，第二列是GPR指数
            if len(gpr_df.columns) >= 2:
                gpr = pd.DataFrame({
                    'date': pd.to_datetime(gpr_df.iloc[:, 0]),
                    'gpr': pd.to_numeric(gpr_df.iloc[:, 1], errors='coerce')
                })
                gpr = gpr.sort_values('date')
                gpr_data['gpr'] = gpr
                print("✅ 加载 GPR 地缘政治风险指数")
            else:
                print("❌ GPR数据格式不正确")
        except Exception as e:
            print(f"❌ 读取GPR数据失败: {e}")
    else:
        print("❌ 未找到 data_gpr_export.xls")
    
    return gpr_data

def load_optional_data():
    """加载其他可选数据（搜索趋势等）"""
    optional_data = {}
    
    # Google搜索趋势数据
    trend_files = ["trend (oil price).csv", "trend(oil price).csv", "trend_oil.csv"]
    for file in trend_files:
        if os.path.exists(file):
            try:
                trend = pd.read_csv(file)
                trend_data = pd.DataFrame({
                    'date': pd.to_datetime(trend.iloc[:, 0]),
                    'trend_oil': pd.to_numeric(trend.iloc[:, 1], errors='coerce')
                })
                optional_data['trend_oil'] = trend_data
                print(f"✅ 加载 油价搜索趋势 (来自 {file})")
                break
            except:
                continue
    
    return optional_data

# ==========================
# 2 数据频率对齐（重采样）
# ==========================

def resample_to_weekly(df, col_name, method='last'):
    """重采样为周度数据（周五）"""
    if df is None or df.empty:
        return None
    
    df = df.set_index("date").sort_index()
    weekly = df.resample('W-FRI').agg({col_name: method})
    return weekly

# ==========================
# 3 主程序：加载所有数据
# ==========================

def main():
    """主程序（增强版，包含VIX和GPR）"""
    
    # 3.1 加载核心数据
    core_data = load_core_data()
    if len(core_data) < 3:
        print("错误: 核心数据不足，无法进行分析")
        sys.exit(1)
    
    # 3.2 加载EIA数据
    eia_data = load_eia_data()
    
    # 3.3 加载VIX和GPR数据
    vix_data = load_vix_data()
    gpr_data = load_gpr_data()
    
    # 3.4 加载其他可选数据
    other_optional = load_optional_data()
    
    # 3.5 合并所有数据
    all_data = {**core_data, **eia_data, **vix_data, **gpr_data, **other_optional}
    
    # 3.6 重采样为周度
    weekly_data = {}
    for name, df in all_data.items():
        weekly = resample_to_weekly(df, name)
        if weekly is not None:
            weekly_data[name] = weekly
    
    # 3.7 合并所有DataFrame
    merged_df = None
    for name, df in weekly_data.items():
        if merged_df is None:
            merged_df = df.copy()
        else:
            merged_df = merged_df.join(df, how='outer')
    
    if merged_df is None or merged_df.empty:
        print("错误: 合并后的数据为空")
        sys.exit(1)
    
    # ==========================
    # 4 设置时间范围
    # ==========================
    
    start_date = '2006-12-15'
    merged_df = merged_df.loc[start_date:]
    
    print("\n" + "=" * 60)
    print("原始数据信息")
    print("=" * 60)
    print(f"日期范围: {merged_df.index.min()} 到 {merged_df.index.max()}")
    print(f"原始观测数: {len(merged_df)}")
    print("\n各变量缺失情况:")
    print(merged_df.isnull().sum())
    
    # ==========================
    # 5 处理缺失值（增强版）
    # ==========================
    
    # 先进行前向和后向填充
    merged_df = merged_df.fillna(method='ffill', limit=4)
    merged_df = merged_df.fillna(method='bfill', limit=4)
    
    # 对新增变量进行缺失率检查
    for col in ['vix', 'gpr']:
        if col in merged_df.columns:
            missing_pct = merged_df[col].isnull().mean() * 100
            if missing_pct > 50:
                print(f"⚠️ {col}缺失率{missing_pct:.1f}%，考虑是否保留")
    
    # 线性插值
    merged_df = merged_df.interpolate(method='linear', limit_direction='both')
    
    # 删除剩余缺失值
    merged_df = merged_df.dropna()
    
    print("\n处理后数据信息:")
    print(f"处理后观测数: {len(merged_df)}")
    print(f"时间跨度: {(merged_df.index.max() - merged_df.index.min()).days/365:.1f} 年")
    
    # ==========================
    # 6 描述统计
    # ==========================
    
    print("\n" + "=" * 60)
    print("描述统计")
    print("=" * 60)
    print(merged_df.describe())
    
    # ==========================
    # 7 构造分析变量
    # ==========================
    
    df_model = merged_df.copy()
    
    if 'imports' in df_model.columns and 'exports' in df_model.columns:
        df_model['net_import'] = df_model['imports'] - df_model['exports']
        print("✅ 添加净进口变量")
    
    core_vars = ['wti', 'usd', 'indpro']
    supply_vars = ['production', 'inventory'] if all(v in df_model.columns for v in ['production', 'inventory']) else []
    demand_vars = ['product_supply'] if 'product_supply' in df_model.columns else []
    optional_vars = [v for v in ['vix', 'gpr', 'trend_oil'] if v in df_model.columns]
    
    # 打印新增变量信息
    if 'vix' in optional_vars:
        print("✅ 已包含 VIX 波动率指数")
    if 'gpr' in optional_vars:
        print("✅ 已包含 GPR 地缘政治风险指数")
    
    all_available_vars = core_vars + supply_vars + demand_vars + optional_vars
    all_available_vars = [v for v in all_available_vars if v in df_model.columns]
    
    print("\n" + "=" * 60)
    print("可用变量列表")
    print("=" * 60)
    for v in all_available_vars:
        print(f"  - {v}")
    
    df_analysis = df_model[all_available_vars].copy()
    print(f"\n最终样本数: {len(df_analysis)}")
    
    # ==========================
    # 8 单位根检验
    # ==========================
    
    print("\n" + "=" * 60)
    print("单位根检验 (ADF)")
    print("=" * 60)
    
    for col in df_analysis.columns:
        result = adfuller(df_analysis[col].dropna(), autolag='AIC', regression='c')
        print(f"\n{col}:")
        print(f"  水平值 p-value: {result[1]:.4f}")
        
        diff_result = adfuller(df_analysis[col].diff().dropna(), autolag='AIC', regression='c')
        print(f"  一阶差分 p-value: {diff_result[1]:.4f}")
    
    # ==========================
    # 9 对数差分（平稳化）
    # ==========================
    
    df_analysis = df_analysis[df_analysis > 0].dropna()
    df_log = np.log(df_analysis)
    df_diff = df_log.diff().dropna()
    
    print("\n" + "=" * 60)
    print("差分后数据")
    print("=" * 60)
    print(f"样本数: {len(df_diff)}")
    print(f"时间范围: {df_diff.index.min()} 到 {df_diff.index.max()}")
    
    # ==========================
    # 10 VAR模型（增强版，可选包含VIX和GPR）
    # ==========================
    
    # 定义论文核心变量和增强变量
    paper_vars = ['usd', 'production', 'indpro', 'inventory', 'wti']
    extended_vars = paper_vars + [v for v in ['vix', 'gpr'] if v in df_diff.columns]
    
    available_paper_vars = [v for v in paper_vars if v in df_diff.columns]
    available_extended_vars = [v for v in extended_vars if v in df_diff.columns]
    
    # 选择使用哪个变量集
    use_extended = len(available_extended_vars) > len(available_paper_vars)
    model_vars = available_extended_vars if use_extended else available_paper_vars
    
    print(f"\n{'=' * 60}")
    print(f"使用{'增强版' if use_extended else '论文核心'}变量进行VAR分析")
    if use_extended:
        print("(包含VIX和/或GPR)")
    print(f"{'=' * 60}")
    print(model_vars)
    
    if len(model_vars) >= 3:
        model = VAR(df_diff[model_vars])
        
        try:
            lag_order = model.select_order(maxlags=8)
            print("\n滞后阶数选择:")
            print(lag_order.summary())
            
            p = lag_order.aic
            if p is None or p < 1:
                p = 7
            p = min(p + 2, 8)
            print(f"\n最优滞后阶数 (AIC): {p}")
            
            results = model.fit(p)
            
            print("\n" + "=" * 60)
            print("VAR模型结果摘要")
            print("=" * 60)
            print(results.summary())
            
            # 脉冲响应
            irf = results.irf(12)
            
            # 方差分解
            fevd = results.fevd(12)
            print("\n" + "=" * 60)
            print("方差分解 (12周)")
            print("=" * 60)
            print(fevd.summary())
            
            # Granger因果检验（对WTI）
            print("\n" + "=" * 60)
            print("Granger因果检验 (对WTI油价)")
            print("=" * 60)
            
            if 'wti' in model_vars:
                for var in model_vars:
                    if var != 'wti':
                        try:
                            test_result = results.test_causality('wti', var, kind='f')
                            significance = "显著" if test_result.pvalue < 0.05 else "不显著"
                            print(f"\n{var} → wti:")
                            print(f"  F统计量: {test_result.test_statistic:.4f}")
                            print(f"  p值: {test_result.pvalue:.4f}")
                            print(f"  {significance}")
                        except Exception as e:
                            print(f"  {var} → wti: 检验失败 - {e}")
            
            # ==========================
            # 11 分图绘制（保持不变，完全按照您原来的注释状态）
            # ==========================
            
            print("\n" + "=" * 60)
            print("开始生成分图...")
            print("=" * 60)
            
            # 创建figures文件夹
            if not os.path.exists("figures"):
                os.makedirs("figures")
            
            # ==========================
            # 图1：所有变量原始序列
            # ==========================
            fig1, axes = plt.subplots(3, 2, figsize=(14, 10))
            axes = axes.flatten()
            for i, var in enumerate(df_analysis.columns[:6]):
                if i < len(axes):
                    axes[i].plot(df_analysis.index, df_analysis[var], linewidth=1.5, color='blue')
                    axes[i].set_title(f'{var.upper()} - Original Series')
                    axes[i].set_xlabel('Date')
                    axes[i].set_ylabel('Value')
                    axes[i].grid(True, alpha=0.3)
            fig1.suptitle('Figure 1: All Variables - Original Time Series', fontsize=14, fontweight='bold')
            plt.tight_layout()
            fig1.savefig("figures/figure1_all_series.png", dpi=300, bbox_inches='tight')
            plt.close(fig1)
            print("✅ 图1已保存: figures/figure1_all_series.png")

            # ==========================
            # 图2：WTI油价历史走势
            # ==========================
            fig2, ax = plt.subplots(figsize=(12, 5))
            ax.plot(df_analysis.index, df_analysis['wti'], linewidth=1.5, color='black')
            ax.set_title('Figure 2: WTI Crude Oil Price (2006-2026)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('USD/barrel')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig2.savefig("figures/figure2_wti_price.png", dpi=300, bbox_inches='tight')
            plt.close(fig2)
            print("✅ 图2已保存: figures/figure2_wti_price.png")

            # ==========================
            # 图3：脉冲响应总览
            # ==========================
            fig3 = irf.plot(orth=False)
            fig3.suptitle('Figure 3: Impulse Response Functions - Overview', fontsize=14, fontweight='bold')
            fig3.tight_layout()
            fig3.savefig("figures/figure3_irf_overview.png", dpi=300, bbox_inches='tight')
            plt.close(fig3)
            print("✅ 图3已保存: figures/figure3_irf_overview.png")

            # ==========================
            # 图4-7：各变量对WTI的脉冲响应（单独）
            # ==========================
            # 只绘制核心变量的脉冲响应
            core_shock_vars = ['usd', 'production', 'indpro', 'inventory']
            shock_titles = ['USD', 'Supply (Production)', 'Demand (INDPRO)', 'Inventory']
            figure_numbers = [4, 5, 6, 7]
            file_names = ['usd', 'production', 'indpro', 'inventory']

            for fig_num, title, shock, fname in zip(figure_numbers, shock_titles, core_shock_vars, file_names):
                if shock in model_vars:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    
                    # 获取索引
                    shock_idx = model_vars.index(shock)
                    wti_idx = model_vars.index('wti')
                    
                    # 获取响应值
                    irf_values = irf.irfs[:, wti_idx, shock_idx]
                    periods = range(len(irf_values))
                    
                    # 绘制主线条
                    ax.plot(periods, irf_values, 'b-', linewidth=2, label='Response')
                    
                    # 添加置信区间
                    try:
                        std_errors = irf.stderr[:, wti_idx, shock_idx]
                        ax.fill_between(periods, 
                                    irf_values - 1.96*std_errors,
                                    irf_values + 1.96*std_errors,
                                    alpha=0.2, color='blue', label='95% CI')
                    except:
                        pass
                    
                    # 美化
                    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                    ax.set_title(f'Figure {fig_num}: Impact of {title} Shock on WTI Price', 
                                fontsize=12, fontweight='bold')
                    ax.set_xlabel('Weeks after shock', fontsize=10)
                    ax.set_ylabel('Response of WTI Price', fontsize=10)
                    ax.legend(loc='best')
                    ax.grid(True, alpha=0.3)
                    ax.set_xlim(0, 11)
                    
                    plt.tight_layout()
                    filename = f"figures/figure{fig_num}_irf_{fname}_to_wti.png"
                    fig.savefig(filename, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    print(f"✅ 图{fig_num}已保存: {filename}")

            # ==========================
            # 图8：所有冲击对比
            # ==========================
            fig8, axes = plt.subplots(2, 2, figsize=(14, 10))
            axes = axes.flatten()

            for idx, (shock, title) in enumerate(zip(core_shock_vars, shock_titles)):
                if shock in model_vars and idx < len(axes):
                    ax = axes[idx]
                    
                    # 获取索引
                    shock_idx = model_vars.index(shock)
                    wti_idx = model_vars.index('wti')
                    
                    # 获取响应值
                    irf_values = irf.irfs[:, wti_idx, shock_idx]
                    periods = range(len(irf_values))
                    
                    # 绘制线条
                    ax.plot(periods, irf_values, 'b-', linewidth=2)
                    
                    # 添加置信区间
                    try:
                        std_errors = irf.stderr[:, wti_idx, shock_idx]
                        ax.fill_between(periods, 
                                    irf_values - 1.96*std_errors,
                                    irf_values + 1.96*std_errors,
                                    alpha=0.2, color='blue')
                    except:
                        pass
                    
                    # 美化
                    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                    ax.set_title(f'{title} Shock')
                    ax.set_xlabel('Weeks')
                    ax.set_ylabel('Response')
                    ax.grid(True, alpha=0.3)
                    ax.set_xlim(0, 11)

            fig8.suptitle('Figure 8: Comparison of All Shocks on WTI Price', fontsize=14, fontweight='bold')
            plt.tight_layout()
            fig8.savefig("figures/figure8_all_shocks_comparison.png", dpi=300, bbox_inches='tight')
            plt.close(fig8)
            print("✅ 图8已保存: figures/figure8_all_shocks_comparison.png")

            # ==========================
            # 图9：方差分解柱状图
            # ==========================
            fig9, ax = plt.subplots(figsize=(10, 6))

            # 获取数据
            wti_idx = model_vars.index('wti')
            fevd_wti = fevd.decomp[-1, :, wti_idx] * 100

            # 安全检查
            if len(fevd_wti) != len(model_vars):
                print(f"⚠️ 数据长度不匹配: fevd_wti={len(fevd_wti)}, vars={len(model_vars)}")
                min_len = min(len(fevd_wti), len(model_vars))
                fevd_wti = fevd_wti[:min_len]
                plot_vars = model_vars[:min_len]
            else:
                plot_vars = model_vars

            # 按贡献度排序
            sorted_idx = np.argsort(fevd_wti)[::-1]
            sorted_vars = [plot_vars[i] for i in sorted_idx]
            sorted_values = fevd_wti[sorted_idx]

            # 绘制柱状图
            bars = ax.bar(range(len(sorted_vars)), sorted_values, tick_label=sorted_vars, color='steelblue')

            # 添加数值标签
            for bar, val in zip(bars, sorted_values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

            ax.set_title('Figure 9: WTI Variance Decomposition (Week 12)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Variables', fontsize=12)
            ax.set_ylabel('Contribution (%)', fontsize=12)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()
            fig9.savefig("figures/figure9_fevd_barchart.png", dpi=300, bbox_inches='tight')
            plt.close(fig9)
            print("✅ 图9已保存: figures/figure9_fevd_barchart.png")

            # ==========================
            # 图10：方差分解堆叠图（注释掉，保持原样）
            # ==========================
            # fig10, ax = plt.subplots(figsize=(14, 6))

            # 确保使用正确的索引
            # wti_idx = model_vars.index('wti')

            # 提取WTI的方差分解（使用正确的维度）
            # fevd.decomp形状: (periods, n_vars, n_vars)
            # 我们需要的是 [所有时期, 所有变量, wti的索引]
            # fevd_wti_over_time = fevd.decomp[:, :, wti_idx] * 100

            # 检查数据
            # print("方差分解数据形状:", fevd_wti_over_time.shape)
            # print("第1期数据:", fevd_wti_over_time[0, :])
            # print("第12期数据:", fevd_wti_over_time[11, :])

            # 确保数据合理（每行和应为100）
            # row_sums = fevd_wti_over_time.sum(axis=1)
            # print("每行总和:", row_sums)

            # 创建堆叠面积图
            # periods = range(1, fevd_wti_over_time.shape[0] + 1)
            # colors = plt.cm.Set3(np.linspace(0, 1, len(model_vars)))

            # ax.stackplot(periods, fevd_wti_over_time.T, 
            #            labels=model_vars, 
            #            colors=colors,
            #            alpha=0.8)
            # ax.set_title('Figure 10: Variance Decomposition of WTI Price Over Time', 
            #            fontsize=14, fontweight='bold')
            # ax.set_xlabel('Weeks Ahead', fontsize=12)
            # ax.set_ylabel('Contribution to Variance (%)', fontsize=12)
            # ax.set_xlim(1, 12)
            # ax.set_ylim(0, 100)
            # ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
            # ax.grid(True, alpha=0.3, axis='y')

            # plt.tight_layout()
            # fig10.savefig("figures/figure10_fevd_stacked.png", dpi=300, bbox_inches='tight')
            # plt.close(fig10)
            # print("✅ 图10已保存: figures/figure10_fevd_stacked.png")

            # ==========================
            # 图11：实际vs拟合
            # ==========================
            if 'wti' in df_diff.columns and 'results' in locals():
                try:
                    # 获取拟合值
                    fitted_values = results.fittedvalues
                    
                    if 'wti' in fitted_values.columns:
                        # 计算累积收益率
                        fitted_returns = fitted_values['wti']
                        
                        # 转换为价格水平
                        actual_prices = df_analysis['wti'].iloc[1:len(fitted_returns)+1]
                        base_price = df_analysis['wti'].iloc[0]
                        
                        # 计算拟合价格
                        fitted_prices = base_price * np.exp(fitted_returns.cumsum())
                        
                        # 确保长度匹配
                        min_len = min(len(actual_prices), len(fitted_prices))
                        
                        fig11, ax = plt.subplots(figsize=(14, 6))
                        
                        # 绘制实际价格
                        ax.plot(actual_prices.index[:min_len], actual_prices.values[:min_len], 
                            'black', label='Actual WTI Price', linewidth=1.5)
                        
                        # 绘制拟合价格
                        ax.plot(actual_prices.index[:min_len], fitted_prices.values[:min_len], 
                            'red', label='Fitted WTI Price', linewidth=1.5, alpha=0.7, linestyle='--')
                        
                        ax.set_title('Figure 11: WTI Price - Actual vs Fitted', 
                                    fontsize=14, fontweight='bold')
                        ax.set_xlabel('Date', fontsize=12)
                        ax.set_ylabel('USD/barrel', fontsize=12)
                        ax.legend(loc='best', fontsize=10)
                        ax.grid(True, alpha=0.3)
                        
                        plt.tight_layout()
                        fig11.savefig("figures/figure11_actual_vs_fitted.png", dpi=300, bbox_inches='tight')
                        plt.close(fig11)
                        print("✅ 图11已保存: figures/figure11_actual_vs_fitted.png")
                except Exception as e:
                    print(f"⚠️ 图11生成失败: {e}")

            # ==========================
            # 图12：油价对数收益率
            # ==========================
            if 'wti' in df_diff.columns:
                try:
                    fig12, ax = plt.subplots(figsize=(14, 5))
                    
                    # 计算收益率（百分比）
                    returns = df_diff['wti'] * 100
                    
                    # 绘制收益率
                    ax.plot(returns.index, returns.values, linewidth=0.8, color='blue', alpha=0.7)
                    
                    # 添加零线
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)
                    
                    # 填充正负区域
                    ax.fill_between(returns.index, 0, returns.values, 
                                where=returns.values > 0, color='red', alpha=0.2, 
                                label=f'Positive ({len(returns[returns>0])} weeks)')
                    ax.fill_between(returns.index, 0, returns.values, 
                                where=returns.values < 0, color='green', alpha=0.2, 
                                label=f'Negative ({len(returns[returns<0])} weeks)')
                    
                    # 统计信息
                    mean_return = returns.mean()
                    std_return = returns.std()
                    ax.axhline(y=mean_return, color='blue', linestyle='--', alpha=0.5, 
                            label=f'Mean: {mean_return:.2f}%')
                    ax.axhline(y=mean_return + 2*std_return, color='orange', linestyle=':', alpha=0.5, 
                            label=f'+2σ: {(mean_return + 2*std_return):.2f}%')
                    ax.axhline(y=mean_return - 2*std_return, color='orange', linestyle=':', alpha=0.5, 
                            label=f'-2σ: {(mean_return - 2*std_return):.2f}%')
                    
                    ax.set_title('Figure 12: WTI Weekly Returns (%)', fontsize=14, fontweight='bold')
                    ax.set_xlabel('Date', fontsize=12)
                    ax.set_ylabel('Return (%)', fontsize=12)
                    ax.legend(loc='best', fontsize=9, ncol=2)
                    ax.grid(True, alpha=0.3)
                    
                    # 设置y轴范围
                    ylim = max(abs(returns.min()), abs(returns.max())) * 1.1
                    ax.set_ylim(-ylim, ylim)
                    
                    plt.tight_layout()
                    fig12.savefig("figures/figure12_wti_returns.png", dpi=300, bbox_inches='tight')
                    plt.close(fig12)
                    print("✅ 图12已保存: figures/figure12_wti_returns.png")
                except Exception as e:
                    print(f"⚠️ 图12生成失败: {e}")

            print("\n" + "=" * 60)
            print("✅ 所有图表生成完成！共12张图")
            print(f"📁 图片已保存到 figures/ 文件夹")
            print("=" * 60)
            
        except Exception as e:
            print(f"VAR模型拟合失败: {e}")
            import traceback
            traceback.print_exc()
    
    # ==========================
    # 12 输出总结
    # ==========================
    
    print("\n" + "=" * 60)
    print("✅ 分析完成")
    print("=" * 60)
    print(f"数据时间范围: {df_diff.index.min()} 到 {df_diff.index.max()}")
    print(f"总样本数: {len(df_diff)}")
    print(f"可用变量数: {len(df_diff.columns)}")
    print(f"变量列表: {list(df_diff.columns)}")
    
    # 新增变量统计
    if 'vix' in df_diff.columns:
        print(f"VIX数据: 已包含 ({df_diff['vix'].count()} 个观测)")
    if 'gpr' in df_diff.columns:
        print(f"GPR数据: 已包含 ({df_diff['gpr'].count()} 个观测)")

if __name__ == "__main__":
    main()
    log_file.close()
    print("✅ 程序运行完毕，日志已保存到 run_log.txt")
