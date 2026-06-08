import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { TrendingUp, FileText, CheckCircle2, Coins, ArrowRight, Flame, RefreshCw, Inbox, Clock3 } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { getCandidates, getDashboard, listRuns, refreshCandidates } from "../../lib/api";

type Candidate = {
  title: string;
  angle?: string;
  platform?: string;
  target_platform?: string;
  source?: string;
  category?: string;
  quality?: number;
  estimated_quality?: number;
  hot?: number;
  hot_score?: number;
};

type RunRow = {
  id?: string;
  run_id?: string;
  user_request?: string;
  status?: string;
  current_agent?: string;
  total_tokens?: number;
  cost_cents?: number;
  words?: number;
  created_at?: string;
  review?: { score?: number };
};

const IN_PROGRESS_STATUSES = new Set(["drafting", "reviewing", "queued", "paused"]);

// 判断一条 run 应跳到「实时运行」还是「文章编辑器」
function isRunInProgress(r: Pick<RunRow, "status" | "words">) {
  return IN_PROGRESS_STATUSES.has(r.status || "") && !(r.words && r.words > 0);
}

const statusBadge = (s = "drafting") => {
  const m: Record<string, { text: string; cls: string }> = {
    done: { text: "已完成", cls: "bg-emerald-500/15 text-emerald-600 border-emerald-500/20" },
    reviewing: { text: "审阅中", cls: "bg-amber-500/15 text-amber-600 border-amber-500/20" },
    needs_human: { text: "需人工", cls: "bg-rose-500/15 text-rose-600 border-rose-500/20" },
    failed: { text: "失败", cls: "bg-rose-500/15 text-rose-600 border-rose-500/20" },
    aborted: { text: "已中止", cls: "bg-zinc-500/15 text-zinc-600 border-zinc-500/20" },
    paused: { text: "已暂停", cls: "bg-sky-500/15 text-sky-600 border-sky-500/20" },
    drafting: { text: "生成中", cls: "bg-violet-500/15 text-violet-600 border-violet-500/20" },
  };
  return m[s] ?? { text: "未知", cls: "bg-muted text-muted-foreground border-border" };
};

const dayNames = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

