// --- DATABASE & STATE ---
const cityDatabase = {
    "FRA": {lat: 50.03, lon: 8.57}, "LHR": {lat: 51.47, lon: -0.45}, "TYO": {lat: 35.67, lon: 139.65}, "JFK": {lat: 40.64, lon: -73.77},
    "BER": {lat: 52.36, lon: 13.50}, "CDG": {lat: 49.00, lon: 2.55}, "DXB": {lat: 25.25, lon: 55.36}
};

let trips = {};
let priceAlerts = [
    {
        id: 1,
        origin: 'BER',
        dest: 'JFK',
        targetPrice: 350,
        currentPrice: 420,
        date: '2026-06-15',
        passengers: 1,
        airline: 'Lufthansa',
        created: '2026-01-01T10:00:00',
        priceHistory: [
            { date: '2026-01-01', price: 450 },
            { date: '2026-01-05', price: 445 },
            { date: '2026-01-08', price: 430 },
            { date: '2026-01-12', price: 425 },
            { date: '2026-01-15', price: 420 },
            { date: '2026-01-18', price: 410 },
            { date: '2026-01-20', price: 420 }
        ]
    },
    {
        id: 2,
        origin: 'FRA',
        dest: 'TYO',
        targetPrice: 600,
        currentPrice: 580,
        date: '2026-07-20',
        passengers: 2,
        airline: 'Emirates',
        created: '2026-01-02T12:00:00',
        priceHistory: [
            { date: '2026-01-02', price: 650 },
            { date: '2026-01-06', price: 630 },
            { date: '2026-01-09', price: 620 },
            { date: '2026-01-13', price: 600 },
            { date: '2026-01-16', price: 590 },
            { date: '2026-01-19', price: 585 },
            { date: '2026-01-20', price: 580 }
        ]
    },
    {
        id: 3,
        origin: 'FRA',
        dest: 'DXB',
        targetPrice: 400,
        currentPrice: 450,
        date: '2026-08-10',
        passengers: 1,
        airline: 'Qatar Airways',
        created: '2026-01-03T14:00:00',
        priceHistory: [
            { date: '2026-01-03', price: 480 },
            { date: '2026-01-07', price: 475 },
            { date: '2026-01-10', price: 470 },
            { date: '2026-01-14', price: 460 },
            { date: '2026-01-17', price: 455 },
            { date: '2026-01-20', price: 450 }
        ]
    }
];
let passengerCounts = { adults: 1, children: 0, infants: 0 };
let alertPassengerCounts = { adults: 1, children: 0, infants: 0 };
let currentDetailKey = null;

// --- THREE.JS ENGINE ---
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 15;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.getElementById('canvas-container').appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.5;
// Zoom Limits
controls.minDistance = 7;
controls.maxDistance = 30;

const globeGroup = new THREE.Group(); scene.add(globeGroup);
const texLoad = new THREE.TextureLoader();

// Background Stars
const starGeo = new THREE.BufferGeometry();
const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.05, transparent: true, opacity: 0.8 });
const starVerts = [];
for(let i=0; i<5000; i++) starVerts.push((Math.random()-0.5)*150, (Math.random()-0.5)*150, (Math.random()-0.5)*150);
starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starVerts, 3));
const stars = new THREE.Points(starGeo, starMat);
scene.add(stars);

// Atmosphere Glow
const atmosphere = new THREE.Mesh(
    new THREE.SphereGeometry(5.2, 64, 64),
    new THREE.MeshPhongMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.1, side: THREE.BackSide, blending: THREE.AdditiveBlending })
);
scene.add(atmosphere);

// Earth with Emissive City Lights
const earthMaterial = new THREE.MeshStandardMaterial({
    map: texLoad.load('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg'),
    emissiveMap: texLoad.load('https://unpkg.com/three-globe/example/img/earth-night.jpg'),
    emissive: new THREE.Color(0xffffcc),
    emissiveIntensity: 0.4,
    roughness: 0.7, metalness: 0.2
});
const earth = new THREE.Mesh(new THREE.SphereGeometry(5, 64, 64), earthMaterial);
globeGroup.add(earth);

