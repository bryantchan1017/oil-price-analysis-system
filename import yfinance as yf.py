import yfinance as yf
import pandas as pd

# 定义要下载的代码和日期范围
ticker_symbol = "^VIX"
start_date = "2006-12-15"
end_date = "2026-03-16"

# 创建 Ticker 对象
ticker = yf.Ticker(ticker_symbol)

# 下载历史数据
# period="max" 也可以，但明确指定日期更稳妥
data = ticker.history(start=start_date, end=end_date)

# 保存为 CSV 文件
data.to_csv("VIX_data.csv")
print("VIX 数据已成功下载并保存为 VIX_data.csv")