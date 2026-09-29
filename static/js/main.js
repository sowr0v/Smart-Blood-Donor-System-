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

document.addEventListener("DOMContentLoaded", () => {
  initLiveTicker();

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