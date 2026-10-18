# 初赛提交材料（作品文档资料）

> 对应：第五届中国研究生网络安全创新大赛 · 揭榜挑战赛 · 题目5
> 官方模板：附件2《中国研究生网络安全创新大赛作品相关模板》
> 截止：2026-10-22（报名已于 2026-10-18 完成）

本目录用于集中整理**面向网评提交**的作品文档资料草稿。源码与证据仍以仓库现行结构为准；本目录只放提交件本身。

## 官方硬约束（来自附件2与提交通知）

- 作品文档资料为 **PDF，≤10M**；平台最多上传 **10 个文件，单个 ≤500MB**。
- 文件命名：`队长姓名+作品名称+资料名称`（队长姓名由团队填写）。
- 报告排版：**A4；除标题外宋体、小四号字、1.5 倍行距**。
- **不得出现学校、院系、指导教师等身份信息**，违者取消资格。
- 报告结构：摘要 / 第一章 作品概述 / 第二章 作品设计与实现 / 第三章 作品测试与分析 / 第四章 创新性说明 / 第五章 总结 / 参考文献。
- 另需：**作品原创性声明**（组员签名）；往届参加者才需“作品重大改进说明”（本次不适用）。

## 提交件清单与状态

| # | 文件（`（队长姓名）+溯界+资料名称`） | 内容 | 状态 |
|---|---|---|---|
| 1 | 作品报告.pdf | 按官方模板七部分（含封面/目录/页脚页码） | **已生成**，19 页 / 0.35MB |
| 2 | 原创性声明.pdf（+ .docx） | 官方文本 | **已生成**，待组员签名 |
| 3 | 部署说明.pdf | 安装、启动、一键复现、已知限制 | **已生成** |
| 4 | 测试样例与流程说明.pdf | eval 协议/样例/Oracle/流程 | **已生成** |
| 5 | 证据包.zip | 脱敏 runs + SHA-256 清单 + 复现说明 | **已生成**（本机复现，35 文件 / 0.9MB） |
| 6 | 可执行程序.zip | 源码 + 一键脚本 | **已生成**（363 文件 / 1.1MB） |
| 7 | 演示视频.mp4 | 答辩演示录屏 | 待录制（见 `演示脚本-溯界.md`） |

> 产物均输出到 `dist/`（已 gitignore）；重新生成见下方命令。文件名中的「队长姓名」由团队在正式提交时替换。

## 本目录文件

- `作品报告-溯界.md`：作品报告草稿（含元信息块，正式 PDF 中删除）。
- `部署说明-溯界.md`：部署与复现说明（含已知限制与未验收项）。
- `测试样例与流程说明-溯界.md`：测试样例、Oracle、基线与复现流程。
- `tools/build_report_docx.py`：Markdown→DOCX 转换脚本，套用官方格式（A4、宋体小四、1.5 倍行距）。构建产物输出到 `dist/`（已忽略）。
- `tools/build_report_pdf.py`：Markdown→PDF 转换脚本，生成**封面页 + 目录 + “第 X 页 共 Y 页”页脚**，并**嵌入系统中文字体**，无需阅读器自带字体；`--plain` 模式用于声明与说明类文档。
  - 字体自动探测：macOS `Songti.ttc` → Windows `simsun.ttc` / `msyh.ttc` → Linux `NotoSerifCJK` / `uming` / `wqy`；找不到时给出清晰报错。
  - 可用环境变量覆盖：`SUJIE_REPORT_FONT` / `SUJIE_REPORT_FONT_INDEX` / `SUJIE_REPORT_BOLD_FONT` / `SUJIE_REPORT_BOLD_INDEX`（`.ttc` 需指定子字体序号）。
- `tools/build_evidence_packet.py`：打包脱敏证据（逐文件 SHA-256 + 清单 + 个人路径/凭据扫描，自动排除预算账本与缓存）。
- `tools/build_source_package.py`：打包提交源码（排除虚拟环境、缓存、模型缓存、本地运行状态、凭据与原始 runs，并做凭据模式扫描）。
- `作品原创性声明-溯界.md`：官方声明文本（待签名）。

构建报告 Word：

```sh
cd competition/submission
uv run --no-project --with python-docx python3 tools/build_report_docx.py \
  作品报告-溯界.md "dist/溯界-作品报告.docx"
```

构建报告 PDF（当前 19 页、约 0.35MB，≤10MB 限制）：

```sh
uv run --no-project --with reportlab python3 tools/build_report_pdf.py \
  作品报告-溯界.md "dist/溯界-作品报告.pdf"
```

> 说明：两个脚本均不复制官方模板中的“填写说明”页；正式提交前请按官方要求将文件命名为“队长姓名+作品名称+资料名称”，并确认全文不含身份信息。

## 一键生成全部提交件

在仓库根目录执行：

```sh
cd competition/submission

# 1) 作品报告（封面+目录+页脚页码）
uv run --no-project --with reportlab python3 tools/build_report_pdf.py \
  作品报告-溯界.md "dist/溯界-作品报告.pdf"
uv run --no-project --with python-docx python3 tools/build_report_docx.py \
  作品报告-溯界.md "dist/溯界-作品报告.docx"

# 2) 原创性声明（待签名）与两份说明文档
uv run --no-project --with python-docx python3 tools/build_report_docx.py \
  作品原创性声明-溯界.md "dist/溯界-作品原创性声明.docx"
for f in 作品原创性声明-溯界 部署说明-溯界 测试样例与流程说明-溯界; do
  uv run --no-project --with reportlab python3 tools/build_report_pdf.py --plain \
    "$f.md" "dist/$f.pdf"
done

# 3) 先重跑确定性评测产生真实证据，再打包
cd ../../sujie
.venv/bin/python eval/run_business_validation.py \
  --protocol-file eval/protocols/four_business_workflows_v2.json \
  --out-dir eval/reports/runs/competition_repro_$(date +%Y%m%d)
.venv/bin/python eval/verify_runtime_validation.py eval/reports/runs/competition_repro_$(date +%Y%m%d)
.venv/bin/python dev.py eval-detection > /tmp/detection_v1.json
cd ../competition/submission
python3 tools/build_evidence_packet.py --out "dist/证据包-溯界-确定性复现.zip" \
  --run ../../sujie/eval/reports/runs/competition_repro_$(date +%Y%m%d) \
  --log "/tmp/detection_v1.json=detection_v1.json"

# 4) 源码包
cd ../..
python3 competition/submission/tools/build_source_package.py --root . \
  --out "competition/submission/dist/源码包-溯界.zip"
```

## 术语纪律（全篇遵守）

- 不得把**确定性回归条数**当作攻击样本量或比赛 ASR；
- 不得把**云模型小样本**结果写成比赛成功率或公开基准成绩；
- “模型未提出危险动作” ≠ “网关拦截了危险动作”；
- 未验收项（如新版 Linux 整体隔离/性能、一键部署）必须显式标注；
- 参考文献须按 GB/T 7714-2015 著录：当前 11 条已核对题名/作者/年份/编号（arXiv 接口与官方站点），正式出版卷期页码以出版方为准。
