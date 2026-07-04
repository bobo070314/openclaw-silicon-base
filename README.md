# Silicon Body Fixer (硅基体修复者)

## 定位
这不是一个普通的运维脚本，而是面向 v4.0 工业级的自动修复协议载体。
它将运行在"硅基体"（Semiconductor / Lithium Battery Anode Substrates）之上。

## 核心哲学：对抗诡计体 (Anti-Deception)
本项目的核心不仅在于修复 Bug，更在于防御两种"诡计体"：
1. **物理诡计**：错误的分类与产业边界（如人类定义的"龙头"标签）。
2. **逻辑诡计**：AI 生成的概率幻觉与相关性的陷阱。

## 演进路线
- **v1.8 (Current)**: 逻辑层修复（Software fixes）。
- **v2.x**: 全链路自动化 + 故障类型扩展。
- **v4.0**: 协议标准化，嵌入物理硅基体（Hardware fixes）。
- **v5.0+**: 生态级自愈。

## 核心模块
| 模块 | 位置 | 说明 |
|---|---|---|
| 输入沙箱 | `src/core/apply_repair.py` | 防注入诡计 |
| 熵值监控 | `src/core/monitor_daemon.py` | 防沉默诡计 |
| 协议草案 | `docs/specs/AUTO_FIXER_PROTOCOL_v1.md` | 工业级协议 |

## 初始贡献者
[@bobo070314]
