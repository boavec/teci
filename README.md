# TECI · 词元成本指数

一个用公开数据算出来的 AI 成本指数：**买到一分"AI 智能"，要花多少钱。**

不需要算力预算、不需要服务器、不需要牌照。运行成本是零。

---

## 网页上有什么

一份 HTML，双击就能看：`site/teci-standalone.html`

**给普通用户的一层（打开就有答案）**

- 顶部一句话结论：现在最划算的是谁、要最强得付多少倍、预算最紧选谁
- 三张推荐卡：日常最划算 / 单价最低 / 能力最强
- 4 个核心指标：中位混合价、每智能点成本、性价比最优、档位价差

**给专业买家 / 机构的一层（往下滚）**

- **性价比前沿散点图**：横轴智能分、纵轴价格（对数）。紫色虚线是**全球前沿**，
  青色实线是**国内前沿**，并标注了国内智能分最高的 10 个模型。
  两条线各自走到哪里，就是"国产替代"目前能做到什么程度
- **「我至少要 X 分，最便宜的在哪」**：按 30/40/50/55/60 分档，直接给出最便宜的达标模型
- **按厂商看**：中位价、中位分、中位每点成本、该厂商最低价型号
- **国内 vs 海外拆到档位**：4×4 交叉矩阵，样本数、中位价、中位分、每点成本
- **全样本明细**：可排序，含上市日期

**能直接用的工具**

- **采购成本计算器**：填能力下限 + 地区 + 月用量 + 输入输出比，当场算出最便宜的达标方案、
  预估月账单（USD/CNY），以及"换最强会贵几倍"。纯前端计算，不联网、不上传

**商业化入口（已暂时关闭）**

页首广告位和「广告位规格与媒体资料」都已移除，先让数据跑一段时间、攒出可信度和访问量再谈变现。

- 广告位：`site/index.html` 里搜 `广告位暂时关闭`，取消那段注释即可恢复（CSS 样式仍保留着）
- 媒体资料：原内容已完整迁移到 `business/TECI-广告刊例.docx`，网页上不再重复
- 报价与签约文件：见下节「商业化文件」

---

## 中英双语

页面右上角有语言选择器，中文 / English，选择结果存在浏览器里，刷新后保持。

- 词典在 `site/i18n/en.json`，**以中文原文为 key**：改中文文案时必须同步改 key，否则会回退成中文
- 构建时合并进页面，单文件版依然是自包含的，不额外请求
- 也支持 `?lang=en` 直接指定，方便发给英文读者
- 切换语言会重载页面：这样所有图表、表格、计算器都用新语言重算一遍，不会出现半中半英

**加文案的规矩**：静态文字直接写在 HTML 里即可；JS 里带数字的句子要走
`T('... {n} ...', {n})` 或 `tr('...')`，否则不会被翻译（动态生成的文本不经 DOM 替换）。

跑 `python scripts/check_i18n.py` 检查覆盖率，要求 100%——差一条就会在英文页露出中文。

---

## 目录结构

```
teci/
├─ site/
│  ├─ index.html            ← 网页本体（读同目录 data/teci.js）
│  ├─ teci-standalone.html  ← 单文件版，可直接发人（由脚本生成）
│  ├─ og.png                ← 分享封面图 1200×630（由 scripts/make_og.py 生成，需提交）
│  └─ data/teci.js          ← 由脚本生成，不要手改
├─ publish/
│  ├─ index.html            ← 可直接上传到 GitHub Pages 的入口（由脚本生成）
│  └─ og.png                ← 封面图副本（构建时自动复制）
├─ .github/workflows/
│  └─ deploy.yml            ← 每天自动抓数、重算、部署到 GitHub Pages
├─ data/
│  ├─ raw/                  ← 原始快照，带日期，永不覆盖
│  ├─ teci_snapshot.csv     ← 当前截面明细
│  └─ teci_history.csv      ← 时间序列，每跑一次长一行
├─ docs/
│  └─ methodology.md        ← 方法论文档（对外发布用这份）
├─ business/                ← 商业化文档（广告刊例、投放订单、SOP）
├─ logs/
│  └─ run.log               ← 每次运行的日志，超过 1MB 自动轮转
├─ scripts/
│  ├─ fetch_models.py       ← 抓数据
│  ├─ build_teci.py         ← 清洗 + 算指数 + 生成网页
│  ├─ extract_json.py       ← 从被截断的抓取结果里回收 JSON
│  ├─ test_site.js          ← 无头验证网页逻辑
│  ├─ check_contrast.py     ← WCAG 对比度检查
│  ├─ check_publish.py      ← 发布前检查：自包含、meta、分享卡片
│  ├─ make_og.py            ← 生成分享封面图（需要 Pillow + numpy）
│  ├─ dump_svg.js           ← 导出散点图 SVG，供预览用
│  ├─ preview_chart.py      ← 把 SVG 画成 PNG，检查标签有没有互相压
│  └─ check_workflow.py     ← GitHub Actions 工作流结构检查
├─ run.cmd / run.ps1        ← 一键更新
├─ daily_run.cmd            ← 计划任务的调用入口（无参数）
└─ install_task.cmd/.ps1    ← 注册每日自动更新
```

