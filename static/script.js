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

// ── Auto-resize textarea ──────────────────────────────────────────────────
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
  sendBtn.disabled = !input.value.trim();
});

// ── Send on Enter (Shift+Enter for newline) ───────────────────────────────
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (input.value.trim()) form.dispatchEvent(new Event("submit"));
  }
});

// ── Form submit ───────────────────────────────────────────────────────────
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  // Hide welcome, show messages
  if (welcomeEl) welcomeEl.style.display = "none";

  appendMessage("user", text);
  input.value = "";
  input.style.height = "auto";
  sendBtn.disabled = true;

  // Show loading indicator
  const loadingEl = appendLoading();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    loadingEl.remove();

    if (data.type === "image") {
      appendImage(data.content, data.caption);
    } else if (data.type === "error") {
      appendMessage("ai", data.content, true);
    } else {
      appendMessage("ai", data.content);
    }
  } catch (err) {
    loadingEl.remove();
    appendMessage("ai", "Failed to reach the server. Is app.py running?", true);
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

/* ═══════════════════════════════════════════════════════════════════════════
   APP STARTUP
   ═══════════════════════════════════════════════════════════════════════════ */

const startupScreen = $("#startup-screen");
const appWrapper = $("#app-wrapper");
const letsGoBtn = $("#lets-go-btn");

letsGoBtn.addEventListener("click", () => {
  startupScreen.classList.add("hidden");
  appWrapper.classList.remove("hidden");
});

/* ═══════════════════════════════════════════════════════════════════════════
   TAB SWITCHING
   ═══════════════════════════════════════════════════════════════════════════ */

const tabButtons = document.querySelectorAll(".nav-tab");
const viewPanels = document.querySelectorAll(".view-panel");

const TAB_MAP = {
  "home": "home-view",
  "library": "library-view",
  "wondertv": "wondertv-view",
  "games": "games-view",
  "parental": "parental-view",
  "nexus": "nexus-view",
};

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetTab = btn.dataset.tab;

    // Toggle active tab button
    tabButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    // Toggle view panels
    viewPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === TAB_MAP[targetTab]);
    });
  });
});


/* ═══════════════════════════════════════════════════════════════════════════
   FACT FEED ENGINE
   ═══════════════════════════════════════════════════════════════════════════ */

const factGenerateBtn = $("#fact-generate-btn");
const factFeedScroll = $("#fact-feed-scroll");
const factFeedEmpty = $("#fact-feed-empty");
let factCount = 0;
let isGenerating = false;

factGenerateBtn.addEventListener("click", () => {
  if (isGenerating) return;
  generateFactBatch(3);
});

async function generateFactBatch(count) {
  isGenerating = true;
  factGenerateBtn.disabled = true;

  // Replace button text with spinner
  const originalBtnHtml = factGenerateBtn.innerHTML;
  factGenerateBtn.innerHTML = `<div class="spinner"></div> Generating...`;

  // Hide empty state
  if (factFeedEmpty) factFeedEmpty.style.display = "none";

  // Generate facts one by one (sequential because each is heavy)
  for (let i = 0; i < count; i++) {
    factCount++;
    const cardIndex = factCount;

    // Create a loading placeholder card
    const card = createLoadingCard(cardIndex, i + 1, count);
    factFeedScroll.appendChild(card);
    card.scrollIntoView({ behavior: "smooth", block: "center" });

    try {
      const res = await fetch("/fact-feed/generate", { method: "POST" });
      const data = await res.json();

      if (data.status === "success") {
        replaceWithFactCard(card, data, cardIndex);
      } else {
        replaceWithErrorCard(card, data.message || "Failed to generate fact");
      }
    } catch (err) {
      replaceWithErrorCard(card, "Server unreachable. Is the AI server running?");
    }
  }

  // Restore button
  factGenerateBtn.innerHTML = originalBtnHtml;
  factGenerateBtn.disabled = false;
  isGenerating = false;
}

