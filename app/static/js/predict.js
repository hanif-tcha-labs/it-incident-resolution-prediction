// Predict & Incident Simulator Client Script

let posChart = null;
let distData = null;
let lastPrediction = null;
let whatIfModeActive = false;
let batchResultsData = [];

const PRESETS = {
  fast: {
    opened_at: "2016-05-10T22:52",
    priority: "3 - Moderate",
    impact: "2 - Medium",
    urgency: "2 - Medium",
    category: "Category 26",
    subcategory: "Subcategory 164",
    u_symptom: "Symptom 295",
    assignment_group: "Group 70",
    location: "Location 204",
    contact_type: "Phone",
    opened_by: "Opened by  58",
    sys_created_by: ""
  },
  medium: {
    opened_at: "2016-05-10T23:39",
    priority: "3 - Moderate",
    impact: "2 - Medium",
    urgency: "2 - Medium",
    category: "Category 37",
    subcategory: "Subcategory 123",
    u_symptom: "Symptom 495",
    assignment_group: "Group 49",
    location: "Location 161",
    contact_type: "Phone",
    opened_by: "Opened by  94",
    sys_created_by: "Created by 45"
  },
  slow: {
    opened_at: "2016-05-10T23:01",
    priority: "3 - Moderate",
    impact: "2 - Medium",
    urgency: "2 - Medium",
    category: "Category 46",
    subcategory: "Subcategory 223",
    u_symptom: "",
    assignment_group: "Group 55",
    location: "Location 204",
    contact_type: "Phone",
    opened_by: "Opened by  305",
    sys_created_by: ""
  }
};

document.addEventListener("DOMContentLoaded", () => {
  initFormDefaults();
  loadOptions();
  initPositionChart();
});

function initFormDefaults() {
  const now = new Date();
  const isoLocal = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  const openedInput = document.getElementById("opened_at");
  if (openedInput) openedInput.value = isoLocal;
}

function loadOptions() {
  fetch("/api/v1/options")
    .then(r => r.json())
    .then(options => {
      const selectIds = [
        "priority", "impact", "urgency", "category", "subcategory",
        "u_symptom", "assignment_group", "location", "contact_type",
        "opened_by", "sys_created_by"
      ];

      selectIds.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;

        const items = options[id] || [];
        let html = '<option value="">Unknown / not provided</option>';

        items.forEach(opt => {
          if (opt.is_missing_marker) return;
          const countStr = opt.count ? ` (${opt.count.toLocaleString()} cases)` : "";
          html += `<option value="${opt.value}">${opt.value}${countStr}</option>`;
        });

        el.innerHTML = html;
      });

      // Set realistic initial defaults
      loadPreset("fast");
    });
}

function loadPreset(type) {
  const p = PRESETS[type];
  if (!p) return;

  Object.entries(p).forEach(([field, val]) => {
    const el = document.getElementById(field);
    if (el) el.value = val;
  });

  submitPrediction();
}

function submitPrediction() {
  const payload = {
    opened_at: document.getElementById("opened_at").value || new Date().toISOString(),
    priority: document.getElementById("priority").value || null,
    impact: document.getElementById("impact").value || null,
    urgency: document.getElementById("urgency").value || null,
    category: document.getElementById("category").value || null,
    subcategory: document.getElementById("subcategory").value || null,
    u_symptom: document.getElementById("u_symptom").value || null,
    assignment_group: document.getElementById("assignment_group").value || null,
    location: document.getElementById("location").value || null,
    contact_type: document.getElementById("contact_type").value || null,
    opened_by: document.getElementById("opened_by").value || null,
    sys_created_by: document.getElementById("sys_created_by").value || null,
  };

  fetch("/api/v1/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(r => {
      if (!r.ok) {
        return r.json().then(err => { throw err; });
      }
      return r.json();
    })
    .then(data => {
      displayPredictionResult(data);
    })
    .catch(err => {
      alert("Prediction error: " + (err.detail || JSON.stringify(err)));
    });
}

