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

function formatInventoryTimestamp(timestamp) {
  if (!timestamp) return "Not updated yet";
  const parsedTimestamp = new Date(timestamp);
  if (Number.isNaN(parsedTimestamp.getTime())) return "Not updated yet";
  return parsedTimestamp.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

window.saveFacilityInventory = async function (bloodGroup, inputId, saveButton) {
  if (saveButton.disabled) return;
  const quantityInput = document.getElementById(inputId);
  const form = saveButton.closest(".inventory-update-form");
  const feedback = form.querySelector(".inventory-row-feedback");
  const rawQuantity = quantityInput.value.trim();
  const quantity = rawQuantity === "" ? Number.NaN : Number(rawQuantity);

  if (!Number.isSafeInteger(quantity) || quantity < 0) {
    const message = "Enter a whole number of zero or more.";
    feedback.textContent = message;
    showMasterToast(message, "⚠️");
    quantityInput.focus();
    return;
  }

  feedback.textContent = "Saving…";
  saveButton.disabled = true;
  try {
    const response = await fetch(
      `/api/v1/facility/inventory/${encodeURIComponent(bloodGroup)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ quantity }),
      }
    );
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(result.detail)
        ? result.detail.map((item) => item.msg).join(" ")
        : result.detail;
      throw new Error(detail || "Could not update inventory.");
    }

    const savedQuantity = result.item.quantity;
    const quantityDisplay = document.querySelector(
      `[data-inventory-quantity="${bloodGroup}"]`
    );
    if (quantityDisplay) {
      quantityDisplay.textContent = savedQuantity;
      quantityDisplay.dataset.stock = savedQuantity > 0 ? "available" : "empty";
    }
    quantityInput.value = savedQuantity;

    const countId = `count-${bloodGroup.replace("+", "-pos").replace(/-$/, "-neg")}`;
    const dashboardCount = document.getElementById(countId);
    if (dashboardCount) dashboardCount.textContent = savedQuantity;
    const total = [...document.querySelectorAll("[data-inventory-quantity]")]
      .reduce((sum, item) => sum + Number(item.textContent), 0);
    const totalDisplay = document.getElementById("kpiTotalUnits");
    if (totalDisplay) totalDisplay.textContent = total;
    const inventoryTotalDisplay = document.getElementById("inventoryTotalUnits");
    if (inventoryTotalDisplay) inventoryTotalDisplay.textContent = total;
    const lowStockCount = [...document.querySelectorAll("[data-inventory-quantity]")]
      .filter((item) => Number(item.textContent) < 2).length;
    const lowStockDisplay = document.getElementById("inventoryLowStockGroups");
    if (lowStockDisplay) lowStockDisplay.textContent = lowStockCount;

    const updatedAt = form.closest("tr").querySelector(".inventory-updated-at");
    if (updatedAt) {
      updatedAt.dataset.timestamp = result.item.updated_at || "";
      updatedAt.textContent = formatInventoryTimestamp(result.item.updated_at);
    }
    const matrixSync = document.getElementById("inventoryLastMatrixSync");
    if (matrixSync && result.item.updated_at) {
      matrixSync.dataset.timestamp = result.item.updated_at;
      matrixSync.textContent = formatInventoryTimestamp(result.item.updated_at);
    }
    const message = result.item.changed ? `${bloodGroup} stock updated.` : "Stock is unchanged.";
    feedback.textContent = message;
    showMasterToast(message, result.item.changed ? "✅" : "ℹ️");
  } catch (error) {
    const message = error.message || "Could not update inventory. Please try again.";
    feedback.textContent = message;
    showMasterToast(message, "⚠️");
  } finally {
    saveButton.disabled = false;
  }
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".inventory-updated-at").forEach((element) => {
    element.textContent = formatInventoryTimestamp(element.dataset.timestamp);
  });
  const matrixSync = document.getElementById("inventoryLastMatrixSync");
  if (matrixSync) {
    matrixSync.textContent = formatInventoryTimestamp(matrixSync.dataset.timestamp);
  }

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

  // ================= 3. FACILITY BLOOD INVENTORY =================
  document.querySelectorAll(".inventory-update-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const saveButton = form.querySelector("[data-inventory-save]");
      window.saveFacilityInventory(
        saveButton.dataset.bloodGroup,
        saveButton.dataset.quantityInput,
        saveButton
      );
    });
  });

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

  // Auto-load donor search when its tab is activated
  const donorSearchNavBtn = document.getElementById("nav-item-donor-search");
  if (donorSearchNavBtn) {
    donorSearchNavBtn.addEventListener("click", () => {
      setTimeout(() => {
        if (typeof window.loadHospitalDonors === "function") window.loadHospitalDonors();
        if (typeof window.loadOutreachLogs === "function") window.loadOutreachLogs();
      }, 80);
    });
  }
});


// ============================================================
// 2. Donor Search & Direct Outreach – Hospital Portal Section
// ============================================================

let _donorSearchDebounceTimer = null;
let _activeDonorBloodGroup = "";

/** Debounced search trigger (fires after 350ms idle) */
window.triggerDonorSearch = function () {
  clearTimeout(_donorSearchDebounceTimer);
  _donorSearchDebounceTimer = setTimeout(() => {
    window.loadHospitalDonors();
  }, 350);
};

/** Handle blood-group chip selection */
window.selectDonorBgChip = function (chip) {
  document.querySelectorAll(".donor-bg-chip").forEach((c) => c.classList.remove("active"));
  chip.classList.add("active");
  _activeDonorBloodGroup = chip.dataset.bg || "";
  window.loadHospitalDonors();
};

/** Fetch and render donor results */
window.loadHospitalDonors = async function () {
  const grid = document.getElementById("donorSearchResults");
  const empty = document.getElementById("donorSearchEmpty");
  const countEl = document.getElementById("donorSearchResultCount");
  if (!grid) return;

  const query = (document.getElementById("donorSearchQuery") || {}).value || "";
  const location = (document.getElementById("donorSearchLocation") || {}).value || "";
  const radius = (document.getElementById("donorSearchRadius") || {}).value || 30;
  const availableOnly = (document.getElementById("donorAvailableOnly") || {}).checked || false;

  const params = new URLSearchParams();
  if (_activeDonorBloodGroup) params.set("blood_group", _activeDonorBloodGroup);
  if (availableOnly) params.set("available_only", "true");
  if (query.trim()) params.set("query", query.trim());
  if (location.trim()) params.set("location", location.trim());
  params.set("radius_km", radius);

  if (countEl) countEl.textContent = "Searching…";
  grid.innerHTML = `<div style="grid-column:1/-1;padding:32px;text-align:center;color:#475569;font-size:14px;">Loading donors…</div>`;
  if (empty) empty.style.display = "none";

  try {
    const res = await fetch(`/api/v1/hospital/donors?${params.toString()}`);
    const data = await res.json();
    const donors = data.donors || [];

    if (countEl) countEl.textContent = `${donors.length} donor${donors.length !== 1 ? "s" : ""} found`;

    if (donors.length === 0) {
      grid.innerHTML = "";
      if (empty) empty.style.display = "block";
      return;
    }
    if (empty) empty.style.display = "none";

    grid.innerHTML = donors.map((d) => renderDonorCard(d)).join("");
  } catch (err) {
    console.error("Donor search error:", err);
    grid.innerHTML = `<div style="grid-column:1/-1;padding:32px;text-align:center;color:#ef4444;font-size:14px;">Failed to load donors. Please try again.</div>`;
    if (countEl) countEl.textContent = "Error loading donors";
  }
};

/** Render a single donor card as HTML string */
function renderDonorCard(d) {
  const isAvail = d.is_available;
  const dotClass = isAvail ? "available" : "unavailable";
  const availText = isAvail ? "Available" : "Unavailable";
  const verified = d.is_verified
    ? `<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;color:#22c55e;font-weight:700;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>NID Verified</span>`
    : `<span style="font-size:11px;color:#64748b;">Unverified</span>`;
  const badge = d.badge_tier
    ? `<span style="font-size:11px;color:#f59e0b;font-weight:600;">⭐ ${escHtml(d.badge_tier)}</span>`
    : "";
  const area = [d.area, d.district].filter(Boolean).join(", ");
  const distKm = d.distance_km != null ? `${d.distance_km} km away` : "";
  const donation = d.donation_count != null ? `<div style="font-size:12px;color:#64748b;">${d.donation_count} donation${d.donation_count !== 1 ? "s" : ""}</div>` : "";
  const bio = d.bio ? `<p style="font-size:12px;color:#64748b;line-height:1.5;margin:0;">${escHtml(d.bio)}</p>` : "";
  const screening = d.screening ? `<div style="font-size:11px;color:#0ea5e9;margin-top:4px;">🔬 ${escHtml(d.screening)}</div>` : "";

  // Contact actions
  let contactHtml = "";
  if (d.contact_available) {
    const phone = d.contact_phone || "";
    contactHtml = `
      <div class="donor-contact-actions">
        <button class="donor-action-btn call" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','call'); window.open('tel:${escHtml(phone)}');" title="Call donor">
          📞 Call
        </button>
        <button class="donor-action-btn message" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','message');" title="Message donor">
          💬 Message
        </button>
        <button class="donor-action-btn dispatch" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','dispatch');" title="Dispatch request">
          🚑 Dispatch
        </button>
      </div>`;
  } else {
    const note = d.contact_note || "Donor has restricted direct contact. Use in-app messaging.";
    contactHtml = `
      <div class="donor-contact-actions">
        <button class="donor-action-btn disabled-contact" disabled title="${escHtml(note)}" style="font-size:11px;">
          🔒 ${escHtml(note)}
        </button>
      </div>`;
  }

  return `
    <div class="donor-result-card" role="listitem" onclick="window.openHospitalDonorDetail('${escHtml(d.id)}')" tabindex="0" onkeypress="if(event.key==='Enter')window.openHospitalDonorDetail('${escHtml(d.id)}')">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div>
          <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:4px;">${escHtml(d.name)}</div>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
            <span class="donor-bg-badge">${escHtml(d.blood_group)}</span>
            ${verified}
            ${badge}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
          <span class="donor-availability-dot ${dotClass}"></span>
          <span style="font-size:12px;color:${isAvail ? "#22c55e" : "#ef4444"};font-weight:600;">${availText}</span>
        </div>
      </div>
      <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#64748b;">
        ${area ? `<span>📍 ${escHtml(area)}</span>` : ""}
        ${distKm ? `<span>📏 ${escHtml(distKm)}</span>` : ""}
        ${d.response_time ? `<span>⚡ ${escHtml(d.response_time)} avg response</span>` : ""}
        ${d.last_donation ? `<span>🩸 Last donated: ${escHtml(d.last_donation)}</span>` : ""}
        ${donation}
      </div>
      ${bio}
      ${screening}
      ${contactHtml}
    </div>`;
}

/** Log an outreach action */
window.logOutreach = async function (donorId, donorName, bloodGroup, contactType, notes) {
  try {
    await fetch("/api/v1/hospital/outreach/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        donor_id: donorId,
        donor_name: donorName,
        blood_group: bloodGroup,
        contact_type: contactType,
        notes: notes || "",
      }),
    });
    showMasterToast(`Outreach action "${contactType}" logged for ${donorName}.`, "📋");
    setTimeout(() => window.loadOutreachLogs(), 400);
  } catch (err) {
    console.error("Outreach log error:", err);
  }
};