---

## 怎么用

### 手动更新：双击 `run.cmd`

抓数据 → 算指数 → 生成网页 → 自动打开。一步到位。

> 为什么不用直接双击 `.ps1`：Windows 默认禁止运行未签名的 PowerShell 脚本。
> `run.cmd` 只在这一次调用里用 `-ExecutionPolicy Bypass` 绕开限制，不改你的系统设置。

参数（命令行里用）：

```
run.cmd -SkipFetch    只用已有快照重建，不联网
run.cmd -NoOpen       不自动开浏览器（给计划任务用）
```

---

## 每日自动更新

**双击 `install_task.cmd`** —— 注册一个每天 **09:30** 运行的计划任务。

注册后它会每天自动：抓最新价格 → 重算指数 → 重新生成网页。不开浏览器，不打扰你。

其他操作（命令行）：

```powershell
.\install_task.ps1 -At "21:15"   # 改成别的时间
.\install_task.ps1 -Status       # 看下次运行时间、上次是否成功
.\install_task.ps1 -Remove       # 删除任务
```

**如果注册时报"拒绝访问"**：右键 `install_task.cmd` → 以管理员身份运行。
脚本会先试 `Register-ScheduledTask`，失败自动改用 `schtasks`，两条路都走不通才报错。

**几个设计上的考虑**

- **错过会补跑**：设了 `StartWhenAvailable`，如果 09:30 电脑是关的，开机后会补一次
- **抓取失败不会毁数据**：网络断了就用已有快照继续算，日志里记 `FETCH FAILED`，网页照常出
- **有日志**：`logs/run.log` 记录每次的开始、抓取结果、构建结果。出了问题先看这里
- **不会重复堆积**：同日重跑只覆盖当天那一行历史，不会产生重复数据点

**验证是否真的在跑**：`install_task.cmd -Status`，看「上次运行」和「上次结果」（0 = 成功）。
更细的看 `logs/run.log`。

---

## 发布到 GitHub Pages

网页是纯静态的，不需要服务器和数据库。**先看「国内能随时打开吗」，再决定要不要用这条路。**

两种发布方式，二选一：

| 方式 | 仓库里放什么 | 每天自动更新 |
|---|---|---|
| **A 手动** | 只放 `publish/index.html` 一个文件 | ❌ 每次要重新上传 |
| **B 自动**（推荐） | 整个项目 | ✅ 每天自动跑 |

> 两种方式在 Pages 里的 **Source 设置不同**，不能同时用。切过去之后要改设置。

### 方式 A：只传一个文件（5 分钟，但每次要手动）

`publish/index.html` 是构建时自动生成的**单文件成品**（数据已内嵌），直接传它就行。
单独放一份是因为 GitHub Pages 要求入口必须叫 `index.html`。

1. 登录 GitHub → 右上角 **+** → **New repository**
   - 名字填 `teci`，选 **Public**（Private 开 Pages 要付费）
   - **不要**勾 Add a README → Create
2. 点 **uploading an existing file**，把 `publish/index.html` 拖进去 → Commit
3. **Settings** → 左侧 **Pages**
   - Source 选 **Deploy from a branch**
   - Branch 选 **main**，目录 **/ (root)** → Save
4. 等 1–2 分钟，顶部出现地址 `https://<用户名>.github.io/teci/`

更新：每次跑完 `run.cmd`，重新拖一次 `publish/index.html` 覆盖。

### 方式 B：整仓库 + Actions（每天自动）

工作流已经写好了：`.github/workflows/deploy.yml`。你需要把**整个项目**推上去，因为 Actions 要跑 Python 脚本。

**上传整个项目**

不能只拖一个文件了。两种办法：

- **装 GitHub Desktop**（推荐，图形界面）：Add existing repository → 选中 `teci` 文件夹 →
  Publish repository。注意别把 `logs/`、`data/raw/` 传上去（`.gitignore` 已经排除了，GitHub Desktop 会遵守）
- **命令行**：在 `teci` 目录下
  ```bash
  git init
  git add .
  git commit -m "init: TECI 指数"
  git branch -M main
  git remote add origin https://github.com/<你的用户名>/teci.git
  git push -u origin main
  ```

