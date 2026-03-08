/* ═══════════════════════════════════════════════════════════════════════════
   NexusAI – Frontend Logic
   ═══════════════════════════════════════════════════════════════════════════ */

const $ = (sel) => document.querySelector(sel);
const chatContainer = $("#chat-container");
const messagesEl = $("#messages");
const welcomeEl = $("#welcome");
const form = $("#chat-form");
const input = $("#user-input");
const sendBtn = $("#send-btn");
const newChatBtn = $("#new-chat-btn");
const sidebarToggle = $("#sidebar-toggle");
const sidebar = $("#sidebar");

let isProcessing = false;

// ── Auto-resize textarea ──────────────────────────────────────────────────
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
  sendBtn.disabled = !input.value.trim() || isProcessing;
});

// ── Send on Enter (Shift+Enter for newline) ───────────────────────────────
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (input.value.trim() && !isProcessing) form.dispatchEvent(new Event("submit"));
  }
});

// ── Form submit ───────────────────────────────────────────────────────────
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || isProcessing) return;

  isProcessing = true;

  // Hide welcome, show messages
  if (welcomeEl) welcomeEl.style.display = "none";

  appendMessage("user", text);
  input.value = "";
  input.style.height = "auto";
  sendBtn.disabled = true;

  // Detect if it's likely an image request (for loading UX)
  const isImage = isImageRequest(text);

  // Show loading indicator (with shimmer for images)
  const loadingEl = appendLoading(isImage);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    loadingEl.remove();

    const agent = data.agent || null;
    if (data.type === "image") {
      appendImage(data.content, data.caption, agent);
    } else if (data.type === "error") {
      appendMessage("ai", data.content, true, agent);
    } else {
      appendMessage("ai", data.content, false, agent);
    }
  } catch (err) {
    loadingEl.remove();
    appendMessage(
      "ai",
      "Failed to reach the server. Is app.py running?",
      true
    );
  } finally {
    isProcessing = false;
    sendBtn.disabled = !input.value.trim();
  }
});

// ── Welcome card shortcuts ────────────────────────────────────────────────
document.querySelectorAll(".welcome-card").forEach((card) => {
  card.addEventListener("click", () => {
    input.value = card.dataset.prompt;
    input.dispatchEvent(new Event("input"));
    input.focus();
  });
});

// ── New chat ──────────────────────────────────────────────────────────────
newChatBtn.addEventListener("click", () => {
  messagesEl.innerHTML = "";
  if (welcomeEl) welcomeEl.style.display = "flex";
  input.focus();
});

// ── Sidebar toggle (mobile) ──────────────────────────────────────────────
sidebarToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  sidebar.classList.toggle("open");
});

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
  if (
    sidebar.classList.contains("open") &&
    !sidebar.contains(e.target) &&
    e.target !== sidebarToggle
  ) {
    sidebar.classList.remove("open");
  }
});

// ── Image keyword check (mirror of backend) ──────────────────────────────
const IMAGE_KEYWORDS = [
  "draw", "generate image", "create image", "picture",
  "art", "illustration", "paint", "sketch", "make an image",
  "generate a picture", "create a picture", "render",
  "design", "visualize", "depict", "imagine an image",
  "show me", "create art",
];

function isImageRequest(text) {
  const lower = text.toLowerCase();
  return IMAGE_KEYWORDS.some((kw) => lower.includes(kw));
}

// ── DOM helpers ───────────────────────────────────────────────────────────

function appendMessage(role, text, isError = false, agent = null) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatarLabel = role === "user" ? "Y" : "✦";
  const roleName = role === "user" ? "You" : "NexusAI";
  const agentBadge = (role === "ai" && agent && agent !== "supervisor")
    ? `<span class="agent-badge">${formatAgentName(agent)}</span>`
    : "";

  const contentHtml = isError
    ? escapeHtml(text)
    : renderMarkdown(text);

  msg.innerHTML = `
    <div class="msg-avatar">${avatarLabel}</div>
    <div class="msg-body">
      <div class="msg-role">${roleName}${agentBadge}</div>
      <div class="msg-content${isError ? " error" : ""}">${contentHtml}</div>
    </div>`;

  messagesEl.appendChild(msg);
  scrollToBottom();
}

function appendImage(src, caption, agent = null) {
  const msg = document.createElement("div");
  msg.className = "msg ai";

  const agentBadge = agent
    ? `<span class="agent-badge">${formatAgentName(agent)}</span>`
    : "";

  msg.innerHTML = `
    <div class="msg-avatar">✦</div>
    <div class="msg-body">
      <div class="msg-role">NexusAI${agentBadge}</div>
      <div class="msg-content">
        <img src="${src}" alt="Generated image" />
        ${caption ? `<span class="caption">${caption}</span>` : ""}
      </div>
    </div>`;

  messagesEl.appendChild(msg);

  // Scroll after image loads
  const img = msg.querySelector("img");
  img.onload = scrollToBottom;

  // Click-to-zoom lightbox
  img.addEventListener("click", () => openLightbox(src));

  scrollToBottom();
}

function appendLoading(isImage = false) {
  const msg = document.createElement("div");
  msg.className = "msg ai";

  const loadingContent = isImage
    ? `<div class="loading-dots"><span></span><span></span><span></span></div>
       <div class="thinking-bar"></div>
       <span style="font-size:12px;color:var(--text-muted);margin-top:4px;display:block;">Generating image…</span>`
    : `<div class="loading-dots"><span></span><span></span><span></span></div>`;

  msg.innerHTML = `
    <div class="msg-avatar">✦</div>
    <div class="msg-body">
      <div class="msg-role">NexusAI</div>
      <div class="msg-content">${loadingContent}</div>
    </div>`;

  messagesEl.appendChild(msg);
  scrollToBottom();
  return msg;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  });
}

// ── Simple Markdown → HTML renderer ──────────────────────────────────────
function renderMarkdown(text) {
  let html = escapeHtml(text);

  // Code blocks: ```...```
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code: `...`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold: **...**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic: *...*
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");

  // Line breaks
  html = html.replace(/\n/g, "<br>");

  return html;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatAgentName(name) {
  const icons = {
    prompt_engineer: "✏️",
    image_director: "🎨",
    research: "🔍",
    content_writer: "📝",
    workflow_planner: "📋",
    supervisor: "🧠",
  };
  const icon = icons[name] || "🤖";
  const label = name.replace(/_/g, " ");
  return `${icon} ${label}`;
}

// ── Lightbox ──────────────────────────────────────────────────────────────
function openLightbox(src) {
  const overlay = document.createElement("div");
  overlay.className = "lightbox-overlay";
  overlay.innerHTML = `<img src="${src}" alt="Full-size image" />`;
  overlay.addEventListener("click", () => overlay.remove());
  document.body.appendChild(overlay);

  // Close on Escape
  const handleEsc = (e) => {
    if (e.key === "Escape") {
      overlay.remove();
      document.removeEventListener("keydown", handleEsc);
    }
  };
  document.addEventListener("keydown", handleEsc);
}

// ── Focus input on load ──────────────────────────────────────────────────
input.focus();