// Lighting (Sun)
scene.add(new THREE.AmbientLight(0x333333));
const sun = new THREE.DirectionalLight(0xffffff, 1.5);
sun.position.set(10, 5, 10);
scene.add(sun);

const markerGroup = new THREE.Group(); globeGroup.add(markerGroup);

function latLonToPos(lat, lon, r) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    return new THREE.Vector3(-(r * Math.sin(phi) * Math.cos(theta)), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

// --- NEU: Bogen-Funktion ---
function drawFlightPath(originCode, destCode) {
    const origin = cityDatabase[originCode];
    const dest = cityDatabase[destCode];
    if (!origin || !dest) return;

    const start = latLonToPos(origin.lat, origin.lon, 5.05);
    const end = latLonToPos(dest.lat, dest.lon, 5.05);

    // Mittelpunkt berechnen und nach außen wölben für den Bogen
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    const distance = start.distanceTo(end);
    mid.setLength(5.05 + distance * 0.4); // Die Höhe des Bogens hängt von der Distanz ab

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    const points = curve.getPoints(50);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.6, linewidth: 2 });

    const line = new THREE.Line(geometry, material);
    markerGroup.add(line);
}

function renderMarkers() {
    while(markerGroup.children.length > 0) markerGroup.remove(markerGroup.children[0]);
    Object.keys(trips).forEach(key => {
        const t = trips[key];
        const m = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), new THREE.MeshBasicMaterial({ color: 0x22d3ee }));
        m.position.copy(latLonToPos(t.lat, t.lon, 5.05));
        m.userData = { key };
        markerGroup.add(m);
    });
    document.getElementById('stat-count').innerText = Object.keys(trips).length;
}

function animate(t) {
    requestAnimationFrame(animate);
    TWEEN.update();
    controls.update();
    stars.rotation.y -= 0.0001;
    earthMaterial.emissiveIntensity = 0.3 + Math.sin(t * 0.001) * 0.1;
    renderer.render(scene, camera);
}
animate();

// --- UI HELPERS ---

function updateCounter(type, delta) {
    passengerCounts[type] = Math.max(type === 'adults' ? 1 : 0, passengerCounts[type] + delta);
    document.getElementById(`count-${type}`).innerText = passengerCounts[type];
}

function updateAlertCounter(type, delta) {
    alertPassengerCounts[type] = Math.max(type === 'adults' ? 1 : 0, alertPassengerCounts[type] + delta);
    document.getElementById(`alert-count-${type}`).innerText = alertPassengerCounts[type];
}

async function performSearch() {
    const origin = document.getElementById('input-origin').value.trim().toUpperCase();
    const dest = document.getElementById('input-dest').value.trim().toUpperCase();
    const date = document.getElementById('input-start').value;
    const btn = document.getElementById('btn-search-trigger');

    if(!origin || !dest || !date) return;

    btn.disabled = true;
    btn.innerHTML = `<div class="flex items-center justify-center gap-2"><div class="loading-ring"></div> SUCHE...</div>`;

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination: dest, date, passengers: passengerCounts })
        });
        const data = await res.json();

        // Marker leeren vor neuer Suche, um Route zu visualisieren
        while(markerGroup.children.length > 0) markerGroup.remove(markerGroup.children[0]);

        if(data.success && data.flights.length > 0) {
            renderResults(data.flights, dest, origin);
            drawFlightPath(origin, dest); // Bogen zeichnen
            flyTo(cityDatabase[dest]?.lat || 0, cityDatabase[dest]?.lon || 0);
        } else {
            mockSearch(dest, origin);
        }
    } catch(e) { mockSearch(dest, origin); }
    finally { btn.disabled = false; btn.innerText = "FLÜGE SUCHEN"; }
}

