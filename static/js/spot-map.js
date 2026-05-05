/**
 * spot-map.js — inicjalizacja mapy Leaflet na stronie szczegółów spotu.
 *
 * Dane geograficzne (lat, lng, nazwa) są przekazywane przez atrybuty data-*
 * na elemencie #spot-map, dzięki czemu plik ten nie zawiera żadnych
 * danych renderowanych przez Django i jest całkowicie statyczny.
 *
 * Wymagana biblioteka: Leaflet (ładowana przez szablon spot_detail.html)
 */
document.addEventListener("DOMContentLoaded", function () {
    var mapEl = document.getElementById("spot-map");
    if (!mapEl) return;

    var lat  = parseFloat(mapEl.dataset.lat);
    var lng  = parseFloat(mapEl.dataset.lng);
    var name = mapEl.dataset.name || "";

    if (isNaN(lat) || isNaN(lng)) return;

    var map = L.map("spot-map").setView([lat, lng], 11);
    map.attributionControl.setPrefix(false);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    L.marker([lat, lng]).addTo(map).bindPopup(name).openPopup();
});
