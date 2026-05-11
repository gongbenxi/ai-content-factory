# AI Content Factory — Phase 1 PRD
## 多 Agent 化版本 v1.1

| 项目代号 | AI Content Factory (ACF) |
|---|---|
| 版本 | Phase 1 — v1.2 |
| 日期 | 2026-05-11 |
| 状态 | Draft（待评审） |
| 作者 | 产品 + 工程 |
| 关联文档 | `docs/design-mockups.html`（高保真 UI）/ `app/agents/graph.py`（LangGraph 状态机）/ `PLAN2.md`（实施计划） |

---

## 1. 产品概述

### 1.1 项目背景

随着大模型能力成熟与中文社交平台（公众号、小红书、抖音）内容供给爆炸，"AI 协助创作"已经从玩具走向生产工具。但当前直接用 ChatGPT/Claude 写稿的方式存在 **4 个结构性问题**：

1. **风格扁平化**：单 prompt 写出来的稿子模板感重，模仿不出特定 KOL 的语感与节奏
2. **事实幻觉**：尤其中文素材薄弱，时事类内容容易胡编
3. **图文割裂**：配图自己生成、文章自己生成，图与正文经常对不上号
4. **平台规范错配**：每个平台的字数、tag、首图、敏感词规则差异大，单稿适配成本高

### 1.2 产品愿景

> **让一个有内容直觉的运营，一个人能撑起以前 5 人小编团队的产能，且产出质量稳定不掉档。**

ACF 的核心思路：用**多 Agent 协同**模仿真人内容团队（主编→记者→写手→插画师→审稿）的工作流程，端到端产出"可直接发"的图文。

借鉴 GPT-Researcher 的三个核心启发：
1. **Planner / Worker 分层** — Planner 拆解任务成 N 个 sub-query，Researcher 并行执行（提速关键）
2. **Stateful Graph** — 用 LangGraph 把流水线建模为有限状态机，每步可 checkpoint、可回退、可人工介入
3. **职业化角色** — 每个 Agent 有专属 system prompt 和工具集，不让一个 agent 既当爹又当妈

### 1.3 目标用户

| 优先级 | 角色 | 场景 |
|---|---|---|
| **P0** | 内容主理人 / 自媒体运营 / 公司新媒体 | 每天产出 1~3 篇符合品牌调性的图文 |
| **P1** | 个人 KOL | 用自己的风格量产，扩大产能 |
| **P1** | MCN 内容主管 | 多账号矩阵的批量内容供应 |
| 暂不覆盖 | 视频脚本 / 学术论文 / 长篇深度报道 | Phase 2+ 再考虑 |

### 1.4 范围界定（In Scope / Out of Scope）

**Phase 1 包含**：
- ✅ 8 个 Agent 多角色协同生成（LangGraph 编排，前端 Timeline 展示 7 步）
- ✅ 中文热点采集（提取 3 个 skill 核心函数集成：baidu-hot / rss_fetcher / style_fingerprint）
- ✅ 风格指纹模仿（复用 style_fingerprint）
- ✅ 配图生成（硅基流动 FLUX/Kolors AI 生图 + ECharts 图表 + Pillow 卡片 + Playwright 信息图，五路径混合）
- ✅ Reviewer 审阅 + 自动修订闭环（max 2 轮）
- ✅ Web Dashboard（运行控制 + 文章管理）
- ✅ 草稿落库 + 编辑器二次修改
- ✅ Token 级成本追踪 + 多 Provider 模型切换
- ✅ 全链路事件回放（run_events + token_usage）
- ✅ Langfuse 全链路 LLM 可观测（trace / cost / latency）

**Phase 1 不包含（Phase 2+）**：
- ❌ 直接发布到小红书/公众号（仅留草稿，发布手动）
- ❌ 多账号矩阵
- ❌ 数据回流（阅读量、点赞）
- ❌ A/B 测试
- ❌ 移动端

---

## 2. 业务目标与成功指标

### 2.1 北极星指标

> **单运营人员日均产出可发布草稿数 ≥ 8 篇**（目前业内同等质量水平：3~4 篇/人/天）

### 2.2 关键指标

| 类别 | 指标 | Phase 1 目标 | 验证方式 |
|---|---|---|---|
| **效率** | 单篇生成耗时（端到端） | ≤ 8 分钟 | 系统埋点 |
| **效率** | 95p 耗时 | ≤ 12 分钟 | 系统埋点 |
| **成本** | 单篇 LLM + 图像总成本 | Token Plan 内趋近 ¥0；付费 provider ≤ ¥3 | LLM Provider 统计 + Langfuse |
| **质量** | 事实编造率 | < 5% | 抽查 20 篇人工核验 |
| **质量** | 风格盲测识别率 | < 70% | 朋友盲测 50 组 |
| **质量** | 图文一致 Reviewer 自动 pass 率 | ≥ 80% | Reviewer 日志 |
| **稳定** | 单次运行成功率（含修订） | ≥ 95% | LangGraph run_status |
| **稳定** | 同时跑 5 个 run 不互相阻塞 | 通过 | 压测 |

---

## 3. 用户故事

### 3.1 主路径（Must-have）

| ID | 用户故事 | 验收标准 |
|---|---|---|
| **M1** | 作为运营，我希望在 Dashboard 看到今天值得写的 3-5 个候选选题，点击其中一个就能开跑 | 候选选题来自当日热榜聚合，已排除最近 30 天写过的，按用户偏好排序 |
| **M2** | 作为运营，我希望看到 7 个 Agent 的实时进度（像快递物流），知道现在卡在哪一步 | SSE 推送 agent_start / token / tool_call / agent_done 事件，前端 Timeline 渲染 |
| **M3** | 作为运营，我希望收到草稿后能在编辑器里直接改、替换配图、看到风格匹配分数 | 富文本编辑器 + 配图替换面板 + 风格指纹对比雷达图 |
| **M4** | 作为运营，我希望标记"通过"后入文章库，导出 markdown 或后续接发布 | 状态机：drafting → reviewing → done，导出 .md |
| **M5** | 作为运营，我希望在风格管理里上传一个公众号文章 URL，自动抽取风格指纹 | URL → 抓取 → 调 style_fingerprint → 入库；最低 5 篇样本 |

### 3.2 异常路径（Should-have）

| ID | 用户故事 | 验收标准 |
|---|---|---|
| **A1** | 中途某个 Agent 失败 → 看到错误，能重试该 Agent 而不是从头跑 | LangGraph checkpoint + UI 上"Retry from XXX"按钮 |
| **A2** | Reviewer 不通过 → 自动 Reviser 修订，2 次后还不行让人介入 | max_revise_rounds=2，超出后状态置 `needs_human` |
| **A3** | 想中途停下来手动改大纲 → Pause / Edit / Resume | LangGraph 的 interrupt API + 前端 state 编辑面板 |
| **A4** | 某个外部 API 限流 → 退避重试，不打断整体 | tenacity 重试装饰器 + 错误事件流 |
| **A5** | 预算快超了 → 自动降级模型，而不是直接报错 | 80% 预算时触发降级，100% 时熔断 |

### 3.3 长期演进（Nice-to-have，Phase 1 不实现但留接口）

| ID | 用户故事 |
|---|---|
| **N1** | 自动按发布日历排期 |
| **N2** | 多账号风格切换 |
| **N3** | 阅读量回流后自动调优 prompt |
| **N4** | 团队多人协作（评论、@） |

---

## 4. 功能需求详述

### 4.1 Agent 团队（8 个角色，前端 Timeline 展示为 7 步——Reviser 归入 Reviewer 步骤）

```
                    ┌──────────────────┐
                    │   TopicAgent      │  选题：从热榜+用户偏好挑出今天写什么
                    │   (主编入口)      │
                    └────────┬─────────┘
                             ↓ 1 个 topic
                    ┌──────────────────┐
                    │   PlannerAgent   │  规划：拆成大纲 + N 个研究子问题
                    └────────┬─────────┘
                             ↓ N sub-queries (并行)
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ResearcherA │  │ResearcherB │  │ResearcherC │  并行调采集器+网页抓取
     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
           └─────────┬─────┴────────────────┘
                     ↓ 汇总素材
            ┌─────────────────┐
            │  EditorAgent    │  编辑：合并素材 + 选定风格 + 出最终大纲
            └────────┬────────┘
                     ↓
            ┌─────────────────┐
            │  WriterAgent    │  撰写：基于 style_fingerprint 写正文
            └────────┬────────┘
                     ↓ markdown 草稿
            ┌─────────────────┐
            │ IllustratorAgent│  配图：基于段落生成 N 张图（Seedream/Flux）
            └────────┬────────┘
                     ↓
            ┌─────────────────┐
            │ ReviewerAgent   │  审稿：校验图文一致性 + 风格 + 合规
            └────────┬────────┘
                     ↓ pass/fail + comments
                  ┌──┴──┐
                pass    fail
                  ↓      ↓
              [完成]  ┌─────────────────┐
                      │ ReviserAgent    │  修订：按 reviewer 反馈改稿
                      └─────┬───────────┘
                            └→ 回 ReviewerAgent (最多 2 次)
```