function localDateKey(value?: string | Date) {
  const d = value ? new Date(value) : new Date();
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatDateTime(value?: string) {
  if (!value) return "刚刚";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function formatSourceCounts(counts: Record<string, number>) {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(([source, count]) => `${source} ${count}`)
    .join(" / ");
}

export function Dashboard({
  onStartRun,
  onOpenArticle,
}: {
  onStartRun: (title?: string) => void;
  onOpenArticle: (runId?: string, status?: string, words?: number) => void;
}) {
  const [stats, setStats] = useState<any>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [recent, setRecent] = useState<RunRow[]>([]);
  const [hotMeta, setHotMeta] = useState<any>(null);
  const [hotError, setHotError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hotLoading, setHotLoading] = useState(false);
  const [draftBoxOpen, setDraftBoxOpen] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [statsRes, candidatesRes, runsRes] = await Promise.all([
        getDashboard(),
        getCandidates(),
        listRuns(undefined, 10),
      ]);
      setStats(statsRes);
      setCandidates(candidatesRes.candidates || []);
      setHotMeta(candidatesRes);
      setHotError(candidatesRes.error || null);
      setRecent(runsRes.runs || []);
    } finally {
      setLoading(false);
    }
  }

  async function refreshHotTopics() {
    setHotLoading(true);
    setHotError(null);
    try {
      const res = await refreshCandidates();
      if (!res.candidates?.length) {
        const fallback = await getCandidates();
        setCandidates(fallback.candidates || []);
        setHotMeta(fallback);
        setHotError(fallback.error || "没有获取到新的热榜数据");
      } else {
        setCandidates(res.candidates);
        setHotMeta(res);
        setHotError(res.error || null);
      }
    } catch (err) {
      setHotError(err instanceof Error ? err.message : "刷新热榜失败");
    } finally {
      setHotLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const kpis = useMemo(() => [
    { label: "今日草稿", value: String(stats?.today_runs ?? 0), delta: draftBoxOpen ? "已展开" : "点击查看", icon: FileText, color: "text-violet-500", action: "drafts" },
    { label: "完成数", value: String(stats?.completed_runs ?? 0), delta: "累计完成", icon: CheckCircle2, color: "text-emerald-500" },
    { label: "总成本", value: `¥${((stats?.total_cost_cents ?? 0) / 100).toFixed(2)}`, delta: "后端累计", icon: Coins, color: "text-amber-500" },
    { label: "完成率", value: `${Math.round((stats?.pass_rate ?? 0) * 100)}%`, delta: "完成 / 总数", icon: TrendingUp, color: "text-sky-500" },
  ], [stats, draftBoxOpen]);

  const todayDrafts = useMemo(() => {
    const today = localDateKey();
    return recent.filter((r) => {
      const isToday = r.created_at ? localDateKey(r.created_at) === today : true;
      const isDraft = r.status !== "published";
      return isToday && isDraft;
    });
  }, [recent]);

  const weekChartData = useMemo(() => {
    const byDay = dayNames.map((day) => ({ day, drafts: 0 }));
    for (const run of recent) {
      if (!run.created_at) continue;
      const d = new Date(run.created_at);
      if (Number.isNaN(d.getTime())) continue;
      byDay[(d.getDay() + 6) % 7].drafts += 1;
    }
    return byDay;
  }, [recent]);

  const todayLabel = useMemo(() => new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date()), []);

  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">{todayLabel} · 内容主理人视角 · 北极星目标 ≥ 8 篇/日</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />刷新
          </Button>
          <Button onClick={() => onStartRun()}>
            <PlayIconCustom /> 开始新一轮生成
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => {
          const Icon = k.icon;
          const isDraftCard = k.action === "drafts";
          return (
            <Card
              key={k.label}
              role={isDraftCard ? "button" : undefined}
              tabIndex={isDraftCard ? 0 : undefined}
              onClick={isDraftCard ? () => setDraftBoxOpen((open) => !open) : undefined}
              onKeyDown={isDraftCard ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setDraftBoxOpen((open) => !open);
                }
              } : undefined}
              className={isDraftCard ? "cursor-pointer transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" : undefined}
            >
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{k.label}</span>
                  <Icon className={`w-4 h-4 ${k.color}`} />
                </div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-2xl">{k.value}</span>
                  <span className="text-xs text-muted-foreground">{k.delta}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {draftBoxOpen && (
        <Card className="border-violet-500/25 bg-violet-500/[0.03]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Inbox className="w-4 h-4 text-violet-500" />今日草稿箱
            </CardTitle>
            <Badge variant="outline">{todayDrafts.length} 篇</Badge>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {todayDrafts.map((r, i) => {
                const b = statusBadge(r.status);
                const runId = r.id || r.run_id;
                const inProgress = isRunInProgress(r);
                const words = r.words || 0;
                return (
                  <div
                    key={runId || i}
                    className="flex items-center gap-4 py-3 cursor-pointer hover:bg-accent/50 -mx-2 px-2 rounded"
                    onClick={() => onOpenArticle(runId, r.status, r.words)}
                  >
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-background border">
                      <FileText className="w-4 h-4 text-violet-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{r.user_request || runId || "未命名草稿"}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-2">
                        <Clock3 className="w-3 h-3" />
                        <span>{formatDateTime(r.created_at)}</span>
                        <span>·</span>
                        <span>{inProgress ? "生成中…" : words > 0 ? `约 ${words} 字` : "暂无正文"}</span>
                      </div>
                    </div>
                    <div className="text-sm tabular-nums">评分 {r.review?.score ?? "-"}</div>
                    <Badge variant="outline" className={b.cls}>{b.text}</Badge>
                    <Button size="sm" variant="ghost">
                      {inProgress ? "查看进度" : "打开"} <ArrowRight className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                );
              })}
              {!todayDrafts.length && (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  今日还没有草稿，创建一条 run 后会出现在这里。
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-3 gap-4">
        <Card className="col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2"><Flame className="w-4 h-4 text-orange-500" />今日候选选题</CardTitle>
              <div className="mt-1 text-xs text-muted-foreground">
                {hotMeta?.fetched_at ? `第 ${hotMeta.refresh_id || 1} 批 · ${formatDateTime(hotMeta.fetched_at)} · 共 ${hotMeta.count || candidates.length} 条` : "等待热榜数据"}
                {hotMeta?.source_counts ? ` · ${formatSourceCounts(hotMeta.source_counts)}` : ""}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hotMeta?.refreshed && (
                <Badge variant="outline" className={hotMeta.changed === false ? "text-amber-600 border-amber-500/30" : "text-emerald-600 border-emerald-500/30"}>
                  {hotMeta.changed === false ? "源未变化" : "已刷新"}
                </Badge>
              )}
              <Button variant="ghost" size="sm" onClick={refreshHotTopics} disabled={hotLoading}>
                <RefreshCw className={`w-3 h-3 mr-1 ${hotLoading ? "animate-spin" : ""}`} />刷新热榜
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {hotError && (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
                {hotError}
              </div>
            )}
            {candidates.slice(0, 5).map((c, i) => {
              const platform = c.platform || c.target_platform || "wechat";
              const quality = c.quality ?? c.estimated_quality ?? 0.75;
              const hot = c.hot ?? c.hot_score ?? 0;
              const source = c.source || "hot";
              return (
                <div key={`${c.title}-${i}`} className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors group cursor-pointer" onClick={() => onStartRun(c.title)}>
                  <div className="w-8 text-center text-muted-foreground text-sm">#{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{c.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-2">
                      <span>{c.angle || "热点解读 + 运营视角"}</span>
                      <span>·</span>
                      <span>热度 {hot.toLocaleString()}</span>
                    </div>
                  </div>
                  <Badge variant="secondary" className="capitalize">{source}</Badge>
                  <Badge variant="outline" className="capitalize">{platform}</Badge>
                  <div className="text-sm tabular-nums w-12 text-right text-emerald-600">{(quality * 100).toFixed(0)}</div>
                  <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onStartRun(c.title); }}>
                    开跑 <ArrowRight className="w-3 h-3 ml-1" />
                  </Button>
                </div>
              );
            })}
            {!candidates.length && <div className="text-sm text-muted-foreground py-6 text-center">暂无候选选题</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>本周产出</CardTitle></CardHeader>
          <CardContent>
            <div style={{ width: "100%", height: 192 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weekChartData}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={24} />
                  <Tooltip cursor={{ fill: "rgba(0,0,0,0.05)" }} />
                  <Bar dataKey="drafts" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 text-sm text-muted-foreground">实时统计来自 `/api/stats/dashboard`</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>最近文章</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => onOpenArticle(recent[0]?.id || recent[0]?.run_id, recent[0]?.status, recent[0]?.words)}>查看最新</Button>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {recent.map((r, i) => {
              const b = statusBadge(r.status);
              const runId = r.id || r.run_id;
              return (
                <div key={runId || i} className="flex items-center gap-4 py-3 cursor-pointer hover:bg-accent/40 -mx-2 px-2 rounded" onClick={() => onOpenArticle(runId, r.status, r.words)}>
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{r.user_request || runId || "未命名运行"}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{r.total_tokens || 0} tokens · {formatDateTime(r.created_at)}</div>
                  </div>
                  <div className="text-sm tabular-nums">评分 {r.review?.score ?? "-"}</div>
                  <Badge variant="outline" className={b.cls}>{b.text}</Badge>
                </div>
              );
            })}
            {!recent.length && <div className="text-sm text-muted-foreground py-6 text-center">暂无运行记录</div>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlayIconCustom() {
  return <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>;
}
