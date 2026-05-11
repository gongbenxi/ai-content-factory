import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Plus, Upload, Link as LinkIcon } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts";

const styles = [
  { id: "caoz", name: "caoz 的梦呓", samples: 8, fit: 92, tags: ["短句", "反讽", "互联网老炮"], color: "from-violet-500 to-fuchsia-500" },
  { id: "bdj", name: "半佛仙人", samples: 12, fit: 88, tags: ["反讽", "金句密集", "财经"], color: "from-orange-500 to-rose-500" },
  { id: "hesheng", name: "何加盐", samples: 15, fit: 85, tags: ["人物深扒", "长叙事"], color: "from-sky-500 to-cyan-500" },
  { id: "ll", name: "L 先生说", samples: 7, fit: 80, tags: ["认知科学", "结构化"], color: "from-emerald-500 to-teal-500" },
  { id: "tong", name: "佟掌柜的店", samples: 5, fit: 72, tags: ["生活化", "温度感"], color: "from-amber-500 to-yellow-500" },
];

const wordFreq = [
  { w: "其实", c: 142 }, { w: "你看", c: 128 }, { w: "说白了", c: 98 },
  { w: "牛逼", c: 87 }, { w: "震惊", c: 65 }, { w: "兄弟", c: 54 },
  { w: "硅谷", c: 49 }, { w: "本质上", c: 42 }, { w: "我跟你讲", c: 38 },
];

export function StyleManager() {
  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>风格管理</h1>
          <p className="text-muted-foreground text-sm mt-1">管理用于模仿的写作指纹 · 共 {styles.length} 个</p>
        </div>
        <Button><Plus className="w-4 h-4 mr-2" />新增风格</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>从文章 URL 抽取风格</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="flex-1 flex items-center gap-2 px-3 border rounded-md focus-within:ring-2 focus-within:ring-ring">
              <LinkIcon className="w-4 h-4 text-muted-foreground" />
              <Input className="border-0 focus-visible:ring-0 px-0" placeholder="粘贴公众号文章 URL，最低 5 篇形成有效指纹..." />
            </div>
            <Button variant="outline"><Upload className="w-4 h-4 mr-2" />批量上传</Button>
            <Button>抽取指纹</Button>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">系统会自动抓取 → 调用 style_fingerprint → 入库 BGE-M3 embedding</div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        {styles.map((s) => (
          <Card key={s.id} className="overflow-hidden hover:shadow-md transition cursor-pointer">
            <div className={`h-20 bg-gradient-to-br ${s.color}`} />
            <CardContent className="p-5 -mt-8">
              <div className="w-14 h-14 rounded-xl bg-card border-4 border-card flex items-center justify-center text-xl">
                {s.name.charAt(0)}
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span>{s.name}</span>
                <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 bg-emerald-500/10">{s.fit}% 拟合</Badge>
              </div>
              <div className="text-xs text-muted-foreground mt-1">{s.samples} 篇样本</div>
              <div className="mt-3 flex flex-wrap gap-1">
                {s.tags.map((t) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>caoz · 高频词分布</CardTitle></CardHeader>
          <CardContent>
            <div style={{ width: "100%", height: 224 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={wordFreq} layout="vertical" margin={{ left: 30 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis dataKey="w" type="category" tick={{ fontSize: 11 }} width={70} />
                  <Tooltip />
                  <Bar dataKey="c" radius={[0, 4, 4, 0]}>
                    {wordFreq.map((item, i) => <Cell key={`cell-${item.w}`} fill={`hsl(${260 + i * 5}, 70%, ${60 - i * 2}%)`} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>caoz · 句法特征</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Stat label="平均句长" value="14.2 字" sub="远低于行业均值 28 字 → 短句风格突出" />
            <Stat label="问句占比" value="11.3%" sub="高于均值 4.8% → 喜用反问钩子" />
            <Stat label="emoji 密度" value="0" sub="完全不用 emoji" />
            <Stat label="第二人称" value="48 次/千字" sub="强对话感" />
            <div className="pt-3 border-t">
              <div className="text-sm mb-2">代表样本句</div>
              <div className="space-y-1.5 text-xs text-muted-foreground italic">
                <div>· "说白了，这事儿核心就一句话。"</div>
                <div>· "你看硅谷那帮 lab 现在的心情，跟当年柯达看到富士一样。"</div>
                <div>· "六百万美金，把整个行业的成本叙事掀了。"</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <div>
        <div className="text-sm">{label}</div>
        <div className="text-xs text-muted-foreground">{sub}</div>
      </div>
      <div className="tabular-nums">{value}</div>
    </div>
  );
}
