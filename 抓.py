import csv
from serpapi import Client
from serpapi.exceptions import HTTPError
import os  # 用于检查文件是否存在

# 初始化Client（只需要一次）
client = Client(api_key="1bac1711297ba43aa9684f19111e3fce92ec6c2e82420161a7af8e971234a57c")

# 定义输出CSV路径
output_csv = "/Users/bryanchan/Desktop/student helper/AI跑完的data/bing.csv"

# 检查文件是否存在，不存在则写入表头
file_exists = os.path.isfile(output_csv)

with open("/Users/bryanchan/Desktop/student helper/AI跑完的data/1.csv", "r", encoding="utf-8-sig") as f_input, \
        open(output_csv, "a", encoding="utf-8-sig", newline="") as f_output:  # newline=""避免空行

    reader = csv.DictReader(f_input)
    # 定义输出CSV的字段名（与需求一致）
    fieldnames = ["hot_search_day", "key", "res_no", "res_title", "res_link"]
    writer = csv.DictWriter(f_output, fieldnames=fieldnames)

    # 首次运行时写入表头
    if not file_exists:
        writer.writeheader()

    for row_num, row in enumerate(reader, 1):
        # 获取原CSV中的日期（hot_search_day）和查询词（key）
        # 这里的"hot_search_day"需与1.csv中日期列的表头完全一致（包括大小写和空格）
        hot_search_day = row.get("date", "无日期")
        Query_s = row.get("suggested_query", "").strip()

        if not Query_s:
            print(f"第 {row_num} 行：查询词为空，跳过\n")
            continue

        print(f"===== 处理第 {row_num} 行查询：{Query_s} =====")

        try:
            result = client.search(
                engine="bing",
                q=Query_s,
                location="China"
            )

            organic_results = result.get("organic_results", [])
            top_10_results = organic_results[:10]

            print(f"前 {len(top_10_results)} 个搜索结果：\n")
            for i, item in enumerate(top_10_results, 1):
                # 提取结果数据
                res_data = {
                    "hot_search_day": hot_search_day,  # 使用从原CSV读取的日期
                    "key": Query_s,
                    "res_no": i,  # 结果序号
                    "res_title": item.get("title", "无标题"),
                    "res_link": item.get("link", "无链接")
                }

                # 写入CSV
                writer.writerow(res_data)

                # 打印结果（可选，方便查看进度）
                #print(f"结果{i}：")
                #print(f"标题：{res_data['res_title']}")
                #print(f"链接：{res_data['res_link']}\n")

        except HTTPError as e:
            print(f"第 {row_num} 行查询失败：{e}\n")
        except Exception as e:
            print(f"第 {row_num} 行发生未知错误：{e}\n")

