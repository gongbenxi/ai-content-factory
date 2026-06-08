import { useEffect, useState } from "react";
import { Sidebar, type PageKey } from "./components/Sidebar";
import { Dashboard } from "./components/Dashboard";
import { NewRun } from "./components/NewRun";
import { RunLive } from "./components/RunLive";
import { ArticleEditor } from "./components/ArticleEditor";
import { StyleManager } from "./components/StyleManager";
import { Settings } from "./components/Settings";
import { getRun, listRuns } from "../lib/api";

const STORAGE_KEY = "acf:ui-state:v1";

type StoredUiState = {
  page?: PageKey;
  activeRunId?: string | null;
  dark?: boolean;
};

function readStoredState(): StoredUiState {
  try {
    if (typeof window === "undefined") return {};
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function persistStoredState(state: StoredUiState) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage failures; the in-memory UI state still works.
  }
}

function validPage(page: unknown): PageKey {
  const pages: PageKey[] = ["dashboard", "new-run", "run-live", "editor", "styles", "settings"];
  return pages.includes(page as PageKey) ? page as PageKey : "dashboard";
}

export default function App() {
  const stored = readStoredState();
  const [page, setPage] = useState<PageKey>(() => validPage(stored.page));
  const [seedTitle, setSeedTitle] = useState<string | undefined>();
  const [activeRunId, setActiveRunId] = useState<string | null>(() => stored.activeRunId || null);
  const [activeRunSnapshot, setActiveRunSnapshot] = useState<any>(null);
  const [dark, setDark] = useState(() => stored.dark ?? true);

  function commitUiState(next: Partial<StoredUiState>) {
    const merged = { page, activeRunId, dark, ...next };
    if (next.page !== undefined) setPage(next.page);
    if (Object.prototype.hasOwnProperty.call(next, "activeRunId")) {
      setActiveRunId(next.activeRunId || null);
    }
    if (next.dark !== undefined) setDark(next.dark);
    persistStoredState(merged);
  }

  useEffect(() => {
    persistStoredState({ page, activeRunId, dark });
  }, [page, activeRunId, dark]);

  useEffect(() => {
    let cancelled = false;

    async function restoreActiveRun() {
      if (activeRunId) {
        try {
          const run = await getRun(activeRunId);
          if (cancelled) return;
          if (run && run.status !== "unknown") return;
        } catch {
          if (cancelled) return;
        }
      }

      try {
        const res = await listRuns(undefined, 1);
        if (cancelled) return;
        const latest = res.runs?.[0];
        const latestId = latest?.id || latest?.run_id || null;

        if (latestId) {
          commitUiState({ activeRunId: latestId });
          return;
        }

        if (page === "run-live" || page === "editor") {
          commitUiState({ page: "dashboard", activeRunId: null });
        }
      } catch {
        // Keep the current screen if the API is temporarily unavailable.
      }
    }

    restoreActiveRun();
    return () => {
      cancelled = true;
    };
  }, []);

  function goPage(next: PageKey) {
    if ((next === "run-live" || next === "editor") && !activeRunId) {
      listRuns(undefined, 1).then((res) => {
        const latest = res.runs?.[0];
        const latestId = latest?.id || latest?.run_id || null;
        commitUiState({ page: next, activeRunId: latestId });
      }).catch(() => commitUiState({ page: next }));
      return;
    }
    commitUiState({ page: next });
  }

  return (
    <div className={`size-full flex bg-background text-foreground ${dark ? "dark" : ""}`}>
      <Sidebar current={page} onChange={goPage} dark={dark} onToggleDark={() => commitUiState({ dark: !dark })} />
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {page === "dashboard" && (
          <Dashboard
            onStartRun={(t) => { setSeedTitle(t); commitUiState({ page: "new-run" }); }}
            onOpenArticle={(runId, status, words) => {
              if (!runId) return;
              setActiveRunSnapshot(null);
              // 仍在生成且尚无正文 → 看实时进度；否则（已完成 / 已有正文）→ 进编辑器
              const inProgressStatuses = ["drafting", "reviewing", "queued", "paused"];
              const inProgress = inProgressStatuses.includes(status || "") && !((words || 0) > 0);
              commitUiState({ activeRunId: runId, page: inProgress ? "run-live" : "editor" });
            }}
          />
        )}
        {page === "new-run" && (
          <NewRun
            initialTitle={seedTitle}
            onLaunch={(runId, snapshot) => { setActiveRunSnapshot(snapshot || null); commitUiState({ activeRunId: runId, page: "run-live" }); }}
          />
        )}
        {page === "run-live" && (
          <RunLive runId={activeRunId} initialRun={activeRunSnapshot} onDone={() => commitUiState({ page: "editor" })} />
        )}
        {page === "editor" && (
          <ArticleEditor runId={activeRunId} onBack={() => commitUiState({ page: "dashboard" })} />
        )}
        {page === "styles" && <StyleManager />}
        {page === "settings" && <Settings />}
      </main>
    </div>
  );
}
