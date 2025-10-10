import gspread
from google.oauth2.service_account import Credentials

# 配置
credentials_file = r'D:\Users\Mussy\Desktop\refined-magpie-474208-i2-6ead78929739.json'
sheet_name = '产品信息列表'  # 通过表格名称打开

# 设置权限范围
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 加载凭证
print("正在连接...")
creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
gc = gspread.authorize(creds)
print("✓ 连接成功!")

# 通过名称打开表格
print(f"正在打开表格: {sheet_name}...")
sheet = gc.open(sheet_name)  # 使用表格名称
worksheet = sheet.get_worksheet(1)  # 第一个工作表
print(f"✓ 打开表格: {sheet.title}")

# 读取数据
print("正在读取数据...")
data = worksheet.get_all_values()
print(f"✓ 读取了 {len(data)} 行数据")

# 显示前5行
print("\n前5行数据:")
for i, row in enumerate(data[:5], 1):
    print(f"第{i}行: {row}")


