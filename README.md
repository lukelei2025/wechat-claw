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

直接运行爬虫，程序会自动打开 Chromium 浏览器进入微信公众平台，你只需**用手机微信扫码**即可，剩余的提取和保存凭证工作会自动完成。

```bash
# 本地运行（会自动弹出浏览器窗口让你扫码）
python crawler.py --nickname "目标公众号"

# 云服务器运行（无头模式，二维码将以图片 login_qrcode.png 形式保存在当前目录供你查看）
python crawler.py --nickname "目标公众号" --headless

# 命令行直传凭证（跳过自动登录流程）
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
