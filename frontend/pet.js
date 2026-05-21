// ===== Elements =====
const svgWrap = document.getElementById("svgWrap");
const bubble = document.getElementById("bubble");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const ctxMenu = document.getElementById("contextMenu");
const BACKEND_URL = "http://127.0.0.1:5000";

// ===== State Machine =====
let currentState = "idle";
let idleTimer = null;
let sleepTimer = null;
let bubbleTimer = null;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragPetOffset = 0;
let wasDragged = false;

// Drag throttling: avoid high-frequency IPC + setPosition jitter.
let dragRaf = null;
let latestDragScreenX = 0;
let latestDragScreenY = 0;

const BUBBLE_PHRASES = [
  "你终于来了？也太慢了吧。",
  "别发呆，快做正事。",
  "哼，我才不是在等你。",
  "今天也要认真一点。",
  "喂，别把我晾在这儿。",
  "完成了？还不错嘛。"
];

// ===== Init: Fetch and inline SVG =====
fetch("./assets/pet.svg")
  .then(r => r.text())
  .then(svgContent => {
    svgWrap.innerHTML = svgContent;
    svgWrap.classList.add("state-idle");
    startIdleTimer();
  })
  .catch(() => {
    svgWrap.textContent = "(>_<)";
    svgWrap.style.fontSize = "80px";
    svgWrap.style.textAlign = "center";
    svgWrap.style.paddingTop = "60px";
    svgWrap.classList.add("state-idle");
    startIdleTimer();
  });

// ===== State Management =====
function setPetState(state) {
  svgWrap.className = "";
  svgWrap.classList.add("state-" + state);
  currentState = state;

  document.querySelector(".zzz").classList.toggle("visible", state === "sleep");

  if (state === "sleep") {
    showBubble("Zzz...");
  }

  if (state !== "walk" && state !== "sleep") {
    resetIdleTimer();
  }
}

// ===== Idle / Sleep Timer =====
function startIdleTimer() {
  resetIdleTimer();
}

function resetIdleTimer() {
  clearTimeout(idleTimer);
  clearTimeout(sleepTimer);

  if (currentState === "sleep") {
    setPetState("idle");
  }

  sleepTimer = setTimeout(() => {
    if (currentState === "idle") {
      setPetState("sleep");
    }
  }, 45000);
}

// ===== Bubble =====
function showBubble(text) {
  bubble.textContent = text;
  bubble.classList.add("show");

  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => {
    bubble.classList.remove("show");
  }, 4000);
}

function showRandomBubble() {
  const text = BUBBLE_PHRASES[Math.floor(Math.random() * BUBBLE_PHRASES.length)];
  showBubble(text);
}

// ===== Drag System =====
svgWrap.addEventListener("mousedown", (e) => {
  if (e.button !== 0) return;

  e.preventDefault();

  isDragging = true;
  wasDragged = false;

  // Use screen coordinates. clientX/clientY changes when the Electron window moves.
  dragStartX = e.screenX;
  dragStartY = e.screenY;
  latestDragScreenX = e.screenX;
  latestDragScreenY = e.screenY;

  dragPetOffset = Math.round(svgWrap.getBoundingClientRect().top);

  clearTimeout(idleTimer);
  clearTimeout(sleepTimer);

  document.body.classList.add("is-dragging");
  setPetState("walk");

  if (window.electronAPI?.dragWindowStart) {
    window.electronAPI.dragWindowStart(e.screenX, e.screenY, dragPetOffset);
  }
});

document.addEventListener("mousemove", (e) => {
  if (!isDragging) return;

  e.preventDefault();

  latestDragScreenX = e.screenX;
  latestDragScreenY = e.screenY;

  if (Math.abs(e.screenX - dragStartX) > 3 || Math.abs(e.screenY - dragStartY) > 3) {
    wasDragged = true;
  }

  if (dragRaf) return;

  dragRaf = requestAnimationFrame(() => {
    dragRaf = null;

    if (window.electronAPI?.dragWindowMove) {
      window.electronAPI.dragWindowMove(latestDragScreenX, latestDragScreenY);
    }
  });
});

