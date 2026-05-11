import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import { Pause, Square, RotateCcw, CheckCircle2, Loader2, Circle, AlertCircle, Wand2, Search, FileEdit, PenTool, Image as ImageIcon, ShieldCheck, GitBranch } from "lucide-react";
import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip } from "recharts";

const agents = [
  { key: "topic", name: "TopicAgent", icon: Wand2, status: "done", tokens: 1450, ms: 1820, model: "MiMo-V2.5" },
  { key: "planner", name: "PlannerAgent", icon: GitBranch, status: "done", tokens: 2100, ms: 2940, model: "MiMo-V2.5-Pro" },
  { key: "researcher", name: "Researcher × 5", icon: Search, status: "done", tokens: 12800, ms: 18200, model: "MiMo-V2.5" },
  { key: "editor", name: "EditorAgent", icon: FileEdit, status: "done", tokens: 4200, ms: 5600, model: "MiMo-V2.5-Pro" },
  { key: "writer", name: "WriterAgent", icon: PenTool, status: "running", tokens: 8740, ms: 12300, model: "MiMo-V2.5-Pro" },
  { key: "illustrator", name: "IllustratorAgent", icon: ImageIcon, status: "pending", tokens: 0, ms: 0, model: "Coze Seedream" },
  { key: "reviewer", name: "ReviewerAgent", icon: ShieldCheck, status: "pending", tokens: 0, ms: 0, model: "MiMo-V2.5-Pro" },
];

const events = [
  { ts: "0:00.05", type: "agent.start", agent: "topic", text: "选题：今日 AI 热榜采集中" },
  { ts: "0:01.82", type: "agent.done", agent: "topic", text: "选定: DeepSeek-V3 发布 — 技术拐点 + 商业影响" },
  { ts: "0:01.92", type: "agent.start", agent: "planner", text: "规划大纲与子查询" },
  { ts: "0:04.86", type: "agent.done", agent: "planner", text: "5 节大纲 + 5 个研究子问题" },
  { ts: "0:04.92", type: "researcher.fanout", agent: "researcher", text: "fan-out 5 worker 并行" },
  { ts: "0:08.40", type: "tool.call", agent: "researcher", text: "web_search('DeepSeek-V3 MMLU 得分') → 5 条" },
  { ts: "0:11.80", type: "tool.call", agent: "researcher", text: "scrape_url(jiqizhixin.com/articles/...)" },
  { ts: "0:23.10", type: "agent.done", agent: "researcher", text: "汇总 17 条 snippets，平均可信度 0.81" },
  { ts: "0:23.18", type: "agent.start", agent: "editor", text: "合并素材 + 加载 caoz 风格指纹" },
  { ts: "0:28.78", type: "agent.done", agent: "editor", text: "最终大纲 6 节，target_words 总计 1900" },
  { ts: "0:28.85", type: "agent.start", agent: "writer", text: "开始撰写，流式输出..." },
  { ts: "0:34.20", type: "agent.token", agent: "writer", text: "这两天科技圈有件事，值得每个还在硅谷..." },
  { ts: "0:38.15", type: "agent.token", agent: "writer", text: "第二节·性能数据对比 [IMG: ... | chart] 写入" },
];

const costData = [
  { name: "Topic", value: 0.08, color: "#a78bfa" },
  { name: "Planner", value: 0.21, color: "#8b5cf6" },
  { name: "Researcher", value: 0.45, color: "#7c3aed" },
  { name: "Editor", value: 0.32, color: "#6366f1" },
  { name: "Writer", value: 0.78, color: "#4f46e5" },
];

const statusIcon = (s: string) => {
  if (s === "done") return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
  if (s === "running") return <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />;
  if (s === "error") return <AlertCircle className="w-4 h-4 text-rose-500" />;
  return <Circle className="w-4 h-4 text-muted-foreground/40" />;
};

