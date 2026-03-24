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

### 3. 获取凭证（书签一键提取）

#### 一次性设置：创建书签

在浏览器收藏栏新建书签，名称填 `提取凭证`，URL 填入：

```
javascript:void(function(){var c=document.cookie;var t=(location.href.match(/token=(\d+)/)||[,'未找到'])[1];var d=document.createElement('div');d.innerHTML='<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;justify-content:center"><div style="background:#fff;padding:24px;border-radius:12px;max-width:600px;width:90%25"><h2 style="margin:0 0 12px">✅ 凭证提取成功</h2><p style="font-size:13px;color:#666">Token: '+t+'</p><textarea id="_wc_out" style="width:100%25;height:200px;font-size:12px;border:1px solid #ddd;border-radius:8px;padding:8px;margin:8px 0" readonly>'+JSON.stringify({cookie:c,token:t})+'</textarea><button onclick="document.getElementById(\'_wc_out\').select();document.execCommand(\'copy\');this.textContent=\'✅ 已复制!\'" style="background:#07c160;color:#fff;border:none;padding:10px 32px;border-radius:8px;font-size:15px;cursor:pointer;width:100%25">📋 一键复制</button><button onclick="this.parentElement.parentElement.remove()" style="background:none;border:1px solid #ddd;padding:8px 24px;border-radius:8px;font-size:13px;cursor:pointer;width:100%25;margin-top:8px">关闭</button></div></div>';document.body.appendChild(d)})()
```

#### 每次使用

1. 浏览器打开 https://mp.weixin.qq.com → 扫码登录
2. 点击收藏栏的 **"提取凭证"** 书签
3. 弹窗中点 **📋 一键复制**

### 4. 运行爬虫

```bash
# 交互式：粘贴凭证后自动抓取
python crawler.py

# 命令行传入凭证
python crawler.py --credentials '{"cookie":"xxx","token":"xxx"}'

# 指定公众号名称
python crawler.py --nickname "目标公众号"

# 再次运行 (自动使用上次保存的凭证)
python crawler.py
```

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
