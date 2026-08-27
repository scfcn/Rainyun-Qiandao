import logging
import os
import random
import time
import sys
import threading
import json
import hashlib
import re
import subprocess
from datetime import datetime, timedelta

selenium_modules = None

def import_selenium_modules():
    global selenium_modules
    if selenium_modules is None:
        from selenium import webdriver
        from selenium.webdriver import ActionChains
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.webdriver import WebDriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.wait import WebDriverWait
        from selenium.common import TimeoutException
        
        selenium_modules = {
            'webdriver': webdriver,
            'ActionChains': ActionChains,
            'Options': Options,
            'Service': Service,
            'WebDriver': WebDriver,
            'By': By,
            'EC': EC,
            'WebDriverWait': WebDriverWait,
            'TimeoutException': TimeoutException
        }
    return selenium_modules

def unload_selenium_modules():
    global selenium_modules
    if selenium_modules is not None:
        modules_to_remove = [
            'selenium',
            'selenium.webdriver',
            'selenium.webdriver.chrome',
            'selenium.webdriver.chrome.options',
            'selenium.webdriver.chrome.service',
            'selenium.webdriver.chrome.webdriver',
            'selenium.webdriver.common',
            'selenium.webdriver.common.by',
            'selenium.webdriver.support',
            'selenium.webdriver.support.expected_conditions',
            'selenium.webdriver.support.wait',
            'selenium.common'
        ]
        
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]
        
        selenium_modules = None

def setup_sigchld_handler():
    import signal
    
    def sigchld_handler(signum, frame):
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
            except ChildProcessError:
                break
            except Exception:
                break
    
    if os.name == 'posix':
        signal.signal(signal.SIGCHLD, sigchld_handler)
        logger.info("已设置子进程自动回收机制")

def cleanup_zombie_processes():
    try:
        if os.name == 'posix':
            try:
                result = subprocess.run(['pgrep', '-f', 'chrome|chromedriver'], 
                                      capture_output=True, text=True, timeout=5)
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    zombie_count = 0
                    
                    for pid in pids:
                        if pid:
                            try:
                                stat_result = subprocess.run(['ps', '-p', pid, '-o', 'stat='], 
                                                           capture_output=True, text=True, timeout=2)
                                if 'Z' in stat_result.stdout:
                                    zombie_count += 1
                            except:
                                pass
                    
                    if zombie_count > 0:
                        logger.info(f"检测到 {zombie_count} 个僵尸进程")
                        subprocess.run(['pkill', '-9', '-f', 'chrome.*--type='], 
                                     timeout=5, stderr=subprocess.DEVNULL)
            except:
                pass
    except Exception as e:
        logger.debug(f"僵尸进程清理失败: {e}")

