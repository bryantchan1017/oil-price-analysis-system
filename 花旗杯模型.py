import csv
from serpapi import Client
from serpapi.exceptions import HTTPError
import os
from snownlp import SnowNLP
import pandas as pd
from openai import OpenAI

# ---------------------- 配置（不用动） ----------------------
#我用的是serpapi
client = Client(api_key="key")
output_csv = "/Users/bryanchan/Documents/CITI case comp/油价预测模型/花旗杯/油价分析数据.csv"
trends_file_list = [
    "/Users/bryanchan/Documents/CITI case comp/油价预测模型/花旗杯/trend（oil price）.csv",
    "/Users/bryanchan/Documents/CITI case comp/油价预测模型/花旗杯/trend(OPEC).csv"
]
vix_path = "/Users/bryanchan/Documents/CITI case comp/油价预测模型/花旗杯/VIX.csv"
report_path = "/Users/bryanchan/Documents/CITI case comp/油价预测模型/花旗杯/情绪分析报告.md"

#我用的是豆包
VOLC_API_KEY = "key"
VOLC_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_ENDPOINT = "ep-key-xx"

# ---------------------- 工具函数 ----------------------
def get_emotion_score(text):
    if not text: return 0
    try: return round((SnowNLP(text).sentiments - 0.5) * 20, 2)
    except: return 0

def load_trends_data(file_list):
    df_list = []
    for file_path in file_list:
        try:
            temp_df = pd.read_csv(file_path, encoding="utf-8-sig")
            if "Time" in temp_df.columns:
                keyword = temp_df.columns[1]
                temp_df.rename(columns={"Time": "date", keyword: "hot_score"}, inplace=True)
                temp_df["keyword"] = keyword
                df_list.append(temp_df)
        except: continue
    if not df_list: return pd.DataFrame()
    trends_df = pd.concat(df_list, ignore_index=True)
    trends_df["date"] = pd.to_datetime(trends_df["date"], errors="coerce")
    trends_df["year"] = trends_df["date"].dt.year
    return trends_df.dropna()

def get_historical_hot(keyword, trends_df):
    if trends_df.empty: return {"max_hot_20y":0,"avg_hot_5y":0,"hot_vol_10y":0}
    data = trends_df[trends_df["keyword"] == keyword]
    if data.empty: return {"max_hot_20y":0,"avg_hot_5y":0,"hot_vol_10y":0}
    current_year = pd.Timestamp.now().year
    return {
        "max_hot_20y": round(data["hot_score"].max(),2),
        "avg_hot_5y": round(data[data["year"]>=current_year-5]["hot_score"].mean(),2) if not data.empty else 0,
        "hot_vol_10y": round(data[data["year"]>=current_year-10]["hot_score"].std(),2) if not data.empty else 0
    }

def load_vix_data(path):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.rename(columns={c:"date" if "date" in c.lower() else c for c in df.columns}, inplace=True)
        df.rename(columns={c:"vix" if "vix" in c.lower() else c for c in df.columns}, inplace=True)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except: return pd.DataFrame()

def get_vix_by_date(hot_day, vix_df):
    if "date" not in vix_df.columns or vix_df.empty: return 0
    try:
        hot_date = pd.to_datetime(hot_day)
        vix_df["diff"] = abs((vix_df["date"] - hot_date).dt.days)
        return round(vix_df.loc[vix_df["diff"].idxmin(), "vix"], 2)
    except: return 0

def generate_llm_report(kw_data):
    try:
        client_llm = OpenAI(api_key=VOLC_API_KEY, base_url=VOLC_BASE_URL)
        prompt = f"""生成{kw_data['key']}油价市场情绪分析报告（300字）：
        日期：{kw_data['hot_search_day']}，平均情绪分：{kw_data['avg_emotion']}
        历史热度：20年峰值{kw_data['max_hot_20y']}，5年均值{kw_data['avg_hot_5y']}
        恐慌指数VIX：{kw_data['vix']}，情绪波动率：{kw_data['emotion_vol']}
        要求：专业、简洁、给出趋势判断"""
        res = client_llm.chat.completions.create(model=MODEL_ENDPOINT, messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except: return "报告生成失败"

trends_df = load_trends_data(trends_file_list)
vix_df = load_vix_data(vix_path)
all_kw_summary = []

# 写分析的关键词
KEYWORDS = [
    {"date": "2026-03-22", "query": "oil price"},
    {"date": "2026-03-22", "query": "OPEC"}
]

# 写入结果CSV
with open(output_csv, "w", encoding="utf-8-sig", newline="") as f_out:
    fieldnames = ["hot_search_day","key","res_no","res_title","res_link","emotion_score","max_hot_20y","avg_hot_5y","hot_vol_10y","vix_value","emotion_vol"]
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()

    for item in KEYWORDS:
        hot_day = item["date"]
        query = item["query"]
        hist = get_historical_hot(query, trends_df)
        vix_val = get_vix_by_date(hot_day, vix_df)

        try:
            result = client.search(engine="bing", q=query, location="China")
            top_10 = result.get("organic_results", [])[:10]
            scores = []

            for i, res in enumerate(top_10, 1):
                score = get_emotion_score(res.get("title", ""))
                scores.append(score)
                writer.writerow({
                    "hot_search_day": hot_day, "key": query, "res_no": i,
                    "res_title": res.get("title"), "res_link": res.get("link"),
                    "emotion_score": score, **hist,
                    "vix_value": vix_val, "emotion_vol": 0
                })

            # 汇总数据
            avg_score = round(sum(scores)/len(scores), 2) if scores else 0
            vol_score = round(pd.Series(scores).std(), 2) if scores else 0
            all_kw_summary.append({
                "key": query, "hot_search_day": hot_day, "avg_emotion": avg_score,
                **hist, "vix": vix_val, "emotion_vol": vol_score
            })
            print(f"分析完成：{query}")

        except Exception as e:
            print(f"分析失败：{query}，错误：{e}")

# 生成LLM报告
with open(report_path, "w", encoding="utf-8") as f:
    f.write("# 油价市场情绪分析报告\n\n")
    for data in all_kw_summary:
        f.write(f"## 关键词：{data['key']}\n{generate_llm_report(data)}\n\n")

print(f"\n 全部运行成功！")
print(f"量化数据：{output_csv}")
print(f"LLM报告：{report_path}")