import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import { Pause, Square, RotateCcw, CheckCircle2, Loader2, Circle, AlertCircle, Wand2, Search, FileEdit, PenTool, Image as ImageIcon, ShieldCheck, GitBranch } from "lucide-react";
import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { abortRun, getRun, getRunEvents, getSettings, interruptRun, resumeRun } from "../../lib/api";
import { useSSE } from "../../lib/useSSE";

const agentDefs = [
  { key: "topic", name: "TopicAgent", icon: Wand2, model: "DeepSeek V4 Flash" },
  { key: "planner", name: "PlannerAgent", icon: GitBranch, model: "DeepSeek V4 Pro" },
  { key: "researcher", name: "Researcher", icon: Search, model: "DeepSeek V4 Flash" },
  { key: "editor", name: "EditorAgent", icon: FileEdit, model: "DeepSeek V4 Pro" },
  { key: "writer", name: "WriterAgent", icon: PenTool, model: "DeepSeek V4 Pro" },
  { key: "illustrator", name: "IllustratorAgent", icon: ImageIcon, model: "FLUX/Kolors" },
  { key: "reviewer", name: "ReviewerAgent", icon: ShieldCheck, model: "DeepSeek V4 Pro" },
];

const costColors = ["#a78bfa", "#8b5cf6", "#7c3aed", "#6366f1", "#4f46e5", "#0ea5e9", "#10b981"];

const statusIcon = (s: string) => {
  if (s === "done") return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
  if (s === "running") return <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />;
  if (s === "error") return <AlertCircle className="w-4 h-4 text-rose-500" />;
  if (s === "aborted") return <Square className="w-4 h-4 text-zinc-500" />;
  return <Circle className="w-4 h-4 text-muted-foreground/40" />;
};

const runStatus: Record<string, { text: string; cls: string }> = {
  done: { text: "已完成", cls: "bg-emerald-500/15 text-emerald-600 border-emerald-500/20" },
  failed: { text: "失败", cls: "bg-rose-500/15 text-rose-600 border-rose-500/20" },
  aborted: { text: "已中止", cls: "bg-zinc-500/15 text-zinc-600 border-zinc-500/20" },
  paused: { text: "已暂停", cls: "bg-sky-500/15 text-sky-600 border-sky-500/20" },
  drafting: { text: "生成中", cls: "bg-violet-500/15 text-violet-600 border-violet-500/20" },
};