def get_random_user_agent(account_id: str) -> str:
    import datetime
    base_date = datetime.date(2022, 3, 29)
    base_version = 100
    days_diff = (datetime.date.today() - base_date).days
    current_ver = base_version + (days_diff // 32)
    
    user_agents = [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{current_ver}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{current_ver-1}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{current_ver-2}.0.0.0 Safari/537.36",
    ]
    
    account_hash = hashlib.sha256(account_id.encode()).hexdigest()
    seed = int(account_hash[:8], 16)
    rng = random.Random(seed)
    return rng.choice(user_agents)

def generate_fingerprint_script(account_id: str):
    account_hash = hashlib.sha256(account_id.encode()).hexdigest()
    seed = int(account_hash[:8], 16)
    rng = random.Random(seed)
    
    webgl_vendors = [
        ("Intel Inc.", "Intel Iris Xe Graphics"),
        ("Intel Inc.", "Intel UHD Graphics 770"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 4070/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
        ("AMD", "AMD Radeon RX 7800 XT"),
    ]
    vendor, renderer = rng.choice(webgl_vendors)
    
    hardware_concurrency = rng.choice([4, 6, 8, 12, 16])
    device_memory = rng.choice([8, 16, 32])
    languages = [["zh-CN", "zh"], ["zh-CN", "en-US"]]
    language = rng.choice(languages)
    canvas_noise_seed = rng.randint(1, 1000000)
    audio_noise = rng.uniform(0.00001, 0.0001)
    plugins_length = rng.randint(0, 5)
    
    fingerprint_script = f"""
    (function() {{
        'use strict';
        
        const getParameterProxyHandler = {{
            apply: function(target, thisArg, args) {{
                const param = args[0];
                if (param === 37445) return '{vendor}';
                if (param === 37446) return '{renderer}';
                return Reflect.apply(target, thisArg, args);
            }}
        }};
        
        try {{
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
        }} catch(e) {{}}
        
        try {{
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
        }} catch(e) {{}}
        
        const noiseSeed = {canvas_noise_seed};
        function seededRandom(seed) {{
            const x = Math.sin(seed) * 10000;
            return x - Math.floor(x);
        }}
        
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type, quality) {{
            const canvas = this;
            const ctx = canvas.getContext('2d');
            if (ctx) {{
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {{
                    if (seededRandom(noiseSeed + i) < 0.01) {{
                        data[i] = data[i] ^ 1;
                        data[i+1] = data[i+1] ^ 1;
                    }}
                }}
                ctx.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.apply(this, arguments);
        }};
        
        const audioNoise = {audio_noise};
        if (window.OfflineAudioContext) {{
            const originalGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function(channel) {{
                const result = originalGetChannelData.call(this, channel);
                for (let i = 0; i < result.length; i += 100) {{
                    const noise = Math.sin({canvas_noise_seed} + i) * audioNoise;
                    result[i] = result[i] + noise;
                }}
                return result;
            }};
        }}
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hardware_concurrency} }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {device_memory} }});
        Object.defineProperty(navigator, 'languages', {{ get: () => {language} }});
        Object.defineProperty(navigator, 'language', {{ get: () => '{language[0]}' }});
        Object.defineProperty(navigator, 'plugins', {{
            get: () => {{
                return {{ length: {plugins_length}, item: () => null, namedItem: () => null, refresh: () => {{}}, [Symbol.iterator]: function* () {{}} }};
            }}
        }});
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        window.chrome = {{ runtime: {{}}, loadTimes: function() {{}}, csi: function() {{}}, app: {{}} }};
    }})();
    """
    return fingerprint_script

def init_selenium(account_id: str, proxy: str = None):
    modules = import_selenium_modules()
    webdriver = modules['webdriver']
    Options = modules['Options']
    Service = modules['Service']
    
    ops = Options()
    ops.add_argument("--no-sandbox")
    ops.add_argument("--disable-dev-shm-usage")
    ops.add_argument("--disable-extensions")
    ops.add_argument("--disable-plugins")
    
    if proxy:
        ops.add_argument(f"--proxy-server=http://{proxy}")
        logger.info(f"浏览器已配置代理: {proxy}")
    
    user_agent = get_random_user_agent(account_id)
    ops.add_argument(f"--user-agent={user_agent}")
    logger.info(f"使用 User-Agent: {user_agent[:50]}...")
    
    if debug:
        ops.add_experimental_option("detach", True)
    
    ops.add_argument("--window-size=1920,1080")
    
    if linux:
        ops.add_argument("--headless")
        ops.add_argument("--disable-gpu")
        chromedriver_path = "/usr/bin/chromedriver"
        
        if os.path.exists(chromedriver_path):
            logger.info(f"使用 Docker 镜像的 ChromeDriver: {chromedriver_path}")
            service = Service(chromedriver_path)
        else:
            logger.info("使用 Selenium Manager 自动管理 ChromeDriver")
            service = Service()
        
        return webdriver.Chrome(service=service, options=ops)
    else:
        service = Service()
        return webdriver.Chrome(service=service, options=ops)

def dismiss_modal_confirm(driver, timeout):
    modules = import_selenium_modules()
    WebDriverWait = modules['WebDriverWait']
    EC = modules['EC']
    By = modules['By']
    TimeoutException = modules['TimeoutException']

    wait = WebDriverWait(driver, min(timeout, 5))
    try:
        confirm = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//footer[contains(@id,'modal') and contains(@id,'footer')]//button[contains(normalize-space(.), '确认')]")
            )
        )
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirm)
        except Exception:
            pass
        time.sleep(0.2)
        confirm.click()
        logger.info("已关闭弹窗：确认")
        time.sleep(0.5)
        return True
    except TimeoutException:
        return False
    except Exception:
        try:
            confirm = driver.find_element(By.XPATH, "//button[contains(normalize-space(.), '确认') and contains(@class,'btn')]")
            driver.execute_script("arguments[0].click();", confirm)
            logger.info("已关闭弹窗：确认")
            time.sleep(0.5)
            return True
        except Exception:
            return False