**开启自动部署**

1. 仓库 **Settings** → 左侧 **Pages**
2. **Source 选 `GitHub Actions`**（关键，不是 "Deploy from a branch"）
3. 完成。第一次 push 就会自动跑一次；之后每天北京时间约 **09:10** 自动运行

**它每天做什么**

```
抓价格 → 重算指数 → 生成网页 → 跑测试和对比度检查 → 提交数据 → 部署
```

任何一步出问题（除了抓取）都会停下，**线上保留上一个可用版本**，不会变成白页。

**仓库里会多什么、不会多什么**

| 内容 | 是否入库 | 量级 |
|---|---|---|
| `data/teci_history.csv` | ✅ 每天提交 | 约 0.2 KB/天 |
| `data/teci_snapshot.csv` | ✅ 每天提交 | 约 26 KB/天 |
| `data/raw/*.json` 原始快照 | ❌ 不入库 | 约 **969 KB/天**（一年 345 MB） |
| `publish/`、`site/data/` | ❌ 不入库 | 构建产物，CI 重新生成 |

原始快照不进仓库，是因为按天提交一年会把仓库撑到 300MB 以上。
**长期资产是 `teci_history.csv`**——每行一天，这才是那条要攒出来的曲线。
需要归档原始数据的话，自己定期拷到网盘或对象存储。

**手动触发一次**：仓库 → **Actions** → 左侧「每日更新并部署」→ **Run workflow**。

### 分享卡片（发到微信/群里长什么样）

页面里已经配好了 `og:title` / `og:description` / `og:image`，封面图是
`site/og.png`（1200×630，深空星云风格，和网页一致）。

**上线后要改一处**：打开 `scripts/build_teci.py`，把顶部的

```python
SITE_URL = "https://YOUR-DOMAIN.example"
```

改成你的实际地址（不带结尾斜杠），然后重新跑 `run.cmd`。

原因是 **`og:image` 必须是绝对地址**——微信、Twitter、Facebook 这些平台不会去解析相对路径，
填 `og.png` 它们直接忽略，分享出去就是没有封面的一片空白。

改完之后 `publish/index.html` 里的 `__SITE_URL__` 会被替换掉，`publish/og.png` 也会自动带上。

**重新生成封面图**（可选，改文案或配色后）：

```powershell
python scripts/make_og.py
```

需要 Pillow + numpy；只在本地跑，CI 不依赖它（`site/og.png` 是提交进仓库的静态资源）。

> 图里刻意没写日期和模型数量——这张图是一次性生成、长期复用的，写死数字过几天就变成假信息。

### 国内能随时打开吗

**不能保证。** 这是必须提前知道的：

| 访问方式 | 国内可用性 | 说明 |
|---|---|---|
| `*.github.io` | ⚠️ **不稳定** | 不同地区、不同运营商差异很大；可能打不开、极慢、时通时不通。这不是你的问题，是网络路径问题 |
| `*.pages.dev`（Cloudflare） | ⚠️ 也不稳定 | 略好于 github.io，但同样不保证 |
| 国内云 + **备案域名** | ✅ 稳定 | 唯一能保证"随时能开"的路子，需要 ICP 备案 |

**现实建议：**

- **自用 / 发给熟人** → GitHub Pages 够用，打不开就重发
- **要发给客户、广告主、投资人** → 别用 github.io。对方点开超时一次，你就少一次机会
- **正式对外** → 买域名 + 国内云（腾讯云 COS / 阿里云 OSS 静态托管）+ ICP 备案

你有个体户，**备案是可行的**：个体工商户可作为主体备案，需要营业执照、法人身份证、
实名域名、以及境内接入资源。周期一般 7–20 个工作日。

前期两条腿走：GitHub Pages 先挂着攒数据，同时走备案，下来再切地址。
反正现在也不变现，**这段时间正好用来备案**。

---

## 数据的诚实边界

必须自己先讲清楚，否则被别人指出就很难看：

| 项目 | 现状 |
|---|---|
| 价格口径 | **挂牌价**，不是成交价。企业协议价通常显著更低 |
| 覆盖范围 | 当前快照约 240 个模型，其中约 1/4 有第三方评分（数字每天会变） |
| 准入窗口 | 只统计最近 12 个月上市的模型——避免退役型号把"最便宜"变成没人用的选项 |
| L1 的含义 | 中位数主要由"未评级"那批模型决定，**不代表好用模型的价格** |
| L2 的用法 | 智能分是序数指标，只能同档位内比较，不能当基数相除 |
| 时间序列 | 每天跑一次才会长成曲线。现在才刚开始 |
| L3 有效成本 | **未启用**。没有吞吐/重试数据，现在的数字不代表真实可用成本 |