function createLoadingCard(index, current, total) {
  const card = document.createElement("div");
  card.className = "fact-short-card loading";
  card.style.animationDelay = "0s";
  card.innerHTML = `
    <div class="fact-loading-inner">
      <div class="spinner"></div>
      <div style="font-size: 16px;">Generating Fact ${current}/${total}</div>
    </div>
  `;
  return card;
}

function replaceWithFactCard(card, data, index) {
  card.className = "fact-short-card";
  card.innerHTML = `
    <img class="fact-card-bg" src="${data.image}" alt="Fact background" />
    <div class="fact-card-overlay"></div>
    <div class="fact-card-content">
      <div class="fact-card-badge">✦ Mind-Blowing Fact</div>
      <div class="fact-card-text">${escapeHtml(data.fact)}</div>
      <div class="fact-card-actions">
        <button class="fact-speak-btn" title="Read aloud">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
          </svg>
          <span>Listen</span>
        </button>
        <span class="fact-card-index">#${index}</span>
      </div>
    </div>
  `;

  // Attach speak button
  const speakBtn = card.querySelector(".fact-speak-btn");
  speakBtn.addEventListener("click", () => speakText(data.fact, speakBtn));
}

function replaceWithErrorCard(card, message) {
  card.className = "fact-short-card";
  card.style.display = "flex";
  card.style.alignItems = "center";
  card.style.justifyContent = "center";
  card.innerHTML = `
    <div class="fact-loading-inner" style="color: #f87171;">
      <div style="font-size: 28px;">⚠️</div>
      <div style="padding: 0 20px; text-align: center;">${escapeHtml(message)}</div>
    </div>
  `;
}


/* ═══════════════════════════════════════════════════════════════════════════
   CHAT DOM HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

function appendMessage(role, text, isError = false) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatarLabel = role === "user" ? "Y" : "✦";
  
  // Explicit Listen button for AI responses
  const speakButtonHtml = (role === "ai" && !isError) ? 
    `<button class="speak-btn active" title="Read aloud">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
      <span>Listen</span>
    </button>` : "";

  msg.innerHTML = `
    <div class="msg-avatar">${avatarLabel}</div>
    <div class="msg-body">
      <div class="msg-role">
        <span class="role-name">${role === "user" ? "You" : "NexusAI"}</span>
        ${speakButtonHtml}
      </div>
      <div class="msg-content${isError ? " error" : ""}">${escapeHtml(text)}</div>
    </div>`;

  // Attach speak event if button exists
  const speakBtn = msg.querySelector(".speak-btn");
  if (speakBtn) {
    speakBtn.addEventListener("click", () => speakText(text, speakBtn));
  }

  messagesEl.appendChild(msg);
  scrollToBottom();
}

async function speakText(text, button) {
  try {
    button.classList.add("speaking");
    const btnSpan = button.querySelector("span");
    const originalText = btnSpan ? btnSpan.innerText : "Listen";
    if (btnSpan) btnSpan.innerText = "Speaking...";

    await fetch("/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    // Reset after some time (approx speech duration or static timeout)
    setTimeout(() => {
      button.classList.remove("speaking");
      if (btnSpan) btnSpan.innerText = originalText;
    }, 3000);
  } catch (err) {
    console.error("TTS call failed", err);
    button.classList.remove("speaking");
  }
}

function appendImage(src, caption) {
  const msg = document.createElement("div");
  msg.className = "msg ai";

  const speakButtonHtml = caption ? 
    `<button class="speak-btn caption-speak" title="Read caption">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
      <span>Listen</span>
    </button>` : "";

  msg.innerHTML = `
    <div class="msg-avatar">✦</div>
    <div class="msg-body">
      <div class="msg-role">
        NexusAI 
        ${speakButtonHtml}
      </div>
      <div class="msg-content">
        <img src="${src}" alt="Generated image" />
        ${caption ? `<span class="caption">${caption}</span>` : ""}
      </div>
    </div>`;

  // Attach speak event for caption
  const speakBtn = msg.querySelector(".speak-btn");
  if (speakBtn && caption) {
    speakBtn.addEventListener("click", () => speakText(caption, speakBtn));
  }

  messagesEl.appendChild(msg);

  // Scroll after image loads
  const img = msg.querySelector("img");
  img.onload = scrollToBottom;
  scrollToBottom();
}

function appendLoading() {
  const msg = document.createElement("div");
  msg.className = "msg ai";
  msg.innerHTML = `
    <div class="msg-avatar">✦</div>
    <div class="msg-body">
      <div class="msg-role">NexusAI</div>
      <div class="msg-content">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
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

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}


/* ═══════════════════════════════════════════════════════════════════════════
   LIBRARY ENGINE
   ═══════════════════════════════════════════════════════════════════════════ */

