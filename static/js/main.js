document.addEventListener("DOMContentLoaded", () => {
  const hamburgerBtn = document.getElementById("hamburger-btn");
  const mobileDrawer = document.getElementById("mobile-drawer");

  if (hamburgerBtn && mobileDrawer) {
    hamburgerBtn.addEventListener("click", () => {
      const isExpanded = hamburgerBtn.getAttribute("aria-expanded") === "true";
      hamburgerBtn.setAttribute("aria-expanded", !isExpanded);
      hamburgerBtn.classList.toggle("is-active");
      mobileDrawer.classList.toggle("open");
    });
  }

  // Close mobile drawer when clicking outside
  document.addEventListener("click", (e) => {
    if (!hamburgerBtn || !mobileDrawer) return;

    if (!hamburgerBtn.contains(e.target) && !mobileDrawer.contains(e.target)) {
      hamburgerBtn.classList.remove("is-active");
      mobileDrawer.classList.remove("open");
      hamburgerBtn.setAttribute("aria-expanded", "false");
    }
  });
});

// ================= SBDS-02: TICKER SEAMLESS LOOP & API INTEGRATION =================
function initLiveTicker() {
  const tickerTrack = document.getElementById("ticker-track");
  if (!tickerTrack) return;

  // Duplicate content so the horizontal animation scrolls seamlessly without blank gaps
  tickerTrack.innerHTML += tickerTrack.innerHTML;

  // Optional: Backend endpoint theke dynamic live data anar function
  async function fetchTickerUpdates() {
    try {
      const response = await fetch("/api/v1/donors/live-ticker");
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          let updatedHTML = "";
          data.forEach(item => {
            updatedHTML += `
              <span class="ticker-item">
                <strong class="blood-group">${item.blood_group}</strong> ${item.message}
              </span>
              <span class="ticker-divider">•</span>
            `;
          });
          // Update and duplicate for infinite scroll
          tickerTrack.innerHTML = updatedHTML + updatedHTML;
        }
      }
    } catch (err) {
      // Backend off thakle default static items chalu thakbe
      console.log("Ticker live update skipped: using default feed.");
    }
  }

  fetchTickerUpdates();

  // Prottek 60 second por por live data refresh hobe
  setInterval(fetchTickerUpdates, 60000);
}

