(() => {
    const form = document.querySelector("[data-chat-form]");
    const messages = document.querySelector("[data-chat-messages]");
    const emptyState = document.querySelector("[data-chat-empty]");
    const bodyField = form?.querySelector("textarea[name='body']");
    if (!form || !messages || !bodyField || !window.WebSocket) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}${form.dataset.chatUrl}`);
    let isReady = false;

    socket.addEventListener("open", () => {
        isReady = true;
    });

    socket.addEventListener("close", () => {
        isReady = false;
    });

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type !== "message") {
            return;
        }

        const message = payload.message;
        if (messages.querySelector(`[data-message-id="${message.id}"]`)) {
            return;
        }

        emptyState?.remove();
        const item = document.createElement("div");
        item.dataset.messageId = message.id;

        const meta = document.createElement("div");
        meta.className = "small fw-semibold";

        const author = document.createElement("a");
        author.className = "text-decoration-none";
        author.href = `/accounts/users/${message.author_username}/`;
        author.textContent = `@${message.author_username}`;

        const time = document.createElement("span");
        time.className = "text-muted fw-normal";
        time.textContent = ` · ${message.created_at}`;

        const body = document.createElement("div");
        body.className = "chat-message-body";
        body.textContent = message.body;

        meta.append(author, time);
        item.append(meta, body);
        messages.append(item);
        item.scrollIntoView({ block: "nearest" });
    });

    form.addEventListener("submit", (event) => {
        if (!isReady) {
            return;
        }

        event.preventDefault();
        const body = bodyField.value.trim();
        if (!body) {
            return;
        }

        socket.send(JSON.stringify({ body }));
        bodyField.value = "";
    });
})();