**不要把"未评级"当低端模型**——它只是第三方还没给分。

---

## 接下来 30 天该做什么

1. **让自动任务稳定跑满 30 天**，每天检查一次 `logs/run.log` 有没有 `FAILED`
2. **写第一篇文章**：《为什么 GPU 小时价不能代表 AI 成本》—— 立论文章，也是唯一获客入口
3. **把方法论挂出去**：GitHub 仓库 + Zenodo 打 DOI，拿时间戳背书
4. **找 3 个人验证**：做 AI 采购的、算力平台的、看研报的，问他们"这个数你会不会用"
5. **别急着变现**。现在这版的价值是证明你能持续产出可信数据，不是卖订阅

---

## 合规边界（别越线）

- ✅ 发布公开数据指数、卖数据订阅、做定制评测报告
- ✅ 用商业合同做"固定价格算力购销"（实物交割，不是衍生品）
- ❌ 把指数做成可交易的合约标的（需要交易所牌照）
- ❌ 让用户充值积分买卖指数（性质会变成对赌/赌博）
- ❌ 用"可套保""可交易""可投资"这类表述描述本指数

本指数**不是**投资标的，**不是**结算基准，**不是**金融产品。

---

## 已验证

```
38/38 通过  node scripts/test_site.js        # 渲染逻辑：图表标签、六张表、计算器、坐标越界
10/10 通过  node scripts/test_i18n.js        # 英文模式：结论句、图注、静态文本替换、html lang
100% 覆盖   python scripts/check_i18n.py     # 英中文案覆盖率（要求 100%）
12/12 达标  python scripts/check_contrast.py # 配色可读性：WCAG 对比度
 结构通过   python scripts/check_workflow.py # 工作流结构（缩进、step、uses 版本号）
 发布就绪   python scripts/check_publish.py  # 自包含（0 外部请求）、meta、分享卡片、og.png
```

**图表标签怎么验证的**：沙箱里开不了 headless 浏览器，所以用 `dump_svg.js` 把页面生成的
SVG 导出来，再由 `preview_chart.py` 用 Pillow 重画成 PNG，肉眼确认标签有没有互相压：

```powershell
node scripts/dump_svg.js
python scripts/preview_chart.py   # 输出 build/scatter_preview.png
```

标签位置是运行时算的：16 个候选位置、按"离自己的点最近 + 不压别的标签 + 不压数据点"打分取最优。
改图表后跑一次预览，能立刻看出有没有挤在一起。

计算器的核心是一个纯函数 `recommend()`，测试里会拿公式手算一遍核对单价与月成本，
并覆盖：达标筛选、地区过滤、权重变化、无结果时的安全返回与"能力天花板"提示。

`check_contrast.py` 直接从 `index.html` 的 CSS 变量读调色板，按 WCAG 公式算实际对比度。
改配色后跑一遍，避免深色主题"看着高级但读不清"。

## 以后想恢复广告位

广告位代码整块保留在 `site/index.html` 的 HTML 注释里，样式（`.ad-zone` 等）也还在 CSS 里。
恢复只要两步：

1. 搜 `广告位暂时关闭`，把那一段的 `<!--` 和 `-->` 去掉
2. 把注释里 `<a class="ad-link" href="mailto:you@example.com">` 的邮箱换成你自己的

改完跑一次 `run.cmd`，`site/teci-standalone.html` 和 `publish/index.html` 会一起更新。

**卖出去之后**：把 `<div class="ad-body">` 里的占位内容换成广告主的图或文字链，
并**必须保留**「广告」标识和 `rel="nofollow sponsored"`。

---

## 商业化文件（`business/`）

当前**不产生收入**，但文档先备着，想开的时候直接能用：

| 文件 | 用途 |
|---|---|
| `TECI-广告刊例.docx` | 对外报价：位规格、价格、投放流程、素材与合规要求、拒投清单 |
| `TECI-广告投放订单.docx` | 一页可签署的投放订单，含金额、付款、上刊条件、双方义务、责任上限 |
| `商业化SOP.md` | 从询位到收款的完整流程、收款方式、开票、合规动作清单、冷启动话术 |
| `TECI-定制评测报告-模板.docx` | 备用，留给以后接定制报告时用 |
| `make_docs.py` / `verify_docs.py` | 重新生成与校验上面这些文档 |

**真要开始收钱前必须先确认**：营业执照经营范围是否含「广告发布」。没有的话去市场监管局变更，
否则开「广告服务」发票会有税务风险。详见 SOP 第二节。
