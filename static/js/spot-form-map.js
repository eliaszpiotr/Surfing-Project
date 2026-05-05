document.addEventListener("DOMContentLoaded", function () {
    var latInput = document.getElementById("id_latitude");
    var lngInput = document.getElementById("id_longitude");
    var latDisplay = document.getElementById("lat-display");
    var lngDisplay = document.getElementById("lng-display");
    var coordsDisplay = document.getElementById("coords-display");

    if (!latInput || !lngInput || !latDisplay || !lngDisplay || !coordsDisplay) {
        return;
    }

    var defaultLat = parseFloat(latInput.value) || 20;
    var defaultLng = parseFloat(lngInput.value) || 0;

    var map = L.map("spot-map", {
        center: [defaultLat, defaultLng],
        zoom: latInput.value ? 10 : 2,
        worldCopyJump: true
    });
    map.attributionControl.setPrefix(false);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    var marker = null;

    function setMarker(lat, lng) {
        var wrapped = L.latLng(lat, lng).wrap();

        if (marker) {
            marker.setLatLng([wrapped.lat, wrapped.lng]);
        } else {
            marker = L.marker([wrapped.lat, wrapped.lng]).addTo(map);
        }

        latInput.value = wrapped.lat.toFixed(6);
        lngInput.value = wrapped.lng.toFixed(6);
        latDisplay.textContent = wrapped.lat.toFixed(4);
        lngDisplay.textContent = wrapped.lng.toFixed(4);
        coordsDisplay.style.display = "block";
    }

    if (latInput.value && lngInput.value) {
        setMarker(parseFloat(latInput.value), parseFloat(lngInput.value));
        map.setView([parseFloat(latInput.value), parseFloat(lngInput.value)], 10);
    }

    map.on("click", function (event) {
        setMarker(event.latlng.lat, event.latlng.lng);
    });
});
