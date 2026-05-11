import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Plus, Upload, Link as LinkIcon, Loader2 } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { createStyle, listStyles, analyzeStyle, getStyle } from "../../lib/api";

export function StyleManager() {
  const [styles, setStyles] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<any | null>(null);
  const [fingerprint, setFingerprint] = useState<any | null>(null);

  async function refresh() {
    const res = await listStyles();
    setStyles(res.styles || []);
  }

  async function addStyle() {
    if (!name.trim()) return;
    await createStyle({ name: name.trim(), description: "从前端创建" });
    setName("");
    await refresh();
  }

  async function handleAnalyze() {
    if (!urlInput.trim()) return;
    // 获取最新创建的风格作为分析目标，或创建新风格
    let targetId = selectedStyle?.id;
    if (!targetId) {
      if (!name.trim()) return;
      const created = await createStyle({ name: name.trim(), description: "从URL分析创建" });
      targetId = created.id;
      setName("");
    }

    setAnalyzing(true);
    try {
      const urls = urlInput.split("\n").map((u) => u.trim()).filter(Boolean);
      const result = await analyzeStyle(targetId, urls);
      setFingerprint(result.fingerprint);
      setUrlInput("");
      await refresh();
      const detail = await getStyle(targetId);
      setSelectedStyle(detail);
    } catch (err) {
      console.error("Analyze failed:", err);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleBatchUpload() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrlInput((prev) => (prev ? prev + "\n" + text : text));
      }
    } catch {
      // 剪贴板不可用
    }
  }

  async function handleCardClick(style: any) {
    try {
      const detail = await getStyle(style.id);
      setSelectedStyle(detail);
      setFingerprint(detail.fingerprint || null);
    } catch {
      setSelectedStyle(style);
      setFingerprint(style.fingerprint || null);
    }
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  // 高频词数据：优先用指纹数据
  const wordFreq = fingerprint?.top_words
    ? (Array.isArray(fingerprint.top_words)
        ? fingerprint.top_words.map((w: string, i: number) => ({ w, c: Math.max(50 - i * 8, 10) }))
        : [{ w: String(fingerprint.top_words), c: 50 }])
    : [
        { w: "其实", c: 142 }, { w: "你看", c: 128 }, { w: "说白了", c: 98 },
        { w: "牛逼", c: 87 }, { w: "震惊", c: 65 }, { w: "兄弟", c: 54 },
        { w: "硅谷", c: 49 }, { w: "本质上", c: 42 }, { w: "我跟你讲", c: 38 },
      ];

  const syntaxStats = fingerprint
    ? [
        { label: "平均句长", value: `${fingerprint.avg_sentence_len ?? "-"} 字`, sub: "指纹提取值" },
        { label: "问句占比", value: fingerprint.question_ratio ? `${(fingerprint.question_ratio * 100).toFixed(1)}%` : "-", sub: "指纹提取值" },
        { label: "emoji 密度", value: `${fingerprint.emoji_density ?? "-"}`, sub: "指纹提取值" },
        { label: "第二人称", value: fingerprint.second_person_freq ? `${fingerprint.second_person_freq} 次/千字` : "-", sub: "指纹提取值" },
      ]
    : [
        { label: "平均句长", value: "14.2 字", sub: "远低于行业均值 28 字 → 短句风格突出" },
        { label: "问句占比", value: "11.3%", sub: "高于均值 4.8% → 喜用反问钩子" },
        { label: "emoji 密度", value: "0", sub: "完全不用 emoji" },
        { label: "第二人称", value: "48 次/千字", sub: "强对话感" },
      ];

  const repSentences = fingerprint?.representative_sentences || [
    "说白了，这事儿核心就一句话。",
    "你看硅谷那帮 lab 现在的心情，跟当年柯达看到富士一样。",
    "六百万美金，把整个行业的成本叙事掀了。",
  ];

  const displayTitle = selectedStyle?.name || "caoz";

  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>风格管理</h1>
          <p className="text-muted-foreground text-sm mt-1">管理用于模仿的写作指纹 · 共 {styles.length} 个</p>
        </div>
        <div className="flex gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="新风格名称" className="w-48" />
          <Button onClick={addStyle}><Plus className="w-4 h-4 mr-2" />新增风格</Button>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>从文章 URL 抽取风格</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="flex-1 flex items-start gap-2 px-3 border rounded-md focus-within:ring-2 focus-within:ring-ring">
              <LinkIcon className="w-4 h-4 text-muted-foreground mt-3" />
              <textarea
                className="flex-1 border-0 bg-transparent text-sm resize-none focus:outline-none min-h-[40px] py-2"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="粘贴公众号文章 URL，每行一个，最低 5 篇形成有效指纹..."
                rows={2}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Button variant="outline" size="sm" onClick={handleBatchUpload}><Upload className="w-4 h-4 mr-1" />粘贴</Button>
              <Button size="sm" onClick={handleAnalyze} disabled={analyzing || !urlInput.trim()}>
                {analyzing ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : null}
                抽取指纹
              </Button>
            </div>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">系统会自动抓取 → 调用 LLM 提取风格指纹 → 入库</div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        {styles.map((s, i) => (
          <Card
            key={s.id}
            className={`overflow-hidden hover:shadow-md transition cursor-pointer ${selectedStyle?.id === s.id ? "ring-2 ring-primary" : ""}`}
            onClick={() => handleCardClick(s)}
          >
            <div className={`h-20 bg-gradient-to-br ${["from-violet-500 to-fuchsia-500", "from-orange-500 to-rose-500", "from-sky-500 to-cyan-500", "from-emerald-500 to-teal-500", "from-amber-500 to-yellow-500"][i % 5]}`} />
            <CardContent className="p-5 -mt-8">
              <div className="w-14 h-14 rounded-xl bg-card border-4 border-card flex items-center justify-center text-xl">
                {s.name.charAt(0)}
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span>{s.name}</span>
                <Badge variant="outline" className={s.fingerprint ? "text-emerald-600 border-emerald-500/30 bg-emerald-500/10" : "text-muted-foreground"}>
                  {s.fingerprint ? "已分析" : "未分析"}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground mt-1">{s.sample_count || 0} 篇样本</div>
            </CardContent>
          </Card>
        ))}
        {!styles.length && <div className="col-span-3 text-sm text-muted-foreground text-center py-8 border rounded-lg">暂无风格。可以先新增一个。</div>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{displayTitle} · 高频词分布</CardTitle></CardHeader>
          <CardContent>
            <div style={{ width: "100%", height: 224 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={wordFreq} layout="vertical" margin={{ left: 30 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis dataKey="w" type="category" tick={{ fontSize: 11 }} width={70} />
                  <Tooltip />
                  <Bar dataKey="c" radius={[0, 4, 4, 0]}>
                    {wordFreq.map((item: any, i: number) => <Cell key={`cell-${item.w}`} fill={`hsl(${260 + i * 5}, 70%, ${60 - i * 2}%)`} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{displayTitle} · 句法特征</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {syntaxStats.map((s) => <Stat key={s.label} label={s.label} value={s.value} sub={s.sub} />)}
            <div className="pt-3 border-t">
              <div className="text-sm mb-2">代表样本句</div>
              <div className="space-y-1.5 text-xs text-muted-foreground italic">
                {repSentences.map((s: string, i: number) => <div key={i}>· "{s}"</div>)}
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
