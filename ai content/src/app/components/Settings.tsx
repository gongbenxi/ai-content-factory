import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Switch } from "./ui/switch";
import { Slider } from "./ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Eye, EyeOff, Plug } from "lucide-react";

const agentDefaults = [
  { agent: "TopicAgent", provider: "xiaomi", tier: "fast" },
  { agent: "PlannerAgent", provider: "xiaomi", tier: "balanced" },
  { agent: "ResearcherAgent", provider: "xiaomi", tier: "fast" },
  { agent: "EditorAgent", provider: "xiaomi", tier: "balanced" },
  { agent: "WriterAgent", provider: "xiaomi", tier: "balanced" },
  { agent: "ReviewerAgent", provider: "xiaomi", tier: "balanced" },
  { agent: "ReviserAgent", provider: "xiaomi", tier: "balanced" },
];

export function Settings() {
  return (
    <div className="h-full overflow-y-auto">
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1>系统设置</h1>
        <p className="text-muted-foreground text-sm mt-1">Provider / 模型分级 / 预算 / API Keys</p>
      </div>

      <Tabs defaultValue="models">
        <TabsList>
          <TabsTrigger value="models">模型与 Provider</TabsTrigger>
          <TabsTrigger value="budget">预算 & 熔断</TabsTrigger>
          <TabsTrigger value="keys">API Keys</TabsTrigger>
          <TabsTrigger value="advanced">高级</TabsTrigger>
        </TabsList>

        <TabsContent value="models" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>当前默认 Provider</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: "xiaomi", name: "小米 MiMo", sub: "Token Plan · ¥0", active: true },
                  { id: "deepseek", name: "DeepSeek", sub: "¥1 / ¥2 per M tok" },
                  { id: "openai", name: "OpenAI", sub: "$0.15 / $0.60 起" },
                ].map((p) => (
                  <div key={p.id} className={`p-4 rounded-lg border-2 cursor-pointer transition ${p.active ? "border-primary bg-primary/5" : "hover:border-foreground/20"}`}>
                    <div className="flex items-center justify-between">
                      <span>{p.name}</span>
                      {p.active && <Badge>当前</Badge>}
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">{p.sub}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Per-Agent 模型分配</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {agentDefaults.map((a) => (
                <div key={a.agent} className="flex items-center gap-3 py-2 border-b last:border-0">
                  <span className="w-40 text-sm">{a.agent}</span>
                  <Select defaultValue={a.provider}>
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="xiaomi">小米 MiMo</SelectItem>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select defaultValue={a.tier}>
                    <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fast">fast (轻量)</SelectItem>
                      <SelectItem value="balanced">balanced (主力)</SelectItem>
                    </SelectContent>
                  </Select>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {a.tier === "fast" ? "MiMo-V2.5" : "MiMo-V2.5-Pro"}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="budget" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>Token 预算</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div>
                <div className="flex justify-between mb-2"><Label>单 run token 上限</Label><span className="tabular-nums text-sm">200,000</span></div>
                <Slider defaultValue={[200]} max={500} min={50} step={10} />
              </div>
              <div>
                <div className="flex justify-between mb-2"><Label>降级触发阈值</Label><span className="tabular-nums text-sm">80%</span></div>
                <Slider defaultValue={[80]} max={100} min={50} step={5} />
                <p className="text-xs text-muted-foreground mt-2">达到阈值时自动降级到 fast 档位模型</p>
              </div>
              <div className="flex items-center justify-between pt-2 border-t">
                <div>
                  <Label>启用硬熔断</Label>
                  <p className="text-xs text-muted-foreground mt-1">100% 时中断 run，保留中间状态</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>付费 provider 时按金额熔断</Label>
                  <p className="text-xs text-muted-foreground mt-1">budget_limit_cents = 300 (¥3)</p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>并发与限速</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Row label="并发 run 上限" value="5" />
              <Row label="Researcher 并行度" value="5 workers" />
              <Row label="Coze 图像生成间隔" value="30 秒" />
              <Row label="外部 API 重试次数" value="3 次（指数退避）" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="keys" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>环境变量</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <KeyRow name="MIMO_API_KEY" value="tp-••••••••••••••••••3f2a" status="connected" />
              <KeyRow name="COZE_API_KEY" value="pat-••••••••••••••••91bf" status="connected" />
              <KeyRow name="DEEPSEEK_API_KEY" value="" status="empty" />
              <KeyRow name="OPENAI_API_KEY" value="" status="empty" />
              <KeyRow name="TAVILY_API_KEY" value="tvly-••••••••••••aef0" status="connected" />
              <KeyRow name="LANGFUSE_SECRET_KEY" value="sk-lf-••••••••••••" status="connected" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>数据库</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Plug className="w-4 h-4 text-emerald-500" />
                <code className="text-xs">postgresql://acf@localhost:5432/acf</code>
                <Badge variant="outline" className="ml-auto text-emerald-600 border-emerald-500/30 bg-emerald-500/10">已连接 · pgvector</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>可观测</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Toggle label="Langfuse Trace" sub="每次 LLM 调用记录 prompt/completion/cost" defaultOn />
              <Toggle label="run_events 全量持久化" sub="支持端到端回放" defaultOn />
              <Toggle label="Token 明细写入 token_usage" defaultOn />
              <Toggle label="Prometheus 指标导出" sub="Phase 2" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>内容安全</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Toggle label="自建敏感词库" defaultOn />
              <Toggle label="阿里云内容安全 API" sub="可选，需双 fail 才拦" />
            </CardContent>
          </Card>
          <div className="flex justify-end gap-2">
            <Button variant="outline">恢复默认</Button>
            <Button>保存设置</Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}

function Toggle({ label, sub, defaultOn }: { label: string; sub?: string; defaultOn?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <Label>{label}</Label>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </div>
      <Switch defaultChecked={defaultOn} />
    </div>
  );
}

function KeyRow({ name, value, status }: { name: string; value: string; status: "connected" | "empty" }) {
  return (
    <div className="flex items-center gap-3">
      <Label className="w-44 shrink-0 font-mono text-xs">{name}</Label>
      <Input className="font-mono text-xs" value={value} placeholder="未配置" readOnly />
      {status === "connected" ? (
        <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 bg-emerald-500/10">已连接</Badge>
      ) : (
        <Badge variant="outline">未配置</Badge>
      )}
    </div>
  );
}