function displayPredictionResult(data) {
  document.getElementById("placeholderText").style.display = "none";
  document.getElementById("resultContent").style.display = "block";

  const hours = data.predicted_hours;
  document.getElementById("predictedDurationValue").textContent = `${hours.toFixed(2)} h`;
  document.getElementById("predictedHumanValue").textContent = data.predicted_human;

  // Velocity badge
  const badge = document.getElementById("velocityBadge");
  if (hours < 1.0) {
    badge.className = "badge badge-fast";
    badge.textContent = "Fast (< 1h)";
  } else if (hours < 24.0) {
    badge.className = "badge badge-moderate";
    badge.textContent = "Standard (1–24h)";
  } else {
    badge.className = "badge badge-slow";
    badge.textContent = "High Latency (> 24h)";
  }

  // Range 80%
  const r80 = data.range_80;
  document.getElementById("range80Value").innerHTML = 
    `<span>${r80.q10_hours} h</span> &mdash; <span>${r80.q90_hours} h</span> <small style="font-weight: normal; color: var(--text-muted);">(Median: ${r80.q50_hours} h)</small>`;
  document.getElementById("rangeInterpretation").textContent = r80.text;
  document.getElementById("prob24hValue").textContent = `${data.prob_over_24h}%`;

  // Warnings
  const warnContainer = document.getElementById("warningsContainer");
  const warnList = document.getElementById("warningsList");
  if (data.warnings && data.warnings.length > 0) {
    warnContainer.style.display = "block";
    warnList.innerHTML = "<strong>Warnings:</strong><br>" + data.warnings.map(w => `&bull; ${w}`).join("<br>");
  } else {
    warnContainer.style.display = "none";
  }

  // What-If delta update
  if (whatIfModeActive && lastPrediction !== null) {
    document.getElementById("whatIfCard").style.display = "block";
    document.getElementById("whatIfPrev").textContent = `${lastPrediction.predicted_hours.toFixed(2)} h`;
    document.getElementById("whatIfNew").textContent = `${hours.toFixed(2)} h`;

    const delta = hours - lastPrediction.predicted_hours;
    const deltaPct = lastPrediction.predicted_hours > 0 ? (delta / lastPrediction.predicted_hours * 100) : 0;
    const sign = delta > 0 ? "+" : "";

    const deltaEl = document.getElementById("whatIfDelta");
    deltaEl.textContent = `Delta: ${sign}${delta.toFixed(2)} h (${sign}${deltaPct.toFixed(1)}%)`;
    deltaEl.style.color = delta > 0 ? "var(--accent-danger)" : "var(--accent-success)";
  }

  lastPrediction = data;
  updatePositionChart(hours);
}

function toggleWhatIfMode() {
  whatIfModeActive = !whatIfModeActive;
  const btn = document.getElementById("btnWhatIf");
  const card = document.getElementById("whatIfCard");

  if (whatIfModeActive) {
    btn.className = "btn btn-primary";
    btn.textContent = "What-If Active (Click to Exit)";
    if (lastPrediction) {
      card.style.display = "block";
      document.getElementById("whatIfPrev").textContent = `${lastPrediction.predicted_hours.toFixed(2)} h`;
      document.getElementById("whatIfNew").textContent = `${lastPrediction.predicted_hours.toFixed(2)} h`;
      document.getElementById("whatIfDelta").textContent = "Modify any ticket attribute above to compare.";
    }
  } else {
    btn.className = "btn btn-secondary";
    btn.textContent = "What-If Mode";
    card.style.display = "none";
  }
}

function initPositionChart() {
  fetch("/api/v1/eda/target-distribution")
    .then(r => r.json())
    .then(data => {
      distData = data;
      const hist = data.log_histogram || [];
      const labels = hist.map(h => `${h.bin_start}`);
      const counts = hist.map(h => h.count);

      const ctx = document.getElementById("predictionPosChart").getContext("2d");
      posChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "Historical Distribution",
            data: counts,
            backgroundColor: "#94a3b8",
            borderRadius: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { display: false },
            y: { display: false }
          }
        }
      });
    });
}

function updatePositionChart(predictedHours) {
  if (!posChart || !distData) return;

  const logVal = Math.log10(1 + predictedHours);
  const hist = distData.log_histogram || [];

  // Find matching bin index
  let matchIdx = -1;
  for (let i = 0; i < hist.length; i++) {
    if (logVal >= hist[i].bin_start && logVal < hist[i].bin_end) {
      matchIdx = i;
      break;
    }
  }
  if (matchIdx === -1 && logVal >= hist[hist.length - 1].bin_end) {
    matchIdx = hist.length - 1;
  }

  const bgColors = hist.map((_, i) => (i === matchIdx ? "#2563eb" : "#cbd5e1"));
  posChart.data.datasets[0].backgroundColor = bgColors;
  posChart.update();
}

