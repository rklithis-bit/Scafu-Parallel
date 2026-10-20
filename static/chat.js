(() => {
  const app = document.querySelector("#scafu-app");
  const privateAllowed = app.dataset.privateAllowed === "true";
  const username = app.dataset.username || "";
  const messages = document.querySelector("#messages");
  const form = document.querySelector("#message-form");
  const messageInput = document.querySelector("#message");
  const imageInput = document.querySelector("#image");
  const preview = document.querySelector("#image-preview");
  const errorBox = document.querySelector("#chat-error");
  const emptyNote = document.querySelector("#empty-note");
  const title = document.querySelector("#room-title");
  const subtitle = document.querySelector("#room-subtitle");
  const avatar = document.querySelector("#room-avatar");
  const label = document.querySelector("#room-label");
  const tabs = [...document.querySelectorAll(".room-tab")];
  let room = "community";
  let peer = null;
  let refreshTimer = null;
  let errorTimer = null;

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Request failed.");
    return data;
  }
  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
    clearTimeout(errorTimer);
    errorTimer = setTimeout(() => errorBox.classList.add("hidden"), 5000);
  }
  function configureRoom() {
    tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.room === room));
    const isPrivate = room === "private";
    title.textContent = isPrivate ? (peer || "Private chat") : "Community";
    subtitle.textContent = isPrivate ? "Only the two authorized accounts" : "Everyone signed in can join";
    avatar.textContent = isPrivate ? "♡" : "C";
    label.textContent = isPrivate ? "PRIVATE" : "GROUP";
    messageInput.placeholder = isPrivate ? "Write a private message…" : "Message the community…";
    emptyNote.classList.add("hidden");
    if (isPrivate && !peer) {
      emptyNote.textContent = "Private chat is available only to lichu@scafu.app and ammu@scafu.app. Both accounts must have registered before messaging.";
      emptyNote.classList.remove("hidden");
    }
  }
  async function loadPeer() {
    if (!privateAllowed) return;
    const data = await api("/api/users");
    peer = data.users.find(name => name !== username) || null;
  }
  function addMessage(item) {
    const row = document.createElement("div");
    row.className = "message-row " + (item.mine ? "mine" : "theirs");
    const bubble = document.createElement("article");
    bubble.className = "message " + (item.mine ? "mine" : "theirs");
    if (room === "community") {
      const sender = document.createElement("div");
      sender.className = "message-sender";
      sender.textContent = item.mine ? "You" : item.sender;
      bubble.append(sender);
    } else if (!item.mine) {
      const sender = document.createElement("div");
      sender.className = "message-sender";
      sender.textContent = item.sender;
      bubble.append(sender);
    }
    if (item.body) {
      const body = document.createElement("p");
      body.className = "message-body";
      body.textContent = item.body;
      bubble.append(body);
    }
    if (item.image) {
      const img = document.createElement("img");
      img.className = "message-image";
      img.src = item.image;
      img.alt = "Shared image";
      img.loading = "lazy";
      img.addEventListener("click", () => window.open(img.src, "_blank", "noopener,noreferrer"));
      bubble.append(img);
    }
    const time = document.createElement("time");
    time.className = "message-time";
    time.textContent = item.time;
    bubble.append(time);
    row.append(bubble);
    messages.append(row);
  }
  async function loadMessages() {
    if (room === "private" && (!privateAllowed || !peer)) return;
    try {
      const endpoint = room === "community"
        ? "/api/community/messages"
        : "/api/messages?with=" + encodeURIComponent(peer);
      const data = await api(endpoint);
      const signature = data.messages.map(item => item.id + ":" + (item.body || "") + ":" + (item.image || "")).join("|");
      if (messages.dataset.signature === room + ":" + signature) return;
      const nearBottom = messages.scrollHeight - messages.scrollTop - messages.clientHeight < 120;
      messages.replaceChildren();
      data.messages.forEach(addMessage);
      messages.dataset.signature = room + ":" + signature;
      if (nearBottom) messages.scrollTop = messages.scrollHeight;
      if (!data.messages.length && room === "private") {
        emptyNote.textContent = "This is the beginning of your private conversation.";
        emptyNote.classList.remove("hidden");
      } else {
        emptyNote.classList.add("hidden");
      }
    } catch (error) {
      if (error.message === "Please sign in again.") location.href = "/";
      else showError(error.message);
    }
  }
  async function switchRoom(nextRoom) {
    if (nextRoom === "private" && !privateAllowed) return;
    room = nextRoom;
    messages.replaceChildren();
    messages.dataset.signature = "";
    configureRoom();
    if (room === "private" && !peer) {
      try { await loadPeer(); } catch (error) { showError(error.message); }
      configureRoom();
    }
    await loadMessages();
    clearInterval(refreshTimer);
    refreshTimer = setInterval(loadMessages, 3000);
  }
  imageInput.addEventListener("change", () => {
    preview.replaceChildren();
    const file = imageInput.files[0];
    if (!file) { preview.classList.add("hidden"); return; }
    if (file.size > 10 * 1024 * 1024) {
      imageInput.value = "";
      showError("Image is too large. Maximum size is 10 MB.");
      preview.classList.add("hidden");
      return;
    }
    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = "Image preview";
    const filename = document.createElement("span");
    filename.textContent = file.name;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Remove attached image");
    remove.addEventListener("click", () => {
      imageInput.value = "";
      preview.classList.add("hidden");
      preview.replaceChildren();
    });
    preview.append(image, filename, remove);
    preview.classList.remove("hidden");
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const body = messageInput.value.trim();
    if (!body && !imageInput.files[0]) return;
    if (room === "private" && !peer) {
      showError("The other authorized account has not registered yet.");
      return;
    }
    const button = form.querySelector(".send-button");
    button.disabled = true;
    const data = new FormData();
    data.append("message", body);
    if (room === "private") data.append("to", peer);
    if (imageInput.files[0]) data.append("image", imageInput.files[0]);
    try {
      const endpoint = room === "community" ? "/api/community/messages" : "/api/messages";
      await api(endpoint, {method: "POST", body: data});
      messageInput.value = "";
      imageInput.value = "";
      preview.classList.add("hidden");
      preview.replaceChildren();
      messages.dataset.signature = "";
      await loadMessages();
      messages.scrollTop = messages.scrollHeight;
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
      messageInput.focus();
    }
  });
  messageInput.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  tabs.forEach(tab => tab.addEventListener("click", () => switchRoom(tab.dataset.room)));
  configureRoom();
  switchRoom("community");
})();