function initUrgentBoard() {
  const requestList = document.getElementById("urgent-request-list");
  const status = document.getElementById("urgent-board-status");
  const emptyState = document.getElementById("urgent-board-empty");
  const bloodFilter = document.getElementById("urgent-blood-filter");
  const districtFilter = document.getElementById("urgent-district-filter");
  if (!requestList || !status || !emptyState || !bloodFilter || !districtFilter) return;

  let requests = [];
  let refreshInProgress = false;

  function createTextElement(tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text;
    return element;
  }

  function updateDistrictOptions() {
    const selectedDistrict = districtFilter.value;
    districtFilter.replaceChildren(new Option("All districts", ""));
    const districts = [...new Set(requests.map((request) => request.district).filter(Boolean))].sort();
    districts.forEach((district) => districtFilter.add(new Option(district, district)));
    districtFilter.value = districts.includes(selectedDistrict) ? selectedDistrict : "";
  }

  function countdownText(expiry) {
    const remaining = Date.parse(expiry) - Date.now();
    if (Number.isNaN(remaining)) return "Time unavailable";
    if (remaining <= 0) return "Expired";

    const totalSeconds = Math.floor(remaining / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
  }

  function renderRequests() {
    const bloodGroup = bloodFilter.value;
    const district = districtFilter.value;
    const visibleRequests = requests.filter((request) =>
      (!bloodGroup || request.blood_group === bloodGroup) &&
      (!district || request.district === district)
    );

    requestList.replaceChildren();
    emptyState.hidden = visibleRequests.length > 0;
    status.textContent = `${visibleRequests.length} active emergency ${visibleRequests.length === 1 ? "request" : "requests"}`;

    visibleRequests.forEach((request) => {
      const card = createTextElement("article", "urgent-request-card");
      const cardTop = createTextElement("div", "urgent-request-card-top");
      cardTop.append(
        createTextElement("span", "urgent-blood-pill", request.blood_group),
        createTextElement("span", "urgent-priority", "Critical")
      );

      const facility = createTextElement("h2", "urgent-facility", request.hospital_name);
      const locationParts = [request.area, request.district].filter(Boolean);
      if (request.distance_km !== null && request.distance_km !== undefined && Number.isFinite(Number(request.distance_km))) {
        locationParts.push(`${Number(request.distance_km).toFixed(1)} km away`);
      }
      const location = createTextElement("p", "urgent-location", locationParts.join(" · "));
      const countdownLabel = createTextElement("span", "urgent-countdown-label", "Time remaining");
      const countdown = createTextElement("time", "urgent-countdown", countdownText(request.expires_at));
      countdown.dateTime = request.expires_at;
      countdown.dataset.expiresAt = request.expires_at;

      const connect = document.createElement("a");
      connect.className = "urgent-connect";
      connect.textContent = "Connect";
      const phone = String(request.contact_phone || "").replace(/[^\d+]/g, "");
      if (/^\+?\d{6,15}$/.test(phone)) {
        connect.href = `tel:${phone}`;
      } else {
        connect.setAttribute("aria-disabled", "true");
        connect.title = "Contact details unavailable";
        connect.addEventListener("click", (event) => event.preventDefault());
      }

      card.append(cardTop, facility, location, countdownLabel, countdown, connect);
      requestList.append(card);
    });
  }

  async function refreshRequests() {
    if (refreshInProgress) return;
    refreshInProgress = true;
    try {
      const response = await fetch("/api/v1/requests/urgent", { cache: "no-store" });
      if (!response.ok) throw new Error("Emergency requests could not be loaded");
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error("Unexpected emergency request response");
      requests = data;
      updateDistrictOptions();
      renderRequests();
    } catch (error) {
      status.textContent = "Emergency requests are temporarily unavailable.";
      if (requests.length === 0) emptyState.hidden = false;
    } finally {
      refreshInProgress = false;
    }
  }

  bloodFilter.addEventListener("change", renderRequests);
  districtFilter.addEventListener("change", renderRequests);
  requestList.addEventListener("click", (event) => {
    if (event.target.closest(".urgent-connect[aria-disabled='true']")) event.preventDefault();
  });
  setInterval(() => {
    requestList.querySelectorAll(".urgent-countdown[data-expires-at]").forEach((countdown) => {
      countdown.textContent = countdownText(countdown.dataset.expiresAt);
    });
    if (requests.some((request) => Date.parse(request.expires_at) <= Date.now())) refreshRequests();
  }, 1000);
  setInterval(refreshRequests, 15000);
  refreshRequests();
}

document.addEventListener("DOMContentLoaded", () => {
  initLiveTicker();
  initUrgentBoard();

  const registrationForm = document.getElementById("registration-form");
  const roleSelect = document.getElementById("register-role");
  const personalFields = document.getElementById("personal-fields");
  const organizationFields = document.getElementById("organization-fields");
  const bloodGroup = document.getElementById("blood-group");

  if (roleSelect && personalFields && organizationFields && bloodGroup) {
    const updateRegistrationFields = () => {
      const isOrganization = roleSelect.value === "blood_bank" || roleSelect.value === "hospital";
      personalFields.hidden = isOrganization;
      organizationFields.hidden = !isOrganization;
      bloodGroup.required = !isOrganization;
      personalFields.querySelectorAll("input, select").forEach((field) => {
        field.disabled = isOrganization;
      });
      organizationFields.querySelectorAll("input, select").forEach((field) => {
        field.disabled = !isOrganization;
      });
    };

    roleSelect.addEventListener("change", updateRegistrationFields);
    updateRegistrationFields();
  }

  if (registrationForm) {
    registrationForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const status = document.getElementById("registration-status");
      status.textContent = "Account creation is not connected yet. Your information has not been submitted.";
      status.hidden = false;
    });
  }
});