def wait_captcha_or_modal(driver, timeout):
    modules = import_selenium_modules()
    WebDriverWait = modules['WebDriverWait']
    EC = modules['EC']
    By = modules['By']
    TimeoutException = modules['TimeoutException']

    def find_visible_tcaptcha_iframe():
        try:
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[id^='tcaptcha_iframe']")
        except Exception:
            return None
        for fr in iframes:
            try:
                if fr.is_displayed() and fr.size.get("width", 0) > 0 and fr.size.get("height", 0) > 0:
                    return fr
            except Exception:
                continue
        return None

    end_time = time.time() + min(timeout, 8)
    while time.time() < end_time:
        if dismiss_modal_confirm(driver, timeout):
            return "modal"
        try:
            iframe = find_visible_tcaptcha_iframe()
            if iframe:
                return "captcha"
        except Exception:
            pass
        time.sleep(0.3)
    return "none"

def _legacy_cookie_path(account_id):
    """升级前使用 MD5 命名 Cookie 文件，仅用于匹配旧缓存文件名（非安全用途）。"""
    legacy_hash = hashlib.md5(account_id.encode()).hexdigest()[:16]
    return os.path.join("temp", "cookies", f"{legacy_hash}.json")


def save_cookies(driver, account_id):
    if not account_id:
        return
    os.makedirs("temp/cookies", exist_ok=True)
    account_hash = hashlib.sha256(account_id.encode()).hexdigest()[:16]
    cookie_path = os.path.join("temp", "cookies", f"{account_hash}.json")
    
    try:
        cookies = driver.get_cookies()
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False)
        logger.info("Cookie 已保存到本地")
    except Exception as e:
        logger.warning(f"保存 Cookie 失败: {e}")

def load_cookies(driver, account_id):
    if not account_id:
        return False
    account_hash = hashlib.sha256(account_id.encode()).hexdigest()[:16]
    cookie_path = os.path.join("temp", "cookies", f"{account_hash}.json")

    # 兼容升级前用 MD5 命名的旧 Cookie 缓存：命中则原子重命名迁移为新命名
    if not os.path.exists(cookie_path):
        legacy_path = _legacy_cookie_path(account_id)
        if os.path.exists(legacy_path):
            try:
                os.makedirs("temp/cookies", exist_ok=True)
                os.replace(legacy_path, cookie_path)
                logger.info("已将旧 MD5 Cookie 缓存迁移为 SHA-256 命名")
            except Exception as e:
                logger.warning(f"迁移旧 Cookie 失败，回退使用旧路径: {e}")
                cookie_path = legacy_path

    if not os.path.exists(cookie_path):
        logger.info("未找到本地 Cookie，将使用账号密码登录")
        return False
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        driver.get("https://app.rainyun.com/")
        time.sleep(1)
        
        for cookie in cookies:
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry'])
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        
        logger.info("已加载本地 Cookie")
        return True
    except Exception as e:
        logger.warning(f"加载 Cookie 失败: {e}")
        return False