#### 角色卡

| Agent | 输入 | 输出 | 模型档位 | 工具集 | 预算占比 |
|---|---|---|---|---|---|
| **TopicAgent** | 用户偏好 + 今日热榜 + 历史文章 | `Topic{title, angle, platform, hook}` | 轻量 | `fetch_hotnews_unified`、`vector_search_history` | ~5% |
| **PlannerAgent** | Topic | `Outline{sections[]}` + `SubQueries[3-7]` | 主力 | 无（纯推理） | ~10% |
| **ResearcherAgent**（×N 并行） | 1 个 sub-query | `Snippets[]{url, title, excerpt, credibility}` | 轻量 | `web_search`、`scrape_url`、`vector_search_history` | ~20% |
| **EditorAgent** | Outline + Snippets + 风格指纹 | 最终大纲 + 引用关系 | 主力 | `load_style_fingerprint` | ~10% |
| **WriterAgent** | 大纲 + 引用 + 风格指纹 | Markdown 草稿 + `[IMG]` 占位符 | 主力 | 无（纯生成） | ~30% |
| **IllustratorAgent** | 配图 prompts | 图片 URL[] + alt 文本 | 轻量 | `gen_image_coze`、`generate_chart`、`generate_card` | 图像单独计费 |
| **ReviewerAgent** | 草稿 + 图片 + 平台规范 | `Review{score, issues[], pass}` | 主力 | `content_safety_check`、`image_consistency_check` | ~15% |
| **ReviserAgent** | 草稿 + Review issues | 修订草稿 | 主力 | 无 | ~10% |

---

### 4.2 选题模块（TopicAgent）

**输入**：
- 用户偏好画像 `{topics: [], styles: [], avoid_keywords: []}`
- 当日热榜（来自 6 个采集 skill 聚合）
- 用户文本指令（可选，如"今天写点 AI 圈的"）

**处理**：
1. 调用 `fetch_hotnews_unified` 拿当日热榜 100 条
2. `vector_search_history(query=topic_title, k=5)` 排除最近 30 天写过的
3. 按用户偏好领域过滤
4. LLM 选出最适合的 3~5 条，每条生成 2 个不同切入角度

**输出**：
```json
{
  "candidates": [
    {
      "title": "DeepSeek-V3 发布带来的国产大模型竞争格局变化",
      "angle": "技术拐点 + 商业影响双线",
      "target_platform": "wechat",
      "hook": "六百万美元，把硅谷震了",
      "estimated_quality": 0.85
    }
  ]
}
```

**UI**：Dashboard 顶部"今日选题"卡片列表，点击 → 进入 New Run。

---

### 4.3 规划模块（PlannerAgent）

**输入**：选定的 Topic 对象

**处理**：LLM 推理生成大纲 + 子查询，遵循"5 角度覆盖"原则：
- 背景 / 数据 / 案例 / 反方观点 / 未来趋势

**System Prompt 核心要求**：
- 研究子问题互不重叠，覆盖五个角度
- 每个问题能用一次搜索回答
- 用中文，包含具体的关键词、时间范围、限定条件

**输出**：
```json
{
  "outline": [
    {"section": "DeepSeek-V3 性能数据", "intent": "建立技术事实"},
    {"section": "对比 GPT-4o 和 Claude Sonnet", "intent": "横向参照"}
  ],
  "sub_queries": ["DeepSeek-V3 在 MMLU/HumanEval 等基准的具体得分", "..."]
}
```

**约束**：3 ≤ outline ≤ 6 节；3 ≤ sub_queries ≤ 7 条。

---

### 4.4 研究模块（ResearcherAgent，并行）

**输入**：1 个 sub_query（每个 worker 一个）

**处理**（每个 worker 独立）：
1. `web_search(query, k=5)` —— Tavily 优先
2. 对前 3 条 `scrape_url` 拿正文（Crawl4AI）
3. `vector_search_history(query, k=3)` 看历史素材有没有可复用的
4. LLM 从中筛 3~5 条"最有价值"的 snippet

**并行机制**：使用 LangGraph 的 `Send` API 动态 fan-out：
```python
from langgraph.types import Send

def research_dispatcher(state):
    return [
        Send("researcher_worker", {"query": q, "topic": state["topic"]})
        for q in state["sub_queries"]
    ]
```

N 个 worker 同时执行，结果通过 `snippets: Annotated[list[dict], add]` reducer 自动合并。

**输出**：
```json
{
  "snippets": [
    {
      "source": "https://...",
      "title": "...",
      "excerpt": "...",
      "credibility": 0.85,
      "angle": "数据"
    }
  ]
}
```

---

### 4.5 编辑模块（EditorAgent）

**输入**：原始 outline + 所有 snippets

**处理**：
1. 加载用户选定的 `style_fingerprint`
2. LLM 综合素材调整大纲（删/合/补节）
3. 决定每节引用哪几条 snippet
4. 输出"最终大纲 + 引用关系"

**输出**：
```json
{
  "final_outline": {
    "sections": [
      {"section": "...", "intent": "...", "cite_snippet_ids": [3, 7, 12], "target_words": 400}
    ]
  },
  "style_adjustments": "保留 caoz 短句节奏；段落首句作为强观点钩子"
}
```

---

### 4.6 写作模块（WriterAgent）

**输入**：final_outline + snippets + 风格指纹

**处理**：
- 系统提示包含风格指纹（句法特征、高频词、修辞偏好、5 条样本句）
- **写作时同步决定配图位置**（不是写完后再贴图），在合适位置插入 `[IMG: ...]` 占位符
- 流式输出，前端实时展示

**配图决策规则**（写在 system prompt 里，让 Writer 自己判断）：

| 段落特征 | 配图类型 | 何时使用 |
|---|---|---|
| 文章首段（hook 段） | `cover` | 必配，1 张 |
| 出现具体数字、对比 | `chart` | 数据 ≥ 2 个时配 |
| 出现场景描述、人物 | `illustration` | 关键场景配 |
| 出现金句、结论 | `card` | 全文 ≤ 1 张 |
| "X 个要点对比"列表 | `infographic` | 4 个以上要点时 |

**总数控制**：1500 字内 ≤ 3 张图，1500–3000 字 ≤ 5 张图。

**占位符语法**（机器可解析）：

```
[IMG: <描述> | <比例> | <类型>]

- 描述：30~80 字中文，画面内容要呼应所在段落，包括场景、对象、氛围
- 比例：16:9（横）/ 1:1（方）/ 3:4（竖）/ 9:16（小红书）
- 类型：cover / chart / illustration / card / infographic
```

**WriterAgent System Prompt 结构**：

```
你是 {persona_name} 风格的写手。下面是这个人的写作指纹：

句法特征: {syntax_patterns}
高频词: {top_words}
修辞偏好: {rhetorical_features}
样本句（5 条参考）:
{examples}

---

现在按以下大纲撰写一篇适合 {target_platform} 的文章：
{outline}

可用素材（必须引用，不许编造）：
{snippets}

要求：
- 模仿上述风格，但事实必须基于素材
- 在合适的段落位置（不是机械每段一张）插入 [IMG: 描述 | 比例 | 类型] 占位符
- 配图决策：首段必配 cover；数字/对比段配 chart；场景段配 illustration；金句段配 card
- 描述要呼应该段内容，让插画师能据此生成与正文匹配的图
- 输出纯 markdown，不要前缀解释
```

**输出示例**：

```markdown
# 六百万美元，把硅谷震了

[IMG: 杭州深夜的办公楼，一扇窗亮着灯，工程师围着白板讨论模型架构，
扁平插画风，冷蓝色调 | 16:9 | cover]

DeepSeek-V3 在 MMLU 上得了 87.5 分，碾压 GPT-4o 的 86.0。
更狠的是训练成本——只花了 557.6 万美元。

[IMG: DeepSeek-V3 与 GPT-4o、Claude 3.5 在 MMLU/HumanEval 三项基准
得分对比柱状图，蓝橙绿三色 | 16:9 | chart]

## 为什么这次震得不一样？
...

> "六百万美元，相当于 OpenAI 一个月电费。"

[IMG: 大字金句卡，引用文字"六百万美元，相当于 OpenAI 一个月电费"，
深色背景白字，微缩景观 | 1:1 | card]
```

**约束**：单篇 1500~2500 字（公众号默认）；2~5 张配图。

---

### 4.7 配图模块（IllustratorAgent）— 混合方案

**输入**：Writer 输出的 markdown 草稿（含 `[IMG: 描述 | 比例 | 类型]` 占位符）

