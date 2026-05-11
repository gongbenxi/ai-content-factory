import { useState } from "react";
import { Sidebar, type PageKey } from "./components/Sidebar";
import { Dashboard } from "./components/Dashboard";
import { NewRun } from "./components/NewRun";
import { RunLive } from "./components/RunLive";
import { ArticleEditor } from "./components/ArticleEditor";
import { StyleManager } from "./components/StyleManager";
import { Settings } from "./components/Settings";

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [seedTitle, setSeedTitle] = useState<string | undefined>();
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRunSnapshot, setActiveRunSnapshot] = useState<any>(null);
  const [dark, setDark] = useState(true);

  return (
    <div className={`size-full flex bg-background text-foreground ${dark ? "dark" : ""}`}>
      <Sidebar current={page} onChange={setPage} dark={dark} onToggleDark={() => setDark((d) => !d)} />
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {page === "dashboard" && (
          <Dashboard
            onStartRun={(t) => { setSeedTitle(t); setPage("new-run"); }}
            onOpenArticle={(runId) => { if (runId) setActiveRunId(runId); setActiveRunSnapshot(null); setPage("editor"); }}
          />
        )}
        {page === "new-run" && (
          <NewRun
            initialTitle={seedTitle}
            onLaunch={(runId, snapshot) => { setActiveRunId(runId); setActiveRunSnapshot(snapshot || null); setPage("run-live"); }}
          />
        )}
        {page === "run-live" && (
          <RunLive runId={activeRunId} initialRun={activeRunSnapshot} onDone={() => setPage("editor")} />
        )}
        {page === "editor" && (
          <ArticleEditor runId={activeRunId} onBack={() => setPage("dashboard")} />
        )}
        {page === "styles" && <StyleManager />}
        {page === "settings" && <Settings />}
      </main>
    </div>
  );
}
