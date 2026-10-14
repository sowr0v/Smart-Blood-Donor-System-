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
});

/* ==========================================================================
   5. Institutional Blood Request & Allocation JavaScript
   ========================================================================== */

(function () {
  let cachedRequests = [];

  function escHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getPriorityBadgeClass(priority) {
    const p = (priority || "").toLowerCase();
    if (p === "critical") return "inst-priority-critical";
    if (p === "urgent") return "inst-priority-urgent";
    if (p === "normal") return "inst-priority-normal";
    return "inst-priority-routine";
  }

  function getStatusBadgeClass(status) {
    const s = (status || "").toLowerCase().replace(/\s+/g, "-");
    if (s.includes("partially")) return "inst-status-partially-allocated";
    if (s.includes("fully")) return "inst-status-fully-allocated";
    if (s.includes("dispatched") || s.includes("fulfilled")) return "inst-status-dispatched";
    return "inst-status-pending";
  }

  window.loadInstitutionalRequests = async function (forceToast = false) {
    const tbody = document.getElementById("instRequestsTableBody");
    const emptyState = document.getElementById("instRequestsEmpty");
    if (!tbody) return;

    try {
      const response = await fetch("/api/v1/hospital/institutional-requests");
      if (!response.ok) {
        throw new Error("Failed to fetch institutional requests");
      }
      const data = await response.json();
      cachedRequests = data.requests || [];
      renderRequestsTable(cachedRequests);
      updateKpis(cachedRequests);
      if (forceToast && typeof window.showToast === "function") {
        window.showToast("Institutional requests refreshed");
      }
    } catch (err) {
      console.error("loadInstitutionalRequests error:", err);
      if (typeof window.showToast === "function") {
        window.showToast("Could not load requests", "error");
      }
    }
  };

  function updateKpis(requests) {
    const total = requests.length;
    let pending = 0;
    let totalNeeded = 0;
    let totalAlloc = 0;

    requests.forEach((r) => {
      if (r.status === "Pending") pending++;
      totalNeeded += r.units_requested || 0;
      totalAlloc += r.units_allocated || 0;
    });

    const elTotal = document.getElementById("kpiTotalRequests");
    const elPending = document.getElementById("kpiPendingRequests");
    const elAlloc = document.getElementById("kpiUnitsAllocated");
    const elRate = document.getElementById("kpiFulfillmentRate");

    if (elTotal) elTotal.textContent = total;
    if (elPending) elPending.textContent = pending;
    if (elAlloc) elAlloc.textContent = `${totalAlloc} / ${totalNeeded}`;
    if (elRate) {
      const rate = totalNeeded > 0 ? Math.round((totalAlloc / totalNeeded) * 100) : 0;
      elRate.textContent = `${rate}%`;
    }
  }

  window.filterInstitutionalRequests = function () {
    const statusVal = document.getElementById("instFilterStatus") ? document.getElementById("instFilterStatus").value : "All";
    const prioVal = document.getElementById("instFilterPriority") ? document.getElementById("instFilterPriority").value : "All";
    const bgVal = document.getElementById("instFilterBloodGroup") ? document.getElementById("instFilterBloodGroup").value : "All";

    let filtered = cachedRequests;
    if (statusVal !== "All") {
      filtered = filtered.filter((r) => (r.status || "").toLowerCase() === statusVal.toLowerCase());
    }
    if (prioVal !== "All") {
      filtered = filtered.filter((r) => (r.priority || "").toLowerCase() === prioVal.toLowerCase());
    }
    if (bgVal !== "All") {
      filtered = filtered.filter((r) => (r.blood_group || "").toUpperCase() === bgVal.toUpperCase());
    }

    renderRequestsTable(filtered);
  };

  function renderRequestsTable(requests) {
    const tbody = document.getElementById("instRequestsTableBody");
    const emptyState = document.getElementById("instRequestsEmpty");
    if (!tbody) return;

    if (!requests || requests.length === 0) {
      tbody.innerHTML = "";
      if (emptyState) emptyState.style.display = "block";
      return;
    }

    if (emptyState) emptyState.style.display = "none";

    tbody.innerHTML = requests
      .map((req) => {
        const remaining = Math.max(0, req.units_requested - req.units_allocated);
        const isFullyAllocated = remaining === 0;

        return `
        <tr>
          <td>
            <div style="font-weight: 700; color: var(--text-primary);">${escHtml(req.id)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${escHtml(req.facility_name || "Internal Facility")}</div>
          </td>
          <td>
            <span class="inst-badge-bg">${escHtml(req.blood_group)}</span>
          </td>
          <td>
            <div style="font-weight: 600;">${req.units_allocated} / ${req.units_requested} Bags</div>
            <div style="font-size: 0.76rem; color: ${remaining > 0 ? '#e11d48' : '#10b981'}; font-weight: 500;">
              ${remaining > 0 ? `${remaining} remaining` : 'Fully Allocated'}
            </div>
          </td>
          <td>
            <span class="inst-priority-badge ${getPriorityBadgeClass(req.priority)}">
              ${escHtml(req.priority)}
            </span>
          </td>
          <td>
            <div style="font-weight: 600;">${escHtml(req.department || "General")}</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escHtml(req.patient_diagnosis || "")}">
              ${escHtml(req.patient_diagnosis || "Not specified")}
            </div>
          </td>
          <td>
            <span class="inst-status-badge ${getStatusBadgeClass(req.status)}">
              ${escHtml(req.status)}
            </span>
          </td>
          <td>
            <div class="inst-action-btns">
              ${
                !isFullyAllocated
                  ? `<button type="button" class="btn-inst-action btn-inst-allocate" onclick="window.openAllocateModal('${escHtml(req.id)}')">Allocate</button>`
                  : ""
              }
              <button type="button" class="btn-inst-action" onclick="window.openDetailsModal('${escHtml(req.id)}')">Details</button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");
  }

  // Create Request Modal
  window.openNewRequestModal = function () {
    const modal = document.getElementById("modalCreateRequest");
    const form = document.getElementById("formCreateInstitutionalRequest");
    if (form) form.reset();
    if (modal) modal.classList.add("open");
  };

  window.closeNewRequestModal = function () {
    const modal = document.getElementById("modalCreateRequest");
    if (modal) modal.classList.remove("open");
  };

  window.handleCreateRequestSubmit = async function (e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitCreateRequest");
    if (btn) btn.disabled = true;

    const payload = {
      blood_group: document.getElementById("reqBloodGroup").value,
      units_requested: parseInt(document.getElementById("reqUnits").value, 10),
      priority: document.getElementById("reqPriority").value,
      department: document.getElementById("reqDepartment").value,
      patient_diagnosis: document.getElementById("reqDiagnosis").value,
      required_within_hours: parseInt(document.getElementById("reqRequiredHours").value, 10) || 24,
      notes: document.getElementById("reqNotes").value,
    };

    try {
      const res = await fetch("/api/v1/hospital/institutional-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        if (typeof window.showToast === "function") {
          window.showToast("Institutional blood request created successfully!");
        }
        window.closeNewRequestModal();
        window.loadInstitutionalRequests();
      } else {
        if (typeof window.showToast === "function") {
          window.showToast(data.detail || data.message || "Failed to create request", "error");
        }
      }
    } catch (err) {
      console.error("Create request error:", err);
      if (typeof window.showToast === "function") {
        window.showToast("Network error creating request", "error");
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  // Blood Allocation Modal
  window.openAllocateModal = function (requestId) {
    const target = cachedRequests.find((r) => r.id === requestId);
    if (!target) return;

    const modal = document.getElementById("modalAllocateBlood");
    const summaryBox = document.getElementById("allocSummaryBox");
    const inputHidden = document.getElementById("allocTargetRequestId");
    const inputUnits = document.getElementById("allocUnits");

    const remaining = Math.max(0, target.units_requested - target.units_allocated);

    if (inputHidden) inputHidden.value = target.id;
    if (inputUnits) {
      inputUnits.value = remaining > 0 ? remaining : 1;
      inputUnits.max = remaining;
    }

    if (summaryBox) {
      summaryBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <div>
            <strong style="font-size: 1rem;">${escHtml(target.id)}</strong> - 
            <span class="inst-badge-bg">${escHtml(target.blood_group)}</span>
          </div>
          <span class="inst-priority-badge ${getPriorityBadgeClass(target.priority)}">${escHtml(target.priority)}</span>
        </div>
        <div style="font-size: 0.84rem; color: var(--text-muted);">
          Department: <strong>${escHtml(target.department || 'General')}</strong> &bull;
          Allocated: <strong>${target.units_allocated} / ${target.units_requested} Units</strong> &bull;
          Needed: <strong style="color: #e11d48;">${remaining} more unit(s)</strong>
        </div>
      `;
    }

    if (modal) modal.classList.add("open");
  };

  window.closeAllocateModal = function () {
    const modal = document.getElementById("modalAllocateBlood");
    if (modal) modal.classList.remove("open");
  };

  window.handleRecordAllocationSubmit = async function (e) {
    e.preventDefault();
    const btn = document.getElementById("btnSubmitAllocation");
    if (btn) btn.disabled = true;

    const requestId = document.getElementById("allocTargetRequestId").value;
    const payload = {
      units_allocated: parseInt(document.getElementById("allocUnits").value, 10),
      batch_number: document.getElementById("allocBatchNumber").value,
      source_facility: document.getElementById("allocSourceFacility").value,
      allocated_by: document.getElementById("allocAllocatedBy").value,
      notes: document.getElementById("allocNotes").value,
    };

    try {
      const res = await fetch(`/api/v1/hospital/institutional-requests/${requestId}/allocate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        if (typeof window.showToast === "function") {
          window.showToast(data.message || "Blood units allocated successfully!");
        }
        window.closeAllocateModal();
        window.loadInstitutionalRequests();
      } else {
        if (typeof window.showToast === "function") {
          window.showToast(data.detail || data.message || "Failed to record allocation", "error");
        }
      }
    } catch (err) {
      console.error("Allocation error:", err);
      if (typeof window.showToast === "function") {
        window.showToast("Network error recording allocation", "error");
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  // Details Modal
  window.openDetailsModal = function (requestId) {
    const target = cachedRequests.find((r) => r.id === requestId);
    if (!target) return;

    const modal = document.getElementById("modalRequestDetails");
    const container = document.getElementById("detailsModalContent");
    const title = document.getElementById("detailsModalTitle");

    if (title) title.textContent = `Request Details: ${target.id}`;

    const allocationsHtml =
      target.allocations && target.allocations.length > 0
        ? `
        <h4 style="margin: 18px 0 10px 0; font-size: 0.95rem; font-weight: 700;">Recorded Allocations (${target.allocations.length})</h4>
        <div style="background: var(--surface); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem;">
            <thead>
              <tr style="background: #f8fafc; text-align: left;">
                <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">Batch / Serial</th>
                <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">Units</th>
                <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">Source / Officer</th>
                <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">Time</th>
                <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">Notes</th>
              </tr>
            </thead>
            <tbody>
              ${target.allocations
                .map(
                  (a) => `
                <tr>
                  <td style="padding: 8px 12px; font-weight: 600; border-bottom: 1px solid var(--border-color);">${escHtml(a.batch_number || "N/A")}</td>
                  <td style="padding: 8px 12px; font-weight: 700; color: #e11d48; border-bottom: 1px solid var(--border-color);">${a.units} Bags</td>
                  <td style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">${escHtml(a.source_facility)}<br><small style="color: var(--text-muted);">${escHtml(a.allocated_by)}</small></td>
                  <td style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">${new Date(a.timestamp).toLocaleString()}</td>
                  <td style="padding: 8px 12px; border-bottom: 1px solid var(--border-color);">${escHtml(a.notes || "-")}</td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
        : `
        <div style="background: #f8fafc; border: 1px dashed var(--border-color); border-radius: 8px; padding: 20px; text-align: center; margin-top: 14px; font-size: 0.85rem; color: var(--text-muted);">
          No blood units have been allocated to this request yet.
        </div>
      `;

    if (container) {
      container.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 0.88rem;">
          <div><strong>Facility:</strong> ${escHtml(target.facility_name)}</div>
          <div><strong>Blood Group:</strong> <span class="inst-badge-bg">${escHtml(target.blood_group)}</span></div>
          <div><strong>Requested Units:</strong> ${target.units_requested} Bags</div>
          <div><strong>Allocated Units:</strong> ${target.units_allocated} Bags</div>
          <div><strong>Priority:</strong> <span class="inst-priority-badge ${getPriorityBadgeClass(target.priority)}">${escHtml(target.priority)}</span></div>
          <div><strong>Status:</strong> <span class="inst-status-badge ${getStatusBadgeClass(target.status)}">${escHtml(target.status)}</span></div>
          <div><strong>Department:</strong> ${escHtml(target.department || "General")}</div>
          <div><strong>Needed Within:</strong> ${target.required_within_hours || 24} Hours</div>
        </div>
        ${target.patient_diagnosis ? `<div style="margin-top: 10px; font-size: 0.86rem;"><strong>Diagnosis / Clinical Reason:</strong> ${escHtml(target.patient_diagnosis)}</div>` : ""}
        ${target.notes ? `<div style="margin-top: 6px; font-size: 0.86rem;"><strong>Notes:</strong> ${escHtml(target.notes)}</div>` : ""}
        ${allocationsHtml}
      `;
    }

    if (modal) modal.classList.add("open");
  };

  window.closeDetailsModal = function () {
    const modal = document.getElementById("modalRequestDetails");
    if (modal) modal.classList.remove("open");
  };

  // Wire automatic tab activation
  const navItem = document.getElementById("nav-item-blood-allocation");
  if (navItem) {
    navItem.addEventListener("click", function () {
      window.loadInstitutionalRequests();
    });
  }
})();