function mockSearch(cityName, originName) {
    const dummyData = [
        { airline: 'Lufthansa', price: '420€', departure: '10:30', duration: '11h 20m' },
        { airline: 'Emirates', price: '389€', departure: '21:15', duration: '13h 05m' }
    ];
    renderResults(dummyData, cityName, originName);
    drawFlightPath(originName, cityName);
}

function renderResults(flights, cityName, originName) {
    const area = document.getElementById('search-results-area');
    const list = document.getElementById('results-list');
    area.classList.remove('hidden'); list.innerHTML = '';

    flights.forEach(f => {
        list.innerHTML += `
            <div class="flight-result-card">
                <div class="flex items-center gap-4">
                    <div class="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center font-black text-cyan-400 border border-slate-700">${f.airline.substring(0,2)}</div>
                    <div><p class="font-bold text-white text-sm">${f.airline}</p><p class="text-[9px] text-slate-500 uppercase">${f.departure} • ${f.duration}</p></div>
                </div>
                <div class="text-right flex items-center gap-4">
                    <p class="text-lg font-black text-white">${f.price}</p>
                    <div class="flex flex-col gap-1">
                        <button onclick="saveTrip('${cityName}', '${f.airline}', '${f.price}', '${originName}')" class="px-3 py-1 bg-cyan-500 text-slate-900 rounded-lg font-black text-[9px] uppercase">Planen</button>
                        <button onclick="addAlert('${cityName}', '${f.price}')" class="px-3 py-1 border border-slate-700 rounded-lg font-black text-[9px] uppercase">Alarm</button>
                    </div>
                </div>
            </div>
        `;
    });
}

function saveTrip(dest, airline, price, origin) {
    const id = 't_' + Date.now();
    const coords = cityDatabase[dest] || {lat: 48 + Math.random()*5, lon: 10 + Math.random()*5};
    trips[id] = {
        title: dest, origin: origin, date: 'MAI 2025', lat: coords.lat, lon: coords.lon,
        img: `https://loremflickr.com/800/600/city,${dest}?lock=${Math.floor(Math.random()*100)}`,
        itinerary: [{title: 'Hinflug', desc: `${airline} • ${price}`}, {title: 'Planung', desc: 'Hotel-Recherche aktiv'}]
    };
    renderMarkers();
    if (origin) drawFlightPath(origin, dest);
    hideAddTripModal();
    flyTo(coords.lat, coords.lon);
}

function addAlert(dest, price) {
    const origin = document.getElementById('input-origin').value.trim().toUpperCase() || 'FRA';
    const date = document.getElementById('input-start').value || '2026-07-01';
    const priceNum = parseInt(price.replace('€', '').trim());

    // Mock Preisverlauf generieren
    const priceHistory = [];
    const today = new Date();
    let currentPrice = priceNum + 30; // Startpreis vor 2 Wochen

    for (let i = 14; i >= 0; i--) {
        const historyDate = new Date(today);
        historyDate.setDate(historyDate.getDate() - i);

        // Zufällige Preisschwankung
        currentPrice = currentPrice + (Math.random() - 0.5) * 20;
        if (i === 0) currentPrice = priceNum; // Aktueller Preis

        priceHistory.push({
            date: historyDate.toISOString().split('T')[0],
            price: Math.round(currentPrice)
        });
    }

    const newAlert = {
        id: Date.now(),
        origin: origin,
        dest: dest,
        targetPrice: Math.round(priceNum * 0.85), // 15% unter aktuellem Preis
        currentPrice: priceNum,
        date: date,
        passengers: passengerCounts.adults + passengerCounts.children,
        airline: 'Diverse',
        created: new Date().toISOString(),
        priceHistory: priceHistory
    };

    priceAlerts.push(newAlert);
    hideAddTripModal();
    document.getElementById('notif-badge').classList.remove('hidden');
    showToast('Preisalarm erstellt! 🔔', 'success');
}

