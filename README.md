# 油价预测与分析项目

本项目围绕油价展开多维度分析，包含搜索数据爬取、文本情绪分析、VIX数据下载、VAR模型建模等功能。

## 代码文件说明
| 文件名                          | 功能说明                                                                 |
|---------------------------------|--------------------------------------------------------------------------|
| serpapi_bing_crawl.py           | 使用SerpAPI爬取Bing搜索结果，提取关键词的标题/链接，输出至CSV             |
| oil_price_emotion_analysis.py   | 结合SnowNLP做油价关键词情绪评分，调用LLM生成市场情绪分析报告             |
| vix_data_download.py            | 基于yfinance下载VIX波动率指数历史数据，保存为CSV                         |
| oil_price_var_analysis.py       | VAR模型分析油价影响因素（含数据清洗、单位根检验、脉冲响应、方差分解）    |

## 环境依赖
安装所需Python包：
```bash
pip install serpapi snownlp pandas openai yfinance numpy matplotlib statsmodels
