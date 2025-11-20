let currentAnalysis = null;

function switchTab(tab) {
    if (tab === 'file') {
        document.getElementById('file-input').classList.remove('hidden');
        document.getElementById('text-input').classList.add('hidden');
        document.getElementById('tab-file').className = "text-blue-400 font-semibold border-b-2 border-blue-400 pb-1";
        document.getElementById('tab-text').className = "text-gray-400 hover:text-white font-semibold pb-1";
    } else {
        document.getElementById('file-input').classList.add('hidden');
        document.getElementById('text-input').classList.remove('hidden');
        document.getElementById('tab-text').className = "text-blue-400 font-semibold border-b-2 border-blue-400 pb-1";
        document.getElementById('tab-file').className = "text-gray-400 hover:text-white font-semibold pb-1";
    }
}

document.getElementById('analyze-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const inputSec = document.getElementById('input-section');

    inputSec.classList.add('hidden');
    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentAnalysis = data.analysis; // Store for PDF download
            displayResults(data.analysis);
        } else {
            alert("Error: " + data.error);
            inputSec.classList.remove('hidden');
        }
    } catch (err) {
        alert("Error de conexión.");
        inputSec.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
});

let chartInstance = null;

function displayResults(analysis) {
    document.getElementById('results').classList.remove('hidden');
    
    // Update Text
    const score = analysis.score;
    document.getElementById('score-display').innerText = score + "%";
    document.getElementById('verdict-display').innerText = analysis.verdict;
    document.getElementById('summary-display').innerText = analysis.summary;
    
    // Color Logic
    const color = score > 70 ? '#ef4444' : (score > 40 ? '#f59e0b' : '#10b981'); // Red, Amber, Green
    document.getElementById('verdict-display').style.color = color;

    // Reasons List
    const list = document.getElementById('reasons-list');
    list.innerHTML = '';
    analysis.reasons.forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        list.appendChild(li);
    });

    // Chart
    const ctx = document.getElementById('scoreChart').getContext('2d');
    
    if(chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Phishing', 'Seguro'],
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [color, '#374151'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '80%',
            plugins: { legend: { display: false } }
        }
    });
}

async function downloadPDF() {
    if (!currentAnalysis) return;
    
    const response = await fetch('/download_report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentAnalysis)
    });
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "NetSereno_Reporte.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
}