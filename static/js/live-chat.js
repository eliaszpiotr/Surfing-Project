(() => {
    const form = document.querySelector("[data-chat-form]");
    const messages = document.querySelector("[data-chat-messages]");
    const emptyState = document.querySelector("[data-chat-empty]");
    const bodyField = form?.querySelector("textarea[name='body']");
    const imageField = form?.querySelector("input[type='file'][name='image']");
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

        appendMessage(payload.message);
    });

    const appendMessage = (message) => {
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
        if (message.image_url) {
            const image = document.createElement("img");
            image.src = message.image_url;
            image.alt = "Chat attachment";
            image.className = "chat-message-image mt-2";
            item.append(image);
        }
        messages.append(item);
        item.scrollIntoView({ block: "nearest" });
    };

    form.addEventListener("submit", (event) => {
        if (imageField?.files?.length) {
            if (!isReady) {
                return;
            }

            event.preventDefault();
            fetch(form.action || window.location.href, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error("Upload failed");
                    }
                    return response.json();
                })
                .then((payload) => {
                    if (payload.type === "message") {
                        appendMessage(payload.message);
                        form.reset();
                    }
                })
                .catch(() => {
                    HTMLFormElement.prototype.submit.call(form);
                });
            return;
        }

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