function finishDrag() {
  if (!isDragging) return;

  isDragging = false;

  if (dragRaf) {
    cancelAnimationFrame(dragRaf);
    dragRaf = null;
  }

  document.body.classList.remove("is-dragging");

  if (window.electronAPI?.dragWindowEnd) {
    window.electronAPI.dragWindowEnd();
  }

  setPetState("idle");
}

document.addEventListener("mouseup", finishDrag);
window.addEventListener("blur", finishDrag);

// ===== Click -> Reaction =====
svgWrap.addEventListener("click", (e) => {
  if (isDragging || wasDragged) {
    wasDragged = false;
    return;
  }

  setPetState("happy");
  showRandomBubble();

  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => setPetState("idle"), 2500);
  clearTimeout(sleepTimer);
});

// ===== Right-Click Context Menu =====
svgWrap.addEventListener("contextmenu", (e) => {
  e.preventDefault();

  const mx = Math.min(e.clientX, window.innerWidth - 140);
  const my = Math.min(e.clientY, window.innerHeight - 220);

  ctxMenu.style.left = mx + "px";
  ctxMenu.style.top = my + "px";
  ctxMenu.classList.add("show");
});

document.addEventListener("click", (e) => {
  if (!ctxMenu.contains(e.target) && !svgWrap.contains(e.target)) {
    ctxMenu.classList.remove("show");
  }
});

// Menu action handlers
ctxMenu.addEventListener("click", (e) => {
  const item = e.target.closest(".menu-item");
  if (!item) return;

  const action = item.dataset.action;
  ctxMenu.classList.remove("show");

  switch (action) {
    case "feed":
      showBubble("哼……还算合格。");
      setPetState("happy");
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => setPetState("idle"), 2500);
      break;

    case "talk":
      showRandomBubble();
      setPetState("talking");
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => setPetState("idle"), 2000);
      break;

    case "settings":
      showBubble("设置还没做好，别催。");
      break;

    case "quit":
      if (window.electronAPI?.closeWindow) {
        window.electronAPI.closeWindow();
      }
      break;
  }
});

// ===== Chat with Backend =====
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  showBubble("等一下，我在想。");
  setPetState("idle");
  userInput.value = "";

  try {
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) {
      showBubble("网络断了？真麻烦。");
      return;
    }

    const data = await res.json();
    showBubble(data.reply);
    setPetState(data.emotion || "talking");
    resetIdleTimer();

    if (data.audio_url) {
      setPetState("talking");
      const audio = new Audio(data.audio_url);
      audio.play();
      audio.onended = () => setPetState("idle");
    }
  } catch (err) {
    showBubble("网络断了？真麻烦。");
  }
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

// ===== Pomodoro exposed for HTML onclick =====
let pomodoroTimer = null;
window.startPomodoro = function (minutes) {
  if (pomodoroTimer) clearTimeout(pomodoroTimer);

  showBubble(`行，我盯你 ${minutes} 分钟。别摸鱼。`);
  setPetState("talking");

  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => setPetState("idle"), 2000);

  pomodoroTimer = setTimeout(() => {
    showBubble("时间到！你居然真的坚持下来了，可以啊。");
    setPetState("happy");
    pomodoroTimer = null;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => setPetState("idle"), 2500);
  }, minutes * 60 * 1000);
};

// ===== Keyboard shortcut to show bubble =====
document.addEventListener("keydown", (e) => {
  if (e.altKey && e.key === "r") {
    e.preventDefault();
    showRandomBubble();
    setPetState("talking");
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => setPetState("idle"), 2000);
  }
});

// ===== Wake on mouse move while sleeping =====
document.addEventListener("mousemove", (e) => {
  if (currentState === "sleep" && !isDragging) {
    const rect = svgWrap.getBoundingClientRect();
    if (
      e.clientX >= rect.left - 30 &&
      e.clientX <= rect.right + 30 &&
      e.clientY >= rect.top - 30 &&
      e.clientY <= rect.bottom + 30
    ) {
      setPetState("idle");
    }
  }
});