function flyTo(lat, lon) {
    controls.autoRotate = false;
    const targetPos = latLonToPos(lat, lon, camera.position.length());
    new TWEEN.Tween(camera.position).to({ x: targetPos.x, y: targetPos.y, z: targetPos.z }, 1500)
        .easing(TWEEN.Easing.Cubic.InOut).onUpdate(()=>camera.lookAt(0,0,0)).start();
}

function switchView(v) {
    ['home','trips'].forEach(id => {
        const el = document.getElementById('view-'+id);
        if(id===v) { el.classList.remove('hidden'); setTimeout(()=>el.classList.remove('opacity-0'),10); if(v==='trips') renderPlanning(); }
        else { el.classList.add('opacity-0'); setTimeout(()=>el.classList.add('hidden'),300); }
    });
    document.getElementById('nav-home').className = v === 'home' ? 'flex flex-col items-center text-cyan-400' : 'flex flex-col items-center text-slate-500';
    document.getElementById('nav-trips').className = v === 'trips' ? 'flex flex-col items-center text-cyan-400' : 'flex flex-col items-center text-slate-500';
    controls.autoRotate = (v==='home');
}

function renderPlanning() {
    const c = document.getElementById('trips-container'); c.innerHTML = '';
    Object.keys(trips).forEach(k => {
        const t = trips[k];
        c.innerHTML += `
            <div class="glass-card rounded-3xl overflow-hidden cursor-pointer" onclick="openDetail('${k}'); flyTo(${t.lat}, ${t.lon})">
                <img src="${t.img}" class="h-40 w-full object-cover" alt="${t.title}">
                <div class="p-6"><h3 class="font-black text-xl">${t.title}</h3><p class="text-xs text-slate-400 uppercase font-bold tracking-widest">${t.date}</p></div>
            </div>
        `;
    });
}

function toggleTripTab(tab) {
    document.getElementById('tab-trips').className = tab === 'trips' ? 'px-6 py-2 rounded-lg bg-cyan-500 text-slate-900 font-bold text-sm' : 'px-6 py-2 rounded-lg text-slate-400 font-bold text-sm';
    document.getElementById('tab-alerts').className = tab === 'alerts' ? 'px-6 py-2 rounded-lg bg-cyan-500 text-slate-900 font-bold text-sm' : 'px-6 py-2 rounded-lg text-slate-400 font-bold text-sm';
    document.getElementById('trips-container').classList.toggle('hidden', tab !== 'trips');
    document.getElementById('alerts-container').classList.toggle('hidden', tab !== 'alerts');

    // Plus-Button nur im Preisalarme-Tab anzeigen
    const addAlertBtn = document.getElementById('add-alert-btn');
    if (tab === 'alerts') {
        addAlertBtn.classList.remove('hidden');
        addAlertBtn.classList.add('flex');
        renderAlerts();
    } else {
        addAlertBtn.classList.add('hidden');
        addAlertBtn.classList.remove('flex');
    }
}

function renderAlerts() {
    const c = document.getElementById('alerts-scroll-container');

    if (priceAlerts.length === 0) {
        c.innerHTML = '<p class="text-center w-full py-20 text-slate-500 font-bold uppercase text-xs tracking-widest">Keine Alarme gesetzt</p>';
        return;
    }

    c.innerHTML = '';

    priceAlerts.forEach(alert => {
        const trend = calculatePriceTrend(alert.priceHistory);
        const difference = alert.currentPrice - alert.targetPrice;
        const statusClass = difference <= 0 ? 'price-below' : 'price-above';
        const createdDate = new Date(alert.created).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
        const travelDate = new Date(alert.date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });

        const cardHtml = `
            <div class="alert-card alert-card-slide ${statusClass}" data-alert-id="${alert.id}">
                <div class="alert-header">
                    <div>
                        <div class="alert-route">${alert.origin} → ${alert.dest}</div>
                        <div class="alert-meta">
                            <span>📅 ${travelDate}</span>
                            <span>👤 ${alert.passengers} Pers.</span>
                            <span>✈️ ${alert.airline}</span>
                        </div>
                    </div>
                    <button class="alert-delete-btn" onclick="deleteAlert(${alert.id})" title="Alarm löschen">×</button>
                </div>

                <div class="alert-details">
                    <div class="alert-price-row">
                        <span class="alert-label">Zielpreis</span>
                        <span class="alert-value alert-target-price">${alert.targetPrice}€</span>
                    </div>
                    <div class="alert-price-row">
                        <span class="alert-label">Aktueller Preis</span>
                        <span class="alert-value alert-current-price">${alert.currentPrice}€ <span class="alert-trend">${trend}</span></span>
                    </div>
                    <div class="alert-price-row">
                        <span class="alert-label">Erstellt</span>
                        <span class="alert-value" style="font-size: 0.75rem;">${createdDate}</span>
                    </div>
                </div>

                <div class="price-chart-container">
                    <canvas id="chart-${alert.id}"></canvas>
                </div>
            </div>
        `;

        c.innerHTML += cardHtml;
    });

    // Charts rendern nach DOM-Update
    setTimeout(() => {
        priceAlerts.forEach(alert => renderPriceChart(alert));
    }, 50);
}

