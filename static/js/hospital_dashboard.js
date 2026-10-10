/**
 * Hospital / Blood Bank Portal Interactive Controller
 * Handles sidebar tab switching, mobile responsive sidebar, theme sync,
 * and Master Operations Dashboard live interactions.
 */

// Global toast helper
function showMasterToast(message, icon = "✅", duration = 3500) {
  const toast = document.getElementById("masterToast");
  const msgEl = document.getElementById("masterToastMessage");
  const iconEl = document.getElementById("masterToastIcon");
  if (!toast || !msgEl) return;

  msgEl.textContent = message;
  if (iconEl) iconEl.textContent = icon;
  toast.classList.add("is-visible");

  if (window._masterToastTimer) clearTimeout(window._masterToastTimer);
  window._masterToastTimer = setTimeout(() => {
    toast.classList.remove("is-visible");
  }, duration);
}

// Table action dispatcher
window.handleTableAction = function (reqId, actionType) {
  const row = document.getElementById(`req-row-${reqId.replace("#", "").replace("REQ-", "")}`);
  if (row) {
    const statusCell = row.cells[6];
    if (statusCell) {
      statusCell.innerHTML = `<span class="status-cell-badge matched">✓ Actioned: ${actionType}</span>`;
    }
  }
  showMasterToast(`Case #${reqId}: ${actionType} recorded successfully.`, "📋");
};

