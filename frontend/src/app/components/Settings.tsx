import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Switch } from "./ui/switch";
import { Slider } from "./ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Eye, EyeOff, Plug, Loader2 } from "lucide-react";
import { getSettings, updateSettings } from "../../lib/api";

export function Settings() {
  const [settings, setSettings] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [activeProvider, setActiveProvider] = useState("xiaomi");
  const [agents, setAgents] = useState<Record<string, { provider: string; tier: string }>>({});
  const [tokenLimit, setTokenLimit] = useState(200);
  const [warnPct, setWarnPct] = useState(80);
  const [hardFuse, setHardFuse] = useState(true);
  const [costFuse, setCostFuse] = useState(true);
  const [langfuseTrace, setLangfuseTrace] = useState(true);
  const [sensitiveWords, setSensitiveWords] = useState(true);

  useEffect(() => {
    getSettings().then((s) => {
      setSettings(s);
      setActiveProvider(s?.defaults?.active_provider || "xiaomi");
      const agentMap: Record<string, { provider: string; tier: string }> = {};
      for (const [k, v] of Object.entries(s?.agents || {})) {
        agentMap[k] = v as { provider: string; tier: string };
      }
      setAgents(agentMap);
      setTokenLimit(Math.round((s?.budget?.max_tokens_per_run || 200000) / 1000));
      setWarnPct(s?.budget?.warn_at_percent || 80);
    }).catch(() => undefined);
  }, []);

  function updateAgent(key: string, field: "provider" | "tier", value: string) {
    setAgents((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  }

  async function saveSettings() {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = {
        ...settings,
        defaults: { ...settings.defaults, active_provider: activeProvider },
        agents: Object.fromEntries(
          Object.entries(agents).map(([k, v]) => [k, { provider: v.provider, tier: v.tier }])
        ),
        budget: {
          ...settings.budget,
          max_tokens_per_run: tokenLimit * 1000,
          warn_at_percent: warnPct,
        },
      };
      await updateSettings(updated);
      setSettings(updated);
    } finally {
      setSaving(false);
    }
  }

  const agentList = useMemo(() => {
    return Object.entries(agents).map(([key, cfg]) => ({
      agent: `${key[0].toUpperCase()}${key.slice(1)}Agent`,
      key,
      provider: cfg.provider,
      tier: cfg.tier,
    }));
  }, [agents]);

  const providerList = [
    { id: "xiaomi", name: "小米 MiMo", sub: "Token Plan · ¥0" },
    { id: "deepseek", name: "DeepSeek", sub: "¥1 / ¥2 per M tok" },
    { id: "openai", name: "OpenAI", sub: "$0.15 / $0.60 起" },
  ];

  return (
    <div className="h-full overflow-y-auto">
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1>系统设置</h1>
          <p className="text-muted-foreground text-sm mt-1">Provider / 模型分级 / 预算 / API Keys</p>
        </div>
        <Button onClick={saveSettings} disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          {saving ? "保存中" : "保存设置"}
        </Button>
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
                {providerList.map((p) => (
                  <div
                    key={p.id}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition ${activeProvider === p.id ? "border-primary bg-primary/5" : "hover:border-foreground/20"}`}
                    onClick={() => setActiveProvider(p.id)}
                  >
                    <div className="flex items-center justify-between">
                      <span>{p.name}</span>
                      {activeProvider === p.id && <Badge>当前</Badge>}
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
              {agentList.map((a) => (
                <div key={a.key} className="flex items-center gap-3 py-2 border-b last:border-0">
                  <span className="w-40 text-sm">{a.agent}</span>
                  <Select value={a.provider} onValueChange={(v) => updateAgent(a.key, "provider", v)}>
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="xiaomi">小米 MiMo</SelectItem>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={a.tier} onValueChange={(v) => updateAgent(a.key, "tier", v)}>
                    <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fast">fast (轻量)</SelectItem>
                      <SelectItem value="balanced">balanced (主力)</SelectItem>
                    </SelectContent>
                  </Select>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {settings?.providers?.[a.provider]?.models?.[a.tier] || a.tier}
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
                <div className="flex justify-between mb-2"><Label>单 run token 上限</Label><span className="tabular-nums text-sm">{tokenLimit}K</span></div>
                <Slider value={[tokenLimit]} onValueChange={(v) => setTokenLimit(v[0])} max={500} min={50} step={10} />
              </div>
              <div>
                <div className="flex justify-between mb-2"><Label>降级触发阈值</Label><span className="tabular-nums text-sm">{warnPct}%</span></div>
                <Slider value={[warnPct]} onValueChange={(v) => setWarnPct(v[0])} max={100} min={50} step={5} />
                <p className="text-xs text-muted-foreground mt-2">达到阈值时自动降级到 fast 档位模型</p>
              </div>
              <div className="flex items-center justify-between pt-2 border-t">
                <div>
                  <Label>启用硬熔断</Label>
                  <p className="text-xs text-muted-foreground mt-1">100% 时中断 run，保留中间状态</p>
                </div>
                <Switch checked={hardFuse} onCheckedChange={setHardFuse} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>付费 provider 时按金额熔断</Label>
                  <p className="text-xs text-muted-foreground mt-1">budget_limit_cents = {settings?.budget?.budget_limit_cents || 300} ({((settings?.budget?.budget_limit_cents || 300) / 100).toFixed(1)} 元)</p>
                </div>
                <Switch checked={costFuse} onCheckedChange={setCostFuse} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="keys" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>环境变量</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <KeyRow name="MIMO_API_KEY" value="tp-" status="connected" />
              <KeyRow name="COZE_API_KEY" value="pat-" status="connected" />
              <KeyRow name="DEEPSEEK_API_KEY" value="" status="empty" />
              <KeyRow name="OPENAI_API_KEY" value="" status="empty" />
              <KeyRow name="TAVILY_API_KEY" value="tvly-" status="connected" />
              <KeyRow name="LANGFUSE_SECRET_KEY" value="sk-lf-" status="connected" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4 mt-4">
          <Card>
            <CardHeader><CardTitle>可观测</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <ToggleRow label="Langfuse Trace" sub="每次 LLM 调用记录 prompt/completion/cost" value={langfuseTrace} onChange={setLangfuseTrace} />
              <ToggleRow label="run_events 全量持久化" sub="支持端到端回放" value={true} onChange={() => {}} />
              <ToggleRow label="Token 明细写入 token_usage" value={true} onChange={() => {}} />
              <ToggleRow label="Prometheus 指标导出" sub="Phase 2" value={false} onChange={() => {}} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>内容安全</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <ToggleRow label="自建敏感词库" value={sensitiveWords} onChange={setSensitiveWords} />
              <ToggleRow label="阿里云内容安全 API" sub="可选，需双 fail 才拦" value={false} onChange={() => {}} />
            </CardContent>
          </Card>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => getSettings().then((s) => { setSettings(s); })}>恢复默认</Button>
            <Button onClick={saveSettings} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              保存设置
            </Button>
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

function ToggleRow({ label, sub, value, onChange }: { label: string; sub?: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <Label>{label}</Label>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </div>
      <Switch checked={value} onCheckedChange={onChange} />
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