**核心原则**：图文匹配靠**写作时同步决定 + 上下文增强 prompt + 校验闭环**三层保障，单一环节不背全责。

#### 4.7.1 五路径分发（按 type）

| 类型 | 实现路径 | 主 provider | 时间 | 成本 | 中文友好 |
|---|---|---|---|---|---|
| `chart` | ECharts SSR 渲染 | 本地（pyecharts + Playwright） | <1s | ¥0 | ✅ |
| `cover` | AI 生图（中文海报特化） | **硅基流动 Kolors** | 5–10s | ~¥0.05/张 | ✅✅ |
| `illustration` | AI 生图（场景氛围） | **硅基流动 FLUX.1-schnell** | 3–5s | ¥0（免费档） | ✅ |
| `card` | Pillow 模板渲染 | 本地 | <1s | ¥0 | ✅✅ |
| `infographic` | HTML 模板 + Playwright 截图 | 本地 | 1–2s | ¥0 | ✅✅ |

**Provider 备份链路**（任一主路径失败时按优先级降级）：

| 主 provider | 备 1 | 备 2 |
|---|---|---|
| 硅基流动 FLUX/Kolors | 火山引擎即梦 3.0 | Coze Seedream 4.5 |

通过 `config/image_providers.yaml` 配置优先级，`tenacity` 重试 + 失败转下一 provider。

#### 4.7.2 处理流程（端到端 7 步）

```
① 解析占位符（保留 ±400 字上下文）
        ↓
② Prompt 增强（LLM 改写：中文→英文，融合上下文，加风格/构图/负面词）
        ↓
③ 缓存查询（prompt_hash 命中直接复用，命中率 30%+ 节省成本）
        ↓
④ 按 type 分发到 5 路径，并发生图（备选池 N=2）
        ↓
⑤ 下载落盘（data/images/{run_id}_{para_id}.png）
        ↓
⑥ 倒序替换占位符 → markdown ![](url)
        ↓
⑦ 写入 runs.images JSONB，绑定 context_excerpt 给 Reviewer
```

#### 4.7.3 关键实现：占位符解析 + 上下文增强

**解析（带 ±400 字上下文）**：

```python
import re

IMG_PATTERN = re.compile(r'\[IMG:\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^\]]+?)\s*\]')

def parse_placeholders(draft_md: str) -> list[dict]:
    placeholders = []
    for i, m in enumerate(IMG_PATTERN.finditer(draft_md)):
        start, end = m.span()
        placeholders.append({
            "para_id": i,
            "description": m.group(1).strip(),
            "ratio":       m.group(2).strip(),
            "type":        m.group(3).strip(),
            "context_before": draft_md[max(0, start-400):start],   # ★ 关键：前文 400 字
            "context_after":  draft_md[end:min(len(draft_md), end+100)],
            "raw":            m.group(0),
            "position":       start,
        })
    return placeholders
```

**Prompt 增强（图文匹配率 60% → 90%+ 的关键步骤）**：

```python
async def enhance_prompt(placeholder: dict, style_id: str) -> str:
    """让 LLM 把占位符描述与上下文融合，生成详细英文 prompt。"""
    return await llm.chat("illustrator", messages=[{
        "role": "system",
        "content": """你是 AI 绘图 prompt 工程师。
任务：把图片描述与文章上下文融合，生成详细英文 prompt。
要求：
1. 画面内容必须呼应前文段落，不只看 description
2. 风格匹配文章调性（caoz=冷峻写实 / 小红书=清新明亮 / 商业=简洁）
3. 加构图细节：构图(close-up/wide-shot)、光线(soft/dramatic)、色彩
4. 加负面词：avoid: text, watermark, distorted hands, ugly face
5. 公众号封面避免出现真实人脸（肖像权）"""
    }, {
        "role": "user",
        "content": f"""前文段落：{placeholder['context_before']}
图片描述：{placeholder['description']}
画面类型：{placeholder['type']}
画幅比例：{placeholder['ratio']}
文章风格：{style_id}"""
    }])
```

**对比效果**：

| 直接喂占位符描述 | 上下文增强后 prompt |
|---|---|
| "杭州深夜 DeepSeek 办公室年轻工程师讨论" | `A cinematic wide shot of a modern tech office in Hangzhou at night, young Chinese engineers gathered around a glass whiteboard with neural network diagrams, warm desk lamps casting soft shadows, blue glow from monitors, flat illustration style with muted colors. avoid: text, watermark, distorted faces` |

#### 4.7.4 图像 API 调用（OpenAI 兼容）

硅基流动兼容 OpenAI Images API，与 §6.1 LLM 抽象层共用 `AsyncOpenAI` 客户端：

```python
from openai import AsyncOpenAI

img_client = AsyncOpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

resp = await img_client.images.generate(
    model="black-forest-labs/FLUX.1-schnell",   # 或 "Kwai-Kolors/Kolors"
    prompt=enhanced_prompt,
    size="1024x576",   # 16:9
    n=2,                # ★ 备选池：每张生 2 张候选给用户选
)
```

#### 4.7.5 替换占位符（倒序避免位移）

```python
def render_with_images(draft_md: str, placeholders: list, generated: list[dict]) -> str:
    # 按 position 倒序替换：替换后字符长度变化不影响前面的 position
    pairs = sorted(zip(placeholders, generated), key=lambda x: x[0]["position"], reverse=True)
    for p, img in pairs:
        markdown_img = f"![{p['description']}]({img['url']})"
        draft_md = draft_md[:p['position']] + markdown_img + draft_md[p['position']+len(p['raw']):]
    return draft_md
```

#### 4.7.6 落库结构（写入 runs.images JSONB）

```json
{
  "images": [
    {
      "para_id": 0,
      "type": "cover",
      "description": "杭州深夜的 DeepSeek 办公室年轻工程师讨论",
      "enhanced_prompt": "A cinematic wide shot of a modern tech office...",
      "url": "data/images/a8c2f9e1_0.png",
      "alt_urls": ["data/images/a8c2f9e1_0_alt.png"],
      "ratio": "16:9",
      "model": "Kwai-Kolors/Kolors",
      "context_excerpt": "...更狠的是训练成本——只花了 557.6 万美元。",
      "consistency_score": 8.5,
      "regenerate_count": 0,
      "cost_cents": 5
    }
  ]
}
```

`context_excerpt`（生成时绑定的段落尾巴 150 字）是 Reviewer 二审时直接判定依据，不用每次去 markdown 里 grep。

#### 4.7.7 图文一致性校验（在 ReviewerAgent 中执行）

**Phase 1：纯文本判断**（默认）

```python
async def check_image_consistency(images: list, final_md: str) -> list[dict]:
    issues = []
    for img in images:
        para = extract_paragraph_around(final_md, img["url"])
        result = await llm.chat_json("reviewer", messages=[{
            "role": "system",
            "content": "判断图片描述是否与段落内容匹配。返回 {match: bool, score: 0-10, reason: ...}"
        }, {
            "role": "user",
            "content": f"段落：\n{para}\n\n图片描述：{img['description']}\n图片类型：{img['type']}"
        }])
        if not result["match"] or result["score"] < 7:
            issues.append({
                "type": "image_mismatch",
                "para_id": img["para_id"],
                "image_url": img["url"],
                "detail": result["reason"],
                "severity": "warning" if result["score"] >= 5 else "critical",
            })
    return issues
```

**Phase 2：Vision 真实校验**（升级）

文本校验只能判断"描述 vs 段落"，**Vision 能判断"实际生成的图 vs 段落"**——防止 AI 生图跑偏（prompt 写"工程师讨论"，生成的图却是机器人）。

| 阶段 | 模型 | 成本 | 准确率 |
|---|---|---|---|
| Phase 1 | LLM 纯文本（MiMo-V2.5-Pro） | Token Plan 内 ¥0 | ~80% |
| Phase 2 | **GLM-4V**（智谱）或 **Qwen-VL-Max**（阿里） | ~¥0.01/次 | ~95% |

#### 4.7.8 Reviser 修订策略（图文不匹配时）

**双策略：优先改文，次之重生图**：

```python
async def revise_image_mismatch(issue: dict, draft_md: str, images: list):
    img = next(i for i in images if i["para_id"] == issue["para_id"])
    para = extract_paragraph_around(draft_md, img["url"])

    # 策略 A：改段落（成本低、保留视觉投资、不影响整体一致性）
    if issue["severity"] != "critical":
        new_para = await llm.chat("reviser", "微调段落使与图匹配，保持语义和风格...")
        return draft_md.replace(para, new_para), images

    # 策略 B：重生图（段落涉及关键事实/数字/品牌名时不能改）
    new_img = await regenerate_image(img, draft_md, attempt=img["regenerate_count"]+1)
    images_updated = [new_img if i["para_id"] == img["para_id"] else i for i in images]
    return draft_md, images_updated
```

