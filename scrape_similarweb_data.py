import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys # 导入Keys用于模拟键盘操作
import time
from selenium.common.exceptions import TimeoutException # 导入TimeoutException
import json # 导入json模块
import os # 导入os模块
from webdriver_manager.chrome import ChromeDriverManager # 自动管理ChromeDriver
import undetected_chromedriver as uc # 绕过Cloudflare检测
import sys
import io

# 设置控制台输出编码为 UTF-8，避免 Windows 下的编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cookie文件路径
COOKIE_FILE = 'cookies.json'

def wait_for_cloudflare_bypass(driver, timeout=30):
    """
    检测并等待 Cloudflare 验证完成
    返回: True 表示已绕过，False 表示仍被拦截
    """
    print("🔍 检查是否存在 Cloudflare 验证...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 检查页面标题和内容
            page_source = driver.page_source.lower()
            page_title = driver.title.lower()
            
            # Cloudflare 特征检测
            cloudflare_indicators = [
                'cloudflare' in page_title,
                'checking your browser' in page_source,
                'just a moment' in page_source,
                'please wait' in page_source and 'cloudflare' in page_source,
                'verify you are human' in page_source
            ]
            
            if any(cloudflare_indicators):
                print(f"⏳ 检测到 Cloudflare 验证，等待自动绕过... ({int(time.time() - start_time)}秒)")
                time.sleep(2)
                continue
            else:
                print("✅ Cloudflare 验证已绕过（或不存在）")
                return True
                
        except Exception as e:
            print(f"⚠️  检测过程出错: {e}")
            time.sleep(2)
    
    print("⚠️  Cloudflare 验证超时，可能需要手动操作")
    return False

def load_cookies_from_file(driver, domain_url):
    """
    从文件加载Cookie到WebDriver（适配浏览器扩展导出的格式）
    返回: True表示成功，False表示失败
    """
    if not os.path.exists(COOKIE_FILE):
        print(f"⚠️  Cookie文件不存在: {COOKIE_FILE}")
        return False
    
    try:
        # 必须先访问目标域名
        driver.get(domain_url)
        time.sleep(2)
        
        # 读取Cookie文件
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        # 转换并添加Cookie
        added_count = 0
        for cookie in cookies:
            try:
                # 转换浏览器扩展导出的Cookie格式到Selenium格式
                selenium_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                }
                
                # 处理过期时间（expirationDate是Unix时间戳）
                if 'expirationDate' in cookie:
                    selenium_cookie['expiry'] = int(cookie['expirationDate'])
                
                # sameSite处理
                if 'sameSite' in cookie and cookie['sameSite'] != 'unspecified':
                    selenium_cookie['sameSite'] = cookie['sameSite']
                
                driver.add_cookie(selenium_cookie)
                added_count += 1
            except Exception as e:
                print(f"⚠️  添加Cookie失败 ({cookie.get('name', 'unknown')}): {e}")
                continue
        
        print(f"✓ 成功加载 {added_count}/{len(cookies)} 个Cookie")
        return added_count > 0
    except Exception as e:
        print(f"❌ 加载Cookie失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_cookies_to_file(driver):
    """
    保存当前浏览器的Cookie到文件（Selenium格式）
    """
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        print(f"✓ Cookie已保存到: {COOKIE_FILE} (共{len(cookies)}个)")
        return True
    except Exception as e:
        print(f"❌ 保存Cookie失败: {e}")
        return False

def initialize_browser_and_prepare_for_search(initial_entry_url, username, password, use_cookies=True):
    # 配置 Chrome 选项（undetected_chromedriver 会自动添加反检测措施）
    options = uc.ChromeOptions()
    options.add_argument(f'user-agent={get_random_user_agent()}') # 伪装User-Agent
    # options.add_argument('--headless=new')  # 无头模式（新版语法）
    options.add_argument('--start-maximized') # 启动时最大化窗口
    options.add_argument('--disable-blink-features=AutomationControlled') # 禁用自动化控制特征
    
    # 添加更多随机性和真实性
    options.add_argument('--disable-dev-shm-usage') # 解决资源限制
    options.add_argument('--no-sandbox') # 绕过操作系统安全模型
    options.add_argument(f'--window-size={random.choice(["1920,1080", "1366,768", "1440,900"])}') # 随机窗口大小
    
    # 使用 undetected_chromedriver（自动绕过检测）
    driver = uc.Chrome(options=options, version_main=None)  # version_main=None 自动检测Chrome版本
    
    # 设置随机的页面加载超时
    driver.set_page_load_timeout(60)
    
    # 额外的反检测措施（虽然 uc 已经做了很多，但多一层保险）
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 覆盖 chrome 对象
            window.chrome = {
                runtime: {}
            };
            
            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
    })

    try:
        # --- 尝试使用Cookie登录 ---
        cookie_loaded = False
        if use_cookies and os.path.exists(COOKIE_FILE):
            print("🍪 检测到Cookie文件，尝试使用Cookie登录...")
            cookie_loaded = load_cookies_from_file(driver, initial_entry_url)
            
            if cookie_loaded:
                # 刷新页面使Cookie生效
                driver.refresh()
                time.sleep(random.uniform(3, 5))
                
                # 等待 Cloudflare 验证（如果有）
                wait_for_cloudflare_bypass(driver, timeout=30)
                
                # 检查是否还在登录页面
                if "login" not in driver.current_url.lower() and "登录" not in driver.title:
                    print("✅ Cookie登录成功！跳过账号密码登录。")
                else:
                    print("⚠️  Cookie可能已过期，将使用账号密码登录...")
                    cookie_loaded = False
        
        # --- 如果Cookie登录失败，使用账号密码登录 ---
        if not cookie_loaded:
            driver.get(initial_entry_url)
            time.sleep(random.uniform(3, 7))
            
            # 检查并等待 Cloudflare 验证
            wait_for_cloudflare_bypass(driver, timeout=30)

            if "login" in driver.current_url.lower() or "登录" in driver.title:
                print("检测到登录界面，正在使用账号密码登录...")
                
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']"))
                )
                username_field.send_keys(username)

                password_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='密码']"))
                )
                password_field.send_keys(password)

                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., '登录')] | //span[contains(., '登录')] "))
                )
                login_button.click()

                time.sleep(random.uniform(5, 10))
                if "login" in driver.current_url.lower() or "登录" in driver.title:
                    print("❌ 登录失败或页面未正确跳转，请检查用户名和密码。")
                    return None
                else:
                    print("✅ 账号密码登录成功！")
                    # 登录成功后保存Cookie（覆盖旧的）
                    if use_cookies:
                        save_cookies_to_file(driver)
            else:
                print("未检测到登录界面，假设已登录或无需登录。")
        
        driver.get("https://sim.3ue.com/#/digitalsuite/home")
        time.sleep(random.uniform(10, 15)) # 增加等待页面跳转到 sim.3ue.com/#/digitalsuite/home 的时间
        
        # 检查并等待 Cloudflare 验证（关键步骤）
        if not wait_for_cloudflare_bypass(driver, timeout=60):
            print("⚠️  Cloudflare 验证未通过，但尝试继续...")
        
        # 此时应该已经位于 sim.3ue.com/#/digitalsuite/home，准备进行搜索
        print("已进入SimilarWeb数字套件首页，准备进行搜索。")
        return driver

    except Exception as e:
        print(f"初始化浏览器或登录时发生错误: {e}")
        return None

