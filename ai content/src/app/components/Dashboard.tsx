import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { TrendingUp, FileText, CheckCircle2, Coins, ArrowRight, Flame } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Line, LineChart } from "recharts";

const kpis = [
  { label: "今日草稿", value: "8", delta: "+2", icon: FileText, color: "text-violet-500" },
  { label: "本周通过率", value: "92%", delta: "+4%", icon: CheckCircle2, color: "text-emerald-500" },
  { label: "总成本", value: "¥0.00", delta: "Token Plan", icon: Coins, color: "text-amber-500" },
  { label: "平均耗时", value: "6.4 min", delta: "-1.2", icon: TrendingUp, color: "text-sky-500" },
];

const candidates = [
  { title: "DeepSeek-V3 发布带来的国产大模型竞争格局变化", angle: "技术拐点 + 商业影响双线", platform: "wechat", quality: 0.85, hot: 9842 },
  { title: "OpenAI 内部文档泄露：下一代模型路线图", angle: "独家爆料 + 行业预测", platform: "wechat", quality: 0.82, hot: 7621 },
  { title: "国产 AI 芯片三季度出货量首次反超英伟达 H20", angle: "数据驱动 + 政策影响", platform: "wechat", quality: 0.79, hot: 5430 },
  { title: "小红书算法大改：低粉博主流量不再", angle: "运营复盘 + 应对策略", platform: "xiaohongshu", quality: 0.76, hot: 4218 },
  { title: "Manus Agent 一周年:被高估了还是被低估了?", angle: "深度思考 + 反方观点", platform: "wechat", quality: 0.74, hot: 3902 },
];

const recent = [
  { title: "Cursor 估值翻倍背后：AI Coding 真正的护城河", status: "done", words: 1872, score: 8.4, time: "2h ago" },
  { title: "字节豆包大模型再降价，这次冲着谁去的", status: "reviewing", words: 1654, score: 7.6, time: "3h ago" },
  { title: "Sora 2 国内可用？真相比你想的复杂", status: "needs_human", words: 2103, score: 6.9, time: "5h ago" },
  { title: "Anthropic 拿下亚马逊百亿投资全解读", status: "done", words: 1921, score: 8.7, time: "yesterday" },
];

const weekData = [
  { day: "周一", drafts: 5, cost: 0 }, { day: "周二", drafts: 7, cost: 0 },
  { day: "周三", drafts: 6, cost: 0 }, { day: "周四", drafts: 9, cost: 0 },
  { day: "周五", drafts: 8, cost: 0 }, { day: "周六", drafts: 4, cost: 0 }, { day: "周日", drafts: 8, cost: 0 },
];

const statusBadge = (s: string) => {
  const m: Record<string, { text: string; cls: string }> = {
    done: { text: "已完成", cls: "bg-emerald-500/15 text-emerald-600 border-emerald-500/20" },
    reviewing: { text: "审阅中", cls: "bg-amber-500/15 text-amber-600 border-amber-500/20" },
    needs_human: { text: "需人工", cls: "bg-rose-500/15 text-rose-600 border-rose-500/20" },
  };
  return m[s];
};

export function Dashboard({ onStartRun, onOpenArticle }: { onStartRun: (title?: string) => void; onOpenArticle: () => void }) {
  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">2026-05-10 · 内容主理人视角 · 北极星目标 ≥ 8 篇/日</p>
        </div>
        <Button onClick={() => onStartRun()}>
          <PlayIconCustom /> 开始新一轮生成
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => {
          const Icon = k.icon;
          return (
            <Card key={k.label}>
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

      <div className="grid grid-cols-3 gap-4">
        <Card className="col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Flame className="w-4 h-4 text-orange-500" />今日候选选题</CardTitle>
            <Button variant="ghost" size="sm">刷新热榜</Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {candidates.map((c, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors group">
                <div className="w-8 text-center text-muted-foreground text-sm">#{i + 1}</div>
                <div className="flex-1 min-w-0">
                  <div className="truncate">{c.title}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-2">
                    <span>{c.angle}</span>
                    <span>·</span>
                    <span>热度 {c.hot.toLocaleString()}</span>
                  </div>
                </div>
                <Badge variant="secondary" className="capitalize">{c.platform}</Badge>
                <div className="text-sm tabular-nums w-12 text-right text-emerald-600">{(c.quality * 100).toFixed(0)}</div>
                <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100" onClick={() => onStartRun(c.title)}>
                  开跑 <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>本周产出</CardTitle></CardHeader>
          <CardContent>
            <div style={{ width: "100%", height: 192 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weekData}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={24} />
                  <Tooltip cursor={{ fill: "rgba(0,0,0,0.05)" }} />
                  <Bar dataKey="drafts" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 text-sm text-muted-foreground">合计 47 篇 · 平均 6.7/日</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>最近文章</CardTitle>
          <Button variant="ghost" size="sm" onClick={onOpenArticle}>查看全部</Button>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {recent.map((r, i) => {
              const b = statusBadge(r.status);
              return (
                <div key={i} className="flex items-center gap-4 py-3 cursor-pointer hover:bg-accent/40 -mx-2 px-2 rounded" onClick={onOpenArticle}>
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{r.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{r.words} 字 · {r.time}</div>
                  </div>
                  <div className="text-sm tabular-nums">评分 {r.score}</div>
                  <Badge variant="outline" className={b.cls}>{b.text}</Badge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlayIconCustom() {
  return <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>;
}