def process_captcha(driver, wait):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    import ICR
    
    try:
        wait.until(EC.presence_of_element_located((By.ID, "slideBg")))
    except TimeoutException:
        logger.info("未检测到可处理验证码内容，跳过验证码处理")
        return

    download_captcha_img(driver, wait)
    
    positions = ICR.find_part_positions("temp/captcha.jpg", "temp/sprite.jpg", 'template')
    
    if positions:
        logger.info(f"识别到 {len(positions)} 个图案位置")
        
        for i, (x, y) in enumerate(positions):
            logger.info(f"图案 {i + 1} 位于 ({int(x)}, {int(y)})")
            slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
            style = slideBg.get_attribute("style")
            
            import re
            bg_width = float(re.search(r'width:\s*([\d.]+)px', style).group(1))
            bg_height = float(re.search(r'height:\s*([\d.]+)px', style).group(1))
            
            import cv2
            captcha = cv2.imread("temp/captcha.jpg")
            raw_w, raw_h = captcha.shape[1], captcha.shape[0]
            
            final_x = int(x / raw_w * bg_width - bg_width / 2)
            final_y = int(y / raw_h * bg_height - bg_height / 2)
            
            from selenium.webdriver import ActionChains
            ActionChains(driver).move_to_element_with_offset(slideBg, final_x, final_y).click().perform()
        
        confirm = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tcStatus"]/div[2]/div[2]/div/div')))
        logger.info("提交验证码")
        confirm.click()
        time.sleep(5)
        result = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
        if result.get_attribute("class") == 'tc-opera pointer show-success':
            logger.info("验证码通过")
            return
        else:
            logger.error("验证码未通过，正在重试")
    else:
        logger.error("验证码识别失败，正在重试")
    
    reload = driver.find_element(By.XPATH, '//*[@id="reload"]')
    time.sleep(5)
    reload.click()
    time.sleep(5)
    process_captcha(driver, wait)

def download_captcha_img(driver, wait):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.wait import WebDriverWait
    
    if os.path.exists("temp"):
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
    
    try:
        current_ua = driver.execute_script("return navigator.userAgent;")
    except Exception:
        current_ua = None
    
    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
    img1_style = slideBg.get_attribute("style")
    img1_url = get_url_from_style(img1_style)
    logger.info("开始下载验证码图片(1): " + img1_url)
    download_image(img1_url, "captcha.jpg", user_agent=current_ua)
    
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    download_image(img2_url, "sprite.jpg", user_agent=current_ua)

