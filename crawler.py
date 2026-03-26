# coding: utf-8
"""
微信公众号文章获取工具

用法:
  1. 本地全自动: python crawler.py --nickname "目标公众号"
  2. 云端手动: python crawler.py --credentials '{"cookie":"xxx","token":"xxx"}'
"""

import json
import time
import os
import sys
import argparse
from datetime import datetime

from fetch_content import fetch_all_content

try:
    from wechatarticles import PublicAccountsWeb
except ImportError:
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)


def load_config(config_path="config.json"):
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_credentials(cookie, token, path="credentials.json"):
    """保存凭证到本地文件"""
    data = {
        "cookie": cookie,
        "token": token,
        "updated_at": datetime.now().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[✓] 凭证已保存到 {path}")


def load_credentials(path="credentials.json"):
    """从本地文件加载凭证"""
    if not os.path.exists(path):
        return None, None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[i] 使用已保存的凭证 (更新于 {data.get('updated_at', '未知')})")
    return data["cookie"], data["token"]


def get_credentials_auto(headless=False):
    """通过 Playwright 自动化获取凭证"""
    from wechat_login import playwright_login
    print("=" * 50)
    print("准备启动浏览器获取微信公众平台登录凭证...")
    print("=" * 50)

    try:
        cookie, token = playwright_login(headless=headless)
        if not cookie or not token:
            print("[✗] 获取凭证失败")
            sys.exit(1)
            
        save_credentials(cookie, token)
        return cookie, token
    except Exception as e:
        print(f"[✗] 启动自动化登录失败: {e}")
        print("请确保已安装依赖: pip install playwright && playwright install chromium")
        sys.exit(1)


def get_credentials_smart(headless=False):
    """智能获取凭证：支持回车直接启动 Playwright，或者手工粘贴 JSON"""
    print("=" * 50)
    print("你想如何提供登录凭证？")
    print("1. [按回车键] -> 自动启动浏览器扫码获取 (Playwright 推荐本地使用)")
    print("2. [粘贴 JSON] -> 贴入手工抓包获取的 {\"cookie\":\"...\",\"token\":\"...\"} 文本 (推荐云服务器使用)")
    print("=" * 50)

    raw = input("> ").strip()
    if not raw:
        return get_credentials_auto(headless=headless)

    try:
        data = json.loads(raw)
        cookie = data["cookie"]
        token = data["token"]
        save_credentials(cookie, token)
        return cookie, token
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[✗] 凭证格式错误: {e}")
        sys.exit(1)


def crawl_account(cookie, token, nickname, settings, fakeid=None, max_articles=None, since_date=None):
    """
    抓取指定公众号的全部文章 URL

    Parameters
    ----------
    cookie : str
        微信公众平台的 cookie
    token : str
        微信公众平台的 token
    nickname : str
        目标公众号名称（需要精确匹配）
    settings : dict
        抓取配置（batch_size, delay_seconds, output_dir）
    fakeid : str, optional
        公众号的 fakeid（固定不变），提供后可跳过搜索步骤
    since_date : datetime, optional
        只抓取此日期之后的文章
    """
    batch_size = settings.get("batch_size", 5)
    delay = settings.get("delay_seconds", 3)
    output_dir = settings.get("output_dir", "output")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"开始抓取公众号: {nickname}")
    print(f"{'='*50}")

    paw = PublicAccountsWeb(cookie=cookie, token=token)

    # 1. 确定 fakeid
    if fakeid:
        # 手动提供了 fakeid，跳过搜索
        print(f"  使用提供的 FakeID: {fakeid}")
    else:
        # 通过 nickname 搜索 fakeid
        try:
            info = paw.official_info(nickname)
            if info:
                found = info[0]
                fakeid = found['fakeid']
                print(f"  公众号: {found['nickname']}")
                print(f"  FakeID: {fakeid}")
                print(f"  [提示] 下次可在 config.json 中填入 fakeid 跳过搜索")
            else:
                print(f"[✗] 未找到公众号: {nickname}")
                return []
        except Exception as e:
            print(f"[✗] 查询公众号失败: {e}")
            print("[!] 可能是 cookie/token 已过期，请重新提取")
            return []

    # 2. 获取文章总数 (使用 fakeid 直接调用内部方法)
    try:
        data = paw._PublicAccountsWeb__get_articles_data("", begin="0", biz=fakeid)
        articles_sum = data["app_msg_cnt"]
    except Exception as e:
        print(f"[✗] 获取文章总数失败: {e}")
        print("[!] 可能是 cookie/token 已过期，请重新提取")
        return []

    # 如果设置了最大数量限制
    if max_articles and max_articles < articles_sum:
        print(f"ℹ️  限制抓取数量: {max_articles}")
        crawl_total = max_articles
    else:
        crawl_total = articles_sum

    if since_date:
        print(f"📅 时间过滤: 仅抓取 {since_date.strftime('%Y-%m-%d')} 之后的文章")
    print(f"📄 文章总数: {articles_sum}，本次抓取上限: {crawl_total}")

    if articles_sum == 0:
        print("[!] 未找到文章")
        return []

    # 3. 循环翻页获取全部文章
    all_articles = []
    failed_count = 0
    reached_date_limit = False
    since_ts = since_date.timestamp() if since_date else None

    for begin in range(0, crawl_total, batch_size):
        try:
            # 使用 fakeid 直接调用，避免每次都搜索 nickname
            data = paw._PublicAccountsWeb__get_articles_data(
                "", begin=str(begin), biz=fakeid, count=batch_size
            )
            article_data = data.get("app_msg_list", [])

            # 按日期过滤（文章按时间倒序排列，遇到早于 since 的就停止）
            if since_ts:
                for article in article_data:
                    article_time = article.get("update_time") or article.get("create_time", 0)
                    if article_time >= since_ts:
                        all_articles.append(article)
                    else:
                        reached_date_limit = True
                        article_date = datetime.fromtimestamp(article_time).strftime('%Y-%m-%d')
                        print(f"  📅 遇到 {article_date} 的文章，已到达时间边界")
                        break
            else:
                all_articles.extend(article_data)

            failed_count = 0
            print(f"  进度: {len(all_articles)} 篇")

            # 达到日期限制时停止
            if reached_date_limit:
                break

            # 达到数量限制时截断
            if max_articles and len(all_articles) >= max_articles:
                all_articles = all_articles[:max_articles]
                break
        except Exception as e:
            failed_count += 1
            print(f"  [!] 第 {begin} 批获取失败: {e}")
            if failed_count >= 3:
                print("[✗] 连续失败 3 次，停止抓取")
                print("[!] 可能是 cookie/token 已过期，请重新提取")
                break
            time.sleep(delay * 2)
            continue

        time.sleep(delay)

    # 4. 保存结果
    safe_name = nickname.replace("/", "_").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{safe_name}_{timestamp}.json")

    result = {
        "account": nickname,
        "total": len(all_articles),
        "crawled_at": datetime.now().isoformat(),
        "articles": all_articles,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 第一阶段（文章列表）抓取完成!")
    print(f"   公众号: {nickname}")
    print(f"   文章数: {len(all_articles)}")
    print(f"   基础列表保存到: {output_file}")

    # 5. 自动无缝进入第二阶段：请求文章内容（默认情况下）
    # 在 settings 中可以允许不请求正文，但通常大家都需要连贯的抓出正文
    skip_content = settings.get("skip_content", False)
    if not skip_content and all_articles:
        results = fetch_all_content(
            all_articles,
            max_articles=len(all_articles),
            delay=settings.get("content_delay_seconds", 2),
            timeout=20
        )
        
        # 将带正文的结果重新保存为 _content_XXXX.json
        full_output_file = os.path.join(output_dir, f"{safe_name}_full_{timestamp}.json")
        output_data = {
            "account": nickname,
            "total": len(results),
            "success": sum(1 for r in results if r.get("content")),
            "crawled_at": datetime.now().isoformat(),
            "articles": results,
        }
        with open(full_output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ 第二阶段（文章纯文本详情）提取完毕！")
        print(f"   最终带有正文的数据已保存至: {full_output_file}")


    return all_articles


def main():
    parser = argparse.ArgumentParser(description="微信公众号文章爬虫")
    parser.add_argument(
        "--credentials",
        type=str,
        help='凭证 JSON，格式: \'{"cookie":"...","token":"..."}\'',
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径 (默认: config.json)",
    )
    parser.add_argument(
        "--nickname",
        type=str,
        default=None,
        help="直接指定公众号名称（覆盖 config.json）",
    )
    parser.add_argument(
        "--fakeid",
        type=str,
        default=None,
        help="公众号的 fakeid（纯数字，固定不变，提供后跳过搜索）",
    )
    parser.add_argument(
        "--biz",
        type=str,
        default=None,
        help="公众号的 biz 参数（如 MzU1NDk2MzQyNg==，从文章URL中获取）",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=None,
        help="只抓取 config 中的第 N 个目标 (从 0 开始)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_articles",
        help="最多抓取的文章数量",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="只抓取此日期之后的文章，格式: YYYY-MM-DD（如 2026-01-01）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="在无头模式下启动登录浏览器（适合云服务器无界面环境）",
    )
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    settings = config.get("crawl_settings", {})
    targets = config.get("targets", [])

    # 命令行指定的 nickname/fakeid 优先
    if args.nickname or args.fakeid or args.biz:
        targets = [{"nickname": args.nickname or "未知", "fakeid": args.fakeid or args.biz}]
    elif args.target is not None:
        targets = [targets[args.target]]

    if not targets:
        print("[✗] 未指定目标公众号")
        print("    用法: python crawler.py --nickname 公众号名称")
        print("    或者在 config.json 中配置 targets")
        sys.exit(1)

    # 获取凭证
    if args.credentials:
        data = json.loads(args.credentials)
        cookie, token = data["cookie"], data["token"]
        save_credentials(cookie, token)
    else:
        cookie, token = load_credentials()
        if not cookie or not token:
            cookie, token = get_credentials_smart(headless=args.headless)

    # 解析 since 日期
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y-%m-%d")
            print(f"📅 时间过滤: 只抓取 {args.since} 之后的文章")
        except ValueError:
            print(f"[✗] 日期格式错误: {args.since}，请使用 YYYY-MM-DD 格式")
            sys.exit(1)

    # 抓取
    for target in targets:
        crawl_account(
            cookie=cookie,
            token=token,
            nickname=target["nickname"],
            settings=settings,
            fakeid=target.get("fakeid"),
            max_articles=args.max_articles,
            since_date=since_date,
        )


if __name__ == "__main__":
    main()
