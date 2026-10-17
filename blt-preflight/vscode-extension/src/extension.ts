import * as vscode from "vscode";

const COL = vscode.window.createOutputChannel("BLT Preflight");

function severity(s: string): vscode.DiagnosticSeverity {
  if (s === "CRITICAL" || s === "HIGH") return vscode.DiagnosticSeverity.Error;
  if (s === "MEDIUM") return vscode.DiagnosticSeverity.Warning;
  return vscode.DiagnosticSeverity.Information;
}

export function activate(ctx: vscode.ExtensionContext) {
  const diags = vscode.languages.createDiagnosticCollection("blt-preflight");
  const bar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  bar.text = "Preflight: checking";
  bar.show();

  async function run(doc: vscode.TextDocument) {
    if (doc.uri.scheme !== "file") return;
    const url =
      vscode.workspace.getConfiguration("preflight").get<string>("serverUrl") ??
      "http://127.0.0.1:8000";
    const rel = vscode.workspace.asRelativePath(doc.uri);
    const ANALYZE_TIMEOUT_MS = 4000;
    const ac = new  AbortController()
    const timer = setTimeout(() => ac.abort(), ANALYZE_TIMEOUT_MS);
    try {
      const res = await fetch(`${url.replace(/\/$/, "")}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ changed_files: [rel], source: "vscode" }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const adv = (await res.json()) as {
        severity: string;
        title: string;
        explanation: string;
        owasp_category?: string;
      };
      bar.text = "Preflight: connected";
      const d = new vscode.Diagnostic(
        new vscode.Range(0, 0, 0, 1),
        `${adv.severity} ${adv.owasp_category ?? ""} — ${adv.title}. ${adv.explanation}`,
        severity(adv.severity),
      );
      d.source = "BLT Preflight";
      diags.set(doc.uri, [d]);
    } catch (e) {
      bar.text = "Preflight: server not running";
      diags.delete(doc.uri);
      COL.appendLine(String(e));
    } finally {
      clearTimeout(timer);
  }

  ctx.subscriptions.push(
    diags,
    bar,
    vscode.workspace.onDidSaveTextDocument((d) => {
      void run(d);
    }),
  );
}

export function deactivate() {}
}