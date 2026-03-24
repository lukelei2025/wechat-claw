# 微信公众号文章爬虫

一键抓取任意微信公众号的全部文章 URL。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置目标公众号

编辑 `config.json`，填入目标公众号名称（需精确匹配）：

```json
{
  "targets": [
    { "nickname": "公众号名称" }
  ]
}
```

或者运行时直接指定：`python crawler.py --nickname "公众号名称"`

### 3. 安装浏览器内核 (Playwright)

爬虫使用 Playwright 自动化获取微信后台凭证，因此需要安装 Chromium 内核：

```bash
playwright install chromium
```

### 4. 运行爬虫自动获取凭证

直接运行爬虫，程序会智能提示你是想自动扫码还是手工输入：

```bash
# 本地运行（按回车键，会自动弹出浏览器窗口让你扫码，全自动）
python crawler.py --nickname "目标公众号"

# 云服务器运行（因微信会对云服务器 IP 实施风控拦截 headless 登录，推荐在此模式下粘贴手工 JSON）
# 做法：在本地电脑按 F12 抓取完整 Cookie 和 Token，拼成 JSON，在云端运行此命令后粘贴回车
python crawler.py --nickname "目标公众号"

# 命令行直传凭证（完全静默，适合定时脚本）
python crawler.py --credentials '{"cookie":"xxx","token":"xxx"}'
```

凭证会自动保存在本地 `credentials.json`，下次运行在过期前无需重新扫码。

### 5. 结果

文章列表保存在 `output/` 目录下，JSON 格式，包含每篇文章的标题、URL、摘要、封面、更新时间。

## 项目结构

```
Crawler/
├── README.md           # 本文件
├── requirements.txt    # Python 依赖
├── config.json         # 目标公众号配置
├── crawler.py          # 主爬虫脚本
├── credentials.json    # 自动保存的凭证（自动生成）
└── output/             # 抓取结果（自动生成）
```

## 注意事项

- Cookie/Token 有效期约 **几小时**，过期需重新扫码提取
- 请求间隔默认 **3 秒**，可在 config.json 中调整
- 仅用于个人学习研究，请尊重著作权
