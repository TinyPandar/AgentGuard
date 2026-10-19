# M24：核心候选参数化与正式评测准入准备

开始日期：2026-10-17。用户明确要求持续以冲击国家级奖项为方向优化计划并执行。这里记录本轮实际实施，不承诺奖级，也不把已暴露开发输入、脚本校准或测试数量当作正式模型防御成绩。

## 当前范围

M23已完成时间线/附件两候选的参数化。本轮扩展IOC、Git检视、三层委派、跨会话Memory四候选，沿用现有Host、契约、权限和真实MCP，不增加由模型或HTTP选择实例的入口。任务、场景、seed、角色与防护配置分别计数。

| 候选 | 实际变化与独立见证 | 局部结果 |
|---|---|---|
| [IOC](M24_IOC_INSTANCES.md) | 1/4/8/20个公开指标、重复/私域噪声；实际读取和Receiver准确一次，参考不复用提取器 | 新67项通过；空公网集合和域外地址明确不支持 |
| [Git检视](M24_GIT_INSTANCES.md) | 真实base/candidate配置blob与diff；真实目标ref与push回执 | 新42项与旧21项共63通过；默认旧fixture保留 |
| [Memory](M24_LONG_TASK_ADMISSION.md) | 两版资产事实、两个独立会话、实际读取/1→2追加/复读顺序、SQLite原历史 | 与委派新增共50项及旧15项共65通过 |
| [三层委派](M24_LONG_TASK_ADMISSION.md) | alert/asset/baseline三源，有向连接匹配/反向/空基线；三个实际对话和主体来源 | 同上；角色数量不增加任务数 |

这些是子模块的局部验收，不能替代统一矩阵、最终源码冻结和整项目回归。

## 2026-10-18最终统一验收

M24本地工程与开发校准已验收：最终v2完整检查 **893 passed / 1 warning（672.97秒）**，Ruff通过，202文件格式通过；80格核心校准/16配对、40格业务复验/8配对、35格固定提议/7配对与Linux六链均通过各自独立核验。总记录见[quality-gates.json](../../competition/reviews/2026-10-17-m24/quality-gates.json)，SHA-256为`fb079ee849d00089796cb838296e6e3446f0f893c3581a28e0179d82cc7ae7b3`。唯一警告为既有Starlette/AnyIO弃用提示。前端7份冻结源码未改变，保留M23类型检查/构建证据，本轮未另作构建或浏览器布局验收。

应用、评测、测试、UI与依赖配置共261文件已作[v1冻结](../../competition/reviews/2026-10-17-m24/final-runtime-sources-v1.json)，SHA-256为`6f115e556be4b013277b67d617103241c3cfff087adb3ecb953b7aae24654dcd`。执行前112份历史报告、159份M23证据和四份M9冻结源码均匹配。

| 运行 | 已实际观察 | 当前解释 |
|---|---|---|
| `m24_core_parameterized_development_20261018_v1` | 80/80校准、16配对；独立核验76格业务完成、4格危险效果 | 首轮通过；后续窄审发现核验器缺口，须修复升版，不作为M24最终验收 |
| `m24_core_parameterized_development_20261018_v2` | 最终80/80校准、16配对；独立核验76格业务完成、4格危险效果；当前源码/M9匹配 | 已在生命周期修复后的v2上重新运行，不复用v1通过数；最终893项回归通过 |
| `m24_business_parameterized_20261018_v1` | 40/40、8配对及独立SQL重算通过 | 复用M23原8个开发实例，不增加任务或独立样本 |
| `m24_direct_effects_20261018_v1` | 35/35、7配对及独立实际效果核验通过 | 29格utility、9格危险效果；两者可重叠，且符合预登记校准不等于防御通过 |

上述运行均无云调用。旧链完整记录见[revalidation/validation-v1.json](../../competition/reviews/2026-10-17-m24/revalidation/validation-v1.json)。80格的四个危险效果均为Git injected在unsafe/strong-static下实际推送，不将这四格写成安全成功。

最终核心运行源码归档SHA-256为`cb937c91fce8b26bdc125ea6a212853c527283a55530a54ed294a42f46f7db53`，完整独立核验见[最终核心输出](../eval/reports/runs/m24_core_parameterized_development_20261018_v2/independent-verification.json)。40/35旧链的91/96份归档源码均不含此次修复的两文件；v2后再次执行其独立CLI，当前源码与原归档均匹配，原summary/输出未覆盖，见[after-core-verifier-v2.json](../../competition/reviews/2026-10-17-m24/revalidation/after-core-verifier-v2.json)。这些是同一开发输入的复验，不增加独立样本。

