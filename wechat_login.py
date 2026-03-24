import time
import os
import json
from playwright.sync_api import sync_playwright


def playwright_login(headless=False):
    """
    使用 Playwright 自动打开微信公众号后台，扫码登录并提取完整的 Cookie 和 Token。
    
    参数:
        headless (bool): 是否使用无头模式配置（如果在服务器运行，请设为 True）。
        
    返回:
        tuple: (cookie_str, token)
    """
    print(f"\n🚀 开始启动浏览器 (Headless={headless})...")
    print("💡 提示: 如果是第一次运行，可能需要下载浏览器内核。请确保执行过 `playwright install chromium`\n")

    with sync_playwright() as p:
        # 启动 Chromium
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        print("🌐 正在访问微信公众平台登录页...")
        page.goto("https://mp.weixin.qq.com/", wait_until="networkidle")

        # 判断是否需要登录扫描
        if "cgi-bin/home" not in page.url:
            print("⏳ 等待二维码加载...")
            qr_locator = page.locator(".login__type__container__scan__qrcode")
            
            # 确保二维码元素可见
            try:
                qr_locator.wait_for(state="visible", timeout=10000)
                
                # 在无头模式下，自动截图保存二维码供用户扫描
                qr_path = "login_qrcode.png"
                qr_locator.screenshot(path=qr_path)
                print(f"📥 【扫码提示】二维码图片已保存到当前目录下的 {qr_path}")
                print(f"📸 请在电脑或手机上打开该图片并使用微信扫一扫")

            except Exception as e:
                print(f"⚠️ 获取二维码截图失败: {e}")
                print("请确保网络正常或检查页面结构是否改变。")

            print("\n🕒 正在等待扫码并确认登录...(超时时间：2分钟)")
            
            try:
                # 轮询等待 URL 变化，直到拿到包含 token 的 URL (不依赖复杂的通配符匹配)
                page.wait_for_function("() => window.location.href.includes('token=')", timeout=120000)
                print("✅ 扫码成功，页面已跳转！")
            except Exception as e:
                print("\n❌ 登录超时，未能检测到登录成功跳转。请重试。")
                browser.close()
                return None, None
                
            # 清理二维码图片
            if os.path.exists("login_qrcode.png"):
                os.remove("login_qrcode.png")

        # 此时页面已经加载，开始提取 Token
        current_url = page.url
        print("🔗 提取 Token 中...")
        
        # URL 格式如: https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=123456789
        token = ""
        if "token=" in current_url:
            token = current_url.split("token=")[1].split("&")[0]
        else:
            print("❌ 未能在 URL 中找到 token，请检查页面状态。")
            browser.close()
            return None, None

        # 提取全部 Cookies
        print("🍪 提取完整 Cookie 中...")
        cookies = context.cookies()
        
        # 组装为 requests 使用的格式 "key1=value1; key2=value2"
        cookie_parts = []
        for c in cookies:
            cookie_parts.append(f"{c['name']}={c['value']}")
        cookie_str = "; ".join(cookie_parts)

        print("\n🎉 成功获取登录凭证！")
        print(f"🎟️  Token: {token}")
        print(f"🛡️  已提取 {len(cookies)} 个 Cookie 项 (包含 HttpOnly 下的核心凭证)\n")

        browser.close()
        return cookie_str, token


if __name__ == "__main__":
    # 简单的本地测试入口
    cookie, token = playwright_login(headless=False)
    if cookie and token:
        with open("credentials_test.json", "w", encoding="utf-8") as f:
            json.dump({"cookie": cookie, "token": token}, f, indent=2)
        print("测试完成，写入凭证到 credentials_test.json")