**为什么优先改文？**

| 维度 | 改文 | 重生图 |
|---|---|---|
| 时间 | ~2s | ~10s |
| 成本 | ¥0.001 | ~¥0.05 |
| 视觉一致性 | 不影响（图保留） | 风险（新图风格可能跳） |
| 适用 | 段落非关键事实 | 段落涉及核心数字/引用 |

#### 4.7.9 缓存机制（降本 30%+）

`runs.images` 之外，单独维护一张图片缓存表（已在 §4.12.2 Schema 列明）：

```sql
CREATE TABLE image_cache (
    prompt_hash  TEXT PRIMARY KEY,    -- SHA256(enhanced_prompt + size + model)
    url          TEXT NOT NULL,
    local_path   TEXT,
    model        TEXT NOT NULL,
    size         TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    hit_count    INT DEFAULT 0
);
```

热门 prompt（如"杭州 AI 公司办公室深夜调试场景"）多次生成命中缓存，秒返且零成本。

---

### 4.8 审阅模块（ReviewerAgent）

**输入**：完整草稿 + 所有图片

**处理**：
1. **内容安全**：调 `content_safety_check`（敏感词库 + 阿里云内容安全）
2. **图文一致性**：详见 §4.7.7
   - Phase 1：LLM 纯文本判断（图片 description + context_excerpt vs 段落）
   - Phase 2：GLM-4V / Qwen-VL-Max 真实 Vision 校验
3. **风格匹配**：对比草稿和风格指纹的统计特征
4. **平台规范**：字数、emoji 用量、tag 数量是否符合目标平台
5. LLM 综合打分 + 列举 issues（image_mismatch 类型驱动 §4.7.8 双策略修订）

**输出**：
```json
{
  "pass": false,
  "score": 6.8,
  "issues": [
    {"type": "image_mismatch", "para_id": 2, "detail": "图描绘的是发布会，但段落讲商业影响"},
    {"type": "style_drift", "detail": "结尾过于客观，原作者偏煽情"}
  ],
  "summary": "图文有 1 处不一致；结尾风格偏离。需修订。"
}
```

**通过阈值**：score ≥ 7.5 且 issues 中无 P0 类型。

---

### 4.9 修订模块（ReviserAgent）

**输入**：当前草稿 + Reviewer 的 issues

**处理**：LLM 针对每条 issue 做精修（不重写整篇）

**输出**：修订后的草稿，回到 Reviewer 二审

**循环上限**：`max_revise_rounds=2`，超出 → 状态 `needs_human`，UI 弹人工介入。

---

### 4.10 LangGraph 状态机

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

class ContentState(TypedDict):
    # 输入
    run_id: str
    user_request: str
    user_preferences: dict             # {topics, styles, avoid_keywords}
    target_platform: str
    style_id: str | None

    # 中间产物
    topic: dict | None
    outline: list[dict] | None
    sub_queries: list[str] | None
    snippets: Annotated[list[dict], add]   # reducer：并发追加
    final_outline: dict | None
    draft_md: str | None
    images: list[dict]                 # IllustratorAgent 填充

    # 审阅
    review: dict | None
    revise_count: int

    # 计量
    cost_cents: int
    usage_by_agent: dict               # per-agent {input_tokens, output_tokens, cost_cents}

# ---- Graph 构建 ----
g = StateGraph(ContentState)

g.add_node("topic", topic_agent)
g.add_node("planner", planner_agent)
g.add_node("researcher_worker", researcher_worker)
g.add_node("editor", editor_agent)
g.add_node("writer", writer_agent)
g.add_node("illustrator", illustrator_agent)
g.add_node("reviewer", reviewer_agent)
g.add_node("reviser", reviser_agent)

g.set_entry_point("topic")
g.add_edge("topic", "planner")

# fan-out：N 个 sub_query → N 个 researcher_worker 并行
g.add_conditional_edges("planner", research_dispatcher, ["researcher_worker"])

# fan-in：所有 worker 完成后聚合到 editor
g.add_edge("researcher_worker", "editor")
g.add_edge("editor", "writer")
g.add_edge("writer", "illustrator")
g.add_edge("illustrator", "reviewer")

# 条件边：pass → END；fail → reviser（最多 2 轮）
def review_gate(state):
    if state["review"]["pass"]:
        return "done"
    if state["revise_count"] >= 2:
        return "done"
    return "revise"

g.add_conditional_edges("reviewer", review_gate, {"done": END, "revise": "reviser"})
g.add_edge("reviser", "reviewer")

# 持久化 checkpoint
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(PG_URL)
graph = g.compile(checkpointer=checkpointer)
```

**Checkpoint 用途**：
- 断点续跑：run 中途挂了，从最后一个完成的 agent 恢复
- 人工介入：Pause → 修改 state → Resume
- 回放：结合 run_events 回看每次 run 的完整过程

---

### 4.11 Token 监控与成本控制

#### 4.11.1 Token 计量

每次 LLM 调用从 OpenAI 兼容 API 响应中直接获取 `usage`（所有 provider 通用）：

```python
async def call_llm(agent: str, messages: list, provider: str, model: str):
    client = get_client(provider)  # 根据 provider 获取对应的 AsyncOpenAI 实例
    resp = await client.chat.completions.create(model=model, messages=messages, max_tokens=4096)
    usage = {
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }
    return resp.choices[0].message.content, usage
```

#### 4.11.2 按 Agent 追踪

```python
@dataclass
class AgentUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: int = 0

# ContentState 中按 agent 分别记录，前端可实时展示每个 agent 的消耗
```

#### 4.11.3 成本计算

按 provider + model 的实际单价计算（Token Plan 内可能趋近 ¥0，但仍记录）：

```python
# 每个 provider 的模型定价（可从外部配置加载）
MODEL_PRICING = {
    # provider:model → (input_per_million_cents, output_per_million_cents)
    "xiaomi:MiMo-V2.5":       (0, 0),       # Token Plan 内免费
    "xiaomi:MiMo-V2.5-Pro":   (0, 0),       # Token Plan 内免费
    "deepseek:deepseek-chat":  (14, 28),     # ¥1/百万输入, ¥2/百万输出
    "openai:gpt-4o-mini":     (15, 60),     # $0.15/$0.60
    "openai:gpt-4o":          (250, 1000),  # $2.5/$10
}

def calc_cost(usage: dict, provider: str, model: str) -> int:
    key = f"{provider}:{model}"
    input_price, output_price = MODEL_PRICING.get(key, (0, 0))
    cost = (
        usage["input_tokens"] * input_price / 1_000_000
        + usage["output_tokens"] * output_price / 1_000_000
    )
    return round(cost)
```

#### 4.11.4 Token 预算熔断

- 单 run token 硬上限：`max_tokens_per_run = 200,000`（总 token 数）
- 80% 消耗时：触发事件警告 + 自动降级到 `fast` 档位模型
- 100% 消耗时：熔断中断，保存当前中间状态，状态置 `budget_exceeded`
- 付费 provider 时：改为按金额熔断（`budget_limit_cents = 300`）

#### 4.11.5 动态降级策略

```python
async def call_with_budget_guard(agent: str, messages: list, provider: str, tier: str, state):
    # Token 熔断检查
    if state["total_tokens_used"] > MAX_TOKENS_PER_RUN * 0.8:
        tier = "fast"  # 降级到轻量模型
        state.emit("budget.warning", agent=agent, action="downgraded")
    if state["total_tokens_used"] > MAX_TOKENS_PER_RUN:
        raise BudgetExceeded("已超出 token 上限")

    model = resolve_model(provider, tier)
    return await call_llm(agent, messages, provider, model)
