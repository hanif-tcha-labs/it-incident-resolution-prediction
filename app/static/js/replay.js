// Stream replay and label delay simulation

const REPLAY_STORAGE_KEY = "htvex-live-simulator-state";
const REPLAY_STATE_VERSION = 1;
let allTestIncidents = [];
let simCurrentTime = null;
let simInterval = null;
let isPlaying = false;
let isProcessing = false;
let simSpeed = 3600; // default 1 simulated hour per real second

let activeIncidents = [];
let resolvedIncidents = [];

let totalAbsModelErr = 0;
let totalAbsBaseErr = 0;
let scatterPoints = [];

let liveMaeChart = null;
let liveScatterChart = null;

const BASELINE_MEDIAN = 2.60; // test set baseline median

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  loadTestIncidents();
});

window.addEventListener("pagehide", persistReplayState);

function initCharts() {
  const ctxMae = document.getElementById("liveMaeChart").getContext("2d");
  liveMaeChart = new Chart(ctxMae, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Model MAE (hours)",
          data: [],
          borderColor: "#2563eb",
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "Baseline MAE (hours)",
          data: [],
          borderColor: "#ef4444",
          borderDash: [4, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.2,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: true, title: { display: true, text: "MAE (hours)" } }
      }
    }
  });

  const ctxScatter = document.getElementById("liveScatterChart").getContext("2d");
  liveScatterChart = new Chart(ctxScatter, {
    type: "scatter",
    data: {
      datasets: [{
        label: "Resolved Incidents",
        data: [],
        backgroundColor: "rgba(37, 99, 235, 0.4)",
        pointRadius: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { type: "linear", position: "bottom", title: { display: true, text: "Actual Duration (hours)" }, min: 0 },
        y: { title: { display: true, text: "Predicted Duration (hours)" }, min: 0 }
      }
    }
  });
}

function loadTestIncidents() {
  // Load first 500 incidents to start streaming immediately
  fetch("/api/v1/simulation/incidents?offset=0&limit=500")
    .then(response => {
      if (!response.ok) {
        throw new Error(`Unable to load incidents (HTTP ${response.status}).`);
      }
      return response.json();
    })
    .then(data => {
      allTestIncidents = (data.incidents || []).map(inc => {
        const openedDate = new Date(inc.opened_at);
        const resolveDate = new Date(openedDate.getTime() + inc.resolution_hours * 3600 * 1000);
        return {
          ...inc,
          opened_date: openedDate,
          resolve_date: resolveDate,
          is_opened: false,
          is_resolved: false,
          prediction: null
        };
      });

      if (allTestIncidents.length > 0) {
        simCurrentTime = new Date(allTestIncidents[0].opened_date.getTime() - 60000);
        const resumePlayback = restoreReplayState();
        updateClockDisplay();
        restoreDashboard();
        if (resumePlayback !== null) updatePlaybackControls();
        if (resumePlayback) {
          processEvents().then(() => {
            if (isPlaying) simInterval = setInterval(tick, 100);
          });
        }
      }
    })
    .catch(showReplayError);
}

