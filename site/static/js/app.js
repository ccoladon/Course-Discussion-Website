/* Course Chat web client: vanilla JS over the JSON API + WebSocket. */
(() => {
  const TOKEN_KEY = "coursechat_token";
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    location.replace("/login/");
    return;
  }

  const $ = (id) => document.getElementById(id);
  const state = {
    profile: null,
    sections: [],
    section: null,
    channel: null,
    ws: null,
    wsChannelId: null,
    reconnectTimer: null,
    renderedIds: new Set(),
    threadRoot: null,
    searchMode: false,
  };

  // ---------------------------------------------------------------- helpers

  function el(tag, className = "", text = null) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== null) node.textContent = text;
    return node;
  }

  function escapeText(value) {
    const node = document.createElement("div");
    node.textContent = value;
    return node.innerHTML;
  }

  function initials(name) {
    return (name || "?")
      .split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("");
  }

  const AVATAR_COLORS = [
    "bg-indigo-500",
    "bg-emerald-500",
    "bg-amber-500",
    "bg-rose-500",
    "bg-sky-500",
    "bg-violet-500",
    "bg-teal-500",
    "bg-orange-500",
  ];

  function colorFor(name) {
    let hash = 0;
    for (const char of name || "") hash = (hash * 31 + char.charCodeAt(0)) % 9973;
    return AVATAR_COLORS[hash % AVATAR_COLORS.length];
  }

  function formatTime(iso) {
    const date = new Date(iso);
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    return sameDay
      ? date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
      : date.toLocaleDateString([], { month: "short", day: "numeric" }) +
          " " +
          date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function formatError(data, fallback) {
    if (!data) return fallback;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    const first = Object.entries(data)[0];
    if (first) return `${first[0]}: ${[].concat(first[1]).join(" ")}`;
    return fallback;
  }

  function toast(message) {
    const node = el(
      "div",
      "fixed bottom-4 right-4 z-50 max-w-sm rounded-lg bg-slate-900 px-4 py-2 text-sm text-white shadow-lg"
    );
    node.textContent = message;
    document.body.appendChild(node);
    setTimeout(() => node.remove(), 4000);
  }

  async function api(path, options = {}) {
    const response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${token}`,
        ...(options.headers || {}),
      },
    });

    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      location.replace("/login/");
      throw new Error("Signed out");
    }

    const data =
      response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(formatError(data, `Request failed (${response.status})`));
      error.status = response.status;
      throw error;
    }
    return data;
  }

  // --------------------------------------------------------------- markdown

  function renderMarkdown(source) {
    const math = [];
    let text = source.replace(/\$\$([\s\S]+?)\$\$/g, (_, body) => {
      math.push({ body, display: true });
      return `@@MATH${math.length - 1}@@`;
    });
    text = text.replace(/\$([^$\n]+?)\$/g, (_, body) => {
      math.push({ body, display: false });
      return `@@MATH${math.length - 1}@@`;
    });

    let html = window.marked
      ? marked.parse(text, { breaks: true, gfm: true })
      : escapeText(text);
    if (window.DOMPurify) html = DOMPurify.sanitize(html);

    return html.replace(/@@MATH(\d+)@@/g, (_, index) => {
      const item = math[Number(index)];
      if (!item) return "";
      return item.display ? `$$${item.body}$$` : `$${item.body}$`;
    });
  }

  function renderInto(container, body) {
    container.innerHTML = renderMarkdown(body);
    if (window.renderMathInElement) {
      try {
        renderMathInElement(container, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false },
            { left: "\\[", right: "\\]", display: true },
          ],
          throwOnError: false,
        });
      } catch (error) {
        /* leave raw math if KaTeX fails */
      }
    }
  }

  // ---------------------------------------------------------------- sidebar

  function renderUser() {
    const profile = state.profile;
    $("user-name").textContent = profile.name;
    $("user-school").textContent = profile.university || "Unverified school";
    $("user-avatar").textContent = initials(profile.name);
  }

  function renderSidebar() {
    const list = $("section-list");
    list.innerHTML = "";

    state.sections.forEach((entry) => {
      const section = entry.section;
      const group = el("div", "mb-4");

      const header = el(
        "div",
        "truncate px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400"
      );
      header.textContent = section.display_name;
      header.title = section.display_name;
      group.appendChild(header);

      entry.channels.forEach((channel) => {
        const active = state.channel && state.channel.id === channel.id;
        const button = el(
          "button",
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition " +
            (active
              ? "bg-indigo-100 font-medium text-indigo-800"
              : "text-slate-600 hover:bg-slate-200/70")
        );
        button.type = "button";
        button.innerHTML = `<span class="text-slate-400">#</span><span class="truncate">${escapeText(
          channel.name
        )}</span>`;
        button.addEventListener("click", () => {
          closeSidebar();
          openChannel(entry, channel);
        });
        group.appendChild(button);
      });

      list.appendChild(group);
    });
  }

  function showEmpty() {
    $("chat-view").classList.add("hidden");
    $("search-view").classList.add("hidden");
    $("empty-state").classList.remove("hidden");
    $("empty-state").classList.add("flex");
    $("channel-title").textContent = "No course selected";
    $("channel-subtitle").textContent = "";
  }

  // ------------------------------------------------------------------ chat

  async function loadSections() {
    const data = await api("/me/sections/");
    state.sections = data.sections;
    renderSidebar();
  }

  async function openChannel(entry, channel) {
    state.section = entry;
    state.channel = channel;
    state.searchMode = false;

    $("empty-state").classList.add("hidden");
    $("search-view").classList.add("hidden");
    $("chat-view").classList.remove("hidden");
    $("channel-title").textContent = `#${channel.name}`;
    $("channel-subtitle").textContent = entry.section.display_name;
    $("composer-input").placeholder = `Message #${channel.name}`;
    $("announce-btn").classList.toggle("hidden", !entry.can_moderate);

    closeThread();
    renderSidebar();

    state.renderedIds.clear();
    $("message-list").innerHTML = "";

    try {
      await Promise.all([loadMessages(), loadPinned()]);
    } catch (error) {
      toast(error.message);
    }
    connectSocket(channel.id);
  }

  async function loadMessages() {
    const data = await api(`/channels/${state.channel.id}/messages/`);
    const list = $("message-list");
    list.innerHTML = "";
    state.renderedIds.clear();

    if (!data.results.length) {
      const empty = el(
        "p",
        "py-10 text-center text-sm text-slate-400",
        `No messages in #${state.channel.name} yet. Start the conversation.`
      );
      empty.dataset.placeholder = "1";
      list.appendChild(empty);
    } else {
      data.results.forEach((message) => appendMessage(message));
    }
    scrollToBottom(true);
  }

  async function loadPinned() {
    const banner = $("pinned-banner");
    const pinned = await api(`/channels/${state.channel.id}/pinned/`);
    banner.innerHTML = "";

    if (!pinned.length) {
      banner.classList.add("hidden");
      return;
    }

    banner.classList.remove("hidden");
    const latest = pinned[0];
    const button = el(
      "button",
      "flex w-full items-center gap-2 text-left hover:underline"
    );
    button.type = "button";
    const pin = el("span", "font-semibold", "📌 Pinned");
    const text = el(
      "span",
      "truncate",
      `${latest.author.name}: ${latest.body.replace(/\s+/g, " ").slice(0, 120)}`
    );
    button.append(pin, text);
    if (pinned.length > 1) {
      button.appendChild(el("span", "ml-auto shrink-0 opacity-70", `+${pinned.length - 1}`));
    }
    button.addEventListener("click", () => openThread(latest));
    banner.appendChild(button);
  }

  function nearBottom() {
    const scroller = $("message-scroll");
    return scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 160;
  }

  function scrollToBottom(force = false) {
    if (!force && !nearBottom()) return;
    const scroller = $("message-scroll");
    scroller.scrollTop = scroller.scrollHeight;
  }

  function badge(label, className, role) {
    const node = el(
      "span",
      `rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${className}`
    );
    node.textContent = label;
    if (role) node.dataset.badge = role;
    return node;
  }

  function actionButton(label, handler, role) {
    const button = el(
      "button",
      "rounded px-1.5 py-0.5 hover:bg-slate-200 hover:text-slate-800"
    );
    button.type = "button";
    button.textContent = label;
    if (role) button.dataset.action = role;
    button.addEventListener("click", () => handler(button));
    return button;
  }

  function buildMessage(message, { inThread = false } = {}) {
    const canModerate = Boolean(state.section && state.section.can_moderate);
    const isMine = state.profile && message.author.id === state.profile.user_id;

    const article = el(
      "article",
      "group relative flex gap-3 rounded-lg px-2 py-2 min-h-40 hover:bg-slate-50"
    );
    article.dataset.id = message.id;

    const avatar = el(
      "div",
      `flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white ${colorFor(
        message.author.name
      )}`
    );
    avatar.textContent = initials(message.author.name);

    const content = el("div", "min-w-0 flex-1");
    const meta = el("div", "flex flex-wrap items-center gap-2 text-xs");
    meta.dataset.role = "meta";
    meta.appendChild(el("span", "font-semibold text-slate-800", message.author.name));
    meta.appendChild(el("span", "text-slate-400", formatTime(message.created_at)));
    if (message.is_answer) {
      meta.appendChild(badge("Answered", "bg-emerald-100 text-emerald-700", "answer"));
    }
    if (message.is_pinned) {
      meta.appendChild(badge("Pinned", "bg-amber-100 text-amber-800", "pinned"));
    }

    const body = el("div", "markdown prose prose-sm max-w-none text-slate-700");
    if (message.deleted_at) {
      body.textContent = "[deleted]";
      body.classList.add("italic", "text-slate-400");
    } else {
      renderInto(body, message.body);
    }

    const actions = el(
      "div",
      "mt-1 hidden items-center gap-3 text-[11px] text-slate-500 group-hover:flex"
    );

    if (!message.parent && !inThread && !message.deleted_at) {
      actions.appendChild(
        actionButton(
          message.reply_count ? `Reply (${message.reply_count})` : "Reply",
          () => openThread(message),
          "reply"
        )
      );
    }

    if (!message.deleted_at && !inThread) {
      if (isMine || canModerate) {
        actions.appendChild(
          actionButton(message.is_answer ? "Unmark" : "Mark answered", (button) =>
            toggleAnswer(message, article, button)
          )
        );
      }
      if (canModerate) {
        actions.appendChild(
          actionButton("Pin", () => togglePin(message, article))
        );
      }
      if (isMine || canModerate) {
        actions.appendChild(
          actionButton("Delete", () => deleteMessage(message, article))
        );
      } else {
        actions.appendChild(actionButton("Report", () => reportMessage(message)));
      }
    }

    content.append(meta, body);
    if (actions.childElementCount) content.appendChild(actions);
    article.append(avatar, content);
    return article;
  }

  function appendMessage(message) {
    if (state.renderedIds.has(message.id)) return;
    state.renderedIds.add(message.id);
    const list = $("message-list");
    const placeholder = list.querySelector("[data-placeholder]");
    if (placeholder) placeholder.remove();
    list.appendChild(buildMessage(message));
    scrollToBottom();
  }

  async function sendMessage(body, parent = null) {
    if (!state.channel) return null;
    const payload = { body };
    if (parent) payload.parent = parent;
    const message = await api(`/channels/${state.channel.id}/messages/`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (parent) {
      if (state.threadRoot && state.threadRoot.id === parent) appendThreadReply(message);
    } else {
      appendMessage(message);
    }
    return message;
  }

  async function toggleAnswer(message, article, button) {
    try {
      const updated = await api(`/messages/${message.id}/answer/`, { method: "POST" });
      message.is_answer = updated.is_answer;
      const meta = article.querySelector('[data-role="meta"]');
      meta.querySelectorAll('[data-badge="answer"]').forEach((node) => node.remove());
      if (updated.is_answer) {
        meta.appendChild(badge("Answered", "bg-emerald-100 text-emerald-700", "answer"));
      }
      button.textContent = updated.is_answer ? "Unmark" : "Mark answered";
    } catch (error) {
      toast(error.message);
    }
  }

  async function togglePin(message, article) {
    try {
      const updated = await api(`/messages/${message.id}/pin/`, { method: "POST" });
      message.is_pinned = updated.is_pinned;
      const meta = article.querySelector('[data-role="meta"]');
      meta.querySelectorAll('[data-badge="pinned"]').forEach((node) => node.remove());
      if (updated.is_pinned) {
        meta.appendChild(badge("Pinned", "bg-amber-100 text-amber-800", "pinned"));
      }
      loadPinned();
    } catch (error) {
      toast(error.message);
    }
  }

  async function deleteMessage(message, article) {
    if (!confirm("Delete this message?")) return;
    try {
      await api(`/messages/${message.id}/`, { method: "DELETE" });
      message.deleted_at = new Date().toISOString();
      article.replaceWith(buildMessage(message));
    } catch (error) {
      toast(error.message);
    }
  }

  async function reportMessage(message) {
    const reason = prompt("What's wrong with this message?");
    if (!reason) return;
    try {
      await api("/reports/", {
        method: "POST",
        body: JSON.stringify({ message: message.id, reason }),
      });
      toast("Thanks — a moderator will review this.");
    } catch (error) {
      toast(error.message);
    }
  }

  // -------------------------------------------------------------- websocket

  function connectSocket(channelId) {
    if (state.ws) {
      state.ws.onclose = null;
      state.ws.close();
    }
    clearTimeout(state.reconnectTimer);
    state.wsChannelId = channelId;

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${protocol}://${location.host}/ws/channels/${channelId}/?token=${encodeURIComponent(
        token
      )}`
    );
    state.ws = socket;

    socket.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      if (data.type === "message") handleIncoming(data.message);
    };

    socket.onclose = () => {
      if (state.wsChannelId === channelId) {
        state.reconnectTimer = setTimeout(() => connectSocket(channelId), 2000);
      }
    };
  }

  function handleIncoming(message) {
    if (message.parent) {
      if (state.threadRoot && state.threadRoot.id === message.parent) {
        appendThreadReply(message);
      }
      const root = document.querySelector(`article[data-id="${message.parent}"]`);
      if (root) {
        const reply = root.querySelector('[data-action="reply"]');
        if (reply) {
          const match = reply.textContent.match(/\((\d+)\)/);
          const next = match ? Number(match[1]) + 1 : 1;
          reply.textContent = `Reply (${next})`;
        }
      }
      return;
    }

    if (state.channel && message.channel === state.channel.id && !state.searchMode) {
      appendMessage(message);
    }
  }

  // ----------------------------------------------------------------- thread

  async function openThread(message) {
    state.threadRoot = message;
    const panel = $("thread-panel");
    panel.classList.remove("hidden");
    panel.classList.add("flex");
    $("thread-subtitle").textContent = `#${state.channel.name}`;

    const root = $("thread-root");
    root.innerHTML = "";
    root.appendChild(buildMessage(message, { inThread: true }));

    const replies = $("thread-replies");
    replies.innerHTML = "";
    try {
      const data = await api(`/messages/${message.id}/replies/`);
      if (!data.length) {
        const empty = el(
          "p",
          "py-6 text-center text-xs text-slate-400",
          "No replies yet."
        );
        empty.dataset.placeholder = "1";
        replies.appendChild(empty);
      } else {
        data.forEach((reply) => appendThreadReply(reply));
      }
    } catch (error) {
      toast(error.message);
    }
    $("thread-input").focus();
  }

  function appendThreadReply(message) {
    const replies = $("thread-replies");
    if (replies.querySelector(`article[data-id="${message.id}"]`)) return;
    const placeholder = replies.querySelector("[data-placeholder]");
    if (placeholder) placeholder.remove();
    replies.appendChild(buildMessage(message, { inThread: true }));
    const scroller = $("thread-scroll");
    scroller.scrollTop = scroller.scrollHeight;
  }

  function closeThread() {
    state.threadRoot = null;
    const panel = $("thread-panel");
    panel.classList.add("hidden");
    panel.classList.remove("flex");
  }

  // ----------------------------------------------------------------- search

  function renderSearch(query, results) {
    state.searchMode = true;
    $("chat-view").classList.add("hidden");
    $("empty-state").classList.add("hidden");
    $("search-view").classList.remove("hidden");
    $("search-heading").textContent = `${results.length} result(s) for "${query}"`;

    const container = $("search-results");
    container.innerHTML = "";

    if (!results.length) {
      container.appendChild(
        el("p", "py-10 text-center text-sm text-slate-400", "No messages matched.")
      );
      return;
    }

    results.forEach((message) => {
      const card = el(
        "div",
        "rounded-xl border border-slate-200 bg-white p-4 hover:border-indigo-300"
      );
      const top = el("div", "flex items-center gap-2 text-xs text-slate-500");
      top.appendChild(el("span", "font-semibold text-slate-700", message.course_code));
      top.appendChild(el("span", "", `#${message.channel_name}`));
      top.appendChild(el("span", "", "·"));
      top.appendChild(el("span", "", message.author.name));
      top.appendChild(el("span", "ml-auto", formatTime(message.created_at)));

      const body = el("div", "markdown prose prose-sm mt-2 max-w-none text-slate-700");
      renderInto(body, message.body);

      const open = el(
        "button",
        "mt-2 text-xs font-medium text-indigo-600 hover:underline",
        "Open in chat"
      );
      open.type = "button";
      open.addEventListener("click", () => {
        const entry = state.sections.find((item) =>
          item.channels.some((channel) => channel.id === message.channel)
        );
        const channel = entry && entry.channels.find((item) => item.id === message.channel);
        if (entry && channel) openChannel(entry, channel);
      });

      card.append(top, body, open);
      container.appendChild(card);
    });
  }

  // ------------------------------------------------------------------ modal

  function closeModal() {
    $("modal").classList.add("hidden");
    $("modal").classList.remove("flex");
  }

  function openModal() {
    $("modal").classList.remove("hidden");
    $("modal").classList.add("flex");
  }

  function openJoinModal() {
    const card = $("modal-card");
    card.innerHTML = "";

    card.appendChild(el("h2", "text-lg font-bold", "Join a course"));
    card.appendChild(
      el(
        "p",
        "mt-1 text-sm text-slate-500",
        "Search by course code or title. Courses are grouped by school."
      )
    );

    const search = el(
      "input",
      "mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
    );
    search.placeholder = "CS101, Intro to CS…";
    const results = el("div", "mt-3 max-h-64 space-y-2 overflow-y-auto");
    card.append(search, results);

    const createHeader = el(
      "h3",
      "mt-6 border-t border-slate-200 pt-4 text-sm font-semibold text-slate-700",
      "Or create a course"
    );
    const codeInput = el(
      "input",
      "mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
    );
    codeInput.placeholder = "Course code, e.g. CS 101";
    const titleInput = el(
      "input",
      "mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
    );
    titleInput.placeholder = "Course title";
    const createButton = el(
      "button",
      "mt-2 w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
    );
    createButton.type = "button";
    createButton.textContent = "Create course";
    card.append(createHeader, codeInput, titleInput, createButton);

    const cancel = el(
      "button",
      "mt-3 w-full text-center text-xs text-slate-500 hover:text-slate-700",
      "Close"
    );
    cancel.type = "button";
    cancel.addEventListener("click", closeModal);
    card.appendChild(cancel);

    async function runSearch() {
      const query = search.value.trim();
      if (query.length < 2) return;
      results.innerHTML = "";
      try {
        const courses = await api(`/courses/search/?q=${encodeURIComponent(query)}`);
        if (!courses.length) {
          results.appendChild(
            el("p", "py-4 text-center text-xs text-slate-400", "No courses found.")
          );
          return;
        }
        courses.forEach((course) => {
          const row = el(
            "div",
            "flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2"
          );
          const info = el("div", "min-w-0 flex-1");
          info.appendChild(el("p", "truncate text-sm font-medium", `${course.code} — ${course.title}`));
          info.appendChild(el("p", "truncate text-xs text-slate-500", course.university.name));
          const join = el(
            "button",
            "shrink-0 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700",
            "Join"
          );
          join.type = "button";
          join.addEventListener("click", async () => {
            try {
              const enrollment = await api(`/courses/${course.id}/join/`, {
                method: "POST",
                body: JSON.stringify({}),
              });
              closeModal();
              await loadSections();
              const entry = state.sections.find(
                (item) => item.section.id === enrollment.section.id
              );
              if (entry && entry.channels.length) openChannel(entry, entry.channels[0]);
              toast(`Joined ${course.code}`);
            } catch (error) {
              toast(error.message);
            }
          });
          row.append(info, join);
          results.appendChild(row);
        });
      } catch (error) {
        toast(error.message);
      }
    }

    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        runSearch();
      }
    });

    createButton.addEventListener("click", async () => {
      const code = codeInput.value.trim();
      const title = titleInput.value.trim();
      if (!code || !title) {
        toast("Course code and title are required.");
        return;
      }
      try {
        const course = await api("/courses/", {
          method: "POST",
          body: JSON.stringify({ code, title }),
        });
        closeModal();
        await loadSections();
        const entry = state.sections.find(
          (item) => item.section.course.id === course.id
        );
        if (entry && entry.channels.length) openChannel(entry, entry.channels[0]);
        toast(`Created ${course.code}`);
      } catch (error) {
        toast(error.message);
      }
    });

    openModal();
    search.focus();
  }

  function openAnnounceModal() {
    if (!state.section) return;
    const card = $("modal-card");
    card.innerHTML = "";

    card.appendChild(el("h2", "text-lg font-bold", "Post an announcement"));
    card.appendChild(
      el(
        "p",
        "mt-1 text-sm text-slate-500",
        `Pinned to #general in ${state.section.section.display_name}.`
      )
    );

    const textarea = el(
      "textarea",
      "mt-4 h-32 w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm"
    );
    textarea.placeholder = "Midterm moved to Friday. Review chapters 4–6.";
    card.appendChild(textarea);

    const label = el("label", "mt-3 flex items-center gap-2 text-sm text-slate-600");
    const checkbox = el("input", "");
    checkbox.type = "checkbox";
    label.append(checkbox, document.createTextNode("Also email the class"));
    card.appendChild(label);

    const submit = el(
      "button",
      "mt-4 w-full rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700",
      "Post announcement"
    );
    submit.type = "button";
    submit.addEventListener("click", async () => {
      const body = textarea.value.trim();
      if (!body) {
        toast("Write something to announce.");
        return;
      }
      try {
        await api(`/sections/${state.section.section.id}/announcements/`, {
          method: "POST",
          body: JSON.stringify({ body, email: checkbox.checked }),
        });
        closeModal();
        await loadMessages();
        await loadPinned();
        toast("Announcement posted.");
      } catch (error) {
        toast(error.message);
      }
    });
    card.appendChild(submit);

    const cancel = el(
      "button",
      "mt-3 w-full text-center text-xs text-slate-500 hover:text-slate-700",
      "Close"
    );
    cancel.type = "button";
    cancel.addEventListener("click", closeModal);
    card.appendChild(cancel);

    openModal();
    textarea.focus();
  }

  // --------------------------------------------------------------- controls

  function closeSidebar() {
    $("sidebar").classList.add("-translate-x-full");
    $("sidebar-backdrop").classList.add("hidden");
  }

  $("menu-btn").addEventListener("click", () => {
    $("sidebar").classList.remove("-translate-x-full");
    $("sidebar-backdrop").classList.remove("hidden");
  });
  $("sidebar-backdrop").addEventListener("click", closeSidebar);

  $("join-course-btn").addEventListener("click", openJoinModal);
  $("empty-join-btn").addEventListener("click", openJoinModal);
  $("announce-btn").addEventListener("click", openAnnounceModal);

  $("logout-btn").addEventListener("click", async () => {
    try {
      await api("/auth/logout/", { method: "POST" });
    } catch (error) {
      /* token may already be gone */
    }
    localStorage.removeItem(TOKEN_KEY);
    location.replace("/login/");
  });

  $("thread-close").addEventListener("click", closeThread);

  $("search-close").addEventListener("click", () => {
    state.searchMode = false;
    $("search-view").classList.add("hidden");
    if (state.channel) {
      $("chat-view").classList.remove("hidden");
    } else {
      showEmpty();
    }
  });

  $("search-input").addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") return;
    const query = event.target.value.trim();
    if (query.length < 2) return;
    try {
      const data = await api(`/search/?q=${encodeURIComponent(query)}`);
      renderSearch(query, data.results);
    } catch (error) {
      toast(error.message);
    }
  });

  function autoGrow(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }

  ["composer-input", "thread-input"].forEach((id) => {
    const textarea = $(id);
    textarea.addEventListener("input", () => autoGrow(textarea));
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        textarea.form.requestSubmit();
      }
    });
  });

  $("composer").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("composer-input");
    const body = input.value.trim();
    if (!body) return;
    input.value = "";
    autoGrow(input);
    try {
      await sendMessage(body);
    } catch (error) {
      toast(error.message);
      input.value = body;
    }
  });

  $("thread-composer").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("thread-input");
    const body = input.value.trim();
    if (!body || !state.threadRoot) return;
    input.value = "";
    autoGrow(input);
    try {
      await sendMessage(body, state.threadRoot.id);
    } catch (error) {
      toast(error.message);
      input.value = body;
    }
  });

  // ------------------------------------------------------------------- boot

  async function boot() {
    try {
      const me = await api("/me/");
      state.profile = me.profile;
      renderUser();
      await loadSections();

      const first = state.sections.find((entry) => entry.channels.length);
      if (first) {
        openChannel(first, first.channels[0]);
      } else {
        showEmpty();
      }
    } catch (error) {
      if (error.status !== 401) toast(error.message);
    }
  }

  boot();
})();
