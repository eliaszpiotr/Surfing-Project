(() => {
    const count = document.querySelector("[data-notification-count]");
    const list = document.querySelector("[data-notification-list]");
    const emptyState = document.querySelector("[data-notification-empty]");
    if (!count || !window.WebSocket) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/notifications/`);

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type !== "notification") {
            return;
        }

        const unreadCount = Number(payload.unread_count || 0);
        count.textContent = unreadCount > 0 ? ` (${unreadCount})` : "";

        if (!list || !payload.notification) {
            return;
        }

        emptyState?.remove();
        const notification = payload.notification;
        if (list.querySelector(`[data-notification-id="${notification.id}"]`)) {
            return;
        }

        const link = document.createElement("a");
        link.href = notification.target_url;
        link.className = "list-group-item list-group-item-action";
        link.dataset.notificationId = notification.id;

        const row = document.createElement("div");
        row.className = "d-flex justify-content-between align-items-start gap-3";

        const content = document.createElement("div");
        const body = document.createElement("div");
        body.className = "fw-semibold";
        body.textContent = notification.body;

        const time = document.createElement("div");
        time.className = "text-muted small";
        time.textContent = notification.created_at;

        const badge = document.createElement("span");
        badge.className = "badge bg-dark";
        badge.textContent = "New";

        content.append(body, time);
        row.append(content, badge);
        link.append(row);
        list.prepend(link);
    });
})();
