---
name: wechat-claw
description: 微信公众号文章综合抓取工具。支持两大核心功能：1. 单篇文章读取：当用户提供 mp.weixin.qq.com 的文章链接时，稳定抓取并解析标题、发布时间、作者和正文纯文本。2. 公众号全量爬取：通过微信公众平台配合本地书签登录凭证，获取指定公众号的全部或特定时间段内的历史文章URL列表，并可批量抓取正文内容。
---

# WeChat Claw - 微信公众号文章综合抓取

本 skill 提供对微信公众号文章的综合抓取能力，无论是单篇文章的结构化解析，还是整个公众号历史文章的全量抓取。

## 核心功能与适用场景

### 1. 单篇文章读取 (Single Article Reader)
**适用场景**：用户提供了 `https://mp.weixin.qq.com/s/...` 公开文章链接，需要获取文章的标题、时间、作者和正文。
**特点**：
- **不需要**任何登录凭证（直接访问公开链接）
- 自动处理微信的反爬策略（使用 curl_cffi 伪装浏览器指纹）
- 解析并返回干净的结构化数据

### 2. 公众号全量/批量爬取 (Account Crawler)
**适用场景**：用户想获取某个公众号的全部历史文章，或者某段日期之后的文章列表（及正文）。
**特点**：
- **需要**使用浏览器提取 `cookie` 和 `token`（通过书签）
- 第一步获取文章URL列表和元数据
- 第二步利用单篇文章读取能力，批量下载正文

---

## 前置依赖

本 skill 需要以下 Python 依赖（推荐使用 uv 或 pip 安装环境）：
```bash
pip install -r requirements.txt
```
或直接安装：`pip install requests wechatarticles beautifulsoup4 curl_cffi`

---

## 🛠 功能 1：单篇文章读取

只要用户提供了具体的微信公众号文章链接，必须使用此脚本读取内容，**禁止使用 web_fetch 或 web_search 替代**。

### 运行命令
```bash
python read_wechat_article.py "https://mp.weixin.qq.com/s/..."
```

### 参数说明
| 参数 | 默认值 | 说明 |
|---|---|---|
| `--timeout` | `20` | 单次请求超时秒数 |
| `--max-retries` | `3` | 最大尝试次数 |
| `--retry-delay` | `1.0` | 重试基准等待秒数（指数退避） |

返回格式为结构化 JSON，包含 `title`, `author`, `pub_time`, `content` 以及原始 `source_url` 等字段。

---

## 🛠 功能 2：公众号全量爬取

### 第一步：获取登录凭证（一次性配置）
在本地电脑浏览器收藏栏新建书签，名称填 `提取凭证`，URL 填入以下 JavaScript 代码：
```
javascript:void(function(){var c=document.cookie;var t=(location.href.match(/token=(\d+)/)||[,'未找到'])[1];var d=document.createElement('div');d.innerHTML='<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;justify-content:center"><div style="background:#fff;padding:24px;border-radius:12px;max-width:600px;width:90%25"><h2 style="margin:0 0 12px">✅ 凭证提取成功</h2><p style="font-size:13px;color:#666">Token: '+t+'</p><textarea id="_wc_out" style="width:100%25;height:200px;font-size:12px;border:1px solid #ddd;border-radius:8px;padding:8px;margin:8px 0" readonly>'+JSON.stringify({cookie:c,token:t})+'</textarea><button onclick="document.getElementById(\'_wc_out\').select();document.execCommand(\'copy\');this.textContent=\'✅ 已复制!\'" style="background:#07c160;color:#fff;border:none;padding:10px 32px;border-radius:8px;font-size:15px;cursor:pointer;width:100%25">📋 一键复制</button><button onclick="this.parentElement.parentElement.remove()" style="background:none;border:1px solid #ddd;padding:8px 24px;border-radius:8px;font-size:13px;cursor:pointer;width:100%25;margin-top:8px">关闭</button></div></div>';document.body.appendChild(d)})()
```
**每次使用前：**
1. 浏览器打开 https://mp.weixin.qq.com 并扫码登录。
2. 点击刚创建的 "提取凭证" 书签，点击一键复制 JSON 凭证。

### 第二步：获取历史文章列表 URL 本地存储 (`crawler.py`)

运行 crawler 获取指定的公众号文章列表：

```bash
# 交互式输入凭证（首次）
python crawler.py --nickname "公众号名称"

# 直接传入凭证 JSON
python crawler.py --nickname "公众号名称" --credentials '{"cookie":"...","token":"..."}'

# 只抓取限制数量的最新文章
python crawler.py --nickname "公众号名称" --max 10

# 只抓取指定日期之后的文章
python crawler.py --nickname "公众号名称" --since 2026-03-01

# 日期 + 数量组合使用
python crawler.py --nickname "公众号名称" --since 2026-03-01 --max 50

# 使用已知的 fakeid 跳过搜索步骤
python crawler.py --fakeid "MzIyMzA5NjEyMA=="
```

结果将会存储在 `output/公众号名称_时间戳.json` 中。

### 第三步：批量抓取正文 (`fetch_content.py`)

利用第二步生成的 JSON，批量抓取这些公开 URL 的实际正文内容（由于是通过只读方式获取，**不需要提供凭证**）。

```bash
# 抓取整个列表的文章正文
python fetch_content.py output/公众号名称_20260324_152815.json

# 限制抓取数量并调整延迟防封策略
python fetch_content.py output/公众号名称_20260324_152815.json --max 5 --delay 5
```

结果将会存储在 `output/公众号名称_content_时间戳.json` 中。

---

## ⚠️ 注意事项

1. `cookie/token` 有效期约**几小时**，过期后 crawler.py 报错，需要重新扫码提取凭证。
2. 批量抓取正文脚本 `fetch_content.py` **无需 cookie/token**（微信文章公开 URL可直接访问）。
3. 频繁或不限制并发及请求间隔的情况下抓取文章正文，可能会遭遇**IP被微信拦截或要求验证**（表现为 HTML 空白返回、没有 js_content 或者 http status 返回失败），请设置合理的 `--delay`。
4. 本工具仅用于个人数据备份、学习分析研究。请尊重内容版权。