const libraryGenerateBtn = $("#library-generate-btn");
const libraryShelf = $("#library-shelf");
const libraryEmpty = $("#library-empty");

// In-memory store of generated books
const generatedBooks = [];
let isGeneratingBook = false;

libraryGenerateBtn.addEventListener("click", () => {
  if (isGeneratingBook) return;
  generateBook();
});

async function generateBook() {
  isGeneratingBook = true;
  libraryGenerateBtn.disabled = true;
  const originalBtnHtml = libraryGenerateBtn.innerHTML;
  libraryGenerateBtn.innerHTML = `<div class="spinner"></div> Generating Book...`;

  // Hide empty state
  if (libraryEmpty) libraryEmpty.style.display = "none";

  // Create loading placeholder on shelf
  const placeholder = document.createElement("div");
  placeholder.className = "book-cover-card loading";
  placeholder.innerHTML = `
    <div class="fact-loading-inner">
      <div class="spinner"></div>
      <div style="font-size: 11px;">Creating...</div>
      <div class="fact-loading-step">🧠 Story → 🎨 Art → 📖 Book</div>
    </div>
  `;
  libraryShelf.appendChild(placeholder);

  try {
    const res = await fetch("/library/generate", { method: "POST" });
    const data = await res.json();

    if (data.status === "success") {
      const bookIndex = generatedBooks.length;
      generatedBooks.push(data);

      // Replace placeholder with a book cover card
      placeholder.className = "book-cover-card";
      placeholder.innerHTML = `
        <img class="book-cover-img" src="${data.cover}" alt="${escapeHtml(data.title)}" />
        <div class="book-cover-label">
          ${escapeHtml(data.title)}
          <div class="book-cover-pages">${data.pages.length} pages • AI illustrated</div>
        </div>
      `;
      placeholder.addEventListener("click", () => openBook(bookIndex));
    } else {
      placeholder.className = "book-cover-card";
      placeholder.style.display = "flex";
      placeholder.style.alignItems = "center";
      placeholder.style.justifyContent = "center";
      placeholder.innerHTML = `
        <div class="fact-loading-inner" style="color: #f87171; padding: 12px;">
          <div style="font-size: 24px;">⚠️</div>
          <div style="font-size: 11px; text-align: center;">${escapeHtml(data.message || "Failed")}</div>
        </div>
      `;
    }
  } catch (err) {
    placeholder.className = "book-cover-card";
    placeholder.style.display = "flex";
    placeholder.style.alignItems = "center";
    placeholder.style.justifyContent = "center";
    placeholder.innerHTML = `
      <div class="fact-loading-inner" style="color: #f87171; padding: 12px;">
        <div style="font-size: 24px;">⚠️</div>
        <div style="font-size: 11px; text-align: center;">Server unreachable</div>
      </div>
    `;
  }

  libraryGenerateBtn.innerHTML = originalBtnHtml;
  libraryGenerateBtn.disabled = false;
  isGeneratingBook = false;
}


/* ═══════════════════════════════════════════════════════════════════════════
   BOOK READER
   ═══════════════════════════════════════════════════════════════════════════ */