function switchPredictTab(tab) {
  const singleBtn = document.getElementById("tabSingleBtn");
  const batchBtn = document.getElementById("tabBatchBtn");
  const singleContent = document.getElementById("tabSingleContent");
  const batchContent = document.getElementById("tabBatchContent");

  if (tab === "single") {
    singleBtn.className = "btn btn-primary";
    batchBtn.className = "btn btn-secondary";
    singleContent.style.display = "block";
    batchContent.style.display = "none";
  } else {
    singleBtn.className = "btn btn-secondary";
    batchBtn.className = "btn btn-primary";
    singleContent.style.display = "none";
    batchContent.style.display = "block";
  }
}

// Batch CSV Processing
function downloadCsvTemplate() {
  const headers = [
    "opened_at", "priority", "impact", "urgency", "category",
    "subcategory", "u_symptom", "assignment_group", "location",
    "contact_type", "opened_by", "sys_created_by"
  ];
  const row1 = [
    "2016-05-12T14:30:00", "3 - Moderate", "2 - Medium", "2 - Medium", "Category 26",
    "Subcategory 174", "Symptom 491", "Group 70", "Location 204",
    "Phone", "Opened by  17", "Created by 10"
  ];
  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), row1.join(",")].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "incident_batch_template.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function handleBatchFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    parseAndScoreBatchCsv(text);
  };
  reader.readAsText(file);
}

function parseAndScoreBatchCsv(csvText) {
  const lines = csvText.trim().split("\n");
  if (lines.length < 2) {
    alert("CSV file is empty or missing data rows.");
    return;
  }

  const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
  
  // Anti-leakage check on CSV headers
  const forbidden = ["resolved_at", "closed_at", "reassignment_count", "reopen_count", "sys_mod_count", "incident_state", "active", "made_sla"];
  const violations = headers.filter(h => forbidden.includes(h.toLowerCase()));
  if (violations.length > 0) {
    alert(`Anti-leakage protection error: CSV contains forbidden post-opening columns: ${violations.join(", ")}. Please remove them.`);
    return;
  }

  const incidents = [];
  for (let i = 1; i < lines.length && incidents.length < 500; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const vals = line.split(",").map(v => v.trim().replace(/^"|"$/g, ""));
    const inc = {};
    headers.forEach((h, idx) => {
      inc[h] = vals[idx] && vals[idx] !== "" ? vals[idx] : null;
    });
    if (!inc.opened_at) inc.opened_at = new Date().toISOString();
    incidents.push(inc);
  }

  document.getElementById("batchProgress").style.display = "block";
  document.getElementById("batchResultsSection").style.display = "none";

  fetch("/api/v1/predict/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incidents: incidents })
  })
    .then(r => {
      if (!r.ok) return r.json().then(e => { throw e; });
      return r.json();
    })
    .then(data => {
      batchResultsData = data.predictions || [];
      renderBatchResults(incidents, batchResultsData);
    })
    .catch(err => {
      alert("Batch inference failed: " + (err.detail || JSON.stringify(err)));
    })
    .finally(() => {
      document.getElementById("batchProgress").style.display = "none";
    });
}

function renderBatchResults(inputs, results) {
  document.getElementById("batchResultsSection").style.display = "block";
  document.getElementById("batchSummaryTitle").textContent = `Batch Results: ${results.length} Incidents Scored`;

  const tbody = document.getElementById("batchResultsBody");
  tbody.innerHTML = results.map((res, i) => {
    const inp = inputs[i] || {};
    return `
      <tr>
        <td>${i + 1}</td>
        <td><code>${inp.opened_at || '-'}</code></td>
        <td>${inp.priority || '-'}</td>
        <td>${inp.category || '-'}</td>
        <td>${inp.assignment_group || '-'}</td>
        <td><strong style="color: var(--brand-primary);">${res.predicted_hours.toFixed(2)} h</strong></td>
        <td>${res.predicted_human}</td>
        <td>[${res.range_80.q10_hours}h &mdash; ${res.range_80.q90_hours}h]</td>
        <td>${res.warnings.length > 0 ? `<span class="badge badge-slow">${res.warnings.length} warning(s)</span>` : '<span class="badge badge-fast">Valid</span>'}</td>
      </tr>
    `;
  }).join("");
}

function exportBatchResultsCsv() {
  if (batchResultsData.length === 0) return;

  const headers = ["row", "predicted_hours", "predicted_human", "range_80_q10", "range_80_q90", "prob_over_24h", "model_version", "warnings"];
  const rows = batchResultsData.map((r, idx) => [
    idx + 1,
    r.predicted_hours,
    `"${r.predicted_human}"`,
    r.range_80.q10_hours,
    r.range_80.q90_hours,
    r.prob_over_24h,
    r.model_version,
    `"${r.warnings.join('; ')}"`
  ]);

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "batch_predictions_output.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