```

---

### 4.12 数据层

#### 4.12.1 技术选型：PostgreSQL + pgvector

| 项 | 选择 |
|---|---|
| 数据库 | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 async + psycopg |
| 向量维度 | 1024（BGE-M3） |
| Embedding | BGE-M3 本地部署 |
| Checkpoint | LangGraph PostgresSaver（自动建表） |

选型理由：
- pgvector 一步到位，Phase 1 就能用语义去重，不用 Phase 2 再迁移
- LangGraph 原生支持 PostgresSaver，checkpoint 持久化零成本
- 支持后续水平扩展（多 worker 并发 run）

#### 4.12.2 Schema

设计原则：
- 一个 `run` = 一次完整的「输入 → 草稿 → 审稿 → 完成」生命周期，**1 篇文章 1 个 run**，文章字段直接落在 `runs` 表上（合并模型），避免 articles ↔ runs 状态同步复杂度
- `run_events` 单独建表存事件流（高频写入、按 run 回放）
- `styles` 主表存风格指纹元数据，`style_samples` 存范文
- 所有需要语义检索的表（`runs`、`snippets`、`style_samples`）携带 `embedding VECTOR(1024)`

```sql
-- ============================================================
-- 1. 运行 / 文章主表（合并模型：一个 run 即一篇文章）
-- ============================================================
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 输入
    user_request    TEXT,
    style_id        TEXT REFERENCES styles(id),
    target_platform TEXT NOT NULL,
    config          JSONB DEFAULT '{}',     -- {research_parallel, max_revise_rounds, max_images, budget_limit_cents, model_mode}

    -- 中间产物
    topic           JSONB,                  -- {title, angle, hook, estimated_quality}
    outline         JSONB,                  -- {sections: [...], sub_queries: [...]}
    final_outline   JSONB,                  -- Editor 输出
    draft_md        TEXT,
    final_md        TEXT,
    images          JSONB DEFAULT '[]',     -- [{para_id, type, prompt, url, ratio}]
    review          JSONB,                  -- {pass, score, issues, summary}
    revise_count    INT DEFAULT 0,

    -- 状态机
    status TEXT NOT NULL DEFAULT 'drafting'
           CHECK (status IN ('drafting', 'reviewing', 'needs_human', 'done', 'published', 'failed')),
    current_agent   TEXT,                   -- 当前正在跑的 agent
    error           TEXT,

    -- 计量
    cost_cents      INT DEFAULT 0,
    total_tokens    INT DEFAULT 0,
    usage_by_agent  JSONB DEFAULT '{}',     -- per-agent {input_tokens, output_tokens, cost_cents}

    -- 检索用
    embedding       VECTOR(1024),           -- 由 topic+title 生成，用于选题去重 / 历史避重

    -- 时间戳
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX runs_status_idx     ON runs(status);
CREATE INDEX runs_started_at_idx ON runs(started_at DESC);
CREATE INDEX runs_embedding_idx  ON runs USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- 2. 事件流（SSE 实时推送 + 历史回放）
-- ============================================================
CREATE TABLE run_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts_offset   REAL NOT NULL,              -- 相对 run 开始的秒数
    event_type  TEXT NOT NULL,              -- graph.start / agent.start / agent.token / tool.call / agent.done / review.done / image.generated / budget.warning / graph.done
    data        JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX run_events_run_idx  ON run_events(run_id, id);   -- SSE 增量拉取按 id > after_id
CREATE INDEX run_events_type_idx ON run_events(event_type, created_at DESC);

-- ============================================================
-- 3. 研究素材（可跨 run 复用，避免重复抓取）
-- ============================================================
CREATE TABLE snippets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      TEXT,                       -- 来源平台（baidu / rss / web 等）
    url         TEXT UNIQUE NOT NULL,
    title       TEXT,
    content     TEXT,
    excerpt     TEXT,
    credibility FLOAT,
    angle       TEXT,                       -- 背景 / 数据 / 案例 / 观点 / 趋势
    embedding   VECTOR(1024),
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX snippets_embedding_idx  ON snippets USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX snippets_fetched_at_idx ON snippets(fetched_at DESC);

