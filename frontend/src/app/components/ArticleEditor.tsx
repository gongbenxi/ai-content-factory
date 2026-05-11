import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Bold, Italic, Heading, Link as LinkIcon, ImageIcon, Quote, RefreshCw, Download, Send, CheckCircle2, AlertTriangle, Save, Loader2 } from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from "recharts";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import { completeRun, exportRun, getRun, updateArticle, regenerateImage } from "../../lib/api";

function buildRadarData(review: any): { axis: string; target: number; draft: number }[] {
  if (!review?.style_scores) {
    return [
      { axis: "短句率", target: 90, draft: 86 },
      { axis: "反讽密度", target: 75, draft: 68 },
      { axis: "钩子强度", target: 88, draft: 91 },
      { axis: "口语化", target: 82, draft: 79 },
      { axis: "数据密度", target: 70, draft: 78 },
      { axis: "段落节奏", target: 85, draft: 80 },
    ];
  }
  const ss = review.style_scores;
  return Object.entries(ss).map(([axis, val]: [string, any]) => ({
    axis,
    target: val.target ?? 80,
    draft: val.draft ?? 70,
  }));
}

const fallbackDraft = `# 等待生成结果

当前还没有可编辑草稿。请先启动一次生成任务，或等待 WriterAgent 完成输出。`;

