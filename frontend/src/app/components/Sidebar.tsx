import { useEffect, useState } from "react";
import { LayoutDashboard, PlayCircle, Activity, FileEdit, Palette, Settings as SettingsIcon, Sparkles, Sun, Moon } from "lucide-react";
import { cn } from "./ui/utils";
import { getSettings } from "../../lib/api";

export type PageKey = "dashboard" | "new-run" | "run-live" | "editor" | "styles" | "settings";

const items: { key: PageKey; label: string; icon: any }[] = [
  { key: "dashboard", label: "仪表盘", icon: LayoutDashboard },
  { key: "new-run", label: "新建运行", icon: PlayCircle },
  { key: "run-live", label: "实时运行", icon: Activity },
  { key: "editor", label: "文章编辑器", icon: FileEdit },
  { key: "styles", label: "风格管理", icon: Palette },
  { key: "settings", label: "设置", icon: SettingsIcon },
];

export function Sidebar({
  current,
  onChange,
  dark,
  onToggleDark,
}: {
  current: PageKey;
  onChange: (k: PageKey) => void;
  dark: boolean;
  onToggleDark: () => void;
}) {
  const [provider, setProvider] = useState("deepseek");
  const [budgetK, setBudgetK] = useState(200);

  useEffect(() => {
    getSettings().then((settings) => {
      setProvider(settings?.defaults?.active_provider || "deepseek");
      const maxTokens = Number(settings?.budget?.max_tokens_per_run || 200000);
      setBudgetK(Math.round(maxTokens / 1000));
    }).catch(() => undefined);
  }, []);

  return (
    <aside className="w-60 shrink-0 border-r bg-card flex flex-col">
      <div className="h-14 flex items-center gap-2.5 px-4 border-b">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm whitespace-nowrap overflow-hidden text-ellipsis leading-tight">AI Content Factory</div>
          <div className="text-xs text-muted-foreground leading-tight">v1.2 · Phase 1</div>
        </div>
        <button
          onClick={onToggleDark}
          className="w-6 h-6 rounded-md flex items-center justify-center hover:bg-accent transition-colors text-muted-foreground hover:text-foreground shrink-0"
          title={dark ? "切换浅色" : "切换深色"}
        >
          {dark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </button>
      </div>
      <nav className="p-3 flex-1 space-y-1">
        {items.map((it) => {
          const Icon = it.icon;
          const active = current === it.key;
          return (
            <button
              key={it.key}
              onClick={() => onChange(it.key)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active ? "bg-primary text-primary-foreground" : "hover:bg-accent text-foreground/80",
              )}
            >
              <Icon className="w-4 h-4" />
              {it.label}
            </button>
          );
        })}
      </nav>
      <div className="p-4 border-t text-xs text-muted-foreground">
        <div className="flex justify-between"><span>Provider</span><span className="capitalize">{provider}</span></div>
        <div className="mt-2 flex justify-between"><span>单 run 上限</span><span>{budgetK}K tokens</span></div>
        <div className="mt-2">实时用量以运行页累计 token 为准</div>
      </div>
    </aside>
  );
}
