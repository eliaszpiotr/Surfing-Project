/**
 * home-map.js — initialises the Leaflet cluster map on the home page.
 *
 * The API URL is read from the data-url attribute on #home-map so this file
 * contains no Django-rendered values and can be served as a plain static file.
 *
 * Required libraries (loaded by home.html before this script):
 *   - Leaflet
 *   - Leaflet.markercluster
 */
(function () {
    "use strict";

    function escapeHtml(t) {
        return String(t).replace(/[&<>"']/g, function (m) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"}[m];
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var mapEl = document.getElementById("home-map");
        if (!mapEl) return;

        var dataUrl = mapEl.dataset.url;
        if (!dataUrl) return;

        var map = L.map("home-map", {center: [20, 0], zoom: 2, worldCopyJump: true});
        map.attributionControl.setPrefix(false);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);

        var markers = L.markerClusterGroup({maxClusterRadius: 50});

        fetch(dataUrl)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!Array.isArray(data) || !data.length) return;
                var bounds = [];
                data.forEach(function (spot) {
                    if (spot.lat == null || spot.lng == null) return;
                    var popup =
                        "<b>" + escapeHtml(spot.name) + "</b><br>" +
                        "<span style='color:#666;font-size:0.82rem'>" +
                            escapeHtml(spot.country) + " &middot; " + escapeHtml(spot.difficulty) +
                        "</span><br>" +
                        "<a href='/spots/" + escapeHtml(spot.slug) + "/'>View spot</a>";
                    L.marker([spot.lat, spot.lng]).bindPopup(popup).addTo(markers);
                    bounds.push([spot.lat, spot.lng]);
                });
                map.addLayer(markers);
                if (bounds.length > 1) map.fitBounds(bounds, {padding: [40, 40]});
            })
            .catch(function (err) { console.error("Map error:", err); });
    });
}());