export function ArticleEditor({ runId, onBack }: { runId: string | null; onBack: () => void }) {
  const [run, setRun] = useState<any>(null);
  const [draft, setDraft] = useState(fallbackDraft);
  const [saving, setSaving] = useState(false);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function insertMd(syntax: string, wrap?: boolean) {
    const ta = textareaRef.current;
    if (!ta) {
      setDraft((prev) => prev + syntax);
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = draft.slice(start, end);
    let insert: string;
    if (wrap && selected) {
      insert = `${syntax}${selected}${syntax}`;
    } else if (wrap) {
      insert = `${syntax}文本${syntax}`;
    } else {
      insert = syntax;
    }
    setDraft(draft.slice(0, start) + insert + draft.slice(end));
  }

  const toolbarItems: { icon: any; label: string; action: () => void }[] = [
    { icon: Heading, label: "标题", action: () => insertMd("\n## ") },
    { icon: Bold, label: "粗体", action: () => insertMd("**", true) },
    { icon: Italic, label: "斜体", action: () => insertMd("*", true) },
    { icon: Quote, label: "引用", action: () => insertMd("\n> ") },
    { icon: LinkIcon, label: "链接", action: () => insertMd("[链接文字](url)") },
    { icon: ImageIcon, label: "图片", action: () => insertMd("\n[IMG: 描述 | 16:9 | illustration]\n") },
  ];

  useEffect(() => {
    if (!runId) return;
    getRun(runId).then((data) => {
      setRun(data);
      setDraft(data.final_md || data.draft_md || fallbackDraft);
    }).catch(() => {
      setDraft(`# 草稿读取失败\n\n未能读取 run ${runId} 的草稿内容，请返回 Dashboard 刷新后重试。`);
    });
  }, [runId]);

  const title = useMemo(() => {
    const firstHeading = draft.split("\n").find((line) => line.startsWith("# "));
    return firstHeading?.replace(/^#\s+/, "") || run?.user_request || "文章编辑器";
  }, [draft, run]);

  const images = run?.images || [];
  const issues = run?.review?.issues || [];
  const radarData = useMemo(() => buildRadarData(run?.review), [run?.review]);

  async function save() {
    if (!runId) return;
    setSaving(true);
    try {
      await updateArticle(runId, { draft_md: draft });
    } finally {
      setSaving(false);
    }
  }

  async function markDone() {
    if (!runId) return;
    await save();
    await completeRun(runId);
    onBack();
  }

  async function downloadMd() {
    if (!runId) return;
    const content = await exportRun(runId);
    const blob = new Blob([content || draft], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || runId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleRegenerateImage(index: number) {
    if (!runId || regeneratingIndex !== null) return;
    setRegeneratingIndex(index);
    try {
      const result = await regenerateImage(runId, index);
      setRun((prev: any) => {
        if (!prev) return prev;
        const newImages = [...(prev.images || [])];
        newImages[index] = result.image;
        return { ...prev, images: newImages };
      });
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setRegeneratingIndex(null);
    }
  }

  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>{title}</h1>
          <p className="text-muted-foreground text-sm mt-1">{run?.style_id || "default"} 风格 · {run?.target_platform || "wechat"} · {draft.length} 字符 · {images.length} 张配图 · 评分 {run?.review?.score ?? "-"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={downloadMd} disabled={!runId}><Download className="w-4 h-4 mr-2" />导出 .md</Button>
          <Button variant="outline" onClick={save} disabled={!runId || saving}>{saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}保存</Button>
          <Button variant="outline" onClick={onBack}>返回</Button>
          <Button onClick={markDone} disabled={!runId}><Send className="w-4 h-4 mr-2" />标记完成</Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4">
          <Card>
            <CardContent className="p-0">
              <div className="flex items-center gap-1 px-3 py-2 border-b">
                {toolbarItems.map((item) => (
                  <Button key={item.label} variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={item.action} title={item.label}>
                    <item.icon className="w-4 h-4" />
                  </Button>
                ))}
                <div className="ml-auto text-xs text-muted-foreground">{saving ? "保存中..." : "连接后端草稿"}</div>
              </div>
              <Tabs defaultValue="edit" className="p-4">
                <TabsList>
                  <TabsTrigger value="edit">编辑</TabsTrigger>
                  <TabsTrigger value="preview">公众号预览</TabsTrigger>
                </TabsList>
                <TabsContent value="edit" className="mt-4">
                  <Textarea
                    ref={textareaRef}
                    className="min-h-[420px] font-mono text-sm leading-relaxed"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                  />
                </TabsContent>
                <TabsContent value="preview" className="mt-4">
                  <div className="border rounded-lg p-6 max-w-md mx-auto bg-card">
                    <h2 className="mb-2">{title}</h2>
                    <div className="text-xs text-muted-foreground mb-4">{run?.style_id || "default"} · 5 分钟阅读</div>
                    <div className="text-sm leading-7 prose prose-sm max-w-none">
                      <ReactMarkdown>{draft}</ReactMarkdown>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>配图（{images.length}）</CardTitle>
              <Button variant="ghost" size="sm"><RefreshCw className="w-4 h-4 mr-2" />批量重新生成</Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                {images.map((img: any, i: number) => (
                  <div key={i} className="space-y-2">
                    <div className="aspect-video rounded-md overflow-hidden bg-muted relative group">
                      <ImageWithFallback src={img.url || "/favicon.svg"} alt={img.description || img.type} className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-2">
                        <Button size="sm" variant="secondary" onClick={() => handleRegenerateImage(i)} disabled={regeneratingIndex !== null}>
                          {regeneratingIndex === i ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : null}
                          替换
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="truncate">{img.description || `图片 ${i + 1}`}</span>
                      <Badge variant="outline" className="text-[10px]">{img.type || "image"}</Badge>
                    </div>
                  </div>
                ))}
                {!images.length && <div className="col-span-3 text-sm text-muted-foreground py-6 text-center">暂无配图</div>}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>风格匹配雷达</CardTitle></CardHeader>
            <CardContent>
              <div style={{ width: "100%", height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis tick={false} axisLine={false} />
                    <Radar name="目标风格" dataKey="target" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.15} />
                    <Radar name="当前草稿" dataKey="draft" stroke="#10b981" fill="#10b981" fillOpacity={0.25} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">综合相似度</span>
                <span className="text-emerald-600">{run?.review?.score ? `${Math.round(run.review.score * 10)}%` : "-"}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Reviewer 反馈</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">综合评分</span>
                <span className="text-2xl tabular-nums text-emerald-600">{run?.review?.score ?? "-"}</span>
              </div>
              <div className="space-y-2">
                {issues.map((iss: any, i: number) => (
                  <div key={i} className="flex gap-2 p-2.5 rounded-md bg-amber-500/5 border border-amber-500/20">
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <div className="text-xs">
                      <Badge variant="outline" className="text-[10px] mb-1">{iss.type || "issue"}</Badge>
                      <div>{iss.detail || iss.text}</div>
                    </div>
                  </div>
                ))}
                {!issues.length && (
                  <div className="flex gap-2 p-2.5 rounded-md bg-emerald-500/5 border border-emerald-500/20">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    <div className="text-xs">暂无阻塞问题</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>平台合规</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row label="字数" value={`${draft.length} / 800-3000`} ok={draft.length >= 800 && draft.length <= 3000} />
              <Row label="敏感词" value={issues.some((i: any) => i.type === "safety") ? `${issues.filter((i: any) => i.type === "safety").length} 处` : "未触发"} ok={!issues.some((i: any) => i.type === "safety")} />
              <Row label="标题字数" value={`${title.length} 字`} ok={title.length >= 10 && title.length <= 40} />
              <Row label="配图数" value={`${images.length} 张`} ok={images.length >= 1} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={ok ? "text-emerald-600" : ""}>{value}</span>
    </div>
  );
}