function persistReplayState() {
  if (!simCurrentTime || allTestIncidents.length === 0) return;

  const state = {
    version: REPLAY_STATE_VERSION,
    currentTime: simCurrentTime.toISOString(),
    speed: simSpeed,
    playing: isPlaying,
    savedAt: Date.now(),
    incidents: allTestIncidents.map(inc => ({
      number: inc.number,
      isOpened: inc.is_opened,
      isResolved: inc.is_resolved,
      prediction: inc.prediction
    }))
  };

  try {
    localStorage.setItem(REPLAY_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error("Unable to save live simulator progress.", error);
  }
}

function restoreReplayState() {
  const storedState = localStorage.getItem(REPLAY_STORAGE_KEY);
  if (!storedState) return null;

  const state = JSON.parse(storedState);
  if (
    state.version !== REPLAY_STATE_VERSION ||
    !Array.isArray(state.incidents) ||
    state.incidents.length !== allTestIncidents.length ||
    !Number.isFinite(state.savedAt) ||
    ![60, 3600, 86400].includes(state.speed) ||
    typeof state.playing !== "boolean"
  ) {
    throw new Error("Saved live simulator progress is invalid.");
  }

  const savedTime = new Date(state.currentTime);
  if (Number.isNaN(savedTime.getTime())) {
    throw new Error("Saved live simulator time is invalid.");
  }

  const savedIncidents = new Map(state.incidents.map(inc => [inc.number, inc]));
  allTestIncidents.forEach(inc => {
    const savedIncident = savedIncidents.get(inc.number);
    if (
      !savedIncident ||
      typeof savedIncident.isOpened !== "boolean" ||
      typeof savedIncident.isResolved !== "boolean"
    ) {
      throw new Error("Saved live simulator incidents do not match the current replay data.");
    }

    inc.is_opened = savedIncident.isOpened;
    inc.is_resolved = savedIncident.isResolved;
    inc.prediction = savedIncident.prediction;
  });

  simSpeed = state.speed;
  updateSpeedControls();
  simCurrentTime = savedTime;
  if (state.playing) {
    const elapsedSeconds = Math.max(0, Date.now() - state.savedAt) / 1000;
    simCurrentTime = new Date(simCurrentTime.getTime() + elapsedSeconds * simSpeed * 1000);
  }
  isPlaying = state.playing;
  return state.playing;
}

function restoreDashboard() {
  activeIncidents = allTestIncidents
    .filter(inc => inc.is_opened && !inc.is_resolved)
    .reverse();
  resolvedIncidents = allTestIncidents.filter(inc => inc.is_resolved).reverse();

  totalAbsModelErr = 0;
  totalAbsBaseErr = 0;
  scatterPoints = [];
  const modelMae = [];
  const baselineMae = [];
  let cumulativeModelError = 0;
  let cumulativeBaselineError = 0;

  resolvedIncidents.slice().reverse().forEach((inc, index) => {
    const predictedHours = inc.prediction ? inc.prediction.predicted_hours : BASELINE_MEDIAN;
    const actualHours = inc.resolution_hours;
    const modelError = Math.abs(predictedHours - actualHours);
    const baselineError = Math.abs(BASELINE_MEDIAN - actualHours);

    totalAbsModelErr += modelError;
    totalAbsBaseErr += baselineError;
    cumulativeModelError += modelError;
    cumulativeBaselineError += baselineError;
    scatterPoints.push({ x: actualHours, y: predictedHours });
    modelMae.push(cumulativeModelError / (index + 1));
    baselineMae.push(cumulativeBaselineError / (index + 1));
  });

  const firstVisiblePoint = Math.max(0, modelMae.length - 60);
  liveMaeChart.data.labels = modelMae.slice(firstVisiblePoint).map((_, index) => firstVisiblePoint + index + 1);
  liveMaeChart.data.datasets[0].data = modelMae.slice(firstVisiblePoint);
  liveMaeChart.data.datasets[1].data = baselineMae.slice(firstVisiblePoint);
  liveMaeChart.update();
  liveScatterChart.data.datasets[0].data = scatterPoints.slice(-100);
  liveScatterChart.update();

  updateDashboardKPIs();
  renderActiveTable();
  renderResolvedTable();
  document.getElementById("scatterCountBadge").textContent = `${scatterPoints.length} points`;
}

function updatePlaybackControls() {
  document.getElementById("playPauseLabel").textContent = isPlaying ? "Pause Stream" : "Resume Stream";
  document.getElementById("playPauseIcon").innerHTML = isPlaying
    ? '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>'
    : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
}

function showReplayError(error) {
  console.error("Live simulator error.", error);
  if (isPlaying) pauseReplay();

  const errorBanner = document.getElementById("simError");
  if (errorBanner) {
    errorBanner.textContent = `Replay paused: ${error.message || "Unable to load simulation data."}`;
    errorBanner.style.display = "flex";
  }
}

function clearReplayError() {
  const errorBanner = document.getElementById("simError");
  if (errorBanner) errorBanner.style.display = "none";
}

function updateClockDisplay() {
  if (!simCurrentTime) return;
  const str = simCurrentTime.toISOString().replace("T", " ").slice(0, 19);
  document.getElementById("simClockDisplay").textContent = str;
}

function togglePlayPause() {
  if (isPlaying) {
    pauseReplay();
  } else {
    startReplay();
  }
}

function startReplay() {
  if (isPlaying) return;
  if (!simCurrentTime && allTestIncidents.length > 0) {
    simCurrentTime = new Date(allTestIncidents[0].opened_date.getTime() - 60000);
  }
  isPlaying = true;
  clearReplayError();
  updatePlaybackControls();
  persistReplayState();
  processEvents().then(() => {
    if (isPlaying) simInterval = setInterval(tick, 100);
  });
}

function pauseReplay() {
  isPlaying = false;
  if (simInterval) clearInterval(simInterval);
  simInterval = null;
  updatePlaybackControls();
  persistReplayState();
}

function setSpeed(spd) {
  simSpeed = spd;
  updateSpeedControls();
  persistReplayState();
}

function updateSpeedControls() {
  document.getElementById("spd1").className = simSpeed === 60 ? "btn btn-sm btn-primary" : "btn btn-sm";
  document.getElementById("spd2").className = simSpeed === 3600 ? "btn btn-sm btn-primary" : "btn btn-sm";
  document.getElementById("spd3").className = simSpeed === 86400 ? "btn btn-sm btn-primary" : "btn btn-sm";
}

function stepClockHours(hours) {
  if (!simCurrentTime) return;
  simCurrentTime = new Date(simCurrentTime.getTime() + hours * 3600 * 1000);
  updateClockDisplay();
  processEvents();
}

function jumpToNextEvent() {
  if (!simCurrentTime) return;
  // Find next opening or resolution
  let nextTime = null;
  allTestIncidents.forEach(inc => {
    if (!inc.is_opened && (!nextTime || inc.opened_date < nextTime)) {
      nextTime = inc.opened_date;
    }
  });
  activeIncidents.forEach(inc => {
    if (!inc.is_resolved && (!nextTime || inc.resolve_date < nextTime)) {
      nextTime = inc.resolve_date;
    }
  });

  if (nextTime) {
    simCurrentTime = new Date(nextTime.getTime() + 1000);
    updateClockDisplay();
    processEvents();
  }
}

function resetReplay() {
  pauseReplay();
  if (allTestIncidents.length > 0) {
    simCurrentTime = new Date(allTestIncidents[0].opened_date.getTime() - 60000);
    updateClockDisplay();
  }
  allTestIncidents.forEach(inc => {
    inc.is_opened = false;
    inc.is_resolved = false;
    inc.prediction = null;
  });
  activeIncidents = [];
  resolvedIncidents = [];
  totalAbsModelErr = 0;
  totalAbsBaseErr = 0;
  scatterPoints = [];

  document.getElementById("kpiActiveCount").textContent = "0";
  document.getElementById("kpiResolvedCount").textContent = "0";
  document.getElementById("kpiCurrentModelMae").textContent = "-- h";
  document.getElementById("kpiCurrentBaseMae").textContent = "-- h";
  document.getElementById("activeBadgeCount").textContent = "0 Open";
  document.getElementById("resolvedBadgeCount").textContent = "0 Resolved";
  document.getElementById("scatterCountBadge").textContent = "0 points";

  document.getElementById("activeTableBody").innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No active tickets opened yet. Start the stream.</td></tr>';
  document.getElementById("resolvedTableBody").innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tickets resolved yet in simulated time.</td></tr>';

  liveMaeChart.data.labels = [];
  liveMaeChart.data.datasets[0].data = [];
  liveMaeChart.data.datasets[1].data = [];
  liveMaeChart.update();

  liveScatterChart.data.datasets[0].data = [];
  liveScatterChart.update();
  clearReplayError();
  persistReplayState();
}

function tick() {
  if (!simCurrentTime || isProcessing) return;
  // Advance simulated time
  simCurrentTime = new Date(simCurrentTime.getTime() + (simSpeed * 0.1) * 1000);
  updateClockDisplay();
  processEvents();
}

async function processEvents() {
  if (isProcessing) return;
  isProcessing = true;
  const newlyOpened = [];

  try {
    allTestIncidents.forEach(inc => {
      if (!inc.is_opened && inc.opened_date <= simCurrentTime) {
        inc.is_opened = true;
        activeIncidents.unshift(inc);
        newlyOpened.push(inc);
      } else if (inc.is_opened && !inc.is_resolved && !inc.prediction) {
        newlyOpened.push(inc);
      }
    });

    if (newlyOpened.length > 0) {
      renderActiveTable();
      const batchPayload = newlyOpened.map(inc => ({
        opened_at: inc.opened_at,
        priority: inc.priority,
        impact: inc.impact,
        urgency: inc.urgency,
        category: inc.category,
        subcategory: inc.subcategory,
        u_symptom: inc.u_symptom,
        assignment_group: inc.assignment_group,
        location: inc.location,
        contact_type: inc.contact_type,
        opened_by: inc.opened_by,
        sys_created_by: inc.sys_created_by,
      }));

      const response = await fetch("/api/v1/predict/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incidents: batchPayload })
      });
      if (!response.ok) {
        throw new Error(`Unable to score incidents (HTTP ${response.status}).`);
      }

      const result = await response.json();
      if (!Array.isArray(result.predictions) || result.predictions.length !== newlyOpened.length) {
        throw new Error("The prediction service returned an unexpected response.");
      }
      result.predictions.forEach((prediction, index) => {
        newlyOpened[index].prediction = prediction;
      });
    }

    const remainingActive = [];
    let newResolutions = 0;

    activeIncidents.forEach(inc => {
      if (inc.resolve_date <= simCurrentTime) {
        inc.is_resolved = true;
        resolvedIncidents.unshift(inc);
        newResolutions++;

        const predictedHours = inc.prediction ? inc.prediction.predicted_hours : BASELINE_MEDIAN;
        const actualHours = inc.resolution_hours;

        totalAbsModelErr += Math.abs(predictedHours - actualHours);
        totalAbsBaseErr += Math.abs(BASELINE_MEDIAN - actualHours);
        scatterPoints.push({ x: actualHours, y: predictedHours });
      } else {
        remainingActive.push(inc);
      }
    });

    activeIncidents = remainingActive;

    if (newlyOpened.length > 0 || newResolutions > 0) {
      updateDashboardKPIs();
      renderActiveTable();
      renderResolvedTable();
      updateCharts();
    }
    persistReplayState();
  } catch (error) {
    newlyOpened.forEach(inc => {
      inc.is_opened = false;
      inc.prediction = null;
      activeIncidents = activeIncidents.filter(active => active !== inc);
    });
    updateDashboardKPIs();
    renderActiveTable();
    showReplayError(error);
    persistReplayState();
  } finally {
    isProcessing = false;
  }
}

