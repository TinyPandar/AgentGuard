# LaTeX 作品报告（M25 交付草稿）

正文入口为 `main.tex`，按官方五章拆分到 `sections/`；两张矢量图由 `figures/` 中的 TikZ 源码生成。后续报告修订以本工程为主，旧 Markdown 报告保留为 M21 材料快照，不自动覆盖。

## 模板与编译

- A4，正文小四（12 pt），1.5 倍行距；封面、保留的“填写说明”、自动目录、五章正文、参考文献与页码。
- 使用 XeLaTeX；引用由 `thebibliography` 和 `cite` 编号，不依赖额外 BibTeX/Biber 步骤。
- 在 Codex 中打开此目录使用内置编辑器和 PDF 预览。已有 TeX 环境也可在本目录运行 `xelatex -interaction=nonstopmode -halt-on-error -output-directory=../dist main.tex` 三次，以解析目录、交叉引用与总页数。
- `font-config.tex` 优先使用已安装的 SimSun；否则为 Songti SC 或 FandolSong 草稿替代。正式宋体要求需单独核验，不因预览成功而视为满足。未分发任何系统字体文件。
- 在已有 XeLaTeX 环境严格检查字体：`xelatex -interaction=nonstopmode -halt-on-error -output-directory=../dist '\def\RequireOfficialFont{1}\input{main.tex}'`，并重复编译至引用稳定。

## 当前验证状态

本轮内置编译请求未返回诊断，未确认 LaTeX 编译成功，也未将旧 Release PDF 标为本工程的编译产物。源文件保留在内置编辑器中；后续拿到成功编译结果后，需逐页检查图表、跨页、目录和引用，并确认嵌入字体、A4 与小于10MB。

源码检查（不代替编译）：在仓库根目录运行 `python3 competition/submission/tools/check_report_latex.py`。它检查输入文件、引用、环境配对、摘要长度、匿名占位、官方说明页和所引用集成本地验证的源码摘要。

## 内容版本

- 基于主线 `99cba60`，集成本地记录为1025项回归通过；本轮没有重跑该回归。
- M25原冻结版本的48格脚本、48格本地HTTP和14格来源代表分别呈现，原始证据仍需独立移交。
- M24六链为有限Linux运行性记录，不作为M25完整隔离或性能验收。
- PR #14 的 DeepSeek/聊天控制台已取到本地审阅分支，仍未合入主线，因此不写成当前报告已验收功能。
- 文献核对与写作辅助出处见上一级 `LATEX_DELIVERY_REVIEW.md`。
