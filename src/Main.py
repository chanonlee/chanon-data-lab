import pandas as pd
import matplotlib.pyplot as plt

# 加载数据（假设有date和sales列）
df = pd.read_csv('D:\github\python_project\sales_prediction\一年四季壹方城.csv', parse_dates=['trade_date'])
df = df.loc[df["trade_date"] < "2025-01-01", ["d_shop_sale","trade_date"]]
# df.plot()
df = df.set_index('trade_date').asfreq('D')  # 确保连续时间序列
# df.plot()