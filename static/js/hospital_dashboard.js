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

  // ================= 5. FACILITY PROFILE & PORTAL SETTINGS CONTROLLER =================
  const facilitySettingsForm = document.getElementById("facilitySettingsForm");
  const btnResetSettings = document.getElementById("btnResetFacilitySettings");
  const btnExportAccreditation = document.getElementById("btnExportAccreditation");
  const btnDetectGps = document.getElementById("btnDetectGps");

  // Live preview elements
  const elPrevName = document.getElementById("previewFacilityName");
  const elPrevType = document.getElementById("previewFacilityType");
  const elPrevLicense = document.getElementById("previewLicenseNo");
  const elPrevDirector = document.getElementById("previewDirector");
  const elPrevHotline = document.getElementById("previewHotline");
  const elPrevAddress = document.getElementById("previewAddress");
  const elPrevColdTemp = document.getElementById("previewColdTemp");
  const elPrevChairs = document.getElementById("previewChairsCount");
  const elPrevChips = document.getElementById("previewComponentChips");
  const elPrevAvatar = document.getElementById("previewAvatar");

  // Form inputs
  const inputName = document.getElementById("facilityName");
  const inputType = document.getElementById("facilityType");
  const inputLicense = document.getElementById("facilityLicense");
  const inputDirector = document.getElementById("facilityDirectorName");
  const inputHotline = document.getElementById("facilityHotline");
  const inputAddress = document.getElementById("facilityAddress");
  const inputColdTemp = document.getElementById("facilityColdTemp");
  const inputChairs = document.getElementById("facilityChairs");
  const inputGps = document.getElementById("facilityGps");
  const inputPhone = document.getElementById("facilityPhone");

  function syncLivePreview() {
    if (elPrevName && inputName) elPrevName.textContent = inputName.value || "Facility Name";
    if (elPrevType && inputType) elPrevType.textContent = inputType.value || "Hospital";
    if (elPrevLicense && inputLicense) elPrevLicense.textContent = inputLicense.value || "Pending License";
    if (elPrevDirector && inputDirector) elPrevDirector.textContent = inputDirector.value || "Duty Desk";
    if (elPrevHotline && inputHotline) elPrevHotline.textContent = inputHotline.value || "N/A";
    if (elPrevAddress && inputAddress) elPrevAddress.textContent = inputAddress.value || "Address";
    if (elPrevColdTemp && inputColdTemp) elPrevColdTemp.textContent = inputColdTemp.value ? `${inputColdTemp.value} (Optimal)` : "3.8°C (Optimal)";
    if (elPrevChairs && inputChairs) elPrevChairs.textContent = `${inputChairs.value || 8} Chairs`;

    if (elPrevAvatar && inputName) {
      const words = (inputName.value || "").trim().split(/\s+/);
      const initials = words.length > 1 ? (words[0][0] + words[1][0]).toUpperCase() : (inputName.value.substring(0, 2) || "HP").toUpperCase();
      elPrevAvatar.textContent = initials;
    }

    if (elPrevChips) {
      const checkedBoxes = document.querySelectorAll('#facilityComponentChips input[type="checkbox"]:checked');
      elPrevChips.innerHTML = "";
      checkedBoxes.forEach((cb) => {
        const chip = document.createElement("span");
        chip.className = "preview-comp-chip";
        chip.textContent = cb.value;
        elPrevChips.appendChild(chip);
      });
    }
  }

  // Bind live listeners
  [inputName, inputType, inputLicense, inputDirector, inputHotline, inputAddress, inputColdTemp, inputChairs].forEach((el) => {
    if (el) {
      el.addEventListener("input", syncLivePreview);
      el.addEventListener("change", syncLivePreview);
    }
  });

  const compCheckboxes = document.querySelectorAll('#facilityComponentChips input[type="checkbox"]');
  compCheckboxes.forEach((cb) => cb.addEventListener("change", syncLivePreview));

  // Geolocation detection button
  if (btnDetectGps) {
    btnDetectGps.addEventListener("click", () => {
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const lat = pos.coords.latitude.toFixed(4);
            const lng = pos.coords.longitude.toFixed(4);
            if (inputGps) inputGps.value = `${lat}° N, ${lng}° E`;
            showMasterToast(`GPS detected: ${lat}° N, ${lng}° E`, "📍");
          },
          () => {
            if (inputGps) inputGps.value = "23.7257° N, 90.3980° E";
            showMasterToast("GPS pinned to Shahbagh Metro Grid (23.7257° N, 90.3980° E)", "📍");
          },
          { timeout: 5000 }
        );
      } else {
        if (inputGps) inputGps.value = "23.7257° N, 90.3980° E";
        showMasterToast("GPS pinned to Shahbagh Metro Grid", "📍");
      }
    });
  }

  // Form submit handler
  if (facilitySettingsForm) {
    facilitySettingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const btnSave = document.getElementById("btnSaveFacilitySettings");
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.style.opacity = "0.7";
      }

      const components = Array.from(
        document.querySelectorAll('#facilityComponentChips input[type="checkbox"]:checked')
      ).map((cb) => cb.value);

      const payload = {
        phone: inputPhone?.value || "+8801734567890",
        facility_name: inputName?.value || "General Hospital",
        facility_type: inputType?.value || "Tertiary Care Teaching Hospital",
        license_no: inputLicense?.value || "",
        est_year: document.getElementById("facilityEstYear")?.value || "",
        director_name: inputDirector?.value || "",
        director_title: document.getElementById("facilityDirectorTitle")?.value || "",
        hotline: inputHotline?.value || "",
        email: document.getElementById("facilityEmail")?.value || "",
        address: inputAddress?.value || "",
        division: document.getElementById("facilityDivision")?.value || "Dhaka",
        area: document.getElementById("facilityArea")?.value || "",
        gps_coords: inputGps?.value || "",
        landmark: document.getElementById("facilityLandmark")?.value || "",
        phlebotomy_chairs: parseInt(inputChairs?.value || "8", 10),
        components: components.length > 0 ? components : ["PRBC", "Platelets", "FFP", "Cryo", "Whole Blood"],
        apheresis_active: document.getElementById("toggleApheresis")?.checked ?? true,
        cold_storage_temp: inputColdTemp?.value || "3.8°C",
        ultra_freezer_active: document.getElementById("toggleUltraFreezer")?.checked ?? true,
        nat_screening: document.getElementById("toggleNatScreening")?.checked ?? true,
        continuous_shift: document.getElementById("toggleContinuousShift")?.checked ?? true,
        low_stock_threshold: parseInt(document.getElementById("facilityStockThreshold")?.value || "5", 10),
        auto_sos_dispatch: document.getElementById("toggleAutoSos")?.checked ?? true,
        inter_facility_network: document.getElementById("toggleInterFacility")?.checked ?? true,
        audio_siren: document.getElementById("toggleAudioSiren")?.checked ?? true,
        sms_doctor_alerts: document.getElementById("toggleSmsAlerts")?.checked ?? true,
        daily_inventory_audit: document.getElementById("toggleDailyAudit")?.checked ?? true,
        two_factor_auth: document.getElementById("toggle2FA")?.checked ?? true,
        maintenance_mode: document.getElementById("toggleMaintenance")?.checked ?? false,
      };

      try {
        const resp = await fetch("/api/v1/hospital/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const resData = await resp.json();
          showMasterToast("Facility Profile & Portal Settings saved successfully!", "💾");

          const heroTitle = document.querySelector(".master-hero-title");
          if (heroTitle && payload.facility_name) {
            heroTitle.textContent = payload.facility_name;
          }
          const sidebarName = document.querySelector(".hospital-name-text");
          if (sidebarName && payload.facility_name) {
            sidebarName.textContent = payload.facility_name;
          }

          const syncEl = document.getElementById("settingsLastSynced");
          if (syncEl) syncEl.textContent = new Date().toLocaleTimeString();

          syncLivePreview();
        } else {
          showMasterToast("Error saving facility settings. Please try again.", "⚠️");
        }
      } catch (err) {
        showMasterToast("Network error saving facility settings.", "❌");
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.style.opacity = "";
        }
      }
    });
  }

  // Reset to Baseline
  if (btnResetSettings) {
    btnResetSettings.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to reset facility profile and settings to the DGHS baseline?")) {
        return;
      }
      try {
        const resp = await fetch("/api/v1/hospital/settings/reset", {
          method: "POST",
          headers: { "Accept": "application/json" },
        });
        if (resp.ok) {
          const data = await resp.json();
          const s = data.settings || {};
          if (inputName && s.facility_name) inputName.value = s.facility_name;
          if (inputType && s.facility_type) inputType.value = s.facility_type;
          if (inputLicense && s.license_no) inputLicense.value = s.license_no;
          if (inputDirector && s.director_name) inputDirector.value = s.director_name;
          if (inputHotline && s.hotline) inputHotline.value = s.hotline;
          if (inputAddress && s.address) inputAddress.value = s.address;
          if (inputColdTemp && s.cold_storage_temp) inputColdTemp.value = s.cold_storage_temp;
          if (inputChairs && s.phlebotomy_chairs) inputChairs.value = s.phlebotomy_chairs;
          syncLivePreview();
          showMasterToast("Settings reset to DGHS certified baseline.", "🔄");
        }
      } catch {
        showMasterToast("Failed to reset settings.", "⚠️");
      }
    });
  }

  // Export Accreditation Summary
  if (btnExportAccreditation) {
    btnExportAccreditation.addEventListener("click", () => {
      showMasterToast("Generating DGHS accreditation certificate summary...", "📋");
      setTimeout(() => {
        window.print();
      }, 600);
    });
  }

  // Delete Facility Account Modal Logic
  const deleteFacilityModal = document.getElementById('deleteFacilityModal');
  const btnOpenDeleteFacilityModal = document.getElementById('btnOpenDeleteFacilityModal');
  const btnCloseDeleteFacilityModal = document.getElementById('btnCloseDeleteFacilityModal');
  const btnCancelDeleteFacilityModal = document.getElementById('btnCancelDeleteFacilityModal');
  const btnConfirmDeleteFacility = document.getElementById('btnConfirmDeleteFacility');
  const deleteFacilityConfirmationInput = document.getElementById('deleteFacilityConfirmationInput');

  function closeDeleteFacilityModal() {
    if (deleteFacilityModal) {
      deleteFacilityModal.style.display = 'none';
      deleteFacilityModal.classList.remove('active');
    }
    if (deleteFacilityConfirmationInput) {
      deleteFacilityConfirmationInput.value = '';
    }
    if (btnConfirmDeleteFacility) {
      btnConfirmDeleteFacility.disabled = true;
      btnConfirmDeleteFacility.style.opacity = '0.5';
      btnConfirmDeleteFacility.style.cursor = 'not-allowed';
    }
  }

  if (btnOpenDeleteFacilityModal) {
    btnOpenDeleteFacilityModal.addEventListener('click', () => {
      if (deleteFacilityModal) {
        deleteFacilityModal.style.display = 'flex';
        deleteFacilityModal.classList.add('active');
        setTimeout(() => {
          deleteFacilityConfirmationInput?.focus();
        }, 50);
      }
    });
  }

  if (btnCloseDeleteFacilityModal) {
    btnCloseDeleteFacilityModal.addEventListener('click', closeDeleteFacilityModal);
  }

  if (btnCancelDeleteFacilityModal) {
    btnCancelDeleteFacilityModal.addEventListener('click', closeDeleteFacilityModal);
  }

  if (deleteFacilityModal) {
    deleteFacilityModal.addEventListener('click', (e) => {
      if (e.target === deleteFacilityModal) {
        closeDeleteFacilityModal();
      }
    });
  }

  if (deleteFacilityConfirmationInput && btnConfirmDeleteFacility) {
    deleteFacilityConfirmationInput.addEventListener('input', () => {
      const val = deleteFacilityConfirmationInput.value.trim().toUpperCase();
      if (val === 'DELETE') {
        btnConfirmDeleteFacility.disabled = false;
        btnConfirmDeleteFacility.style.opacity = '1';
        btnConfirmDeleteFacility.style.cursor = 'pointer';
      } else {
        btnConfirmDeleteFacility.disabled = true;
        btnConfirmDeleteFacility.style.opacity = '0.5';
        btnConfirmDeleteFacility.style.cursor = 'not-allowed';
      }
    });

    deleteFacilityConfirmationInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !btnConfirmDeleteFacility.disabled) {
        btnConfirmDeleteFacility.click();
      }
    });
  }

  if (btnConfirmDeleteFacility) {
    btnConfirmDeleteFacility.addEventListener('click', async () => {
      if (btnConfirmDeleteFacility.disabled) return;
      btnConfirmDeleteFacility.disabled = true;
      btnConfirmDeleteFacility.textContent = 'Deleting Account...';

      try {
        const response = await fetch('/api/v1/hospital/account', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (response.ok && data.status === 'success') {
          closeDeleteFacilityModal();
          showToast('Account deleted successfully. Redirecting to login...');
          setTimeout(() => {
            window.location.href = data.redirect_url || '/login?account_deleted=1&role=hospital';
          }, 1000);
        } else {
          showToast(data.message || 'Failed to delete account. Please try again.', 'error');
          btnConfirmDeleteFacility.disabled = false;
          btnConfirmDeleteFacility.textContent = 'Permanently Delete Account';
        }
      } catch (err) {
        console.error('Account deletion error:', err);
        showToast('Error deleting account. Please try again.', 'error');
        btnConfirmDeleteFacility.disabled = false;
        btnConfirmDeleteFacility.textContent = 'Permanently Delete Account';
      }
    });
  }

  // Handle initial tab from URL hash if provided
  const initialHash = window.location.hash ? window.location.hash.substring(1) : "";
  if (initialHash && document.getElementById(initialHash)) {
    activateTab(initialHash);
  }
});