def search_and_scrape_website_data(driver, website_to_search, data_url_template):
    # --- 数据抓取核心逻辑 ---
    print(f"正在准备访问网站数据页面: {website_to_search}")

    # 初始化所有变量，设置默认值
    desktop_percent_str = "N/A"
    mobile_percent_str = "N/A"
    desktop_percent = 0.0 # 用于验证
    mobile_percent = 0.0 # 用于验证
    visits_data = 0.0
    monthly_unique_visitors_data = 0.0
    users_tab_data = 0.0
    pages_per_visit_data = 0.0
    avg_visit_duration_data = "N/A"
    bounce_rate_data = "N/A"
    visits_per_visitor_data = 0.0

    try:
        # 导航到目标数据页面
        target_data_page_url = data_url_template.format(website_name=website_to_search)
        print(f"将直接导航到: {target_data_page_url}")
        driver.get(target_data_page_url)
        time.sleep(random.uniform(3, 7)) # 额外等待数据页面加载
        
        # 检查 Cloudflare 验证
        if not wait_for_cloudflare_bypass(driver, timeout=30):
            print("⚠️  检测到 Cloudflare 验证，但尝试继续...")

        # 等待网站性能数据页面加载（使用更长的固定等待时间，替代不稳定的元素检测）
        print("正在等待网站性能数据页面加载...")
        time.sleep(random.uniform(8, 12)) # 增加等待时间，确保页面和动态内容完全加载
        print("等待完成，尝试提取 desktopPersent 和 mobilePercent 数据...")

        # --- desktopPersent 和 mobilePercent 的提取和验证 ---
        try:
            # 尝试多种选择器策略以提高稳定性
            desktop_xpath = "(//span[contains(@class, 'LabelValue')])[1]"
            desktop_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, desktop_xpath))
            )
            desktop_percent_str = desktop_element.text.strip()
            print(f"提取到桌面端数据: {desktop_percent_str}")
            if desktop_percent_str.endswith('%') and desktop_percent_str[:-1].strip().upper() != "N/A":
                desktop_percent = float(desktop_percent_str[:-1])
            
            mobile_xpath = "(//span[contains(@class, 'LabelValue')])[2]"
            mobile_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, mobile_xpath))
            )
            mobile_percent_str = mobile_element.text.strip()
            print(f"提取到移动端数据: {mobile_percent_str}")
            if mobile_percent_str.endswith('%') and mobile_percent_str[:-1].strip().upper() != "N/A":
                mobile_percent = float(mobile_percent_str[:-1])
            
            # 只有当两个百分比都成功提取并转换为非零数字时才进行验证
            if desktop_percent != 0.0 and mobile_percent != 0.0:
                sum_check = (abs(desktop_percent + mobile_percent - 100.0) < 0.1) # 允许浮点数误差
                if not sum_check:
                    print(f"错误：desktopPersent ({desktop_percent_str}) + mobilePercent ({mobile_percent_str}) 不等于 100%。")
                    return "N/A", "N/A", 0.0, 0.0, 0.0, 0.0, "N/A", "N/A"
            else:
                print(f"错误：desktopPersent ({desktop_percent_str}) 或 mobilePercent ({mobile_percent_str}) 数据无效或缺失，无法进行相加验证。")
                return "N/A", "N/A", 0.0, 0.0, 0.0, 0.0, "N/A", "N/A"

        except TimeoutException:
            print(f"错误：在 {website_to_search} 页面未能在指定时间内找到 desktopPersent 或 mobilePercent 元素，XPath 可能不正确或页面未完全加载。")
            return "N/A", "N/A", 0.0, 0.0, 0.0, 0.0, "N/A", "N/A"

        # --- 其他指标的独立提取 ---
        # 提取 visits 数据
        try:
            visits_xpath = "//div[text()='每月访问量']/ancestor::div[contains(@class, 'MetricContainer')]/descendant::div[contains(@class, 'MetricValue')]"
            visits_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, visits_xpath))
            )
            visits_str = visits_element.text.strip()
            if visits_str.upper() != "N/A":
                visits_data = convert_metric_value_to_number(visits_str)
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 visits 元素。")

        # 提取 monthly_unique_visitors 数据
        try:
            monthly_unique_visitors_xpath = "//div[text()='月独立访客数']/../following-sibling::div/div[contains(@class, 'MetricValue')]"
            monthly_unique_visitors_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, monthly_unique_visitors_xpath))
            )
            monthly_unique_visitors_str = monthly_unique_visitors_element.text.strip()
            if monthly_unique_visitors_str.upper() != "N/A":
                monthly_unique_visitors_data = convert_metric_value_to_number(monthly_unique_visitors_str)
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 monthly_unique_visitors 元素。")

        # 计算 visits_per_visitor
        if visits_data != 0.0 and monthly_unique_visitors_data != 0.0:
            raw_visits_per_visitor = visits_data / monthly_unique_visitors_data
            visits_per_visitor_data = round(raw_visits_per_visitor, 2)
        else:
            print("无法计算 visits_per_visitor，因为 visits 或 monthlyUniqueVisitors 数据无效。")

        # 提取 users_tab 数据
        try:
            users_tab_xpath = "//div[text()='已消除重叠的受众']/ancestor::div[contains(@class, 'MetricContainer')]/descendant::div[contains(@class, 'MetricValue')]"
            users_tab_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, users_tab_xpath))
            )
            users_tab_str = users_tab_element.text.strip()
            if users_tab_str.upper() != "N/A":
                users_tab_data = convert_metric_value_to_number(users_tab_str)
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 users_tab 元素。")

        # 提取 pages-per-visit 数据
        try:
            pages_per_visit_xpath = "//div[text()='页面数/访问']/ancestor::div[contains(@class, 'MetricContainer')]/descendant::div[contains(@class, 'MetricValue')]"
            pages_per_visit_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, pages_per_visit_xpath))
            )
            pages_per_visit_str = pages_per_visit_element.text.strip()
            if pages_per_visit_str.upper() != "N/A":
                pages_per_visit_data = convert_metric_value_to_number(pages_per_visit_str)
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 pages-per-visit 元素。")

        # 提取 avg_visit_duration 数据
        try:
            avg_visit_duration_xpath = "//div[text()='访问持续时间']/ancestor::div[contains(@class, 'MetricContainer')]/descendant::div[contains(@class, 'MetricValue')]"
            avg_visit_duration_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, avg_visit_duration_xpath))
            )
            avg_visit_duration_str = avg_visit_duration_element.text.strip()
            if avg_visit_duration_str.upper() != "N/A":
                avg_visit_duration_data = avg_visit_duration_str # 保持字符串
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 avg_visit_duration 元素。")

        # 提取 bounce_rate 数据
        try:
            bounce_rate_xpath = "//div[text()='跳出率']/ancestor::div[contains(@class, 'MetricContainer')]/descendant::div[contains(@class, 'MetricValue')]"
            bounce_rate_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, bounce_rate_xpath))
            )
            bounce_rate_str = bounce_rate_element.text.strip()
            if bounce_rate_str.upper() != "N/A":
                bounce_rate_data = bounce_rate_str # 保持字符串
        except TimeoutException:
            print(f"警告：在 {website_to_search} 页面未能在指定时间内找到 bounce_rate 元素。")
            
        return desktop_percent_str, mobile_percent_str, visits_data, visits_per_visitor_data, users_tab_data, pages_per_visit_data, avg_visit_duration_data, bounce_rate_data

    except TimeoutException:
        print(f"错误：在 {website_to_search} 页面未能在指定时间内加载。")
        return "N/A", "N/A", 0.0, 0.0, 0.0, 0.0, "N/A", "N/A"
    except Exception as e:
        print(f"访问数据页面或抓取数据时发生错误: {e}")
        return "N/A", "N/A", 0.0, 0.0, 0.0, 0.0, "N/A", "N/A"