def download_image(url, filename, user_agent=None):
    import requests
    
    os.makedirs("temp", exist_ok=True)
    
    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            path = os.path.join("temp", filename)
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        else:
            logger.error(f"下载图片失败！状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"下载图片异常: {e}")
        return False

def get_url_from_style(style):
    import re
    return re.search(r'url\(["\']?(.*?)["\']?\)', style).group(1)

def run_checkin(account_user=None, account_pwd=None):
    modules = import_selenium_modules()
    webdriver = modules['webdriver']
    ActionChains = modules['ActionChains']
    By = modules['By']
    EC = modules['EC']
    WebDriverWait = modules['WebDriverWait']
    TimeoutException = modules['TimeoutException']
    
    current_user = account_user or user
    current_pwd = account_pwd or pwd
    driver = None
    retry_stats = {'count': 0}

    masked_user = f"{current_user[:3]}***{current_user[-3:] if len(current_user) > 6 else current_user}"
    
    class PrefixAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[%s] %s' % (self.extra['prefix'], msg), kwargs

    logger_adapter = PrefixAdapter(logger, {'prefix': masked_user})
    
    try:
        logger_adapter.info(f"开始执行签到任务...")
        
        logger_adapter.info("初始化 Selenium（账号专属配置）")
        driver = init_selenium(current_user)
        
        with open("stealth.min.js", mode="r") as f:
            js = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        
        fingerprint_js = generate_fingerprint_script(current_user)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": fingerprint_js})
        logger_adapter.info("已注入浏览器指纹脚本（账号专属指纹）")
        
        wait = WebDriverWait(driver, timeout)
        
        load_cookies(driver, current_user)
        logger_adapter.info("正在跳转积分页...")
        driver.get("https://app.rainyun.com/account/reward/earn")
        time.sleep(3)
        
        if "/auth/login" in driver.current_url:
            logger_adapter.info("Cookie 已失效，使用账号密码登录")
            
            try:
                username = wait.until(EC.visibility_of_element_located((By.NAME, 'login-field')))
                password = wait.until(EC.visibility_of_element_located((By.NAME, 'login-password')))
                login_button = wait.until(EC.visibility_of_element_located((By.XPATH,
                    '//*[@id="app"]/div[1]/div[1]/div/div[2]/fade/div/div/span/form/button')))
                username.send_keys(current_user)
                password.send_keys(current_pwd)
                login_button.click()
            except TimeoutException:
                logger_adapter.error("页面加载超时")
                return {
                    'status': False, 'msg': '页面加载超时', 'points': 0,
                    'username': masked_user,
                    'retries': retry_stats['count']
                }
            
            try:
                login_captcha = wait.until(EC.visibility_of_element_located((By.ID, 'tcaptcha_iframe_dy')))
                logger_adapter.warning("触发验证码！")
                driver.switch_to.frame("tcaptcha_iframe_dy")
                process_captcha(driver, wait)
            except TimeoutException:
                logger_adapter.info("未触发验证码")
            
            time.sleep(5)
            driver.switch_to.default_content()
            dismiss_modal_confirm(driver, timeout)
            
            if "/dashboard" in driver.current_url or "/account" in driver.current_url:
                logger_adapter.info("登录成功！")
                save_cookies(driver, current_user)
                driver.get("https://app.rainyun.com/account/reward/earn")
                time.sleep(2)
            else:
                logger_adapter.error(f"登录失败，当前页面: {driver.current_url}")
                return {
                    'status': False, 'msg': '登录失败', 'points': 0,
                    'username': masked_user,
                    'retries': retry_stats['count']
                }
        else:
            logger_adapter.info("Cookie 有效，免密登录成功！")
        
        if "/account/reward/earn" not in driver.current_url:
            driver.get("https://app.rainyun.com/account/reward/earn")

        driver.implicitly_wait(5)
        time.sleep(1)
        dismiss_modal_confirm(driver, timeout)
        dismiss_modal_confirm(driver, timeout)
        
        earn = driver.find_element(By.XPATH,
                                   '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div[1]/div/div[1]/div/span[2]/a')
        btn_text = earn.text.strip()
        logger_adapter.info(f"签到按钮文字: [{btn_text}]")
        
        if btn_text == "领取奖励":
            logger_adapter.info("点击领取奖励")
            earn.click()
            state = wait_captcha_or_modal(driver, timeout)
            if state == "captcha":
                logger_adapter.info("处理验证码")
                try:
                    captcha_iframe = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "iframe[id^='tcaptcha_iframe']")))
                    driver.switch_to.frame(captcha_iframe)
                    process_captcha(driver, wait)
                finally:
                    driver.switch_to.default_content()
                driver.implicitly_wait(5)
            else:
                logger_adapter.info("未触发验证码")
        else:
            logger_adapter.info(f"今日已签到（按钮显示: {btn_text}）")

        points_raw = driver.find_element(By.XPATH,
                                         '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3').get_attribute("textContent")
        current_points = int(''.join(re.findall(r'\d+', points_raw)))
        logger_adapter.info(f"当前剩余积分: {current_points} | 约为 {current_points / 2000:.2f} 元")
        logger_adapter.info("签到任务执行成功！")
        return {
            'status': True,
            'msg': '签到成功',
            'points': current_points,
            'username': masked_user,
            'retries': retry_stats['count']
        }
            
    except Exception as e:
        logger_adapter.error(f"签到任务执行失败: {e}")
        import traceback
        logger_adapter.error(f"详细错误信息: {traceback.format_exc()}")
        return {
            'status': False,
            'msg': f'执行异常: {str(e)[:50]}...',
            'points': 0,
            'username': masked_user,
            'retries': retry_stats['count']
        }
    finally:
        if driver is not None:
            try:
                logger_adapter.info("正在关闭 WebDriver...")
                try:
                    driver.quit()
                    logger_adapter.info("WebDriver 已安全关闭")
                except Exception as e:
                    logger_adapter.error(f"关闭 WebDriver 时出错: {e}")
                
                time.sleep(1)
                
                try:
                    if hasattr(driver, 'service') and driver.service.process:
                        process = driver.service.process
                        pid = process.pid
                        
                        if os.name == 'posix' and pid:
                            try:
                                subprocess.run(['pkill', '-9', '-P', str(pid)], stderr=subprocess.DEVNULL)
                            except Exception:
                                pass

                        if process.poll() is None:
                            process.terminate()
                            try:
                                process.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            logger_adapter.info(f"已终止 ChromeDriver 进程 (PID: {pid})")
                except Exception as e:
                    logger_adapter.debug(f"清理 ChromeDriver 进程时出错: {e}")
                        
            except Exception as e:
                logger_adapter.error(f"WebDriver 清理过程出现异常: {e}")
        
        try:
            unload_selenium_modules()
        except:
            pass