const bookReaderOverlay = $("#book-reader");
const bookReaderTitle = $("#book-reader-title");
const bookReaderClose = $("#book-reader-close");
const bookPrevBtn = $("#book-prev");
const bookNextBtn = $("#book-next");
const bookPageImg = $("#book-page-img");
const bookPageText = $("#book-page-text");
const bookPageCounter = $("#book-page-counter");
const bookSpeakBtn = $("#book-speak-btn");

let currentBook = null;
let currentPage = -1; // -1 = cover page

function openBook(bookIndex) {
  const book = generatedBooks[bookIndex];
  if (!book) return;

  currentBook = book;
  currentPage = -1; // Start at cover

  bookReaderTitle.textContent = book.title;
  bookReaderOverlay.classList.add("open");
  document.body.style.overflow = "hidden";

  renderCurrentPage();
}

function closeBook() {
  bookReaderOverlay.classList.remove("open");
  document.body.style.overflow = "";
  currentBook = null;
  currentPage = -1;
}

function renderCurrentPage() {
  if (!currentBook) return;

  const totalPages = currentBook.pages.length;

  if (currentPage === -1) {
    // Cover page
    bookPageImg.innerHTML = `<img src="${currentBook.cover}" alt="Cover" />`;
    bookPageText.className = "book-page book-page-right cover-page";
    bookPageText.innerHTML = `
      ${escapeHtml(currentBook.title)}
      <div class="cover-subtitle">📖 ${totalPages} illustrated pages</div>
    `;
    bookPageCounter.textContent = "Cover";
  } else {
    // Story page
    const page = currentBook.pages[currentPage];
    bookPageImg.innerHTML = `<img src="${page.image}" alt="Page illustration" />`;
    bookPageText.className = "book-page book-page-right";
    bookPageText.innerHTML = `
      ${escapeHtml(page.text)}
      <span class="page-number">${currentPage + 1}</span>
    `;
    bookPageCounter.textContent = `Page ${currentPage + 1} of ${totalPages}`;
  }

  // Update navigation button states
  bookPrevBtn.disabled = currentPage <= -1;
  bookNextBtn.disabled = currentPage >= totalPages - 1;
}

// Navigation
bookPrevBtn.addEventListener("click", () => {
  if (currentPage > -1) {
    currentPage--;
    renderCurrentPage();
  }
});

bookNextBtn.addEventListener("click", () => {
  if (currentBook && currentPage < currentBook.pages.length - 1) {
    currentPage++;
    renderCurrentPage();
  }
});

// Close
bookReaderClose.addEventListener("click", closeBook);

// Keyboard navigation
document.addEventListener("keydown", (e) => {
  if (!bookReaderOverlay.classList.contains("open")) return;

  if (e.key === "ArrowLeft" || e.key === "a") {
    bookPrevBtn.click();
  } else if (e.key === "ArrowRight" || e.key === "d") {
    bookNextBtn.click();
  } else if (e.key === "Escape") {
    closeBook();
  }
});

// Read Aloud current page
bookSpeakBtn.addEventListener("click", () => {
  if (!currentBook) return;

  let textToRead;
  if (currentPage === -1) {
    textToRead = currentBook.title;
  } else {
    textToRead = currentBook.pages[currentPage].text;
  }

  speakText(textToRead, bookSpeakBtn);
});


/* ═══════════════════════════════════════════════════════════════════════════
   WONDERTV ENGINE
   ═══════════════════════════════════════════════════════════════════════════ */

const wtvGenerateBtn = $("#wtv-generate-btn");
const wtvFeed = $("#wtv-feed");
const wtvEmpty = $("#wtv-empty");
const wtvPlayerOverlay = $("#wtv-player");
const wtvPlayerTitle = $("#wtv-player-title");
const wtvPlayerClose = $("#wtv-player-close");
const wtvSceneImg = $("#wtv-scene-img");
const wtvSubtitle = $("#wtv-subtitle");
const wtvLoadingScreen = $("#wtv-loading-screen");
const wtvProgressFill = $("#wtv-progress-fill");
const wtvPlayBtn = $("#wtv-play-btn");
const wtvPlayIcon = $("#wtv-play-icon");
const wtvPauseIcon = $("#wtv-pause-icon");