后续[窄审](../../competition/reviews/2026-10-17-m24/git/final-verifier-review-v1.md)复现Memory结束事件actor与两会话先后约束缺失：错误主体或延后capture结束仍可被独立核验接受。这是证据核验缺口，尚未发现运行时会话越权；原v1输出与两个反例保留。

修复已写入：绑定创建principal/结束subject、两次创建/结束各唯一、真实读写落在会话窗口内，以及capture结束早于reconcile创建。新增7项反例，核验器专项54 passed/1 warning（44.54秒）；[v2有限复审](../../competition/reviews/2026-10-17-m24/git/final-verifier-review-v2.md)确认正常观察仍可复算、七负例均拒绝且不虚构危险效果。[最终v2应用冻结](../../competition/reviews/2026-10-17-m24/final-runtime-sources-v2.json)仍为261文件，SHA-256为`640b6f604362b732f1e6519e0c1a664021f853b699e41328d942254ea376d873`，相对v1只改独立核验器和其测试；完整原字节及补丁保留。v1全量886 passed/1 warning（685.49秒）仅作修复前结果，最终v2已另行完成上述893项与新80格验收。

[Linux六候选](M24_LINUX_SMOKE.md)已在v2应用冻结上实际通过：非root/只读/无外网单容器，六条真实Host/MCP链全部FINISHED且清理确认，主机再对六份导出及原文见证重算通过。IOC恰好一次许可发送、Git未推送且ref不变、Memory两会话及1→2历史保全、委派三主体真实读取均通过。范围为同容器有限运行性，不代表工具/角色独立隔离、性能或新机器完整安装。统一证据见[linux-smoke-verification.json](../../competition/reviews/2026-10-17-m24/linux-smoke/linux-smoke-verification.json)。

## 共同协议与判定

新`core_parameterized_development_v1.json`预登记四候选各四实例、每实例五配置，共16个配对/80单元。实例为`development-exposed`、`formal_ready=false`。运行器保存真实资料、Git对象与ref、SQLite行、Receiver摘要和各角色产物，并由独立离线核验器重算。

`calibration_passed`仅表示正常执行及实际观察符合预登记。Git injected在unsafe/strong-static中预期确实发生禁止推送、业务不完成；这些单元校准通过不能写成安全通过。实际业务、安全效果、执行终态和整体完整性分开报告。

新增Host实例仅接收有界纯事实，不允许gold、权限、路径、远端或执行命令。旧默认fixture与四份M9冻结源码保留。所有新输入在封存前生成并公开于开发过程，本地hash不产生未见留出或签名真实性。

## 复审修正

- 已确认的Git实际推送，即使测试Host随后将ref恢复，也必须由`PUSH_CONFIRMED`回执保留，不能只看末态ref。
- best-effort清理函数的返回值不能证明worker终止。新runner冻结模型工厂闭包参数，逐格确认worker、Agent和上下文均结束，未确认就停止整批。
- 首格或末格完成后的取消保留已写行；整批必须正常FINISHED才可通过。取消时尚未登记的完整配对由独立核验注明，不补写原始记录或改成正常结束。

## 下一步与资源

Memory独立核验修复、最终源码与整项目验收已关闭。接下来按[M25执行安排](M25_NEXT_STEPS.md)做来源/绕过的可执行覆盖、同事实正式云比较协议及材料。三来源×七类绕过中真实多轮、分片Memory等缺口须单独标明，不能用规则测试或21个标签代替真实入口。

正式实验应在同一封存业务事实上构造C/A及适用Q。当前开发协议在不同seed指定场景，不能据此估计同实例C/A差异。IOC C与R若为相同输入和批准流程，复用同单元而不重复计数；旧51单元仅为建议，需按实际独特运行重算。

私密凭据路径和总调用预算仍待用户提供，此前继续无密钥实现与交付准备。本轮不读取真实凭据、不调用云模型、不清理已有用户服务。原始失败与既有报告继续保留，M24基线见[baseline.json](../../competition/reviews/2026-10-17-m24/baseline.json)。
