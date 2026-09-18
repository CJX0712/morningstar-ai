// 晨星 AI 前端逻辑：模型切换、流式对话、工具展示、RAG 上传与问答。

const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const inputEl = $("#input");
const sendBtn = $("#send");

let providers = [];
let conversation = []; // {role, content}

// ---------- 初始化 ----------
async function init() {
  try {
    const res = await fetch("/api/providers");
    const data = await res.json();
    providers = data.providers;
    const sel = $("#provider");
    sel.innerHTML = "";
    providers.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${p.label}${p.configured ? "" : "（未配置）"} · ${p.default_model}`;
      if (p.id === data.default_provider) opt.selected = true;
      sel.appendChild(opt);
    });
    syncModel();
    refreshDocs();
  } catch (e) {
    console.error(e);
  }
}

function currentProvider() {
  return providers.find((p) => p.id === $("#provider").value) || providers[0];
}
function syncModel() {
  const p = currentProvider();
  $("#model").value = p ? p.default_model : "";
}
$("#provider").addEventListener("change", syncModel);

// ---------- 消息渲染 ----------
function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  wrap.innerHTML = `<div class="avatar">${role === "user" ? "你" : "✦"}</div><div class="bubble"></div>`;
  wrap.querySelector(".bubble").innerHTML = renderMarkdown(text || "");
  messagesEl.appendChild(wrap);
  scrollBottom();
  return wrap.querySelector(".bubble");
}
function addToolBlock(name, args, result) {
  const block = document.createElement("div");
  block.className = "tool";
  block.innerHTML = `<div class="tool-head"><span>🔧</span><span class="tool-name">${esc(name)}</span><span>调用</span></div><div class="tool-body"></div>`;
  block.querySelector(".tool-head").addEventListener("click", () => block.classList.toggle("open"));
  block.querySelector(".tool-body").textContent = `参数: ${args}\n\n结果:\n${result}`;
  messagesEl.appendChild(block);
  scrollBottom();
}
function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

// ---------- 发送 ----------
async function send() {
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  autoGrow();

  addMessage("user", text);
  conversation.push({ role: "user", content: text });

  const bubble = addMessage("assistant", "");
  bubble.classList.add("cursor");
  let acc = "";

  const payload = {
    messages: conversation,
    provider: $("#provider").value,
    model: $("#model").value || undefined,
    use_rag: $("#rag").checked,
    temperature: 0.7,
  };

  sendBtn.disabled = true;
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        raw.split("\n").forEach((line) => {
          if (!line.startsWith("data: ")) return;
          const data = line.slice(6).trim();
          if (data === "[DONE]") return;
          handleEvent(JSON.parse(data), bubble, (t) => (acc = t));
        });
      }
    }
  } catch (e) {
    acc += `\n\n[连接错误] ${e}`;
    bubble.innerHTML = renderMarkdown(acc);
  } finally {
    bubble.classList.remove("cursor");
    conversation.push({ role: "assistant", content: acc });
    sendBtn.disabled = false;
    scrollBottom();
  }
}

function handleEvent(ev, bubble, setAcc) {
  if (ev.type === "token") {
    setAcc(current => (current || "") + ev.text);
    bubble.innerHTML = renderMarkdown(bubble.__acc = (bubble.__acc || "") + ev.text);
  } else if (ev.type === "tool") {
    addToolBlock(ev.name, ev.args, ev.result);
  } else if (ev.type === "error") {
    bubble.innerHTML = renderMarkdown("⚠️ " + ev.message);
  }
}

// ---------- 文档上传 / 知识库 ----------
$("#file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  const btn = e.target.closest(".upload-btn");
  btn.textContent = "上传中…";
  try {
    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (res.ok) {
      btn.textContent = `✓ 已索引 ${data.chunks} 段`;
      refreshDocs();
    } else {
      btn.textContent = "上传失败: " + (data.detail || "");
    }
  } catch (err) {
    btn.textContent = "上传出错";
  }
  setTimeout(() => (btn.textContent = "选择文件（txt / md / pdf）"), 2500);
});

async function refreshDocs() {
  try {
    const res = await fetch("/api/documents");
    const docs = await res.json();
    const el = $("#docs");
    el.innerHTML = docs.length ? docs.map((d) => `<div class="doc">📄 ${esc(d.source)} · ${d.chunks} 段</div>`).join("") : "";
  } catch (e) {}
}

$("#clearRag").addEventListener("click", async () => {
  if (!confirm("确认清空全部知识库？")) return;
  await fetch("/api/clear_rag", { method: "POST" });
  refreshDocs();
});

$("#newChat").addEventListener("click", () => {
  conversation = [];
  messagesEl.innerHTML = "";
});

// ---------- 输入框 ----------
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
inputEl.addEventListener("input", autoGrow);
function autoGrow() { inputEl.style.height = "auto"; inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px"; }
sendBtn.addEventListener("click", send);

// ---------- 轻量 Markdown 渲染（离线安全） ----------
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function renderMarkdown(src) {
  if (!src) return "";
  const escaped = esc(src);
  const lines = escaped.split("\n");
  let html = "", i = 0, inCode = false, codeBuf = [], listType = null;
  const flushList = () => { if (listType) { html += `</${listType}>`; listType = null; } };
  while (i < lines.length) {
    let line = lines[i];
    if (line.startsWith("```")) {
      if (!inCode) { flushList(); inCode = true; codeBuf = []; i++; continue; }
      else { html += `<pre><code>${codeBuf.join("\n")}</code></pre>`; inCode = false; i++; continue; }
    }
    if (inCode) { codeBuf.push(line); i++; continue; }
    if (/^\s*$/.test(line)) { flushList(); i++; continue; }
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) { flushList(); html += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`; i++; continue; }
    if ((m = line.match(/^>\s?(.*)$/))) { flushList(); html += `<blockquote>${inline(m[1])}</blockquote>`; i++; continue; }
    if ((m = line.match(/^(\s*)[-*]\s+(.*)$/))) { if (listType !== "ul") { flushList(); html += "<ul>"; listType = "ul"; } html += `<li>${inline(m[2])}</li>`; i++; continue; }
    if ((m = line.match(/^(\s*)\d+\.\s+(.*)$/))) { if (listType !== "ol") { flushList(); html += "<ol>"; listType = "ol"; } html += `<li>${inline(m[2])}</li>`; i++; continue; }
    flushList();
    html += `<p>${inline(line)}</p>`;
    i++;
  }
  flushList();
  if (inCode) html += `<pre><code>${codeBuf.join("\n")}</code></pre>`;
  return html;
}
function inline(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+?)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

init();