let isGeneratingFeed = false;
let currentVideo = null;    // { title, scenes: [{narration, image}] }
let currentSceneIndex = 0;
let isVideoPlaying = false;
let videoAborted = false;

// ── Feed Generation ──────────────────────────────────────────────────────

wtvGenerateBtn.addEventListener("click", () => {
  if (isGeneratingFeed) return;
  generateWTVFeed();
});

async function generateWTVFeed() {
  isGeneratingFeed = true;
  wtvGenerateBtn.disabled = true;
  const originalHtml = wtvGenerateBtn.innerHTML;
  wtvGenerateBtn.innerHTML = `<div class="spinner"></div> Generating Feed...`;

  if (wtvEmpty) wtvEmpty.style.display = "none";

  // Create 4 loading placeholders
  const placeholders = [];
  for (let i = 0; i < 4; i++) {
    const card = document.createElement("div");
    card.className = "wtv-video-card loading";
    card.innerHTML = `
      <div class="fact-loading-inner">
        <div class="spinner"></div>
        <div style="font-size: 11px;">Loading video ${i + 1}...</div>
      </div>
    `;
    wtvFeed.appendChild(card);
    placeholders.push(card);
  }

  try {
    const res = await fetch("/wondertv/generate-feed", { method: "POST" });
    const data = await res.json();

    if (data.status === "success" && data.feed) {
      data.feed.forEach((item, i) => {
        if (placeholders[i]) {
          replaceWithVideoCard(placeholders[i], item);
        }
      });
      // Remove extra placeholders if fewer results
      for (let i = data.feed.length; i < placeholders.length; i++) {
        placeholders[i].remove();
      }
    } else {
      placeholders.forEach(p => {
        p.className = "wtv-video-card";
        p.style.minHeight = "120px";
        p.style.display = "flex";
        p.style.alignItems = "center";
        p.style.justifyContent = "center";
        p.innerHTML = `<div style="color:#f87171;padding:16px;text-align:center;font-size:12px;">⚠️ ${escapeHtml(data.message || "Failed")}</div>`;
      });
    }
  } catch (err) {
    placeholders.forEach(p => {
      p.className = "wtv-video-card";
      p.innerHTML = `<div style="color:#f87171;padding:16px;text-align:center;font-size:12px;">⚠️ Server unreachable</div>`;
    });
  }

  wtvGenerateBtn.innerHTML = originalHtml;
  wtvGenerateBtn.disabled = false;
  isGeneratingFeed = false;
}

function replaceWithVideoCard(card, item) {
  const fakeMinutes = Math.floor(Math.random() * 3) + 1;
  const fakeSeconds = String(Math.floor(Math.random() * 60)).padStart(2, "0");
  const duration = `${fakeMinutes}:${fakeSeconds}`;

  card.className = "wtv-video-card";
  card.innerHTML = `
    <div class="wtv-thumb-container">
      <img class="wtv-thumb-img" src="${item.thumbnail}" alt="${escapeHtml(item.title)}" />
      <div class="wtv-play-overlay">
        <div class="wtv-play-circle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        </div>
      </div>
      <span class="wtv-duration-badge">${duration}</span>
    </div>
    <div class="wtv-card-info">
      <div class="wtv-card-title">${escapeHtml(item.title)}</div>
      <div class="wtv-card-desc">${escapeHtml(item.description)}</div>
    </div>
  `;
  card.addEventListener("click", () => watchVideo(item.title, item.description));
}


// ── Video Player ─────────────────────────────────────────────────────────

