import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Bold, Italic, Heading, Link as LinkIcon, ImageIcon, Quote, RefreshCw, Download, Send, CheckCircle2, AlertTriangle } from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from "recharts";
import { ImageWithFallback } from "./figma/ImageWithFallback";

const radarData = [
  { axis: "短句率", target: 90, draft: 86 },
  { axis: "反讽密度", target: 75, draft: 68 },
  { axis: "钩子强度", target: 88, draft: 91 },
  { axis: "口语化", target: 82, draft: 79 },
  { axis: "数据密度", target: 70, draft: 78 },
  { axis: "段落节奏", target: 85, draft: 80 },
];

const issues = [
  { type: "image_mismatch", level: "warning", text: "第 3 段配图描绘发布会，但段落讲商业影响" },
  { type: "style_drift", level: "info", text: "结尾偏客观，原作者偏煽情" },
];

export function ArticleEditor({ onBack }: { onBack: () => void }) {
  return (
    <div className="p-8 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1>DeepSeek-V3 发布：六百万美元，把硅谷震了</h1>
          <p className="text-muted-foreground text-sm mt-1">caoz 风格 · 公众号 · 1872 字 · 3 张配图 · 评分 8.4</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline"><Download className="w-4 h-4 mr-2" />导出 .md</Button>
          <Button variant="outline" onClick={onBack}>返回</Button>
          <Button><Send className="w-4 h-4 mr-2" />标记完成</Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4">
          <Card>
            <CardContent className="p-0">
              <div className="flex items-center gap-1 px-3 py-2 border-b">
                {[Heading, Bold, Italic, Quote, LinkIcon, ImageIcon].map((Icon, i) => (
                  <Button key={i} variant="ghost" size="sm" className="h-8 w-8 p-0"><Icon className="w-4 h-4" /></Button>
                ))}
                <div className="ml-auto text-xs text-muted-foreground">自动保存于 14:32</div>
              </div>
              <Tabs defaultValue="edit" className="p-4">
                <TabsList>
                  <TabsTrigger value="edit">编辑</TabsTrigger>
                  <TabsTrigger value="preview">公众号预览</TabsTrigger>
                </TabsList>
                <TabsContent value="edit" className="mt-4">
                  <Textarea
                    className="min-h-[420px] font-mono text-sm leading-relaxed"
                    defaultValue={`# DeepSeek-V3 发布：六百万美元，把硅谷震了

## 一、技术拐点已至

这两天科技圈有件事，值得每个还在硅谷做 PPT 融资的人警醒。

DeepSeek 把 V3 模型扔出来了。MMLU 88.5，HumanEval 82.6，价格还是同档位的几分之一。

[IMG: DeepSeek-V3 vs GPT-4o MMLU 对比柱状图 | 16:9 | chart]

## 二、训练成本到底多离谱

六百万美元。这个数字传出来的时候，硅谷不少 lab 的负责人坐不住了。

## 三、对国产大模型生态的影响

[IMG: 杭州 DeepSeek 办公室深夜调试场景 | 16:9 | cover]

阿里通义、字节豆包、Kimi——他们的策略全得改。`}
                  />
                </TabsContent>
                <TabsContent value="preview" className="mt-4">
                  <div className="border rounded-lg p-6 max-w-md mx-auto bg-card">
                    <h2 className="mb-2">DeepSeek-V3 发布：六百万美元，把硅谷震了</h2>
                    <div className="text-xs text-muted-foreground mb-4">caoz · 5 分钟阅读</div>
                    <p className="text-sm leading-7 mb-4">这两天科技圈有件事，值得每个还在硅谷做 PPT 融资的人警醒...</p>
                    <div className="aspect-video rounded overflow-hidden bg-muted my-3">
                      <ImageWithFallback src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600" alt="chart" className="w-full h-full object-cover" />
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>配图（3 / 4）</CardTitle>
              <Button variant="ghost" size="sm"><RefreshCw className="w-4 h-4 mr-2" />批量重新生成</Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { url: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600", type: "chart", label: "MMLU 对比" },
                  { url: "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600", type: "cover", label: "深夜调试" },
                  { url: "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600", type: "card", label: '"六百万震硅谷"金句卡' },
                ].map((img, i) => (
                  <div key={i} className="space-y-2">
                    <div className="aspect-video rounded-md overflow-hidden bg-muted relative group">
                      <ImageWithFallback src={img.url} alt={img.label} className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-2">
                        <Button size="sm" variant="secondary">替换</Button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span>{img.label}</span>
                      <Badge variant="outline" className="text-[10px]">{img.type}</Badge>
                    </div>
                  </div>
                ))}
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
                    <Radar name="目标 caoz" dataKey="target" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.15} />
                    <Radar name="当前草稿" dataKey="draft" stroke="#10b981" fill="#10b981" fillOpacity={0.25} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">综合相似度</span>
                <span className="text-emerald-600">87.3%</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Reviewer 反馈</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">综合评分</span>
                <span className="text-2xl tabular-nums text-emerald-600">8.4</span>
              </div>
              <div className="space-y-2">
                {issues.map((iss, i) => (
                  <div key={i} className="flex gap-2 p-2.5 rounded-md bg-amber-500/5 border border-amber-500/20">
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <div className="text-xs">
                      <Badge variant="outline" className="text-[10px] mb-1">{iss.type}</Badge>
                      <div>{iss.text}</div>
                    </div>
                  </div>
                ))}
                <div className="flex gap-2 p-2.5 rounded-md bg-emerald-500/5 border border-emerald-500/20">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div className="text-xs">事实准确性 · 已通过（17/17 引用对应）</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>平台合规</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row label="字数" value="1872 / 800-3000" ok />
              <Row label="emoji 用量" value="0 / 8" ok />
              <Row label="敏感词" value="未触发" ok />
              <Row label="标签数" value="3 / 5" ok />
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
