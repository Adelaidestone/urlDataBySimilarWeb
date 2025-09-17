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

def initialize_browser_and_prepare_for_search(initial_entry_url, username, password, chrome_driver_path):
    # 配置 Chrome 选项，添加反反爬措施
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={get_random_user_agent()}') # 伪装User-Agent
    # options.add_argument('--headless')  # 无头模式，不显示浏览器界面
    # options.add_argument('--disable-gpu') # 禁用GPU，无头模式下可能需要
    options.add_argument('--start-maximized') # 启动时最大化窗口，有时有助于定位元素
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"]) # 禁用DevTools listening的日志和自动化提示
    options.add_experimental_option('useAutomationExtension', False) # 禁用自动化扩展

    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # 移除 WebDriver 标记，避免被识别
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    try:
        driver.get(initial_entry_url) # 首先访问入口URL (dash.3ue.com的首页)
        time.sleep(random.uniform(3, 7))

        # --- 处理登录界面 ---
        if "login" in driver.current_url.lower() or "登录" in driver.title:
            print("检测到登录界面，正在尝试登录...")
            
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']"))
            )
            username_field.send_keys(username)
            # print("已输入用户名") # 移除详细打印

            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='密码']"))
            )
            password_field.send_keys(password)
            # print("已输入密码") # 移除详细打印

            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '登录')] | //span[contains(., '登录')] "))
            )
            login_button.click()
            # print("已点击登录按钮") # 移除详细打印

            time.sleep(random.uniform(5, 10)) # 随机延时等待页面跳转和数据加载
            if "login" in driver.current_url.lower() or "登录" in driver.title:
                print("登录失败或页面未正确跳转，请检查用户名和密码。")
                return None
            else:
                print("登录成功。")
        else:
            print("未检测到登录界面，假设已登录或无需登录。")
        
        driver.get("https://sim.3ue.com/#/digitalsuite/home")
        time.sleep(random.uniform(10, 15)) # 增加等待页面跳转到 sim.3ue.com/#/digitalsuite/home 的时间
        
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

        # 等待网站性能数据页面加载
        print("正在等待网站性能数据页面加载...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='BaseFlex-bjWZGo FlexRow-hsoCCV TopPageWidgetsRow-diqVyP TopPageWidgetsRowWrap-fLcndQ dYkKBh iCsmVo cXClbx gHnUto']"))
        )
        print("网站数据页面加载完成，尝试提取 desktopPersent 和 mobilePercent 数据...")
        time.sleep(random.uniform(3, 7)) # 额外随机等待，确保所有动态内容都渲染完成

        # --- desktopPersent 和 mobilePercent 的提取和验证 ---
        try:
            desktop_xpath = "(//span[@class='LabelValue-bIRZky bbhWVt'])[1]"
            desktop_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, desktop_xpath))
            )
            desktop_percent_str = desktop_element.text.strip()
            if desktop_percent_str.endswith('%') and desktop_percent_str[:-1].strip().upper() != "N/A":
                desktop_percent = float(desktop_percent_str[:-1])
            
            mobile_xpath = "(//span[@class='LabelValue-bIRZky bbhWVt'])[2]"
            mobile_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, mobile_xpath))
            )
            mobile_percent_str = mobile_element.text.strip()
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

if __name__ == "__main__":
    chrome_driver_path = r"E:\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    initial_entry_url = "https://dash.3ue.com/zh-Hans/#/page/m/home"
    your_username = "sloth" 
    your_password = "b35iNGpgZcrd!Ge"
    
    # 查询的网站列表
    target_websites = [
       "http.www.mophouse.com"
        # 添加更多您需要查询的网站，例如："google.com", "bing.com"
        # 注意：gemini.google.com, claude.ai, grok.com 可能在 SimilarWeb 上没有直接的公开数据，抓取可能会失败。
    ]

    # SimilarWeb数据页面的URL模板，使用{website_name}作为占位符
    base_data_url_template = "https://sim.3ue.com/#/digitalsuite/websiteanalysis/overview/website-performance/*/999/2025.01-2025.08?webSource=Total&key={website_name}"

    driver_instance = None
    try:
        print("正在启动浏览器并准备进行网站搜索...")
        driver_instance = initialize_browser_and_prepare_for_search(initial_entry_url, your_username, your_password, chrome_driver_path)

        if driver_instance:
            print("浏览器初始化和准备完成。开始批量导航并抓取 desktopPersent、mobilePercent、visits、visits_per_visitor、users_tab、pages-per-visit、avg_visit_duration 和 bounce_rate 数据...")
            all_results = {}
            output_file_path = r"E:\aiUrlDataBySimilarWeb\similarweb_data.txt"
            # 在开始批量抓取前清空文件内容
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write("") 
            print(f"已清空或创建输出文件: {output_file_path}")

            start_time = time.time() # 记录开始时间
            for i, website_name in enumerate(target_websites):
                print(f"\n--- 正在导航并抓取第 {i+1} 个网站: {website_name} ---")
                
                # driver_instance.get("https://sim.3ue.com/#/digitalsuite/home") # 移除这行，避免重新导航到首页
                time.sleep(random.uniform(3, 5)) # 等待页面加载

                desktop_percent_str, mobile_percent_str, visits_data, visits_per_visitor_data, users_tab_data, pages_per_visit_data, avg_visit_duration_data, bounce_rate_data = search_and_scrape_website_data(driver_instance, website_name, base_data_url_template)
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
                    all_results[website_name] = current_website_result # 也更新到all_results字典中
                    print(f"成功抓取 {website_name} 的数据：桌面端 {desktop_percent_str}，移动端 {mobile_percent_str}，Visits：{visits_data}，每次访客访问量：{visits_per_visitor_data:.2f}，已消除重叠的受众：{users_tab_data}，页面数/访问：{pages_per_visit_data}，访问持续时间：{avg_visit_duration_data}，跳出率：{bounce_rate_data}")

                    # 将当前网站的结果保存到文件
                    with open(output_file_path, 'a', encoding='utf-8') as f:
                        json.dump({website_name: current_website_result}, f, ensure_ascii=False)
                        f.write('\n')
                    print(f"[{website_name}] 结果已保存到文件。")
                else:
                    print(f"抓取 {website_name} 的 desktopPersent、mobilePercent、visits、visits_per_visitor、users_tab、pages-per-visit、avg_visit_duration 或 bounce_rate 数据失败。")
            
            end_time = time.time() # 记录结束时间
            total_time = end_time - start_time
            print("\n所有批量抓取完成！")
            print("所有结果:", all_results)
            print(f"总共耗时: {total_time:.2f} 秒")
        else:
            print("浏览器初始化或登录失败，无法进行数据抓取。")

    except Exception as e:
        print(f"主程序运行发生错误: {e}")
    finally:
        if driver_instance:
            print("脚本运行结束，浏览器将自动关闭。等待 20 分钟...")
            time.sleep(1200) # 等待20分钟 (20 * 60 秒)
            driver_instance.quit()
