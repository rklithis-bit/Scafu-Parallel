(() => {
  const userList = document.querySelector("#user-list");
  const userCount = document.querySelector("#user-count");
  const emptyState = document.querySelector("#empty-state");
  const view = document.querySelector("#conversation-view");
  const peerName = document.querySelector("#peer-name");
  const peerAvatar = document.querySelector("#peer-avatar");
  const messages = document.querySelector("#messages");
  const form = document.querySelector("#message-form");
  const messageInput = document.querySelector("#message");
  const imageInput = document.querySelector("#image");
  const preview = document.querySelector("#image-preview");
  let peer = null;
  let refreshTimer = null;

  async function api(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed.");
    return data;
  }
  function showError(text) {
    let el = document.querySelector("#chat-error");
    if (!el) {
      el = document.createElement("p"); el.id = "chat-error"; el.className = "notice chat-error";
      form.before(el);
    }
    el.textContent = text;
    setTimeout(() => el.remove(), 5000);
  }
  async function loadUsers() {
    try {
      const data = await api("/api/users");
      userCount.textContent = data.users.length;
      userList.replaceChildren();
      if (!data.users.length) {
        const p = document.createElement("p"); p.className = "muted small";
        p.textContent = "No one here yet. Ask your person to create an account.";
        userList.append(p); return;
      }
      data.users.forEach(name => {
        const b = document.createElement("button");
        b.className = "user-item" + (name === peer ? " selected" : "");
        const av = document.createElement("span"); av.className = "avatar small-avatar"; av.textContent = name.slice(0,1).toUpperCase();
        const details = document.createElement("span"); details.className = "user-details";
        const title = document.createElement("strong"); title.textContent = name;
        const sub = document.createElement("small"); sub.textContent = "Private chat";
        details.append(title, sub); b.append(av, details);
        b.addEventListener("click", () => selectPeer(name)); userList.append(b);
      });
    } catch (e) { showError(e.message); }
  }
  async function selectPeer(name) {
    peer = name; emptyState.classList.add("hidden"); view.classList.remove("hidden");
    peerName.textContent = name; peerAvatar.textContent = name.slice(0,1).toUpperCase();
    await loadUsers(); await loadMessages();
    clearInterval(refreshTimer); refreshTimer = setInterval(loadMessages, 3000);
    messageInput.focus();
  }
  function addMessage(item) {
    const bubble = document.createElement("article");
    bubble.className = "message " + (item.mine ? "mine" : "theirs");
    if (!item.mine) {
      const sender = document.createElement("div"); sender.className = "message-sender"; sender.textContent = item.sender; bubble.append(sender);
    }
    if (item.body) {
      const body = document.createElement("p"); body.className = "message-body"; body.textContent = item.body; bubble.append(body);
    }
    if (item.image) {
      const img = document.createElement("img"); img.className = "message-image"; img.src = item.image; img.alt = "Shared image"; img.loading = "lazy";
      img.addEventListener("click", () => window.open(img.src, "_blank", "noopener")); bubble.append(img);
    }
    const time = document.createElement("time"); time.className = "message-time"; time.textContent = item.time; bubble.append(time);
    messages.append(bubble);
  }
  async function loadMessages() {
    if (!peer) return;
    try {
      const data = await api(`/api/messages?with=${encodeURIComponent(peer)}`);
      const signature = data.messages.map(m => m.id).join(",");
      if (messages.dataset.signature === signature) return;
      const nearBottom = messages.scrollHeight - messages.scrollTop - messages.clientHeight < 100;
      messages.replaceChildren(); data.messages.forEach(addMessage); messages.dataset.signature = signature;
      if (nearBottom) messages.scrollTop = messages.scrollHeight;
    } catch (e) { if (e.message !== "Please sign in again.") showError(e.message); else location.href = "/"; }
  }
  imageInput.addEventListener("change", () => {
    preview.replaceChildren();
    const file = imageInput.files[0];
    if (!file) { preview.classList.add("hidden"); return; }
    if (file.size > 10 * 1024 * 1024) {
      imageInput.value = ""; showError("Image is too large. Maximum size is 10 MB."); preview.classList.add("hidden"); return;
    }
    const img = document.createElement("img"); img.src = URL.createObjectURL(file); img.alt = "Image preview";
    const name = document.createElement("span"); name.textContent = file.name;
    const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "×";
    remove.addEventListener("click", () => { imageInput.value = ""; preview.classList.add("hidden"); });
    preview.append(img, name, remove); preview.classList.remove("hidden");
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!peer) return;
    const body = messageInput.value.trim();
    if (!body && !imageInput.files[0]) return;
    const button = form.querySelector(".send-button"); button.disabled = true;
    const data = new FormData(); data.append("to", peer); data.append("message", body);
    if (imageInput.files[0]) data.append("image", imageInput.files[0]);
    try {
      await api("/api/messages", {method: "POST", body: data});
      messageInput.value = ""; imageInput.value = ""; preview.classList.add("hidden");
      await loadMessages(); messages.scrollTop = messages.scrollHeight;
    } catch (e) { showError(e.message); }
    finally { button.disabled = false; messageInput.focus(); }
  });
  messageInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  loadUsers();
})();