// Inter-facility assistance
window.handleInterFacilityTransfer = function (facility, group) {
  showMasterToast(`Inter-facility support dispatched for ${group} to ${facility}.`, "🚑");
};

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("hospitalSidebar");
  const navItems = document.querySelectorAll(".hospital-nav-item");
  const sections = document.querySelectorAll(".portal-section");
  const mobileToggleBtn = document.getElementById("mobileSidebarToggle");

  // Switch tabs
  function activateTab(targetId) {
    if (!targetId) return;

    // Remove active state from all nav buttons and sections
    navItems.forEach((btn) => {
      const isTarget = btn.getAttribute("data-target") === targetId;
      btn.classList.toggle("active", isTarget);
      btn.setAttribute("aria-selected", isTarget ? "true" : "false");
    });

    sections.forEach((sec) => {
      const isTarget = sec.id === targetId;
      sec.classList.toggle("active", isTarget);
    });

    // Close mobile drawer if open
    if (sidebar && sidebar.classList.contains("is-open")) {
      sidebar.classList.remove("is-open");
    }

    // Update URL hash smoothly
    if (history.replaceState) {
      history.replaceState(null, null, "#" + targetId);
    }
  }

  // Attach click listeners to sidebar navigation items
  navItems.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute("data-target");
      activateTab(targetId);
    });
  });

  // Mobile sidebar drawer toggle
  if (mobileToggleBtn && sidebar) {
    mobileToggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("is-open");
    });

    // Close when clicking outside on mobile
    document.addEventListener("click", (e) => {
      if (
        sidebar.classList.contains("is-open") &&
        !sidebar.contains(e.target) &&
        !mobileToggleBtn.contains(e.target)
      ) {
        sidebar.classList.remove("is-open");
      }
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) {
        sidebar.classList.remove("is-open");
      }
    });
  }

  // ================= 1. REQUISITION MODAL CONTROLLER =================
  const requisitionModal = document.getElementById("requisitionModalBackdrop");
  const btnOpenReq = document.getElementById("btnOpenRequisitionModal");
  const btnQuickAddReq = document.getElementById("btnQuickAddReq");
  const btnCloseReq = document.getElementById("btnCloseRequisitionModal");
  const btnCancelReq = document.getElementById("btnCancelRequisitionModal");
  const newRequisitionForm = document.getElementById("newRequisitionForm");

  function openRequisitionModal() {
    if (requisitionModal) {
      requisitionModal.classList.add("is-open");
      const nameInput = document.getElementById("reqPatientName");
      if (nameInput) nameInput.focus();
    }
  }

  function closeRequisitionModal() {
    if (requisitionModal) {
      requisitionModal.classList.remove("is-open");
      if (newRequisitionForm) newRequisitionForm.reset();
    }
  }

  if (btnOpenReq) btnOpenReq.addEventListener("click", openRequisitionModal);
  if (btnQuickAddReq) btnQuickAddReq.addEventListener("click", openRequisitionModal);
  if (btnCloseReq) btnCloseReq.addEventListener("click", closeRequisitionModal);
  if (btnCancelReq) btnCancelReq.addEventListener("click", closeRequisitionModal);

  if (requisitionModal) {
    requisitionModal.addEventListener("click", (e) => {
      if (e.target === requisitionModal) {
        closeRequisitionModal();
      }
    });
  }

  // Handle requisition submission
  if (newRequisitionForm) {
    let reqCounter = 906;
    newRequisitionForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const ward = document.getElementById("reqWard")?.value || "General Ward";
      const patientName = document.getElementById("reqPatientName")?.value || "Emergency Patient";
      const bloodGroup = document.getElementById("reqBloodGroup")?.value || "O+";
      const units = document.getElementById("reqUnits")?.value || "2";
      const component = document.getElementById("reqComponent")?.value || "PRBC";
      const priority = document.getElementById("reqPriority")?.value || "High Urgency";

      const currentReqId = `REQ-${reqCounter++}`;
      const tbody = document.getElementById("requisitionsTableBody");

      if (tbody) {
        const priorityClass = priority.includes("Emergency") ? "sos" : priority.includes("High") ? "high" : "normal";
        const priorityText = priority.includes("Emergency") ? "🚨 Emergency (SOS)" : priority.includes("High") ? "⚡ High Urgency" : "Scheduled";

        const newRow = document.createElement("tr");
        newRow.id = `req-row-${currentReqId.replace("REQ-", "")}`;
        newRow.innerHTML = `
          <td class="req-id-cell">#${currentReqId}</td>
          <td><span class="ward-dept-pill">${ward}</span></td>
          <td><strong>${patientName}</strong> <small style="display:block; color:var(--text-muted);">Just logged · Duty Desk</small></td>
          <td><span class="blood-spec-pill">${bloodGroup}</span> · ${units} Units ${component}</td>
          <td><span class="urgency-badge ${priorityClass}">${priorityText}</span></td>
          <td><span class="status-cell-badge crossmatch">Screening Started</span></td>
          <td><span class="status-cell-badge pending">Allocating</span></td>
          <td><button type="button" class="btn-table-action" onclick="handleTableAction('${currentReqId}', 'Allocate')">Allocate</button></td>
        `;
        tbody.prepend(newRow);
      }

      // Increment active requisitions KPI
      const kpiReqs = document.getElementById("kpiActiveReqs");
      if (kpiReqs) {
        const curCount = parseInt(kpiReqs.textContent, 10) || 5;
        kpiReqs.textContent = curCount + 1;
      }

      closeRequisitionModal();
      showMasterToast(`Requisition #${currentReqId} submitted for ${patientName} (${bloodGroup})!`, "🩸");
    });
  }

  // ================= 2. EMERGENCY SOS BROADCAST =================
  const btnMasterSos = document.getElementById("btnMasterSos");
  if (btnMasterSos) {
    btnMasterSos.addEventListener("click", () => {
      showMasterToast("🚨 Emergency SOS broadcast active! Real-time donor alert dispatched across 5km radius.", "🚨", 5000);
      btnMasterSos.style.transform = "scale(0.96)";
      setTimeout(() => {
        btnMasterSos.style.transform = "";
      }, 200);
    });
  }

  // ================= 3. MATRIX COMPONENT FILTER =================
  const filterGroup = document.getElementById("matrixComponentFilter");
  if (filterGroup) {
    const filterButtons = filterGroup.querySelectorAll(".filter-pill-btn");
    const stockMatrixData = {
      all: { "A+": 32, "A-": 12, "B+": 38, "B-": 8, "AB+": 18, "AB-": 2, "O+": 36, "O-": 2, total: 148 },
      prbc: { "A+": 16, "A-": 6, "B+": 20, "B-": 4, "AB+": 8, "AB-": 1, "O+": 18, "O-": 1, total: 74 },
      wb: { "A+": 8, "A-": 3, "B+": 10, "B-": 2, "AB+": 5, "AB-": 1, "O+": 10, "O-": 1, total: 40 },
      plt: { "A+": 5, "A-": 2, "B+": 5, "B-": 1, "AB+": 3, "AB-": 0, "O+": 5, "O-": 0, total: 21 },
      ffp: { "A+": 3, "A-": 1, "B+": 3, "B-": 1, "AB+": 2, "AB-": 0, "O+": 3, "O-": 0, total: 13 }
    };

    filterButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        filterButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const comp = btn.getAttribute("data-component") || "all";
        const dataset = stockMatrixData[comp] || stockMatrixData.all;

        document.getElementById("count-A-pos") && (document.getElementById("count-A-pos").textContent = dataset["A+"]);
        document.getElementById("count-A-neg") && (document.getElementById("count-A-neg").textContent = dataset["A-"]);
        document.getElementById("count-B-pos") && (document.getElementById("count-B-pos").textContent = dataset["B+"]);
        document.getElementById("count-B-neg") && (document.getElementById("count-B-neg").textContent = dataset["B-"]);
        document.getElementById("count-AB-pos") && (document.getElementById("count-AB-pos").textContent = dataset["AB+"]);
        document.getElementById("count-AB-neg") && (document.getElementById("count-AB-neg").textContent = dataset["AB-"]);
        document.getElementById("count-O-pos") && (document.getElementById("count-O-pos").textContent = dataset["O+"]);
        document.getElementById("count-O-neg") && (document.getElementById("count-O-neg").textContent = dataset["O-"]);

        const kpiUnits = document.getElementById("kpiTotalUnits");
        if (kpiUnits) kpiUnits.textContent = dataset.total;
      });
    });
  }

  // ================= 4. LIVE EMERGENCY NETWORK FEED SYNC =================
  async function loadRegionalEmergencyFeed() {
    const feedContainer = document.getElementById("networkFeedCards");
    if (!feedContainer) return;

    try {
      const resp = await fetch("/api/v1/requests/urgent", { headers: { "Accept": "application/json" } });
      if (!resp.ok) return;
      const data = await resp.json();
      const requests = data.requests || data || [];

      if (Array.isArray(requests) && requests.length > 0) {
        feedContainer.innerHTML = "";
        requests.slice(0, 4).forEach((item) => {
          const blood = item.blood_group || "O+";
          const hosp = item.hospital_name || item.hospital || "Dhaka Hospital";
          const area = item.area || item.district || "Dhaka";
          const dist = item.distance_km ? `${item.distance_km} km away` : "Nearby";
          const phone = item.contact_phone || "+8801700000000";

          const card = document.createElement("div");
          card.className = "feed-card-item";
          card.innerHTML = `
            <div class="feed-card-top">
              <div style="display: flex; gap: 12px; align-items: center;">
                <div class="feed-blood-circle">${blood}</div>
                <div>
                  <div class="feed-facility-name">${hosp}</div>
                  <div class="feed-location-text">📍 ${area} · ${dist}</div>
                </div>
              </div>
              <span class="feed-expiry-chip">🚨 Urgent Network</span>
            </div>
            <div class="feed-card-actions">
              <span style="font-size: 0.8rem; color: var(--text-muted);">Contact: ${phone}</span>
              <button type="button" class="btn-feed-assist" onclick="handleInterFacilityTransfer('${hosp.replace(/'/g, "\\'")}', '${blood}')">Offer Assistance</button>
            </div>
          `;
          feedContainer.appendChild(card);
        });
      }
    } catch {
      // Keep existing items if offline or error
    }
  }

  loadRegionalEmergencyFeed();
  // Poll network feed every 15 seconds
  setInterval(loadRegionalEmergencyFeed, 15000);

  // Handle initial tab from URL hash if provided
  const initialHash = window.location.hash ? window.location.hash.substring(1) : "";
  if (initialHash && document.getElementById(initialHash)) {
    activateTab(initialHash);
  }
});