def convert_metric_value_to_number(value_str):
    """
    将MetricValue字符串（如"224.8M", "123K", "1,234", "1.2万", "3亿"）转换为数字。
    """
    if value_str is None or (isinstance(value_str, str) and value_str.strip().upper() == "N/A"):
        return 0.0 # 根据要求，如果为N/A或None，返回0.0

    value_str = value_str.strip().replace(',', '') # 移除千位分隔符

    if value_str.endswith('M'):
        return float(value_str[:-1]) * 1_000_000
    elif value_str.endswith('K'):
        return float(value_str[:-1]) * 1_000
    elif value_str.endswith('亿'):
        return float(value_str[:-1]) * 100_000_000
    elif value_str.endswith('万'):
        return float(value_str[:-1]) * 10_000
    elif value_str.endswith('千'):
        return float(value_str[:-1]) * 1_000
    else:
        try:
            # 尝试转换为浮点数，包括处理百分比（去除百分号后转换）
            if value_str.endswith('%'):
                return float(value_str[:-1])
            return float(value_str)
        except ValueError:
            return value_str # 如果无法转换成数字，则返回原始字符串

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.67",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/90.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]
    return random.choice(user_agents)

def get_first_url_from_file(urls_file_path):
    """
    读取urls.txt文件的第一行URL
    返回URL字符串，如果文件为空或不存在返回None
    """
    try:
        with open(urls_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                return lines[0].strip()
            return None
    except FileNotFoundError:
        print(f"错误：文件 {urls_file_path} 不存在")
        return None
    except Exception as e:
        print(f"读取URL文件时发生错误: {e}")
        return None

def remove_first_url_from_file(urls_file_path):
    """
    删除urls.txt文件的第一行URL
    """
    try:
        with open(urls_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 写回剩余的行（跳过第一行）
        with open(urls_file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines[1:])
        
        remaining_count = len(lines) - 1
        print(f"已从URL列表中删除该URL，剩余 {remaining_count} 个URL待处理")
        return True
    except Exception as e:
        print(f"删除URL时发生错误: {e}")
        return False

def count_remaining_urls(urls_file_path):
    """
    统计urls.txt中剩余的URL数量
    """
    try:
        with open(urls_file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def check_duplicate_data(output_file_path):
    """
    检查最后三个JSON数据的desktopPersent和visits是否完全相同
    如果相同则返回True（表示检测到重复），否则返回False
    """
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 至少需要3条记录才能检查
        if len(lines) < 3:
            return False
        
        # 获取最后3条记录
        last_three = []
        for line in lines[-3:]:
            if line.strip():
                data = json.loads(line)
                # 获取第一个（也是唯一）的键值对
                url = list(data.keys())[0]
                values = data[url]
                last_three.append({
                    'desktopPersent': values.get('desktopPersent'),
                    'visits': values.get('visits')
                })
        
        # 检查最后三个是否完全相同
        if len(last_three) == 3:
            if (last_three[0]['desktopPersent'] == last_three[1]['desktopPersent'] == last_three[2]['desktopPersent'] and
                last_three[0]['visits'] == last_three[1]['visits'] == last_three[2]['visits']):
                return True
        
        return False
    except Exception as e:
        print(f"检查重复数据时出错: {e}")
        return False

if __name__ == "__main__":
    # chrome_driver_path = r"E:\chromedriver-win64\chromedriver-win64\chromedriver.exe"  # 已改用自动管理，无需手动指定
    initial_entry_url = "https://dash.3ue.com/zh-Hans/#/page/m/home"
    your_username = "sloth" 
    your_password = "b35iNGpgZcrd!Ge"
    
    # URLs文件路径（使用相对路径，更灵活）
    urls_file_path = "urls.txt"
    output_file_path = "similarweb_data.txt"

    # SimilarWeb数据页面的URL模板，使用{website_name}作为占位符
    base_data_url_template = "https://sim.3ue.com/#/digitalsuite/websiteanalysis/overview/website-performance/*/999/2025.01-2025.08?webSource=Total&key={website_name}"

    driver_instance = None
    try:
        print("正在启动浏览器并准备进行网站搜索...")
        # use_cookies=True 表示启用Cookie登录功能
        driver_instance = initialize_browser_and_prepare_for_search(initial_entry_url, your_username, your_password, use_cookies=True)

        if driver_instance:
            print("浏览器初始化和准备完成。开始循环抓取数据...")
            
            # 统计初始URL数量
            total_urls = count_remaining_urls(urls_file_path)
            print(f"URL列表中共有 {total_urls} 个网站待抓取")
            
            # 在开始批量抓取前清空输出文件内容
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write("") 
            print(f"已清空或创建输出文件: {output_file_path}\n")

            processed_count = 0
            start_time = time.time() # 记录开始时间
            
            # 循环处理：读取第一个URL -> 抓取 -> 删除
            while True:
                # 读取第一个URL
                current_url = get_first_url_from_file(urls_file_path)
                
                if current_url is None:
                    print("\n所有URL已处理完成！")
                    break
                
                processed_count += 1
                remaining = count_remaining_urls(urls_file_path)
                print(f"\n{'='*60}")
                print(f"正在处理第 {processed_count} 个网站: {current_url}")
                print(f"剩余待处理: {remaining - 1} 个")
                print(f"{'='*60}")
                
                time.sleep(random.uniform(3, 5)) # 每次请求间随机延时

                # 抓取数据
                desktop_percent_str, mobile_percent_str, visits_data, visits_per_visitor_data, users_tab_data, pages_per_visit_data, avg_visit_duration_data, bounce_rate_data = search_and_scrape_website_data(driver_instance, current_url, base_data_url_template)
                
                if desktop_percent_str is not None and mobile_percent_str is not None:
                    current_website_result = {
                        "desktopPersent": desktop_percent_str,
                        "mobilePercent": mobile_percent_str,
                        "visits": visits_data,
                        "visits_per_visitor": visits_per_visitor_data,
                        "users_tab": users_tab_data,
                        "pages-per-visit": pages_per_visit_data,
                        "avg_visit_duration": avg_visit_duration_data,
                        "bounce_rate": bounce_rate_data
                    }
                    
                    print(f"✓ 成功抓取 {current_url} 的数据：")
                    print(f"  - 桌面端: {desktop_percent_str}, 移动端: {mobile_percent_str}")
                    print(f"  - Visits: {visits_data}, 每次访客访问量: {visits_per_visitor_data:.2f}")
                    print(f"  - 已消除重叠的受众: {users_tab_data}, 页面数/访问: {pages_per_visit_data}")
                    print(f"  - 访问持续时间: {avg_visit_duration_data}, 跳出率: {bounce_rate_data}")

                    # 将当前网站的结果保存到文件
                    with open(output_file_path, 'a', encoding='utf-8') as f:
                        json.dump({current_url: current_website_result}, f, ensure_ascii=False)
                        f.write('\n')
                    print(f"✓ [{current_url}] 结果已保存到文件")
                    
                    # 抓取成功后，从urls.txt中删除该URL
                    remove_first_url_from_file(urls_file_path)
                    
                    # 检查最后三个数据是否重复
                    if check_duplicate_data(output_file_path):
                        print("\n" + "!"*60)
                        print("⚠️  警告：检测到连续三个网站的数据完全相同！")
                        print("这可能表示抓取出现了问题，程序将自动中断。")
                        print("!"*60)
                        break
                else:
                    print(f"✗ 抓取 {current_url} 数据失败，该URL将保留在列表中等待下次重试")
            
            end_time = time.time() # 记录结束时间
            total_time = end_time - start_time
            print(f"\n{'='*60}")
            print(f"所有抓取任务完成！")
            print(f"成功处理: {processed_count} 个网站")
            print(f"总耗时: {total_time:.2f} 秒 ({total_time/60:.2f} 分钟)")
            print(f"{'='*60}")
        else:
            print("浏览器初始化或登录失败，无法进行数据抓取。")

    except KeyboardInterrupt:
        print("\n\n用户中断程序，正在保存进度并退出...")
    except Exception as e:
        print(f"主程序运行发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver_instance:
            print("\n脚本运行结束，浏览器将自动关闭。等待 5 秒...")
            time.sleep(5) # 缩短等待时间到5秒
            driver_instance.quit()