function calculatePriceTrend(priceHistory) {
    if (priceHistory.length < 2) return '';
    const last = priceHistory[priceHistory.length - 1].price;
    const prev = priceHistory[priceHistory.length - 2].price;

    if (last < prev) return '📉';
    if (last > prev) return '📈';
    return '→';
}

function renderPriceChart(alert) {
    const canvas = document.getElementById(`chart-${alert.id}`);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Gradient für Hintergrund
    const gradient = ctx.createLinearGradient(0, 0, 0, 140);
    gradient.addColorStop(0, 'rgba(34, 211, 238, 0.3)');
    gradient.addColorStop(1, 'rgba(34, 211, 238, 0.01)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: alert.priceHistory.map(p => {
                const date = new Date(p.date);
                return `${date.getDate()}.${date.getMonth() + 1}`;
            }),
            datasets: [
                {
                    label: 'Preis',
                    data: alert.priceHistory.map(p => p.price),
                    borderColor: 'rgba(34, 211, 238, 1)',
                    backgroundColor: gradient,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(34, 211, 238, 1)',
                    pointBorderColor: 'rgba(15, 23, 42, 1)',
                    pointBorderWidth: 2
                },
                {
                    label: 'Zielpreis',
                    data: alert.priceHistory.map(() => alert.targetPrice),
                    borderColor: 'rgba(34, 197, 94, 0.8)',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: 'rgba(255, 255, 255, 0.9)',
                    bodyColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: 'rgba(34, 211, 238, 0.5)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: (context) => `${context.parsed.y}€`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { size: 10 } }
                },
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.5)',
                        font: { size: 10 },
                        callback: (value) => `${value}€`
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function deleteAlert(alertId) {
    priceAlerts = priceAlerts.filter(a => a.id !== alertId);
    renderAlerts();
    showToast('Preisalarm gelöscht', 'success');
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

function openDetail(k) {
    const t = trips[k]; currentDetailKey = k;
    document.getElementById('detail-img').src = t.img;
    document.getElementById('detail-title').innerText = t.title;
    document.getElementById('detail-date').innerText = t.date;
    const tl = document.getElementById('detail-itinerary'); tl.innerHTML = '';
    t.itinerary.forEach(i => tl.innerHTML += `<div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50"><p class="font-bold text-white text-sm">${i.title}</p><p class="text-[10px] text-slate-400 mt-1 uppercase font-bold">${i.desc}</p></div>`);
    document.getElementById('detail-sheet').classList.add('open');
}

function closeDetail() { document.getElementById('detail-sheet').classList.remove('open'); }
function showAddTripModal() { document.getElementById('add-trip-modal').classList.remove('hidden'); setTimeout(()=>document.getElementById('add-trip-modal').classList.remove('opacity-0'),10); }
function hideAddTripModal() { document.getElementById('add-trip-modal').classList.add('opacity-0'); setTimeout(()=>document.getElementById('add-trip-modal').classList.add('hidden'),300); }
function toggleNotifications() { document.getElementById('notification-dropdown').classList.toggle('hidden'); document.getElementById('notif-badge').classList.add('hidden'); }
function deleteCurrentTrip() { if(currentDetailKey) { delete trips[currentDetailKey]; renderMarkers(); renderPlanning(); closeDetail(); } }

function showAddAlertModal() {
    // Reset form
    document.getElementById('alert-origin').value = '';
    document.getElementById('alert-dest').value = '';
    document.getElementById('alert-date').value = '';
    document.getElementById('alert-target-price').value = '';
    document.getElementById('alert-current-price').value = '';
    document.getElementById('alert-airline').value = '';

    // Reset passenger counts
    alertPassengerCounts = { adults: 1, children: 0, infants: 0 };
    document.getElementById('alert-count-adults').innerText = '1';
    document.getElementById('alert-count-children').innerText = '0';
    document.getElementById('alert-count-infants').innerText = '0';

    // Show modal
    document.getElementById('add-alert-modal').classList.remove('hidden');
    setTimeout(() => document.getElementById('add-alert-modal').classList.remove('opacity-0'), 10);
}

function hideAddAlertModal() {
    document.getElementById('add-alert-modal').classList.add('opacity-0');
    setTimeout(() => document.getElementById('add-alert-modal').classList.add('hidden'), 300);
}

function createPriceAlert() {
    const origin = document.getElementById('alert-origin').value.trim().toUpperCase();
    const dest = document.getElementById('alert-dest').value.trim().toUpperCase();
    const date = document.getElementById('alert-date').value;
    const targetPrice = parseInt(document.getElementById('alert-target-price').value);
    const currentPrice = parseInt(document.getElementById('alert-current-price').value);
    const airline = document.getElementById('alert-airline').value.trim() || 'Diverse';

    // Validierung
    if (!origin || !dest || !date || !targetPrice || !currentPrice) {
        showToast('Bitte alle Pflichtfelder ausfüllen', 'error');
        return;
    }

    if (origin.length !== 3 || dest.length !== 3) {
        showToast('IATA-Codes müssen 3 Zeichen lang sein', 'error');
        return;
    }

    if (targetPrice <= 0 || currentPrice <= 0) {
        showToast('Preise müssen größer als 0 sein', 'error');
        return;
    }

    // Mock Preisverlauf generieren
    const priceHistory = [];
    const today = new Date();
    let price = currentPrice + 30; // Startpreis vor 2 Wochen

    for (let i = 14; i >= 0; i--) {
        const historyDate = new Date(today);
        historyDate.setDate(historyDate.getDate() - i);

        // Zufällige Preisschwankung
        price = price + (Math.random() - 0.5) * 20;
        if (i === 0) price = currentPrice; // Aktueller Preis

        priceHistory.push({
            date: historyDate.toISOString().split('T')[0],
            price: Math.round(price)
        });
    }

    const newAlert = {
        id: Date.now(),
        origin: origin,
        dest: dest,
        targetPrice: targetPrice,
        currentPrice: currentPrice,
        date: date,
        passengers: alertPassengerCounts.adults + alertPassengerCounts.children + alertPassengerCounts.infants,
        airline: airline,
        created: new Date().toISOString(),
        priceHistory: priceHistory
    };

    priceAlerts.push(newAlert);
    hideAddAlertModal();
    renderAlerts();
    showToast('Preisalarm erfolgreich erstellt! 🔔', 'success');
    document.getElementById('notif-badge').classList.remove('hidden');
}

window.addEventListener('click', e => {
    const mouse = new THREE.Vector2((e.clientX/window.innerWidth)*2-1, -(e.clientY/window.innerHeight)*2+1);
    const raycaster = new THREE.Raycaster(); raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(markerGroup.children);
    if(hits.length>0) { const key = hits[0].object.userData.key; if(key) { openDetail(key); flyTo(trips[key].lat, trips[key].lon); } }
});

window.addEventListener('resize', () => { camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); });
