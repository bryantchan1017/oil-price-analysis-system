import yfinance as yf
import pandas as pd

# 定义要下载的代码和日期范围
ticker_symbol = "TICKER_SYMBOL_PLACEHOLDER"  
start_date = "START_DATE_PLACEHOLDER"        
end_date = "END_DATE_PLACEHOLDER"           

# 创建 Ticker 对象
ticker = yf.Ticker(ticker_symbol)

# 下载历史数据
# period="max" 也可以，但明确指定日期更稳妥
data = ticker.history(start=start_date, end=end_date)

# 保存为 CSV 文件
data.to_csv("ticker_data.csv") 
print("指定标的数据已成功下载并保存为 ticker_data.csv") 
