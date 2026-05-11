import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Slider } from "./ui/slider";
import { Switch } from "./ui/switch";
import { Badge } from "./ui/badge";
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group";
import { Rocket, Wand2 } from "lucide-react";

export function NewRun({ initialTitle, onLaunch }: { initialTitle?: string; onLaunch: () => void }) {
  const [request, setRequest] = useState(initialTitle ?? "今天 AI 圈有什么值得写的？模仿 caoz 风格的公众号文。");
  const [platform, setPlatform] = useState("wechat");
  const [style, setStyle] = useState("caoz");
  const [parallel, setParallel] = useState([5]);
  const [revise, setRevise] = useState([2]);
  const [maxImg, setMaxImg] = useState([4]);
  const [budget, setBudget] = useState([200]);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 overflow-auto">
      <div>
        <h1>新建生成任务</h1>
        <p className="text-muted-foreground text-sm mt-1">配置 7 个 Agent 协同写一篇可发布草稿</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <Card>
            <CardHeader><CardTitle>选题指令</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>用户指令（自然语言）</Label>
                <Textarea className="mt-2 h-24" value={request} onChange={(e) => setRequest(e.target.value)} placeholder="例如：写一篇模仿 caoz 风格的关于 DeepSeek-V3 的公众号文章" />
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Wand2 className="w-4 h-4" /> TopicAgent 会从今日热榜中挑选最契合的切入角度
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>风格 & 平台</CardTitle></CardHeader>
            <CardContent className="space-y-5">
              <div>
                <Label>风格指纹</Label>
                <Select value={style} onValueChange={setStyle}>
                  <SelectTrigger className="mt-2"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="caoz">caoz 的梦呓 · 短句犀利 · 8 篇样本</SelectItem>
                    <SelectItem value="bdj">半佛仙人 · 反讽密集 · 12 篇样本</SelectItem>
                    <SelectItem value="hesheng">何加盐 · 长文叙事 · 15 篇样本</SelectItem>
                    <SelectItem value="custom">+ 上传新风格...</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>目标平台</Label>
                <ToggleGroup type="single" value={platform} onValueChange={(v) => v && setPlatform(v)} className="mt-2 justify-start">
                  <ToggleGroupItem value="wechat">公众号</ToggleGroupItem>
                  <ToggleGroupItem value="xiaohongshu">小红书</ToggleGroupItem>
                  <ToggleGroupItem value="zhihu">知乎</ToggleGroupItem>
                  <ToggleGroupItem value="douyin">抖音文案</ToggleGroupItem>
                </ToggleGroup>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>高级参数</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <SliderRow label="Researcher 并行度" value={parallel[0]} unit=" workers" max={8} min={1} onChange={(v) => setParallel([v])} />
              <SliderRow label="最大修订轮次" value={revise[0]} unit=" 轮" max={4} min={0} onChange={(v) => setRevise([v])} />
              <SliderRow label="配图数量上限" value={maxImg[0]} unit=" 张" max={8} min={0} onChange={(v) => setMaxImg([v])} />
              <SliderRow label="Token 预算" value={budget[0] * 1000} unit=" tokens" max={500} min={50} step={50} onChange={(v) => setBudget([v])} format={(v) => `${(v / 1000).toFixed(0)}K`} display={`${budget[0]}K`} />
              <div className="flex items-center justify-between pt-2 border-t">
                <div>
                  <Label>启用 Langfuse Trace</Label>
                  <div className="text-xs text-muted-foreground mt-1">每次 LLM 调用的 prompt / cost / latency</div>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>预估</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Row label="预计耗时" value="~ 6 分钟" />
              <Row label="LLM 调用" value="~ 14 次" />
              <Row label="Token 预估" value="~ 95K" />
              <Row label="图像生成" value={`${maxImg[0]} 张 (Coze)`} />
              <Row label="预估成本" value="¥ 0.00" highlight />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Agent 模型分配</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {[
                ["TopicAgent", "MiMo-V2.5", "fast"],
                ["PlannerAgent", "MiMo-V2.5-Pro", "balanced"],
                ["Researcher×N", "MiMo-V2.5", "fast"],
                ["EditorAgent", "MiMo-V2.5-Pro", "balanced"],
                ["WriterAgent", "MiMo-V2.5-Pro", "balanced"],
                ["IllustratorAgent", "Coze Seedream", "image"],
                ["ReviewerAgent", "MiMo-V2.5-Pro", "balanced"],
              ].map(([a, m, t]) => (
                <div key={a} className="flex items-center justify-between">
                  <span>{a}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">{m}</span>
                    <Badge variant="outline" className="text-[10px]">{t}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Button className="w-full" size="lg" onClick={onLaunch}>
            <Rocket className="w-4 h-4 mr-2" /> 启动生成
          </Button>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={highlight ? "text-emerald-600" : ""}>{value}</span>
    </div>
  );
}

function SliderRow({ label, value, unit, max, min, step = 1, onChange, format, display }: any) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <span className="text-sm tabular-nums text-muted-foreground">{display ?? `${value}${unit}`}</span>
      </div>
      <Slider className="mt-3" value={[value]} max={max} min={min} step={step} onValueChange={(v) => onChange(v[0])} />
    </div>
  );
}