-- ============================================================
-- 4. 风格指纹主表
-- ============================================================
CREATE TABLE styles (
    id              TEXT PRIMARY KEY,        -- 'caoz' / 'xhs_zhongcao' 等可读 ID
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    fingerprint     JSONB DEFAULT '{}',      -- style_fingerprint 输出（句法、高频词、修辞偏好等）
    sample_count    INT DEFAULT 0,
    total_generated INT DEFAULT 0,           -- 用此风格已生成的文章数
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. 风格样本范文
-- ============================================================
CREATE TABLE style_samples (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    style_id    TEXT NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    source_url  TEXT,
    title       TEXT,
    text        TEXT NOT NULL,
    embedding   VECTOR(1024),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX style_samples_style_idx ON style_samples(style_id);

-- ============================================================
-- 6. 图片生成缓存（同 prompt+model+size 命中复用，降本 30%+）
-- ============================================================
CREATE TABLE image_cache (
    prompt_hash TEXT PRIMARY KEY,            -- SHA256(enhanced_prompt + size + model)
    url         TEXT NOT NULL,
    local_path  TEXT,
    model       TEXT NOT NULL,               -- FLUX.1-schnell / Kolors / 即梦 3.0 / ...
    size        TEXT NOT NULL,               -- 1024x576 / 1024x1024 / ...
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    hit_count   INT DEFAULT 0
);

-- ============================================================
-- 7. Token 消耗明细（每次 LLM 调用一条记录）
-- ============================================================
CREATE TABLE token_usage (
    id                BIGSERIAL PRIMARY KEY,
    run_id            UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    agent             TEXT NOT NULL,
    provider          TEXT NOT NULL,          -- xiaomi / deepseek / openai
    model             TEXT NOT NULL,
    input_tokens      INT NOT NULL,
    output_tokens     INT NOT NULL,
    cache_read_tokens INT DEFAULT 0,
    cost_cents        INT NOT NULL,
    latency_ms        INT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX token_usage_run_idx   ON token_usage(run_id);
CREATE INDEX token_usage_agent_idx ON token_usage(agent, created_at DESC);
```

#### 4.12.2.1 表间关系

```
                   ┌────────────────────────┐
                   │       styles           │  风格主表
                   │   id, fingerprint      │
                   └──────┬─────────────────┘
                          │ 1:N
                  ┌───────┴─────────┐
                  │  style_samples  │  范文
                  │  text, embedding│
                  └─────────────────┘

                   ┌────────────────────────┐
                   │       runs             │  运行 = 文章（合并模型）
                   │  status, draft_md,     │
                   │  final_md, embedding   │
                   └──────┬──────┬──────────┘
                          │ 1:N  │ 1:N
                  ┌───────┘      └────────┐
            ┌─────▼──────┐        ┌───────▼────────┐
            │ run_events │        │  token_usage   │
            │  事件流     │        │  per-call 计量  │
            └────────────┘        └────────────────┘

                   ┌────────────────────────┐
                   │       snippets         │  研究素材（跨 run 复用）
                   │   url unique, embed    │
                   └────────────────────────┘
```

#### 4.12.2.2 Status 状态机

```
       create
         ↓
     ┌─────────┐
     │drafting │ ← Topic/Planner/Research/Editor/Writer/Illustrator
     └────┬────┘
          ↓ Reviewer 开始
     ┌──────────┐    pass=true        ┌──────┐
     │reviewing │ ───────────────────→│ done │
     └────┬─────┘                     └──┬───┘
          │ pass=false                   │ 用户标记发布
          │ revise_count<2               ↓
          └─────► reviser → reviewing  ┌──────────┐
                                       │published │
                  pass=false &&        └──────────┘
                  revise_count>=2
                       ↓
                  ┌────────────┐
                  │needs_human │  人工介入
                  └────────────┘

                  任意阶段异常
                       ↓
                  ┌────────┐
                  │ failed │
                  └────────┘
```

#### 4.12.3 RAG 双层检索

| 层 | 用途 | 检索方式 |
|---|---|---|
| **L1: 新鲜素材** | Researcher 阶段，避免重复抓取 | `snippets` 表，最近 24h，cosine 相似度 |
| **L2: 历史避重** | TopicAgent 阶段，避免炒冷饭 | `runs` 表（已完成的文章），最近 90d，cosine 相似度 |

```python
async def vector_search_history(query: str, k=5):
    emb = await embed_text(query)  # BGE-M3 本地
    return await db.fetch(
        """
        SELECT id, topic, final_md, 1 - (embedding <=> $1) AS sim
        FROM runs
        WHERE status IN ('done', 'published')
          AND created_at > NOW() - INTERVAL '90 days'
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        emb, k,
    )
```

---

### 4.13 Skills_Repo 集成方案

**原则**：把需要的 Skill 核心代码直接搬进 `app/tools/`，不再依赖外部 Skills_Repo 路径。只提取核心采集/分析函数，去掉 CLI 入口、DB 写入、HTML 报告等外壳代码。

#### Phase 1 集成清单

| 来源 Skill | 集成到 | 核心文件 | 提取内容 | 依赖 |
|---|---|---|---|---|
| `baidu-hot-cn-1` | `app/tools/hotnews.py` | `scripts/baidu_hot.py` | `get_baidu_hot()`：urllib 请求百度实时热搜 API | 纯 Python stdlib |
| `rss_fetcher` | `app/tools/hotnews.py` | `scripts/fetch.py` | RSS 解析 + 多线程批量抓取 + 增量去重 | 纯 Python stdlib |
| `style_fingerprint` | `app/tools/style.py` | `style_fingerprint.py` | `StyleFingerprint` 类：中文文本风格分析 | 纯 Python stdlib |

#### 不集成

| Skill | 原因 |
|---|---|
| `image-gen-coze-1.1.3` | 核心逻辑集成到 `app/tools/image_gen.py`（调 Coze API） |
| `coze-workflow-1.1.3` | 调用层逻辑集成到 `app/tools/image_gen.py` |
| `ec_creator` | 电商文案，非主流程 |
| `weibo-publisher` | 发布功能 Phase 2 |
| `longtask_system` | 用 LangGraph + FastAPI BackgroundTasks 替代 |

#### Phase 2 补充

| 来源 Skill | 说明 |
|---|---|
| `weibo-fresh-posts-0` | 依赖 openclaw 浏览器自动化，Phase 2 改写为 API 方式 |
| `zhihu-fetcher` | 依赖 Node.js，Phase 2 改写为纯 Python |
| `toutiao-news-trends-0` | 依赖 Node.js，Phase 2 改写 |
| `douyin-hot-trend-1` | 依赖 Node.js，Phase 2 改写 |

---

### 4.14 前端关键页面

| 页面 | 路由 | 核心 UI 要素 |
|---|---|---|
| **Dashboard** | `/` | 选题候选卡片、运行中任务、最近文章、KPI 数字（含成本统计） |
| **New Run** | `/runs/new` | 选题确认、风格选择、平台 toggle、模型选择、预算设置、开跑按钮 |
| **Run Live** | `/runs/{id}` | 7 节点 Timeline、当前 token 流式预览、per-agent 成本、控制按钮（pause/resume/abort） |
| **Article Editor** | `/runs/{id}/edit` | TipTap 富文本、配图栏、风格匹配雷达图、平台预览（编辑同一个 run 的 draft_md） |
| **Style Manager** | `/styles` | 风格卡片网格、上传范文、指纹可视化（词云+句法图） |
| **Settings** | `/settings` | Provider 选择、Agent 模型分配、API Keys、并发上限、预算阈值 |

---

## 5. 非功能需求

### 5.1 性能

| 项 | 目标 |
|---|---|
| 单次端到端耗时（中位数） | ≤ 8 分钟 |
| 单次端到端耗时（95p） | ≤ 12 分钟 |
| 单 run 硬超时 | 15 分钟（超出强制 abort，保存中间产物） |
| Web Dashboard 首屏 | ≤ 2s |
| SSE 事件延迟 | ≤ 200ms |
| 并发 run 上限 | 5（单机）/ 可水平扩展 |

### 5.2 成本控制

| 项 | 目标 |
|---|---|
| 单篇 LLM 成本 | 取决于 provider，Token Plan 内趋近 ¥0 |
| 单篇图像成本 | Coze 免费额度内，趋近 ¥0 |
| 模型分级 | 非核心 Agent 用轻量模型；核心 Agent 用主力模型 |
| Token 消耗监控 | 每 run ≤ 200K tokens（熔断上限） |
| 预算熔断 | 80% 警告降级，100% 硬熔断 |

**模型分级配置** (`config/models.yaml`)，详见 §6.1 多 Provider 切换机制：

```yaml
# 当前默认配置（可随时在 Settings 页面切换）
defaults:
  active_provider: xiaomi

budget:
  max_tokens_per_run: 200000     # token 上限
  warn_at_percent: 80
  fallback_tier: fast            # 降级到轻量模型
```

**Settings 页面** 暴露配置：
- **Provider 选择**：下拉切换 MiMo / DeepSeek / OpenAI
- **Agent 分配**：每个 Agent 可独立选 provider + 模型档位
- **预算控制**：token 上限、警告阈值

### 5.3 数据安全

- API Key 通过环境变量注入，**绝不入 git**
- 用户上传素材本地存储，不外发
- 内容审核结果留 30 天审计

### 5.4 合规

- 国内平台：接阿里云内容安全 API（敏感词、暴恐、低俗）
- 不做"伪造身份发文"（模仿风格 OK，不署他人名）
- 配图避免肖像权问题（提示词里加 `non-celebrity face`）

### 5.5 可观测

- 所有 Agent 事件写入 `run_events` 表，支持完整回放
- 每次 LLM 调用记录 token 明细到 `token_usage` 表
- 每个 run 记录成本、耗时、状态变更
- **Langfuse** 全链路 LLM 可观测：每次 LLM 调用自动 trace，记录 prompt / completion / token / latency / cost，支持按 agent / run / 日期维度筛选分析

---

## 6. 技术架构

### 6.1 技术栈选型

| 层 | 选型 | 备注 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | async-first |
| Agent 编排 | **LangGraph**（核心） | StateGraph + PostgresSaver checkpoint |
| LLM 抽象 | **OpenAI SDK**（AsyncOpenAI） | 兼容任何 OpenAI 格式 provider |
| 模型切换 | `config/models.yaml` 按 agent 分配 provider + tier | 支持多个 provider 同时配置 |
| 默认模型 | 按 `config/models.yaml` 配置，支持随时切换 | |
| Embedding | BGE-M3（本地，1024 维） | |
| 向量库 | PostgreSQL 16 + pgvector | |
| 队列 | Phase 1: FastAPI BackgroundTasks；Phase 2+: Celery + Redis | 异步生成任务 |
| 对象存储 | MinIO（自建）/ 本地 `data/images/` | 配图 |
| 图像生成 | **硅基流动 FLUX/Kolors**（AI 生图，OpenAI 兼容）+ ECharts SSR（图表）+ Pillow（卡片）+ Playwright（信息图） | 五路径混合方案；备份：火山即梦 / Coze Seedream |
| 图文一致性校验 | Phase 1 LLM 纯文本判断；Phase 2 **GLM-4V** / **Qwen-VL-Max** Vision 校验 | |
| 浏览器抓取 | Crawl4AI | LLM-friendly |
| Web 搜索 | Tavily API | |
| 内容安全 | 自建敏感词库 + 阿里云内容安全（可选） | Phase 1 先用自建 |
| 可观测 | **Langfuse**（LLM trace）+ `run_events` / `token_usage` 表（业务事件） | |
| 前端 | Vite + React 18 + TypeScript + React Router + Tailwind + shadcn/ui | SPA，无 SSR；构建产物挂载到 FastAPI 静态文件 |

**多 Provider 切换机制**：

```python
# config/models.yaml — 支持配置多个 provider，按 agent 分配
providers:
  xiaomi:
    base_url: "https://token-plan-cn.xiaomimimo.com/v1"
    api_key_env: "MIMO_API_KEY"
    models:
      fast: "MiMo-V2.5"
      balanced: "MiMo-V2.5-Pro"

  deepseek:
    base_url: "https://api.deepseek.com/v1"
    api_key_env: "DEEPSEEK_API_KEY"
    models:
      fast: "deepseek-chat"
      balanced: "deepseek-chat"

  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    models:
      fast: "gpt-4o-mini"
      balanced: "gpt-4o"

# 每个 agent 选 provider + tier
agents:
  topic:      { provider: xiaomi, tier: fast }
  researcher: { provider: xiaomi, tier: fast }
  planner:    { provider: xiaomi, tier: balanced }
  editor:     { provider: xiaomi, tier: balanced }
  writer:     { provider: xiaomi, tier: balanced }
  reviewer:   { provider: xiaomi, tier: balanced }
  reviser:    { provider: xiaomi, tier: balanced }
```

切换方式：改 `config/models.yaml` 里的 `provider` 字段即可，Agent 代码不动。

### 6.2 架构图

```
┌──────── Browser (React SPA / Vite) ────────┐
│  Dashboard | NewRun | RunLive | Editor   │
│  StyleManager | Settings                 │
└──────────────────┬──────────────────────┘
                   │ REST + SSE
┌──────────────────▼──────────────────────┐
│       FastAPI Backend                    │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  LangGraph Orchestrator            │ │
│  │  Topic → Planner → Research(N并行) │ │
│  │  → Editor → Writer → Illustrator   │ │
│  │  → Reviewer ↔ Reviser             │ │
│  │                                    │ │
│  │  Checkpoint: PostgresSaver         │ │
│  │  Budget Guard: token 熔断          │ │
│  └────────┬───────────────────────────┘ │
│           │                              │
│  ┌────────▼───────────────────────────┐ │
│  │  Tools Layer (app/tools/)          │ │
│  │  ├─ hotnews.py ← 百度/RSS         │ │
│  │  ├─ style.py ← 风格指纹           │ │
│  │  ├─ web_search (Tavily)            │ │
│  │  ├─ scraper (Crawl4AI)             │ │
│  │  ├─ rag (pgvector)                 │ │
│  │  ├─ image_gen (硅基流动 FLUX/Kolors)│ │
│  │  ├─ chart_gen (ECharts SSR)        │ │
│  │  ├─ card_gen (Pillow)              │ │
│  │  ├─ infographic_gen (Playwright)   │ │
│  │  ├─ image_cache (prompt hash)      │ │
│  │  └─ safety (自建敏感词)             │ │
│  └────────┬───────────────────────────┘ │
│           │                              │
│  ┌────────▼───────────────────────────┐ │
│  │  LLM Layer (OpenAI SDK)           │ │
│  │  可切换: MiMo / DeepSeek / OpenAI │ │
│  │  config/models.yaml 控制分配       │ │
│  │  + Token 计量 + 预算熔断           │ │
│  └────────┬───────────────────────────┘ │
└───────────┼─────────────────────────────┘
            │
   ┌────────┼─────────┬───────────┬──────────┐
   ▼        ▼         ▼           ▼          ▼
PostgreSQL  Redis   Coze API   Skills_Repo  Langfuse
+pgvector                       (集成)     (LLM trace)
```

### 6.3 后端文件结构

```
ai-content-factory/
├── app/
│   ├── main.py                      # FastAPI 入口
│   ├── config.py                    # Pydantic Settings（从 models.yaml + 环境变量读）
│   ├── agents/
│   │   ├── graph.py                 # LangGraph 定义（状态机 + 条件边）
│   │   ├── topic.py                 # TopicAgent 实现
│   │   ├── planner.py               # PlannerAgent
│   │   ├── researcher.py            # ResearcherAgent（含 Send fan-out）
│   │   ├── editor.py                # EditorAgent
│   │   ├── writer.py                # WriterAgent（流式输出）
│   │   ├── illustrator.py           # IllustratorAgent
│   │   ├── reviewer.py              # ReviewerAgent（含 Vision 校验）
│   │   └── reviser.py               # ReviserAgent
│   ├── tools/
│   │   ├── legacy_skills.py         # 包 Skills_Repo（hotnews + style）
│   │   ├── search.py                # Tavily/Bing
│   │   ├── scraper.py               # Crawl4AI
│   │   ├── rag.py                   # pgvector 检索
│   │   ├── safety.py                # 内容审核
│   │   └── image.py                 # 图像生成 + 一致性
│   ├── api/
│   │   ├── runs.py                  # POST /runs, GET /runs/{id}/stream (SSE), PUT /runs/{id}/article（编辑草稿）
│   │   ├── styles.py                # 风格指纹 CRUD
│   │   ├── topics.py                # 选题候选 / 用户偏好
│   │   ├── stats.py                 # Dashboard 统计
│   │   └── settings.py              # 模型/预算配置
│   ├── llm/
│   │   ├── client.py                # LLM 抽象层（OpenAI SDK，多 provider 切换）
│   │   ├── budget.py                # 预算熔断 + 动态降级
│   │   └── prompts/                 # 各 agent 的 system prompt 文件
│   │       ├── topic.txt
│   │       ├── planner.txt
│   │       ├── researcher.txt
│   │       ├── editor.txt
│   │       ├── writer.txt           # 含风格指纹注入点
│   │       ├── reviewer.txt
│   │       └── reviser.txt
│   ├── db/
│   │   ├── schema.sql               # 上面定义的完整 schema
│   │   ├── models.py                # SQLAlchemy ORM
│   │   └── migrations/              # alembic
│   ├── observability/
│   │   ├── langfuse.py              # Langfuse 集成（LLM trace）
│   │   └── metrics.py               # Prometheus 指标（Phase 2）
│   └── workers/
│       └── runner.py                # LangGraph driver（Phase 1 BackgroundTasks / Phase 2+ Celery）
├── config/
│   └── models.yaml                  # 模型分级 + 预算配置
├── frontend/                        # Vite + React 18 + TypeScript
│   ├── src/
│   │   ├── routes/
│   │   │   ├── Dashboard.tsx        # /            选题+运行+KPI
│   │   │   ├── NewRun.tsx           # /runs/new    选题确认+开跑
│   │   │   ├── RunLive.tsx          # /runs/:id    7 节点实时 Timeline
│   │   │   ├── ArticleEditor.tsx    # /runs/:id/edit  富文本+配图
│   │   │   ├── StyleManager.tsx     # /styles      风格 CRUD
│   │   │   └── Settings.tsx         # /settings    配置
│   │   ├── components/
│   │   │   ├── AgentTimeline.tsx     # 7 节点进度 + token 实时显示
│   │   │   ├── DraftEditor.tsx       # TipTap 富文本
│   │   │   ├── ImageGallery.tsx
│   │   │   ├── CostDashboard.tsx     # 成本看板（per-agent 饼图）
│   │   │   └── StyleRadar.tsx        # 风格匹配雷达图
│   │   ├── stores/                   # Zustand 状态管理
│   │   ├── hooks/
│   │   │   └── useSSE.ts            # EventSource 封装 + 断线重连
│   │   └── api/
│   │       └── client.ts            # fetch 封装（类型化）
│   ├── vite.config.ts               # dev proxy /api → localhost:8000
│   └── index.html
├── skills/                          # 原始 Skills（不动，app/tools/ 提取集成）
├── docker-compose.yml               # postgres+pgvector / redis / langfuse
└── pyproject.toml
```

### 6.4 REST API 设计

#### Runs（生成任务）

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/runs` | 创建并启动一次生成 |
| `GET` | `/api/runs` | 列表（`?status=&limit=&offset=`） |
| `GET` | `/api/runs/{id}` | 单条详情（含 cost + usage） |
| `GET` | `/api/runs/{id}/stream` | SSE 实时事件流 |
| `GET` | `/api/runs/{id}/events` | 历史事件（SSE 断了可 catch up） |
| `POST` | `/api/runs/{id}/interrupt` | 人工介入：停在某个 agent |
| `POST` | `/api/runs/{id}/resume` | 修改 state 后继续 |
| `POST` | `/api/runs/{id}/abort` | 中止运行 |
| `PUT` | `/api/runs/{id}/article` | 编辑草稿 |
| `POST` | `/api/runs/{id}/complete` | 标记完成 |

创建请求体：
```json
{
  "user_request": "今天 AI 圈有什么值得写的？写一篇模仿 caoz 风格的公众号文",
  "style_id": "caoz",
  "target_platform": "wechat",
  "config": {
    "research_parallel": 5,
    "max_revise_rounds": 2,
    "max_images": 4,
    "budget_limit_cents": 300,
    "model_mode": "standard"
  }
}
```

SSE 事件格式：
```
event: agent.start
data: {"ts": 0.05, "agent": "topic", "provider": "xiaomi", "model": "MiMo-V2.5"}

event: agent.token
data: {"ts": 0.12, "agent": "topic", "text": "正在分析热榜..."}

event: tool.call
data: {"ts": 0.35, "tool": "fetch_hotnews_unified", "returned": 30}

event: agent.done
data: {"ts": 2.10, "agent": "topic", "tokens_in": 1200, "tokens_out": 350, "cache_read": 800, "cost_cents": 4}

event: researcher.start
data: {"ts": 3.50, "q_idx": 0, "query": "DeepSeek-V3 MMLU 得分", "parallel": 5}

event: writer.token
data: {"ts": 5.80, "text": "这两天科技圈"}

event: image.generated
data: {"ts": 7.20, "para_id": 1, "url": "/data/images/a8c2_1.png"}

event: review.done
data: {"ts": 8.10, "pass": true, "score": 8.4, "issues": 0}

event: graph.done
data: {"ts": 8.37, "status": "done", "words": 1872, "images": 3, "total_tokens": 45000, "cost_cents": 0}
```

#### Topics / Styles / Stats / Settings

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/topics/candidates` | 今日候选选题 |
| `POST` | `/api/topics/refresh` | 强制刷新 |
| `GET` | `/api/styles` | 风格列表 |
| `POST` | `/api/styles/{id}/analyze` | 触发指纹分析 |
| `GET` | `/api/stats/dashboard` | 产出/成本/pass 率 |
| `GET` | `/api/stats/cost` | Per-agent 成本趋势（支持日期范围） |
| `GET` | `/api/settings` | 读取配置 |
| `PUT` | `/api/settings` | 更新配置（含模型分级） |

### 6.5 环境变量

```bash
# ---- LLM（按 config/models.yaml 中的 provider 配置对应的 key）----
MIMO_API_KEY=tp-xxx                   # 小米 MiMo API Key（当前默认）
# 可选：切换 provider 时设置对应 key
# DEEPSEEK_API_KEY=sk-xxx
# OPENAI_API_KEY=sk-xxx

# ---- 图像生成 ----
SILICONFLOW_API_KEY=sk-xxx            # 硅基流动 API Key（FLUX/Kolors 主路径）
# 可选：备份 provider 配置对应 key
# VOLC_AK=xxx                         # 火山引擎即梦 3.0（备 1）
# VOLC_SK=xxx
# COZE_API_KEY=pat-xxx                # Coze Seedream 4.5（备 2）

# ---- 图文一致性校验（Phase 2 升级时用）----
# ZHIPU_API_KEY=xxx                   # GLM-4V Vision 校验
# DASHSCOPE_API_KEY=xxx               # 阿里 Qwen-VL-Max Vision 校验

# ---- Embedding ----
EMBEDDING_MODEL=BGE-M3                # 本地部署 or API

# ---- 数据库 ----
DATABASE_URL=postgresql://user:pass@localhost:5432/acf
REDIS_URL=redis://localhost:6379/0

# ---- 对象存储（可选，默认本地 data/images/）----
# MINIO_ENDPOINT=localhost:9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin

# ---- 可观测 ----
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_HOST=http://localhost:3000
```

---

## 7. Agent Prompt 模板

### 7.1 PlannerAgent System Prompt

```
你是中文图文内容的资深主编。给定一个选题，你需要：

1. 输出文章大纲（3~6 节，每节一句话）
2. 提出 3~7 个能补全这篇文章的"研究子问题"

研究子问题原则（重要）：
- 互不重叠，覆盖背景/数据/案例/反方观点/未来趋势 五个角度
- 每个问题应该能用一次搜索回答
- 用中文，包含具体的关键词、时间范围、限定条件

返回 JSON:
{
  "outline": [{"section": "...", "intent": "..."}],
  "sub_queries": ["...", "..."]
}
```

### 7.2 ResearcherAgent System Prompt

```
你是研究员。基于给定的子问题，你已经拿到 web_search 和 vector_search_history 的结果。

任务：从中筛出 3~5 条"对成稿最有价值"的素材片段（snippet），每条 100~300 字。

输出 JSON 数组，每条：
{
  "source": "url",
  "excerpt": "原文摘录或关键事实",
  "credibility": 0.0-1.0,
  "angle": "背景|数据|案例|观点|趋势"
}

不要编造，不要二次创作。如果素材不够，明确说"insufficient: <reason>"。
```

### 7.3 ReviewerAgent System Prompt

```
你是内容审稿人。你需要从四个维度审查这篇草稿：

1. 事实准确性：草稿中的事实是否有对应 snippet 支撑？是否存在编造？
2. 图文一致性：每张配图是否与对应段落内容匹配？
3. 风格匹配：是否符合目标风格指纹的句法/修辞特征？
4. 平台规范：字数、emoji 用量、tag 数量是否符合 {target_platform} 的要求？

输出 JSON:
{
  "pass": true/false,
  "score": 0.0-10.0,
  "issues": [
    {"type": "factual|image_mismatch|style_drift|platform_violation", "detail": "..."}
  ],
  "summary": "一句话总评"
}

通过阈值：score ≥ 7.5 且无 P0 类型 issue。
```

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| LLM 编造事实 | 高 | 高 | RAG 强制引用 + Reviewer 校验 + 人工抽查 |
| 图文不一致 | 中 | 中 | Vision 模型校验 + max_revise=2 兜底 |
| 风格学习样本不足 | 中 | 中 | 最低 5 篇样本要求 + UI 警告提示 |
| 单次成本失控 | 中 | 高 | 模型分级 + 每 run 预算硬上限熔断 + 动态降级 |
| 跨源信息冲突 | 中 | 中 | Researcher 输出 credibility，Editor 决断 |
| LangGraph 版本变化 | 低 | 中 | 锁版本，Phase 1 不追新 |
| Tavily/外部 API 不稳定 | 中 | 中 | tenacity 重试 + 多 search provider 备用 |
| 中文内容审核误判 | 中 | 中 | 接两家审核（阿里 + 自建敏感词），双 fail 才拦 |
| LLM API 限流/不稳定 | 中 | 中 | tenacity 重试 + config/models.yaml 切换 provider |

---

## 9. 里程碑与验收

### 9.1 实施节奏（详见 `PLAN2.md`）

| Phase | 工期 | 关键交付 | 验收 |
|---|---|---|---|
| **0** 基础设施 | 0.5d | Docker（PG+pgvector+Langfuse）+ 目录骨架 + 依赖 | `psql` pgvector 扩展 OK；`tree app` 骨架齐 |
| **1** DB Schema | 0.5d | 7 表 + Alembic 迁移 | `alembic upgrade head` 成功 |
| **2** LLM 层 | 1d | 多 Provider 路由 + 预算熔断 + Langfuse trace | Langfuse 看到 trace；熔断可触发 |
| **3** 工具层 | 1.5d | 8 个工具（hotnews/rss/style/search/scraper/rag/safety/image） | `pytest tests/tools/` 全绿 |
| **4** LangGraph + 8 Agent | 2d | StateGraph + PostgresSaver checkpoint + 全流程跑通 | `--mock` 通过；真 LLM 出 1500 字图文 |
| **5** API + SSE | 1d | FastAPI 全套路由 + SSE 实时推送 | `curl` SSE 事件流正常 |
| **6** 前端 | 3d | React SPA 6 页面（Vite + React Router） | 浏览器端到端走完 |
| **7** 验收 | 0.5d | PRD §9.2 全部验收标准 | 10d 总计 |

### 9.2 验收标准（Phase 1 出口）

- [ ] 端到端 demo：从用户说一句话 → 8 分钟内拿到完整图文（含 2~3 张配图）
- [ ] 6 个前端页面可用
- [ ] 单篇成本：Token Plan 内趋近 ¥0；付费 provider ≤ ¥3
- [ ] 风格盲测识别率 < 70%
- [ ] 连续 50 次 run 成功率 ≥ 95%
- [ ] run_events 能回放任意一次 run（含 per-agent token 明细）
- [ ] Langfuse 能看到每次 LLM 调用的 trace（prompt / completion / token / latency）
- [ ] 预算熔断功能验证：设置 token 限额 → run 在 80% 时降级，100% 时熔断
- [ ] 文档齐全：API 文档（OpenAPI 自动生成）+ 部署文档

### 9.3 依赖安装

```bash
pip install langgraph psycopg[binary] \
    fastapi uvicorn openai \
    langfuse \
    tavily-python crawl4ai httpx \
    pyecharts pillow playwright \
    boto3 redis celery
playwright install chromium  # 用于 ECharts SSR + 信息图截图
```

---

## 10. 附录

### 10.1 术语表

| 术语 | 含义 |
|---|---|
| **Run** | 一次完整的"输入 → 草稿"端到端流程 |
| **Snippet** | Researcher 抓回的素材片段（带来源、可信度） |
| **Style Fingerprint** | 风格指纹，由 style_fingerprint skill 生成的 JSON |
| **Outline** | 文章大纲，section 数组 |
| **Image Prompt** | 写手在草稿里留下的 `[IMG: ...]` 占位符 |
| **Review** | Reviewer 输出的 {pass, score, issues} 对象 |
| **Budget Guard** | 预算熔断机制，per-run token 上限 + 动态降级到轻量模型 |
| **Provider** | LLM 服务商（MiMo / DeepSeek / OpenAI 等），通过 config/models.yaml 切换 |

### 10.2 数据契约示例

详见 `app/agents/graph.py` 中 `ContentState` TypedDict。

### 10.3 失败恢复策略表

| 失败点 | 自动恢复 | 人工介入 |
|---|---|---|
| Topic 失败 | 重试 1 次（换温度） | 让用户手填 |
| Researcher 单 worker 失败 | 跳过，其他继续 | 不必 |
| Researcher 全部失败 | 退化到只用历史素材 | 警告 |
| Image 生成失败 | 重试 2 次（换 provider） | 让用户上传 |
| Reviewer pass=false | Reviser 修订 ≤2 次 | 超出转 needs_human |
| 整体超时（> 15min 硬上限，§5.1） | abort + 保存中间产物 | 弹"重新开始 vs 部分保留" |
| 预算超限 | 80% 降级模型，100% 熔断 | 弹"追加预算 vs 保留当前产出" |

### 10.4 与 GPT-Researcher 的关键差异

| 维度 | GPT-Researcher | ACF |
|---|---|---|
| 输出 | 英文研究报告 | 中文图文（含配图） |
| 信源 | Web search | Web search + **国内热榜聚合** |
| 风格 | 客观研报 | **可模仿任意人**（style_fingerprint） |
| 终态 | Markdown 报告 | 草稿 + 配图 + 平台规范 +（Phase 2 直发） |
| 审阅 | Reviewer + Reviser | **文本层面图文一致性校验** |
| 成本控制 | 无 | **多 Provider 切换 + Token 监控 + 预算熔断** |
| 可观测 | 基础日志 | **run_events 全链路回放 + token_usage 明细** |

### 10.5 后续 Phase 预告

- **Phase 2**：发布矩阵（公众号 API + 小红书/抖音浏览器自动化）+ 定时排期；知乎/头条/抖音采集改写为纯 Python；Vision 模型做图文校验
- **Phase 3**：数据回流（阅读量、点赞）+ 自动 prompt 调优 + LoRA 微调
- **Phase 4**：多账号矩阵 + 团队协作 + 移动端
