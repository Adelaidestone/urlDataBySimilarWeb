import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from urllib.parse import urlparse
import time

# 配置文件路径
txt_file_path = r'E:\aiUrlDataBySimilarWeb\similarweb_data.txt'
credentials_file = r'D:\Users\Mussy\Desktop\refined-magpie-474208-i2-6ead78929739.json'
sheet_name = '产品信息列表'
worksheet_index = 1  # 第2个工作表（索引从0开始）
batch_size = 30  # 每30行批量更新一次

def extract_domain(url):
    """
    从URL中提取主域名，去除协议、www、路径、参数等
    例如: https://www.example.com/path?param=value -> example.com
    """
    if not url:
        return ""
    
    url = url.strip().lower()
    
    # 添加协议如果没有的话（用于urlparse解析）
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc if parsed.netloc else parsed.path.split('/')[0]
        
        # 移除www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except:
        # 如果解析失败，手动处理
        url = url.replace('https://', '').replace('http://', '')
        domain = url.split('/')[0].split('?')[0]
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

def domains_match(domain1, domain2):
    """
    判断两个域名是否完全匹配
    只有完全相等才返回True
    """
    return domain1 == domain2

# 1. 读取JSON数据
print("正在读取JSON数据...")
json_data_dict = {}
with open(txt_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            url = list(data.keys())[0]
            json_data_dict[url] = data[url]

print(f"✓ 已读取 {len(json_data_dict)} 条JSON数据")

# 2. 连接Google Sheets
print("\n正在连接Google Sheets...")
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

try:
    creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    gc = gspread.authorize(creds)
    print("✓ Google Sheets 连接成功")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    exit(1)

# 3. 打开表格
print(f"正在打开表格: {sheet_name}...")
try:
    sheet = gc.open(sheet_name)
    worksheet = sheet.get_worksheet(worksheet_index)
    print(f"✓ 打开工作表: {worksheet.title}")
except Exception as e:
    print(f"❌ 打开表格失败: {e}")
    exit(1)

# 4. 读取所有数据
print("\n正在读取表格数据...")
try:
    all_data = worksheet.get_all_values()
    print(f"✓ 读取了 {len(all_data)} 行数据")
except Exception as e:
    print(f"❌ 读取数据失败: {e}")
    exit(1)

# 列索引（Google Sheets从1开始，但Python列表从0开始）
COL_PRODUCT_NAME = 0  # 产品名称（列表索引0 = 表格第1列）
COL_ID = 1  # 入库id
COL_URL = 2  # 官网链接
COL_DESKTOP = 3  # 桌面端占比
COL_MOBILE = 4  # 移动端占比
COL_VISITS = 5  # 每月访问量
COL_VISITS_PER_VISITOR = 6  # 每访客访问次数
COL_USERS_TAB = 7  # 已消除重叠的受众
COL_PAGES_PER_VISIT = 8  # 页面数/访问
COL_AVG_VISIT_DURATION = 9  # 访问持续时间
COL_BOUNCE_RATE = 10  # 跳出率
COL_UPDATE_TIME = 11  # 数据抓取时间

# 5. 匹配数据并准备更新
print("\n开始匹配数据...")
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
updates = []  # 存储所有更新操作
matched_count = 0

for row_index, row_data in enumerate(all_data[1:], start=2):  # 从第2行开始（跳过标题）
    if len(row_data) <= COL_URL:
        continue
    
    excel_url = row_data[COL_URL] if COL_URL < len(row_data) else ""
    
    if not excel_url:
        continue
    
    # 提取域名
    excel_domain = extract_domain(excel_url)
    
    # 在JSON数据中查找匹配
    matched_data = None
    matched_json_url = None
    for json_url, json_values in json_data_dict.items():
        json_domain = extract_domain(json_url)
        
        if domains_match(excel_domain, json_domain):
            matched_data = json_values
            matched_json_url = json_url
            break
    
    if matched_data:
        # 准备更新数据（第4列到第12列，即D到L列）
        # Google Sheets使用A1标记法
        range_name = f'D{row_index}:L{row_index}'
        
        values = [[
            matched_data.get('desktopPersent', 'N/A'),
            matched_data.get('mobilePercent', 'N/A'),
            matched_data.get('visits', 0),
            matched_data.get('visits_per_visitor', 0),
            matched_data.get('users_tab', 0),
            matched_data.get('pages-per-visit', 0),
            matched_data.get('avg_visit_duration', 'N/A'),
            matched_data.get('bounce_rate', 'N/A'),
            current_time
        ]]
        
        updates.append({
            'range': range_name,
            'values': values
        })
        
        matched_count += 1
        product_name = row_data[COL_PRODUCT_NAME] if COL_PRODUCT_NAME < len(row_data) else "未知"
        print(f"✓ 行{row_index}: {product_name} ({excel_domain}) - 准备更新")

print(f"\n共匹配到 {matched_count} 条数据")

# 6. 批量提交更新（每30行一批）
if updates:
    print(f"\n开始批量更新到Google Sheets（每{batch_size}行一批）...")
    total_batches = (len(updates) + batch_size - 1) // batch_size
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        try:
            # 使用batch_update方法批量更新
            worksheet.batch_update(batch)
            print(f"✓ 批次 {batch_num}/{total_batches}: 成功更新 {len(batch)} 行")
            
            # 避免超出API限制，批次间稍作延时
            if i + batch_size < len(updates):
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ 批次 {batch_num} 更新失败: {e}")
            continue
    
    print("\n" + "="*60)
    print("✅ 更新完成！")
    print(f"成功更新: {matched_count} 条数据")
    print(f"更新时间: {current_time}")
    print(f"API调用次数: {total_batches} 次")
    print("="*60)
else:
    print("\n没有找到匹配的数据需要更新。")