def parse_accounts():
    usernames_raw = os.getenv("RAINYUN_USER", "").replace("\r\n", "\n").replace("\r", "\n")
    passwords_raw = os.getenv("RAINYUN_PASS", "").replace("\r\n", "\n").replace("\r", "\n")
    
    usernames = [u for u in usernames_raw.split("\n") if u.strip()]
    passwords = [p for p in passwords_raw.split("\n") if p.strip()]
    
    if len(usernames) != len(passwords):
        logger.warning("用户名和密码数量不匹配，只使用匹配的部分")
        min_len = min(len(usernames), len(passwords))
        usernames = usernames[:min_len]
        passwords = passwords[:min_len]
    
    accounts = [(u.strip(), p.strip()) for u, p in zip(usernames, passwords) if u.strip() and p.strip()]
    
    if not accounts:
        single_user = os.getenv("RAINYUN_USER", "username")
        single_pwd = os.getenv("RAINYUN_PASS", "password")
        accounts = [(single_user, single_pwd)]
    
    logger.info(f"检测到 {len(accounts)} 个账号")
    for i, (username, _) in enumerate(accounts, 1):
        masked_user = f"{username[:3]}***{username[-3:] if len(username) > 6 else username}"
        logger.info(f"账号 {i}: {masked_user}")
    
    return accounts

def _safe_int(env_value, default, name=""):
    """安全地把环境变量解析为整数；非法值时回退默认值并打印警告，不抛出异常。"""
    try:
        return int(env_value)
    except (ValueError, TypeError):
        if name:
            print(f"警告: 环境变量 {name} 值无效: {env_value!r}，已回退默认值 {default}")
        return default


