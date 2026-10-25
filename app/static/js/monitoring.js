// Monitoring & Prediction Audit Log Client Script

let durationChart = null;
let auditLogRecords = [];

document.addEventListener("DOMContentLoaded", () => {
  loadMonitoringSummary();
  loadAuditLog();

  const searchInput = document.getElementById("logSearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      filterAuditLog(e.target.value.toLowerCase());
    });
  }
});

function loadMonitoringSummary() {
  fetch("/api/v1/monitoring/summary")
    .then(r => r.json())
    .then(data => {
      document.getElementById("monTotalCount").textContent = data.total_predictions.toLocaleString();
      document.getElementById("monWarningRate").textContent = `${data.warning_rate_pct}%`;
      
      if (data.median_predicted_hours !== null) {
        document.getElementById("monMedianDuration").textContent = `${data.median_predicted_hours} h`;
      } else {
        document.getElementById("monMedianDuration").textContent = "-- h";
      }

      // Drift index
      const driftEl = document.getElementById("monDriftIndex");
      if (data.warning_rate_pct > 15) {
        driftEl.textContent = "High Drift";
        driftEl.style.color = "var(--accent-danger)";
      } else if (data.warning_rate_pct > 5) {
        driftEl.textContent = "Moderate Drift";
        driftEl.style.color = "var(--accent-warning)";
      } else {
        driftEl.textContent = "Nominal";
        driftEl.style.color = "var(--accent-success)";
      }

      // Render duration donut chart
      const buckets = data.duration_distribution || {};
      const u1 = buckets.under_1h || 0;
      const u24 = buckets["1_to_24h"] || 0;
      const o24 = buckets.over_24h || 0;

      const ctx = document.getElementById("durationDonutChart").getContext("2d");
      durationChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: ["Under 1 hour", "1 to 24 hours", "Over 24 hours"],
          datasets: [{
            data: [u1, u24, o24],
            backgroundColor: ["#10b981", "#3b82f6", "#ef4444"],
            borderWidth: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right" }
          }
        }
      });
    });
}

function loadAuditLog() {
  fetch("/api/v1/monitoring/predictions?limit=100")
    .then(r => r.json())
    .then(records => {
      auditLogRecords = records || [];
      renderAuditLogTable(auditLogRecords);
    });
}

function renderAuditLogTable(records) {
  const tbody = document.getElementById("auditLogBody");
  if (!records || records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No inferences logged yet. Predict an incident to generate audit logs.</td></tr>';
    return;
  }

  tbody.innerHTML = records.map(r => {
    const inp = r.inputs || {};
    const out = r.output || {};
    const range = out.range_80 || {};
    const rangeText = range.q10_hours !== undefined ? `[${range.q10_hours}h - ${range.q90_hours}h]` : '--';
    const warnings = out.warnings || [];

    const groupCat = `${inp.assignment_group || '-'} / ${inp.category || '-'}`;
    const idShort = r.id ? r.id.slice(0, 8) + '...' : '-';
    const timeShort = r.timestamp ? r.timestamp.replace("T", " ").slice(0, 19) : '-';

    return `
      <tr>
        <td><code>${idShort}</code></td>
        <td><small>${timeShort}</small></td>
        <td><small>${inp.opened_at ? inp.opened_at.replace("T", " ").slice(0, 16) : '-'}</small></td>
        <td><strong>${groupCat}</strong></td>
        <td><strong style="color: var(--brand-primary);">${r.predicted_hours.toFixed(2)} h</strong></td>
        <td><small>${rangeText}</small></td>
        <td>${warnings.length > 0 ? `<span class="badge badge-slow">${warnings.length} warning(s)</span>` : '<span class="badge badge-fast">Clean</span>'}</td>
      </tr>
    `;
  }).join("");
}

function filterAuditLog(query) {
  if (!query) {
    renderAuditLogTable(auditLogRecords);
    return;
  }

  const filtered = auditLogRecords.filter(r => {
    const inp = r.inputs || {};
    const str = `${inp.assignment_group || ''} ${inp.category || ''} ${r.id || ''}`.toLowerCase();
    return str.includes(query);
  });

  renderAuditLogTable(filtered);
}

function exportAuditLogCsv() {
  if (auditLogRecords.length === 0) return;

  const headers = ["id", "timestamp", "opened_at", "assignment_group", "category", "predicted_hours", "has_warnings"];
  const rows = auditLogRecords.map(r => {
    const inp = r.inputs || {};
    return [
      r.id,
      r.timestamp,
      inp.opened_at || '',
      `"${inp.assignment_group || ''}"`,
      `"${inp.category || ''}"`,
      r.predicted_hours,
      r.has_warnings ? 1 : 0
    ];
  });

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "prediction_audit_log.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
