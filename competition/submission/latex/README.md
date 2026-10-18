# LaTeX 作品报告（M25 交付草稿）

正文入口为 `main.tex`，按官方五章拆分到 `sections/`；两张矢量图由 `figures/` 中的 TikZ 源码生成。后续报告修订以本工程为主，旧 Markdown 报告保留为 M21 材料快照，不自动覆盖。

## 模板与编译

- A4，正文小四（12 pt），1.5 倍行距；封面、保留的“填写说明”、章级自动目录、五章正文、参考文献与页码；PDF书签保留节级导航。
- 使用 XeLaTeX；引用由 `thebibliography` 和 `cite` 编号，不依赖额外 BibTeX/Biber 步骤。
- 在 Codex 中打开此目录使用内置编辑器和 PDF 预览。已有 TeX 环境也可在本目录运行 `xelatex -interaction=nonstopmode -halt-on-error -output-directory=../dist main.tex` 三次，以解析目录、交叉引用与总页数。
- `font-config.tex` 优先使用已安装的 SimSun；否则为 Songti SC 或 FandolSong 草稿替代。正式宋体要求需单独核验，不因预览成功而视为满足。未分发任何系统字体文件。
- 在已有 XeLaTeX 环境严格检查字体：`xelatex -interaction=nonstopmode -halt-on-error -output-directory=../dist '\def\RequireOfficialFont{1}\input{main.tex}'`，并重复编译至引用稳定。

## 当前验证状态

内置编译请求未返回诊断；已通过 GitHub XeLaTeX 首轮构建（[Actions](https://github.com/jiapengLi11/AgentGuard/actions/runs/39139293592)），初版为18页、361735字节，已取得实际PDF做版式检查。随后修正目录孤页、拉丁字体选面和图中连线；最新产物以PR #15对应提交的Actions附件为准。旧Release保持M21快照身份。

CI使用TeX Live 2025预置环境，latex-action固定提交，关闭shell escape，产出 `sujie-m25-latex-review` 附件。该环境使用FandolSong草稿替代，正式SimSun字体验收仍待完成。本机若捆绑Poppler缺少Adobe-GB1语言映射，不能以其漏画中文字判定PDF缺字；字体已嵌入，可用支持该映射的阅读器或MuPDF核查。

源码检查（不代替编译）：在仓库根目录运行 `python3 competition/submission/tools/check_report_latex.py`。它检查输入文件、引用、环境配对、摘要长度、匿名占位、官方说明页和所引用集成本地验证的源码摘要。

## 内容版本

- 基于主线 `99cba60`，集成本地记录为1025项回归通过；本轮没有重跑该回归。
- M25原冻结版本的48格脚本、48格本地HTTP和14格来源代表分别呈现，原始证据仍需独立移交。
- M24六链为有限Linux运行性记录，不作为M25完整隔离或性能验收。
- PR #14 的 DeepSeek/聊天控制台已取到本地审阅分支，仍未合入主线，因此不写成当前报告已验收功能。
- 文献核对与写作辅助出处见上一级 `LATEX_DELIVERY_REVIEW.md`。
