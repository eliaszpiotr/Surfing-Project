/**
 * spot-list.js — obsługa przycisku "Load more" na liście spotów.
 *
 * URL endpointu load-more jest przekazywany przez atrybut data-url
 * na przycisku #load-more-btn (renderowany przez Django w szablonie),
 * dzięki czemu ten plik jest w pełni statyczny.
 */
document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("load-more-btn");
    if (!btn) return;

    var container = document.getElementById("spots-container");

    btn.addEventListener("click", function () {
        var url      = btn.dataset.url;
        var params   = new URLSearchParams({ page: btn.dataset.nextPage });

        if (btn.dataset.country)    params.append("country",    btn.dataset.country);
        if (btn.dataset.difficulty) params.append("difficulty", btn.dataset.difficulty);
        if (btn.dataset.query)      params.append("q",          btn.dataset.query);

        btn.textContent = "Loading...";
        btn.disabled    = true;

        fetch(url + "?" + params.toString())
            .then(function (r) {
                if (!r.ok) throw new Error("Network response was not ok");
                return r.json();
            })
            .then(function (data) {
                container.insertAdjacentHTML("beforeend", data.html);
                if (data.has_next) {
                    btn.dataset.nextPage = data.next_page;
                    btn.textContent      = "Load more";
                    btn.disabled         = false;
                } else {
                    var wrapper = btn.closest(".text-center");
                    if (wrapper) wrapper.remove();
                }
            })
            .catch(function () {
                btn.textContent = "Load more";
                btn.disabled    = false;
            });
    });
});
