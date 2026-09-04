let ws = null;
let chart = null;
let lastPrice = null;
const maxDataPoints = 20;

const priceEl = document.getElementById('price');
const changeEl = document.getElementById('price-change');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const pairSelect = document.getElementById('pair-select');

// Inicializar Gráfico con Chart.js
function initChart() {
  const ctx = document.getElementById('cryptoChart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Precio USD',
        data: [],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.3,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: true, grid: { color: '#334155' } },
        y: { display: true, grid: { color: '#334155' } }
      }
    }
  });
}

// Conectar con WebSocket Binance
function connectWebSocket(symbol) {
  if (ws) ws.close();

  ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol}@trade`);

  ws.onopen = () => {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-green-500';
    statusText.textContent = 'En Vivo';
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const price = parseFloat(data.p).toFixed(2);
    const time = new Date(data.T).toLocaleTimeString();

    // Actualizar precio y color de fluctuación
    priceEl.textContent = `$${price} USD`;
    if (lastPrice !== null) {
      const diff = price - lastPrice;
      if (diff > 0) {
        priceEl.className = 'text-2xl font-bold mt-1 text-green-400';
        changeEl.textContent = `+${diff.toFixed(2)}`;
        changeEl.className = 'text-2xl font-bold mt-1 text-green-400';
      } else if (diff < 0) {
        priceEl.className = 'text-2xl font-bold mt-1 text-red-400';
        changeEl.textContent = `${diff.toFixed(2)}`;
        changeEl.className = 'text-2xl font-bold mt-1 text-red-400';
      }
    }
    lastPrice = price;

    // Actualizar gráfico
    chart.data.labels.push(time);
    chart.data.datasets[0].data.push(price);

    if (chart.data.labels.length > maxDataPoints) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update();
  };

  ws.onerror = () => {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-red-500';
    statusText.textContent = 'Error de conexión';
  };

  ws.onclose = () => {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-yellow-500';
    statusText.textContent = 'Desconectado';
  };
}

// Event Listeners
pairSelect.addEventListener('change', (e) => {
  chart.data.labels = [];
  chart.data.datasets[0].data = [];
  lastPrice = null;
  connectWebSocket(e.target.value);
});

// Arrancar
initChart();
connectWebSocket(pairSelect.value);