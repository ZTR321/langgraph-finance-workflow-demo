# project_2_langgraph_workflow.md

## 项目名称
基于 LangGraph 的金融问答与合规审核 Workflow Demo

## 一句话介绍
基于 LangGraph 搭建一个 `Researcher -> Tools -> Researcher -> Reviewer` 的最小工作流，让模型在需要时调用 A 股价格查询工具，并对最终输出做基础合规改写。

## 背景
- 目标不是做成熟投研系统，而是做一个**可解释、可运行、可演示**的 Workflow Demo
- 重点展示：
  - LangGraph 的节点流转
  - Tool Calling 闭环
  - 生成与审核职责拆分
  - Gradio Demo 封装

## 我的职责
- 设计 `Researcher` / `Reviewer` 双角色分工
- 封装 A 股价格查询工具，并补基础输入校验
- 用 `StateGraph` 组织 state / node / edge
- 增加基础 history 透传，让 Demo 至少具备上下文延续能力
- 设计基础输出审核 prompt，并封装为 Web Demo

## 技术栈
- LangGraph
- LangChain / OpenAI-compatible Chat 接口
- Tool Calling
- requests
- Gradio
- Prompt Engineering

## 真实代码主线
用户提问 -> `Researcher` 判断是否调工具 -> `Tools` 执行 A 股价格查询 -> 返回 `Researcher` 整合成初稿 -> `Reviewer` 做基础审核 -> Gradio 返回最终输出

## 更稳的项目定位
- 双角色工作流 Demo
- A 股价格查询 + 基础输出审核 Demo
- LangGraph 最小闭环实践
- 不是成熟投研系统
- 不是成熟风控系统

## 最值得讲的点
1. 真实写了 `bind_tools + ToolNode + tools_condition` 的完整闭环，不是只在 PPT 上讲 Agent。
2. 把“生成”和“审核”拆成两个节点，流程比单 prompt 更可解释。
3. `history` 现在真正接入了图调用入口，Demo 至少具备了基础上下文延续，而不再是纯单轮。
4. 工具函数增加了股票代码校验、市场前缀判断和基础异常处理，代码口径比旧版更稳。

## 面试时必须主动收住的边界
1. `Researcher` 和 `Reviewer` 仍然是**同一个 llm 实例**，只是 system prompt 不同，不是两个独立大脑。
2. 当前仍然只有一个工具 `get_ashare_price`，所以不能讲成多工具投研系统。
3. 合规审核仍然是 prompt 级改写，不是规则引擎，也不能说 100% 拦截。
4. history 只是会话消息透传，不是长期记忆、总结记忆或外部 memory store。
5. 工具返回仍然是字符串，不是结构化行情对象，所以这更像 Demo，而不是生产级工具层。

## 最容易被追问的实现细节
1. 为什么要用 LangGraph，而不是一个大 prompt 顺着写完？
2. `bind_tools`、`ToolNode` 和 `tools_condition` 分别做什么？
3. `State` 里为什么只有 `messages + latest_tool_result + draft_response` 这几个字段？
4. 用户只给股票名称时，为什么现在不再强行猜代码？
5. 你说 history 接上了，那它到底是不是“多轮记忆”？
6. Reviewer 为什么只能算输出审核，而不是完整风控？
7. 为什么说它是 Workflow Demo，而不是成熟投研系统？

## 易被质疑的漏洞
1. 使用第三方 OpenAI-compatible 接口，本身有稳定性和合规风险。
2. 工具依赖公开行情接口，格式脆弱，没有生产级 SLA。
3. 股票名称到代码仍然不是显式映射工具，模型只会在“高置信”时推断，否则会要求用户补代码。
4. state 虽然比旧版多了两个字段，但仍然是非常轻量的结构化状态。