function updateDashboardKPIs() {
  document.getElementById("kpiActiveCount").textContent = activeIncidents.length.toLocaleString();
  document.getElementById("kpiResolvedCount").textContent = resolvedIncidents.length.toLocaleString();
  document.getElementById("activeBadgeCount").textContent = `${activeIncidents.length} Open`;
  document.getElementById("resolvedBadgeCount").textContent = `${resolvedIncidents.length} Resolved`;

  const n = resolvedIncidents.length;
  if (n > 0) {
    const curModelMae = totalAbsModelErr / n;
    const curBaseMae = totalAbsBaseErr / n;

    document.getElementById("kpiCurrentModelMae").textContent = `${curModelMae.toFixed(1)} h`;
    document.getElementById("kpiCurrentBaseMae").textContent = `${curBaseMae.toFixed(1)} h`;

    const gain = curBaseMae > 0 ? ((curBaseMae - curModelMae) / curBaseMae * 100) : 0;
    document.getElementById("kpiMaeDelta").textContent = `Delta: -${(curBaseMae - curModelMae).toFixed(1)} h (${gain.toFixed(1)}%)`;
  }
}

function renderActiveTable() {
  const tbody = document.getElementById("activeTableBody");
  if (activeIncidents.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No active tickets in progress.</td></tr>';
    return;
  }

  // Show top 25 recent active
  const topActive = activeIncidents.slice(0, 25);
  tbody.innerHTML = topActive.map(inc => {
    const pred = inc.prediction;
    const predText = pred ? `${pred.predicted_hours.toFixed(1)} h` : '<em>Scoring...</em>';
    const rangeText = pred ? `[${pred.range_80.q10_hours}h - ${pred.range_80.q90_hours}h]` : '--';

    return `
      <tr>
        <td><strong>${inc.number}</strong></td>
        <td><code>${inc.opened_at.split(" ")[1]}</code></td>
        <td>${inc.assignment_group || '-'}</td>
        <td><strong style="color: var(--brand-primary);">${predText}</strong></td>
        <td><small>${rangeText}</small></td>
      </tr>
    `;
  }).join("");
}