export function RunLive({ onDone }: { onDone: () => void }) {
  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1>Run #a8c2f1</h1>
            <Badge className="bg-violet-500/15 text-violet-600 border-violet-500/20">运行中</Badge>
          </div>
          <p className="text-muted-foreground text-sm mt-1">DeepSeek-V3 发布带来的国产大模型竞争格局变化 · caoz · 公众号</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Pause className="w-4 h-4 mr-2" />暂停</Button>
          <Button variant="outline" size="sm"><RotateCcw className="w-4 h-4 mr-2" />重试</Button>
          <Button variant="outline" size="sm" onClick={onDone}><Square className="w-4 h-4 mr-2" />中止</Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPI label="进度" value="5 / 7" sub="WriterAgent 进行中" />
        <KPI label="已用时" value="00:38" sub="预计还需 2:30" />
        <KPI label="累计 token" value="29,290" sub="预算 200K · 14.6%" />
        <KPI label="累计成本" value="¥0.00" sub="Token Plan 内" />
      </div>

      <Card>
        <CardHeader><CardTitle>Agent Pipeline</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {agents.map((a, i) => {
              const Icon = a.icon;
              const isLast = i === agents.length - 1;
              return (
                <div key={a.key} className="flex items-center shrink-0">
                  <div className={`flex flex-col items-center gap-2 p-3 rounded-lg border min-w-[140px] ${a.status === "running" ? "border-violet-500 bg-violet-500/5" : a.status === "done" ? "border-emerald-500/30 bg-emerald-500/5" : "border-dashed"}`}>
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4" />
                      <span className="text-sm">{a.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {statusIcon(a.status)}
                      <span className="text-xs text-muted-foreground">
                        {a.status === "done" ? `${(a.ms / 1000).toFixed(1)}s · ${a.tokens.toLocaleString()} tok` : a.status === "running" ? "进行中..." : "等待"}
                      </span>
                    </div>
                  </div>
                  {!isLast && <div className={`h-0.5 w-4 ${a.status === "done" ? "bg-emerald-500/40" : "bg-border"}`} />}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        <Card className="col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>WriterAgent · 流式输出</CardTitle>
            <Badge variant="outline"><Loader2 className="w-3 h-3 mr-1 animate-spin" />streaming</Badge>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-72 rounded-md bg-muted/40 p-4 font-mono text-sm leading-relaxed">
              <div className="whitespace-pre-wrap">
{`# DeepSeek-V3 发布：六百万美元，把硅谷震了

## 一、技术拐点已至

这两天科技圈有件事，值得每个还在硅谷做 PPT 融资的人警醒。

DeepSeek 把 V3 模型扔出来了。MMLU 88.5，HumanEval 82.6，
价格还是同档位的几分之一。

[IMG: DeepSeek-V3 与 GPT-4o/Claude Sonnet 在 MMLU 上的得分对比柱状图 | 16:9 | chart]

## 二、训练成本到底多离谱

六百万美元。这个数字传出来的时候，硅谷不少 lab 的负责人坐不住了。
GPT-4 时代说要 1 亿美金起跳，到现在不到两年——

[正在生成▎`}
              </div>
            </ScrollArea>
            <div className="mt-3">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>预计 1900 字</span><span>已生成 ~ 620 字</span>
              </div>
              <Progress value={33} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Per-Agent 成本</CardTitle></CardHeader>
          <CardContent>
            <div style={{ width: "100%", height: 176 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={costData} dataKey="value" innerRadius={40} outerRadius={70} paddingAngle={2}>
                    {costData.map((c) => <Cell key={`cell-${c.name}`} fill={c.color} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1.5 mt-2 text-sm">
              {costData.map((c) => (
                <div key={c.name} className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                  <span className="flex-1">{c.name}</span>
                  <span className="tabular-nums text-muted-foreground">¢{c.value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>事件流</CardTitle></CardHeader>
        <CardContent>
          <ScrollArea className="h-56">
            <div className="space-y-1 font-mono text-xs">
              {events.map((e, i) => (
                <div key={i} className="flex items-start gap-3 py-1 border-l-2 pl-3 border-border hover:border-violet-500 hover:bg-accent/40 -ml-px">
                  <span className="text-muted-foreground tabular-nums w-16 shrink-0">{e.ts}</span>
                  <Badge variant="outline" className="text-[10px] py-0 px-1.5 shrink-0">{e.type}</Badge>
                  <span className="text-muted-foreground shrink-0">[{e.agent}]</span>
                  <span className="flex-1">{e.text}</span>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

function KPI({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card><CardContent className="p-5">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl mt-1 tabular-nums">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{sub}</div>
    </CardContent></Card>
  );
}