async function watchVideo(title, description) {
  // Open the player immediately with loading state
  currentVideo = null;
  currentSceneIndex = 0;
  isVideoPlaying = false;
  videoAborted = false;

  wtvPlayerTitle.textContent = title;
  wtvPlayerOverlay.classList.add("open");
  document.body.style.overflow = "hidden";

  wtvLoadingScreen.classList.remove("hidden");
  wtvSceneImg.src = "";
  wtvSubtitle.textContent = "";
  wtvProgressFill.style.width = "0%";
  setPlayPauseIcon(false);

  try {
    // Fetch the full video content (script + scenes + images)
    const res = await fetch("/wondertv/watch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    const data = await res.json();

    if (videoAborted) return;

    if (data.status === "success" && data.scenes && data.scenes.length > 0) {
      currentVideo = data;
      wtvLoadingScreen.classList.add("hidden");
      renderScene(0);

      // Auto-play immediately
      autoPlayVideo();
    } else {
      wtvLoadingScreen.innerHTML = `
        <div style="color:#f87171;font-size:14px;">⚠️ ${escapeHtml(data.message || "Failed to generate video")}</div>
      `;
    }
  } catch (err) {
    if (!videoAborted) {
      wtvLoadingScreen.innerHTML = `
        <div style="color:#f87171;font-size:14px;">⚠️ Server unreachable</div>
      `;
    }
  }
}

function renderScene(index) {
  if (!currentVideo) return;
  const scene = currentVideo.scenes[index];
  if (!scene) return;

  currentSceneIndex = index;
  const total = currentVideo.scenes.length;

  // Crossfade: fade out, swap, fade in
  wtvSceneImg.style.transition = "opacity 0.8s ease-in-out";
  wtvSceneImg.classList.add("fade-out");
  setTimeout(() => {
    wtvSceneImg.src = scene.image;
    wtvSceneImg.classList.remove("fade-out");
  }, 800);

  wtvSubtitle.textContent = scene.narration;
  wtvProgressFill.style.width = `${((index) / total) * 100}%`;
}

async function autoPlayVideo() {
  if (!currentVideo) return;
  isVideoPlaying = true;
  setPlayPauseIcon(true);

  for (let i = currentSceneIndex; i < currentVideo.scenes.length; i++) {
    if (!isVideoPlaying || videoAborted) break;

    renderScene(i);

    // Wait a beat for the crossfade, then trigger TTS
    await sleep(500);

    if (!isVideoPlaying || videoAborted) break;

    // TTS narration — this blocks until speech finishes, giving natural pacing
    try {
      await fetch("/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: currentVideo.scenes[i].narration }),
      });
    } catch (e) {
      console.error("TTS error during playback:", e);
    }

    if (!isVideoPlaying || videoAborted) break;

    // Brief pause between scenes
    await sleep(1200);
  }

  // Video finished
  if (isVideoPlaying && !videoAborted) {
    isVideoPlaying = false;
    setPlayPauseIcon(false);
    wtvProgressFill.style.width = "100%";
    wtvSubtitle.textContent = "Thanks for watching!";
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function setPlayPauseIcon(playing) {
  wtvPlayIcon.style.display = playing ? "none" : "block";
  wtvPauseIcon.style.display = playing ? "block" : "none";
}

function closeVideoPlayer() {
  videoAborted = true;
  isVideoPlaying = false;
  wtvPlayerOverlay.classList.remove("open");
  document.body.style.overflow = "";
  currentVideo = null;
}

// Controls
wtvPlayBtn.addEventListener("click", () => {
  if (!currentVideo) return;
  if (isVideoPlaying) {
    isVideoPlaying = false;
    setPlayPauseIcon(false);
  } else {
    autoPlayVideo();
  }
});

wtvPlayerClose.addEventListener("click", closeVideoPlayer);

// Keyboard controls for video player
document.addEventListener("keydown", (e) => {
  if (!wtvPlayerOverlay.classList.contains("open")) return;

  if (e.key === "Escape") {
    closeVideoPlayer();
  } else if (e.key === " ") {
    e.preventDefault();
    wtvPlayBtn.click();
  }
});
