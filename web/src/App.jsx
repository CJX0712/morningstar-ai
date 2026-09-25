import React, { useEffect, useRef, useState } from "react";

const API = "/api";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [docText, setDocText] = useState("");
  const [backend, setBackend] = useState("检测中…");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setBackend(`${d.status} · ${d.backend} · 文档 ${d.docs}`))
      .catch(() => setBackend("未连接（请先启动 rag-api）"));
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  }

  async function ingest() {
    if (!docText.trim()) return showToast("请先粘贴知识文本");
    setBusy(true);
    try {
      const res = await fetch(`${API}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: docText, source: "web" }),
      });
      const d = await res.json();
      showToast(`已入库 ${d.ingested_chunks} 段`);
      setDocText("");
    } catch (e) {
      showToast("入库失败：" + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setDocText((prev) => prev + "\n" + text);
    showToast(`已读取 ${file.name}`);
  }

  async function send() {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setBusy(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, stream: true }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.slice(5).trim();
          if (payload === "[DONE]") continue;
          try {
            const { token } = JSON.parse(payload);
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1].content += token;
              return copy;
            });
          } catch {
            /* ignore malformed */
          }
        }
      }
    } catch (e) {
      showToast("对话失败：" + e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>✦ MorningStar AI</h1>
        <p className="sub">端到端 RAG + Agent 平台</p>
        <div className="status">后端：{backend}</div>

        <label className="label">知识库入库</label>
        <textarea
          placeholder="粘贴文档 / 笔记文本，或选择文件…"
          value={docText}
          onChange={(e) => setDocText(e.target.value)}
        />
        <div className="row">
          <button onClick={ingest} disabled={busy}>入库</button>
          <label className="filebtn">
            选择文件
            <input type="file" accept=".txt,.md,.json" onChange={uploadFile} hidden />
          </label>
        </div>
      </aside>

      <main className="chat">
        <div className="messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty">先入库知识，再开始提问。</div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="role">{m.role === "user" ? "你" : "晨星"}</div>
              <div className="content">{m.content || "…"}</div>
            </div>
          ))}
        </div>
        <div className="composer">
          <input
            placeholder="输入问题，回车发送"
            value={input}
            disabled={busy}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button onClick={send} disabled={busy || !input.trim()}>发送</button>
        </div>
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