function renderResolvedTable() {
  const tbody = document.getElementById("resolvedTableBody");
  if (resolvedIncidents.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tickets resolved yet in simulated time.</td></tr>';
    return;
  }

  // Show top 25 recent resolved
  const topResolved = resolvedIncidents.slice(0, 25);
  tbody.innerHTML = topResolved.map(inc => {
    const predHours = inc.prediction ? inc.prediction.predicted_hours : BASELINE_MEDIAN;
    const actualHours = inc.resolution_hours;
    const err = predHours - actualHours;
    const isOver = err > 0;

    return `
      <tr>
        <td><strong>${inc.number}</strong></td>
        <td>${predHours.toFixed(1)} h</td>
        <td><strong style="color: var(--text-primary);">${actualHours.toFixed(1)} h</strong></td>
        <td><span style="color: ${Math.abs(err) > 20 ? 'var(--accent-danger)' : 'var(--accent-success)'}; font-weight: 600;">${isOver ? '+' : ''}${err.toFixed(1)} h</span></td>
        <td><span class="badge ${isOver ? 'badge-moderate' : 'badge-slow'}">${isOver ? 'Over-estimated' : 'Under-estimated'}</span></td>
      </tr>
    `;
  }).join("");
}

function updateCharts() {
  const n = resolvedIncidents.length;
  if (n === 0) return;

  const curModelMae = totalAbsModelErr / n;
  const curBaseMae = totalAbsBaseErr / n;

  // Update Line Chart (limit to 60 points)
  if (liveMaeChart.data.labels.length > 60) {
    liveMaeChart.data.labels.shift();
    liveMaeChart.data.datasets[0].data.shift();
    liveMaeChart.data.datasets[1].data.shift();
  }

  liveMaeChart.data.labels.push(n);
  liveMaeChart.data.datasets[0].data.push(curModelMae.toFixed(1));
  liveMaeChart.data.datasets[1].data.push(curBaseMae.toFixed(1));
  liveMaeChart.update();

  // Update Scatter Plot (limit to 100 points)
  document.getElementById("scatterCountBadge").textContent = `${scatterPoints.length} points`;
  const recentPoints = scatterPoints.slice(-100);
  liveScatterChart.data.datasets[0].data = recentPoints;
  liveScatterChart.update();
}
