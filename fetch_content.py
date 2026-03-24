# coding: utf-8
"""
微信公众号文章内容批量抓取

读取 crawler.py 生成的文章列表 JSON，逐篇抓取文章正文内容。
依赖 read_wechat_article.py 中的 WechatArticleFetcher 和 WechatArticleParser。

用法:
  python fetch_content.py output/数字生命卡兹克_20260324_152815.json
  python fetch_content.py output/数字生命卡兹克_20260324_152815.json --max 5
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime

from read_wechat_article import WechatArticleFetcher, WechatArticleParser


def load_article_list(json_path):
    """加载 crawler.py 生成的文章列表 JSON"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持两种格式：直接列表 或 带 metadata 的字典
    if isinstance(data, list):
        return data, "未知"
    elif isinstance(data, dict):
        return data.get("articles", []), data.get("account", "未知")
    else:
        print("[✗] 无法识别的 JSON 格式")
        sys.exit(1)


def fetch_all_content(articles, max_articles=None, delay=3, timeout=20, max_retries=3):
    """
    批量抓取文章正文内容

    Parameters
    ----------
    articles : list
        文章列表（每项需包含 link 或 url 字段）
    max_articles : int, optional
        最多抓取的文章数量
    delay : int
        每篇文章之间的等待秒数
    timeout : int
        单次 HTTP 请求超时秒数
    max_retries : int
        每篇文章的最大重试次数
    """
    fetcher = WechatArticleFetcher(timeout=timeout, max_retries=max_retries)
    parser = WechatArticleParser()

    if max_articles:
        articles = articles[:max_articles]

    total = len(articles)
    results = []
    success_count = 0
    fail_count = 0

    print(f"\n📖 开始抓取 {total} 篇文章正文...\n")

    for i, article in enumerate(articles):
        # 获取文章 URL（兼容不同字段名）
        url = article.get("link") or article.get("url") or article.get("content_url")
        title = article.get("title", "无标题")

        if not url:
            print(f"  [{i+1}/{total}] ⚠️ 跳过（无 URL）: {title}")
            fail_count += 1
            continue

        # 确保使用 https（crawler 返回的是 http，WeChat 需要 https）
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        print(f"  [{i+1}/{total}] 抓取: {title[:40]}...")

        # 使用 read_wechat_article 的 fetcher 抓取
        fetched = fetcher.fetch(url)

        if "error" in fetched:
            print(f"           ❌ 失败: {fetched.get('message', fetched['error'])}")
            results.append({
                "title": title,
                "url": url,
                "error": fetched["error"],
                "content": None,
            })
            fail_count += 1
        else:
            # 解析 HTML 提取正文
            parsed = parser.parse(fetched["page_html"])
            content = parsed.get("content", "")

            if content:
                print(f"           ✅ 成功 ({len(content)} 字)")
                success_count += 1
            else:
                print(f"           ⚠️ 页面已获取但正文为空")
                fail_count += 1

            results.append({
                "title": parsed.get("title") or title,
                "author": parsed.get("author", ""),
                "pub_time": parsed.get("pub_time", ""),
                "url": fetched["source_url"],
                "content": content,
                "content_length": len(content),
            })

        # 控制频率
        if i < total - 1:
            time.sleep(delay)

    print(f"\n{'='*50}")
    print(f"✅ 抓取完成: 成功 {success_count} / 失败 {fail_count} / 总计 {total}")

    return results


def main():
    cli = argparse.ArgumentParser(description="批量抓取微信公众号文章正文内容")
    cli.add_argument(
        "input",
        help="crawler.py 生成的文章列表 JSON 文件路径",
    )
    cli.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_articles",
        help="最多抓取的文章数量",
    )
    cli.add_argument(
        "--delay",
        type=int,
        default=3,
        help="每篇文章间隔秒数 (默认: 3)",
    )
    cli.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="单次 HTTP 请求超时秒数 (默认: 20)",
    )
    cli.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录 (默认: 与输入文件同目录)",
    )
    args = cli.parse_args()

    # 加载文章列表
    if not os.path.exists(args.input):
        print(f"[✗] 文件不存在: {args.input}")
        sys.exit(1)

    articles, account_name = load_article_list(args.input)
    print(f"📄 公众号: {account_name}")
    print(f"📄 文章列表: {len(articles)} 篇 (来自 {args.input})")

    # 批量抓取正文
    results = fetch_all_content(
        articles,
        max_articles=args.max_articles,
        delay=args.delay,
        timeout=args.timeout,
    )

    # 保存结果
    output_dir = args.output_dir or os.path.dirname(args.input) or "output"
    os.makedirs(output_dir, exist_ok=True)

    safe_name = account_name.replace("/", "_").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{safe_name}_content_{timestamp}.json")

    output_data = {
        "account": account_name,
        "total": len(results),
        "success": sum(1 for r in results if r.get("content")),
        "crawled_at": datetime.now().isoformat(),
        "source_file": args.input,
        "articles": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"💾 结果保存到: {output_file}")

    # 预览
    for i, r in enumerate(results[:3]):
        title = r.get("title", "无标题")
        length = r.get("content_length", 0)
        status = f"✅ {length}字" if r.get("content") else "❌ 失败"
        print(f"   [{i+1}] {title[:40]} — {status}")


if __name__ == "__main__":
    main()