def run_all_accounts():
    import concurrent.futures

    max_retries = _safe_int(os.getenv("CHECKIN_MAX_RETRIES", "2"), 2, "CHECKIN_MAX_RETRIES")
    max_workers = _safe_int(os.getenv("MAX_WORKERS", "3"), 3, "MAX_WORKERS")
    stagger_delay = _safe_int(os.getenv("MAX_DELAY", "15"), 15, "MAX_DELAY")
    
    accounts = parse_accounts()
    results = {}
    
    for i, (username, password) in enumerate(accounts):
        results[username] = {
            'password': password,
            'result': None,
            'retry_count': 0,
            'index': i + 1
        }
    
    pending_accounts = list(accounts)
    current_attempt = 0
    
    while pending_accounts and current_attempt <= max_retries:
        if current_attempt == 0:
            logger.info(f"========== 开始执行签到任务（共 {len(pending_accounts)} 个账号，并发数: {max_workers}） ==========")
        else:
            logger.info(f"========== 第 {current_attempt} 次重试（共 {len(pending_accounts)} 个失败账号） ==========")
        
        failed_accounts = []
        future_to_account = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i, (username, password) in enumerate(pending_accounts):
                if i > 0 and stagger_delay > 0:
                     lower_bound = 5
                     upper_bound = max(5, stagger_delay)
                     actual_delay = random.randint(lower_bound, upper_bound)
                     logger.info(f"随机等待 {actual_delay} 秒后启动下一个账号任务...")
                     time.sleep(actual_delay)
                
                account_idx = results[username]['index']
                retry_info = f"（第 {results[username]['retry_count'] + 1} 次尝试）" if results[username]['retry_count'] > 0 else ""
                logger.info(f"========== 启动账号 {account_idx}/{len(accounts)} {retry_info} ==========")
                
                future = executor.submit(run_checkin, username, password)
                future_to_account[future] = username

            for future in concurrent.futures.as_completed(future_to_account):
                username = future_to_account[future]
                account_idx = results[username]['index']
                
                try:
                    result = future.result()
                    results[username]['result'] = result
                    
                    if result['status']:
                        logger.info(f"✅ 账号 {account_idx} 签到成功")
                    else:
                        logger.error(f"❌ 账号 {account_idx} 签到失败: {result['msg']}")
                        results[username]['retry_count'] += 1
                        if results[username]['retry_count'] <= max_retries:
                            failed_accounts.append((username, results[username]['password']))
                except Exception as e:
                    logger.error(f"❌ 账号 {account_idx} 执行异常: {e}")
                    results[username]['retry_count'] += 1
                    if results[username]['retry_count'] <= max_retries:
                        failed_accounts.append((username, results[username]['password']))

        pending_accounts = failed_accounts
        current_attempt += 1
        
        if pending_accounts:
            retry_wait = 60
            logger.info(f"等待 {retry_wait} 秒后开始重试 {len(pending_accounts)} 个失败账号...")
            time.sleep(retry_wait)
    
    final_results = [results[username]['result'] for username, _ in accounts]
    success_count = len([r for r in final_results if r and r['status']])
    
    retry_accounts = [(username, results[username]['retry_count']) for username, _ in accounts if results[username]['retry_count'] > 0]
    if retry_accounts:
        logger.info(f"重试统计: {len(retry_accounts)} 个账号进行了重试")
        for username, count in retry_accounts:
            masked_user = f"{username[:3]}***{username[-3:] if len(username) > 6 else username}"
            final_status = "成功" if results[username]['result'] and results[username]['result']['status'] else "失败"
            logger.info(f"  - {masked_user}: 重试 {count} 次, 最终{final_status}")
    
    failed_count = len(accounts) - success_count
    notify_only_failure = os.getenv("NOTIFY_ONLY_FAILURE", "false").lower() == "true"
    
    if accounts:
        if notify_only_failure and failed_count == 0:
            logger.info("所有账号签到成功，跳过推送通知（NOTIFY_ONLY_FAILURE=true）")
        else:
            try:
                import notify
                logger.info("正在发送通知...")
                
                notification_title = f"雨云签到: {success_count}/{len(accounts)} 成功"
                notification_content = f"雨云自动签到结果汇总：\n\n总账户数: {len(accounts)}\n成功账户数: {success_count}\n失败账户数: {failed_count}\n\n详细结果：\n"
                
                for i, result in enumerate(final_results, 1):
                    if result:
                        if result['status']:
                            notification_content += f"\n{i}. {result['username']}: ✅ 成功 - 积分 {result['points']}"
                        else:
                            notification_content += f"\n{i}. {result['username']}: ❌ 失败 - {result['msg']}"
                
                notify.send(notification_title, notification_content)
            except Exception as e:
                logger.warning(f"发送通知失败: {e}")
    
    logger.info("任务完成，执行最终清理...")
    cleanup_zombie_processes()
    
    return success_count > 0


if __name__ == "__main__":
    timeout = _safe_int(os.getenv("TIMEOUT", "15000"), 15000, "TIMEOUT") // 1000
    max_delay = _safe_int(os.getenv("MAX_DELAY", "5"), 5, "MAX_DELAY")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    linux = os.getenv("LINUX_MODE", "true").lower() == "true" or os.path.exists("/.dockerenv")
    
    user = os.getenv("RAINYUN_USER", "username").split("|")[0]
    pwd = os.getenv("RAINYUN_PASS", "password").split("|")[0]
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    ver = "2.6 (ICR + Cookie)"
    logger.info("------------------------------------------------------------------")
    logger.info(f"雨云自动签到工作流 v{ver}")
    logger.info("------------------------------------------------------------------")
    
    setup_sigchld_handler()
    cleanup_zombie_processes()
    
    run_all_accounts()