export function RunLive({ runId, initialRun, onDone }: { runId: string | null; initialRun?: any; onDone: () => void }) {
  const { events, connected } = useSSE(runId);
  const [historyEvents, setHistoryEvents] = useState<any[]>([]);
  const [run, setRun] = useState<any>(initialRun || null);
  const [emptyEventTimedOut, setEmptyEventTimedOut] = useState(false);
  const [selectedEventIndex, setSelectedEventIndex] = useState<number | null>(null);
  const [settings, setSettings] = useState<any>(null);
  const writerScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!runId) return;
    setRun(initialRun || null);
    setHistoryEvents([]);
    setEmptyEventTimedOut(false);
    setSelectedEventIndex(null);
    const load = () => getRun(runId).then(setRun).catch(() => undefined);
    const loadEvents = () => getRunEvents(runId).then((res) => setHistoryEvents(res.events || [])).catch(() => undefined);
    load();
    loadEvents();
    const timer = window.setInterval(() => {
      load();
      loadEvents();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [runId, initialRun]);

  const allEvents = useMemo(() => mergeEvents(historyEvents, events), [historyEvents, events]);
  const businessEvents = useMemo(() => allEvents.filter((e) => e.event !== "heartbeat" && e.event !== "message"), [allEvents]);
  const selectedEvent = selectedEventIndex === null ? null : allEvents[selectedEventIndex];

  const agents = useMemo(() => {
    const status: Record<string, string> = {};
    for (const event of allEvents) {
      const rawAgent = event.data?.agent;
      const agent = rawAgent === "researcher_worker" ? "researcher" : rawAgent;
      if (!agent) continue;
      if (event.event === "agent.start") status[agent] = "running";
      if (event.event === "agent.done") status[agent] = "done";
      if (event.event === "graph.error") status[agent] = "error";
    }
    if (run?.status === "done") {
      for (const def of agentDefs) status[def.key] = "done";
    }
    if (run?.status === "aborted" || (run?.status === "failed" && isAbortError(run?.error))) {
      for (const key of Object.keys(status)) {
        if (status[key] === "running") status[key] = "aborted";
      }
    }
    return agentDefs.map((def) => ({
      ...def,
      model: displayModelForAgent(def.key, def.model, settings),
      status: status[def.key] || "pending",
    }));
  }, [allEvents, run, settings]);

  const doneCount = agents.filter((a) => a.status === "done").length;
  const streamedDraft = useMemo(
    () => allEvents.filter((e) => e.event === "writer.token").map((e) => e.data?.delta || e.data?.text || "").join(""),
    [allEvents]
  );
  const draft = streamedDraft || run?.draft_md || "";
  const graphError = run?.error || [...allEvents].reverse().find((e) => e.event === "graph.error")?.data?.error;
  const normalizedStatus = normalizeRunStatus(run?.status, graphError);
  const currentRunStatus = runStatus[normalizedStatus || "drafting"] ?? runStatus.drafting;
  const isTerminal = run?.status === "done" || run?.status === "failed" || run?.status === "aborted" || run?.status === "paused";
  const startupWarning = emptyEventTimedOut && !businessEvents.length && !draft && !isTerminal;
  const eventUsage = useMemo(() => sumUsageFromEvents(allEvents), [allEvents]);
  const liveTotalTokens = Math.max(run?.total_tokens || 0, eventUsage.totalTokens);
  const liveCostCents = Math.max(run?.cost_cents || 0, eventUsage.costCents);
  const usageByAgent = run?.usage_by_agent || {};
  const costData = agentDefs.map((a, i) => ({
    name: a.name.replace("Agent", ""),
    value: (usageByAgent[a.key]?.cost_cents || 0) / 100,
    color: costColors[i],
  }));

  async function handleAbort() {
    if (runId) {
      const result = await abortRun(runId);
      setRun((prev: any) => ({
        ...(prev || {}),
        ...result,
        run_id: runId,
        status: "aborted",
        error: prev?.error || "aborted by user",
        ended_at: new Date().toISOString(),
      }));
      getRun(runId).then(setRun).catch(() => undefined);
    }
  }

  useEffect(() => {
    getSettings().then(setSettings).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!runId) return;
    const timer = window.setTimeout(() => setEmptyEventTimedOut(true), 8000);
    return () => window.clearTimeout(timer);
  }, [runId]);

  useEffect(() => {
    const el = writerScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [draft]);

  if (!runId) {
    return <div className="p-8 text-muted-foreground">还没有活动运行。请先创建一个生成任务。</div>;
  }

  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1>Run #{runId.slice(0, 8)}</h1>
            <Badge className={currentRunStatus.cls}>{currentRunStatus.text}</Badge>
            <Badge variant="outline">{connected ? "SSE 已连接" : "SSE 连接中"}</Badge>
          </div>
          <p className="text-muted-foreground text-sm mt-1">{run?.user_request || "生成任务初始化中"} · {run?.target_platform || "wechat"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => interruptRun(runId)}><Pause className="w-4 h-4 mr-2" />暂停</Button>
          <Button variant="outline" size="sm" onClick={() => resumeRun(runId)}><RotateCcw className="w-4 h-4 mr-2" />继续</Button>
          <Button variant="outline" size="sm" onClick={handleAbort}><Square className="w-4 h-4 mr-2" />中止</Button>
          <Button size="sm" onClick={onDone}>打开编辑器</Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPI label="进度" value={`${doneCount} / ${agents.length}`} sub={agents.find((a) => a.status === "running")?.name || "等待事件"} />
        <KPI label="事件数" value={String(allEvents.length)} sub="历史 + 实时 SSE" />
        <KPI label="累计 token" value={liveTotalTokens.toLocaleString()} sub={eventUsage.totalTokens ? "事件实时汇总" : `预算 ${formatTokenBudget(settings)}`} />
        <KPI label="累计成本" value={`¥${(liveCostCents / 100).toFixed(2)}`} sub={eventUsage.costCents ? "事件实时汇总" : run?.cost_cents ? "后端累计" : "等待用量"} />
      </div>

      {graphError && (
        <Card className={isAbortError(graphError) ? "border-zinc-500/30 bg-zinc-500/10" : "border-rose-500/30 bg-rose-500/10"}>
          <CardContent className="p-4">
            <div className={`flex items-start gap-3 ${isAbortError(graphError) ? "text-zinc-600 dark:text-zinc-300" : "text-rose-600"}`}>
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="min-w-0">
                <div className="font-medium">{isAbortError(graphError) ? "任务已中止" : "生成任务失败"}</div>
                <div className="mt-1 break-words text-xs opacity-90">{graphError}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {startupWarning && (
        <Card className="border-amber-500/30 bg-amber-500/10">
          <CardContent className="p-4">
            <div className="flex items-start gap-3 text-amber-700 dark:text-amber-400">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="min-w-0">
                <div className="font-medium">任务暂时没有业务事件</div>
                <div className="mt-1 break-words text-xs opacity-90">任务未成功启动或后端事件流未写入，请检查后端连接和 worker 日志。</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
                      <span className="text-xs text-muted-foreground">{a.status === "pending" ? a.model : a.status}</span>
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
            <Badge variant="outline">
              {writerBadge(normalizedStatus)}
            </Badge>
          </CardHeader>
          <CardContent>
            <div ref={writerScrollRef} className="h-72 overflow-y-auto rounded-md bg-muted/40 p-4 font-mono text-sm leading-relaxed">
              <div className="whitespace-pre-wrap">{draft || "等待 WriterAgent 输出..."}</div>
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>预计 1900 字</span><span>已生成 ~ {draft.length} 字符</span>
              </div>
              <Progress value={Math.min(100, Math.round((draft.length / 1900) * 100))} />
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
                  <span className="tabular-nums text-muted-foreground">¥{c.value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>事件流</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            <ScrollArea className="col-span-3 h-72 rounded-md border bg-muted/20">
              <div className="space-y-1 p-2 font-mono text-xs">
                {allEvents.map((e, i) => {
                  const selected = selectedEventIndex === i;
                  return (
                    <button
                      key={`${e.id ?? "live"}-${i}`}
                      type="button"
                      onClick={() => setSelectedEventIndex(i)}
                      className={`flex w-full items-start gap-3 rounded border-l-2 py-1.5 pl-3 pr-2 text-left transition ${
                        selected
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-border hover:border-violet-500 hover:bg-accent/40"
                      }`}
                    >
                      <span className="text-muted-foreground tabular-nums w-14 shrink-0">#{i + 1}</span>
                      <Badge variant="outline" className="text-[10px] py-0 px-1.5 shrink-0">{e.event}</Badge>
                      <span className="text-muted-foreground shrink-0">[{e.data?.agent || e.data?.run_id || "-"}]</span>
                      <span className="min-w-0 flex-1 truncate">{eventSummary(e)}</span>
                    </button>
                  );
                })}
                {!businessEvents.length && <div className="p-3 text-muted-foreground">等待事件...</div>}
              </div>
            </ScrollArea>

            <div className="col-span-2 rounded-md border bg-muted/20">
              {selectedEvent ? (
                <div className="flex h-72 flex-col">
                  <div className="border-b p-3">
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="outline">{selectedEvent.event}</Badge>
                      <span className="font-mono text-xs text-muted-foreground">#{(selectedEventIndex ?? 0) + 1}</span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                      <div>ID: {selectedEvent.id ?? "live"}</div>
                      <div>offset: {selectedEvent.ts_offset ?? "-"}</div>
                      <div className="col-span-2 truncate">agent: {selectedEvent.data?.agent || "-"}</div>
                    </div>
                  </div>
                  <ScrollArea className="min-h-0 flex-1">
                    <pre className="whitespace-pre-wrap break-words p-3 font-mono text-xs leading-relaxed">
                      {JSON.stringify(selectedEvent.data ?? selectedEvent, null, 2)}
                    </pre>
                  </ScrollArea>
                </div>
              ) : (
                <div className="flex h-72 items-center justify-center p-4 text-center text-sm text-muted-foreground">
                  点击左侧事件查看完整数据。
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function writerBadge(status?: string) {
  if (status === "done") return "done";
  if (status === "failed") return "failed";
  if (status === "aborted") return "aborted";
  if (status === "paused") return "paused";
  return <><Loader2 className="w-3 h-3 mr-1 animate-spin" />streaming</>;
}

function isAbortError(error?: string) {
  return String(error || "").toLowerCase().includes("aborted by user");
}

function normalizeRunStatus(status?: string, error?: string) {
  if (status === "failed" && isAbortError(error)) return "aborted";
  return status;
}

function displayModelForAgent(agentKey: string, fallback: string, settings: any) {
  if (agentKey === "illustrator") return "Kolors / FLUX fallback";
  const cfg = settings?.agents?.[agentKey];
  const model = cfg ? settings?.providers?.[cfg.provider]?.models?.[cfg.tier] : null;
  return model || fallback;
}

function formatTokenBudget(settings: any) {
  const maxTokens = Number(settings?.budget?.max_tokens_per_run || 200000);
  if (maxTokens >= 1000) return `${Math.round(maxTokens / 1000)}K`;
  return String(maxTokens);
}

function eventSummary(event: any) {
  const data = event.data || {};
  if (event.event === "writer.token" || event.event === "agent.token") {
    return String(data.delta || data.text || "").replace(/\s+/g, " ").slice(0, 160);
  }
  if (event.event === "agent.done" && data.topic) return String(data.topic);
  if (event.event === "graph.error") return String(data.error || "graph.error");
  if (event.event === "tool.call") return `${data.tool || "tool"} ${data.query || data.url || ""}`;
  return JSON.stringify(data);
}

function mergeEvents(historyEvents: any[], liveEvents: any[]) {
  const merged: any[] = [];
  const seen = new Set<string>();

  for (const event of [...historyEvents, ...liveEvents]) {
    const key = event.id ? `${event.event}:${event.id}` : "";
    if (key) {
      if (seen.has(key)) continue;
      seen.add(key);
    }
    merged.push(event);
  }

  return merged;
}

function sumUsageFromEvents(events: any[]) {
  return events.reduce((acc, event) => {
    const usage = event.data?.usage;
    if (!usage) return acc;
    const totalTokens = Number(usage.total_tokens ?? ((usage.input_tokens || 0) + (usage.output_tokens || 0))) || 0;
    const costCents = Number(usage.cost_cents || 0) || 0;
    return {
      totalTokens: acc.totalTokens + totalTokens,
      costCents: acc.costCents + costCents,
    };
  }, { totalTokens: 0, costCents: 0 });
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