/** Load and render the outreach log table */
window.loadOutreachLogs = async function () {
  const tbody = document.getElementById("outreachLogBody");
  if (!tbody) return;
  try {
    const res = await fetch("/api/v1/hospital/outreach/logs");
    const data = await res.json();
    const logs = data.logs || [];
    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="padding:24px;text-align:center;color:#475569;font-size:13px;">No outreach actions recorded yet.</td></tr>`;
      return;
    }
    const actionIcons = { call: "📞", message: "💬", dispatch: "🚑" };
    const actionColors = { call: "#22c55e", message: "#3b82f6", dispatch: "#f59e0b" };
    tbody.innerHTML = logs.map((log) => {
      const icon = actionIcons[log.contact_type] || "📋";
      const color = actionColors[log.contact_type] || "#94a3b8";
      return `<tr>
        <td>${escHtml(log.donor_name)}</td>
        <td><span class="donor-bg-badge" style="font-size:11px;padding:2px 8px;">${escHtml(log.blood_group)}</span></td>
        <td><span style="display:inline-flex;align-items:center;gap:4px;color:${color};font-weight:700;font-size:12px;">${icon} ${escHtml(log.contact_type)}</span></td>
        <td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(log.notes)}">${escHtml(log.notes)}</td>
        <td style="white-space:nowrap;">${escHtml(log.created_at)}</td>
      </tr>`;
    }).join("");
  } catch (err) {
    console.error("Outreach log fetch error:", err);
    tbody.innerHTML = `<tr><td colspan="5" style="padding:24px;text-align:center;color:#ef4444;font-size:13px;">Failed to load outreach log.</td></tr>`;
  }
};

/** Open the donor detail modal */
window.openHospitalDonorDetail = async function (donorId) {
  const modal = document.getElementById("donorDetailModal");
  const body = document.getElementById("donorDetailModalBody");
  if (!modal || !body) return;

  body.innerHTML = `<div style="text-align:center;padding:40px;color:#64748b;">Loading donor profile…</div>`;
  modal.classList.add("open");
  document.body.style.overflow = "hidden";

  try {
    const res = await fetch(`/api/v1/hospital/donors/${encodeURIComponent(donorId)}`);
    const data = await res.json();
    const d = data.donor;
    if (!d) throw new Error("Donor not found");

    const isAvail = d.is_available;
    const verified = d.is_verified
      ? `<span style="color:#22c55e;font-weight:700;font-size:13px;">✓ NID Verified</span>`
      : `<span style="color:#64748b;font-size:13px;">Not Verified</span>`;
    const area = [d.area, d.district].filter(Boolean).join(", ");

    let contactSection = "";
    if (d.contact_available) {
      contactSection = `
        <div style="background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);border-radius:12px;padding:16px;margin-top:16px;">
          <div style="font-size:11px;color:#22c55e;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Authorised Contact Info</div>
          <div style="font-size:14px;color:#e2e8f0;font-weight:600;">${escHtml(d.contact_phone || "")}</div>
          <div class="donor-contact-actions" style="margin-top:12px;">
            <button class="donor-action-btn call" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','call');window.closeDonorDetailModal();window.open('tel:${escHtml(d.contact_phone || "")}');">📞 Call</button>
            <button class="donor-action-btn message" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','message');window.closeDonorDetailModal();">💬 Message</button>
            <button class="donor-action-btn dispatch" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','dispatch');window.closeDonorDetailModal();">🚑 Dispatch</button>
          </div>
        </div>`;
    } else {
      contactSection = `
        <div style="background:rgba(71,85,105,.1);border:1px solid #1e293b;border-radius:12px;padding:14px;margin-top:16px;">
          <div style="font-size:12px;color:#64748b;">🔒 ${escHtml(d.contact_note || "Donor contact is restricted.")}</div>
          <button class="donor-action-btn message" style="margin-top:10px;" onclick="window.logOutreach('${escHtml(d.id)}','${escHtml(d.name)}','${escHtml(d.blood_group)}','message');window.closeDonorDetailModal();">💬 Send In-App Message</button>
        </div>`;
    }

    body.innerHTML = `
      <div id="donorDetailModalTitle" style="font-size:18px;font-weight:800;color:#e2e8f0;margin-bottom:4px;">${escHtml(d.name)}</div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px;">
        <span class="donor-bg-badge">${escHtml(d.blood_group)}</span>
        ${verified}
        ${d.badge_tier ? `<span style="font-size:12px;color:#f59e0b;font-weight:600;">⭐ ${escHtml(d.badge_tier)}</span>` : ""}
        <span class="donor-availability-dot ${isAvail ? "available" : "unavailable"}"></span>
        <span style="font-size:12px;color:${isAvail ? "#22c55e" : "#ef4444"};font-weight:600;">${isAvail ? "Available" : "Unavailable"}</span>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
        ${area ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Location</div><div style="font-size:13px;color:#e2e8f0;">${escHtml(area)}</div></div>` : ""}
        ${d.distance_km != null ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Distance</div><div style="font-size:13px;color:#e2e8f0;">${d.distance_km} km</div></div>` : ""}
        ${d.response_time ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Avg Response</div><div style="font-size:13px;color:#e2e8f0;">⚡ ${escHtml(d.response_time)}</div></div>` : ""}
        ${d.last_donation ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Last Donation</div><div style="font-size:13px;color:#e2e8f0;">${escHtml(d.last_donation)}</div></div>` : ""}
        ${d.reliability ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Reliability</div><div style="font-size:13px;color:#22c55e;font-weight:700;">${escHtml(d.reliability)}</div></div>` : ""}
        ${d.donation_count != null ? `<div style="background:#0f172a;border-radius:10px;padding:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Donations</div><div style="font-size:13px;color:#e2e8f0;">🩸 ${d.donation_count}</div></div>` : ""}
      </div>

      ${d.bio ? `<div style="background:#0f172a;border-radius:10px;padding:12px;margin-bottom:12px;"><div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Bio</div><div style="font-size:13px;color:#94a3b8;line-height:1.6;">${escHtml(d.bio)}</div></div>` : ""}
      ${d.hemoglobin ? `<div style="font-size:12px;color:#0ea5e9;margin-bottom:6px;">💉 Hb: ${escHtml(d.hemoglobin)}</div>` : ""}
      ${d.screening ? `<div style="font-size:12px;color:#0ea5e9;margin-bottom:6px;">🔬 ${escHtml(d.screening)}</div>` : ""}

      ${contactSection}`;
  } catch (err) {
    body.innerHTML = `<div style="padding:24px;text-align:center;color:#ef4444;">Could not load donor profile.</div>`;
  }
};

/** Close the donor detail modal */
window.closeDonorDetailModal = function () {
  const modal = document.getElementById("donorDetailModal");
  if (modal) modal.classList.remove("open");
  document.body.style.overflow = "";
};

/** HTML-escape helper */
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Close modal on backdrop click
document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("donorDetailModal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) window.closeDonorDetailModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("open")) {
        window.closeDonorDetailModal();
      }
    });
  }
});

