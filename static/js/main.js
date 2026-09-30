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

    // Close drawer when a mobile link is clicked
    const drawerLinks = mobileDrawer.querySelectorAll(".mobile-nav-link");
    drawerLinks.forEach((link) => {
      link.addEventListener("click", () => {
        hamburgerBtn.classList.remove("is-active");
        mobileDrawer.classList.remove("open");
        hamburgerBtn.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Close mobile drawer when clicking outside
  document.addEventListener("click", (e) => {
    if (!hamburgerBtn.contains(e.target) && !mobileDrawer.contains(e.target)) {
      hamburgerBtn.classList.remove("is-active");
      mobileDrawer.classList.remove("open");
      hamburgerBtn.setAttribute("aria-expanded", "false");
    }
  });
  const feed = document.getElementById("request-feed");
  const groupFilter = document.getElementById("blood-group-filter");
  const feedMessage = document.getElementById("feed-message");

  if (feed && groupFilter) {
    const relativeTime = (timestamp) => {
      const minutes = Math.max(0, Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000));
      if (minutes < 1) return "Just now";
      if (minutes < 60) return `${minutes} min${minutes === 1 ? "" : "s"} ago`;
      const hours = Math.floor(minutes / 60);
      return `${hours} hr${hours === 1 ? "" : "s"} ago`;
    };

    const createRequestCard = (request) => {
      const card = document.createElement("article");
      card.className = "request-card";

      const top = document.createElement("div");
      top.className = "request-card-top";
      const group = document.createElement("span");
      group.className = "request-blood-group";
      group.textContent = request.blood_group;
      const status = document.createElement("span");
      status.className = `request-status status-${request.status.toLowerCase()}`;
      status.textContent = request.status;
      top.append(group, status);

      const hospital = document.createElement("h3");
      hospital.textContent = request.hospital;
      const area = document.createElement("p");
      area.className = "request-area";
      area.textContent = request.area;
      const units = document.createElement("p");
      units.className = "request-units";
      units.textContent = `${request.units} unit${request.units === 1 ? "" : "s"} required`;

      const footer = document.createElement("div");
      footer.className = "request-card-footer";
      const time = document.createElement("time");
      time.dateTime = request.posted_at;
      time.textContent = relativeTime(request.posted_at);
      const connect = document.createElement("a");
      connect.className = "connect-button";
      connect.href = `/requests/${encodeURIComponent(request.id)}/connect`;
      connect.textContent = "Connect";
      footer.append(time, connect);
      card.append(top, hospital, area, units, footer);
      return card;
    };

    const refreshFeed = async () => {
      feed.setAttribute("aria-busy", "true");
      try {
        const group = encodeURIComponent(groupFilter.value);
        const response = await fetch(`/api/blood-requests?blood_group=${group}`, { cache: "no-store" });
        if (!response.ok) throw new Error("Request feed unavailable");
        const requests = await response.json();
        feed.replaceChildren(...requests.map(createRequestCard));
        feedMessage.hidden = requests.length > 0;
        feedMessage.textContent = "No open requests for this blood group right now.";
      } catch {
        feedMessage.hidden = false;
        feedMessage.textContent = "Requests could not be refreshed. Showing the latest loaded results.";
      } finally {
        feed.setAttribute("aria-busy", "false");
      }
    };

    groupFilter.addEventListener("change", refreshFeed);
    window.setInterval(refreshFeed, 30000);
  }
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

  function textElement(tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text;
    return element;
  }

  function countdownText(expiry) {
    const remaining = Date.parse(expiry) - Date.now();
    if (Number.isNaN(remaining)) return "Time unavailable";
    if (remaining <= 0) return "Expired";
    const secondsRemaining = Math.floor(remaining / 1000);
    const hours = Math.floor(secondsRemaining / 3600);
    const minutes = Math.floor((secondsRemaining % 3600) / 60);
    const seconds = secondsRemaining % 60;
    return `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
  }

  function updateDistrictOptions() {
    const selectedDistrict = districtFilter.value;
    districtFilter.replaceChildren(new Option("All districts", ""));
    const districts = [...new Set(requests.map((request) => request.district).filter(Boolean))].sort();
    districts.forEach((district) => districtFilter.add(new Option(district, district)));
    districtFilter.value = districts.includes(selectedDistrict) ? selectedDistrict : "";
  }

  function renderRequests() {
    const visibleRequests = requests.filter((request) =>
      (!bloodFilter.value || request.blood_group === bloodFilter.value) &&
      (!districtFilter.value || request.district === districtFilter.value)
    );
    requestList.replaceChildren();
    emptyState.hidden = visibleRequests.length > 0;
    status.textContent = `${visibleRequests.length} active emergency ${visibleRequests.length === 1 ? "request" : "requests"}`;

    visibleRequests.forEach((request) => {
      const card = textElement("article", "urgent-request-card", "");
      const cardTop = textElement("div", "urgent-request-card-top", "");
      cardTop.append(
        textElement("span", "urgent-blood-pill", request.blood_group),
        textElement("span", "urgent-priority", "Critical")
      );
      const facility = textElement("h2", "urgent-facility", request.hospital_name);
      const locationParts = [request.area, request.district].filter(Boolean);
      if (request.distance_km !== null && request.distance_km !== undefined && Number.isFinite(Number(request.distance_km))) {
        locationParts.push(`${Number(request.distance_km).toFixed(1)} km away`);
      }
      const location = textElement("p", "urgent-location", locationParts.join(" · "));
      const countdownLabel = textElement("span", "urgent-countdown-label", "Time remaining");
      const countdown = textElement("time", "urgent-countdown", countdownText(request.expires_at));
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
      if (!response.ok) throw new Error("Emergency requests are temporarily unavailable.");
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error("Unexpected emergency request response.");
      requests = data;
      updateDistrictOptions();
      renderRequests();
    } catch (error) {
      status.textContent = error.message || "Emergency requests are temporarily unavailable.";
      emptyState.textContent = "Emergency requests are temporarily unavailable.";
      emptyState.hidden = false;
    } finally {
      refreshInProgress = false;
    }
  }

  bloodFilter.addEventListener("change", renderRequests);
  districtFilter.addEventListener("change", renderRequests);
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

  const contactForm = document.getElementById("public-contact-form");
  if (contactForm) {
    contactForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const status = document.getElementById("contact-form-status");
      const contactEmail = contactForm.dataset.contactEmail;
      if (!contactEmail) {
        status.textContent = "Email delivery is not configured yet. Your message has not been sent.";
        return;
      }

      const formData = new FormData(contactForm);
      const subject = `[Smart Blood Donor System] ${formData.get("subject")}`;
      const body = [
        `Name: ${formData.get("name")}`,
        `Reply email: ${formData.get("email")}`,
        "",
        formData.get("message"),
      ].join("\n");
      window.location.href = `mailto:${contactEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      status.textContent = "Your email app should open with a draft. Review it and send it from there.";
    });
  }

  const loginForm = document.getElementById("login-form");
  const loginStatus = document.getElementById("login-status");
  if (loginForm && loginStatus) {
    if (new URLSearchParams(window.location.search).get("reset") === "success") {
      loginStatus.textContent = "Your password has been reset. Sign in with your new password.";
      loginStatus.classList.add("is-success");
      loginStatus.hidden = false;
    }

    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      loginStatus.classList.remove("is-success");
      loginStatus.textContent = "Signing in...";
      loginStatus.hidden = false;
      const formData = new FormData(loginForm);
      try {
        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            phone: formData.get("phone"),
            password: formData.get("password"),
          }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Sign in failed.");
        window.location.assign("/");
      } catch (error) {
        loginStatus.textContent = error.message || "Sign in is temporarily unavailable.";
      }
    });
  }

  const recoveryPhoneForm = document.getElementById("recovery-phone-form");
  const recoveryCodeForm = document.getElementById("recovery-code-form");
  const recoveryPasswordForm = document.getElementById("recovery-password-form");
  const recoveryStatus = document.getElementById("recovery-status");
  const recoveryStepLabel = document.getElementById("recovery-step-label");
  if (recoveryPhoneForm && recoveryCodeForm && recoveryPasswordForm && recoveryStatus) {
    let recoveryPhone = "";
    let resetToken = "";

    async function postRecovery(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Password recovery is temporarily unavailable.");
      return result;
    }

    function showRecoveryStep(step, label) {
      recoveryPhoneForm.hidden = step !== "phone";
      recoveryCodeForm.hidden = step !== "code";
      recoveryPasswordForm.hidden = step !== "password";
      recoveryStepLabel.textContent = label;
      recoveryStatus.hidden = true;
      const activeForm = step === "phone" ? recoveryPhoneForm : step === "code" ? recoveryCodeForm : recoveryPasswordForm;
      activeForm.querySelector("input")?.focus();
    }

    function showRecoveryError(error) {
      recoveryStatus.textContent = error.message || "Password recovery is temporarily unavailable.";
      recoveryStatus.classList.remove("is-success");
      recoveryStatus.hidden = false;
    }

    recoveryPhoneForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      recoveryPhone = new FormData(recoveryPhoneForm).get("phone").trim();
      const submit = recoveryPhoneForm.querySelector("button[type='submit']");
      submit.disabled = true;
      try {
        await postRecovery("/api/v1/auth/password-recovery/request", { phone: recoveryPhone });
        showRecoveryStep("code", "Enter the six-digit code sent to your registered phone.");
      } catch (error) {
        showRecoveryError(error);
      } finally {
        submit.disabled = false;
      }
    });

    recoveryCodeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const code = new FormData(recoveryCodeForm).get("code").trim();
      const submit = recoveryCodeForm.querySelector("button[type='submit']");
      submit.disabled = true;
      try {
        const result = await postRecovery("/api/v1/auth/password-recovery/verify", {
          phone: recoveryPhone,
          code,
        });
        resetToken = result.reset_token;
        showRecoveryStep("password", "Choose a new password for your account.");
      } catch (error) {
        showRecoveryError(error);
      } finally {
        submit.disabled = false;
      }
    });

    recoveryPasswordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(recoveryPasswordForm);
      const password = formData.get("new_password");
      const confirmation = formData.get("confirm_password");
      if (
        password.length < 12 || !/[a-z]/.test(password) || !/[A-Z]/.test(password) ||
        !/[0-9]/.test(password) || !/[^a-zA-Z0-9]/.test(password)
      ) {
        showRecoveryError(new Error("Use at least 12 characters with uppercase, lowercase, number, and symbol."));
        return;
      }
      if (password !== confirmation) {
        showRecoveryError(new Error("The passwords do not match."));
        return;
      }

      const submit = recoveryPasswordForm.querySelector("button[type='submit']");
      submit.disabled = true;
      try {
        await postRecovery("/api/v1/auth/password-recovery/reset", {
          phone: recoveryPhone,
          reset_token: resetToken,
          new_password: password,
        });
        window.location.assign("/auth/login?reset=success");
      } catch (error) {
        showRecoveryError(error);
      } finally {
        submit.disabled = false;
      }
    });
  }

  // ================= SBDS-10: Multi-Role User Registration =================
  const roleSelect = document.getElementById("role-select");
  const formIndividual = document.getElementById("form-individual");
  const formOrganization = document.getElementById("form-organization");
  
  if (roleSelect && formIndividual && formOrganization) {
    
    const updateForms = () => {
      const role = roleSelect.value;
      const roleName = roleSelect.options[roleSelect.selectedIndex].text;
      
      // Update H1 title
      const h1Title = document.querySelector(".form-panel h1");
      if (h1Title) {
        h1Title.textContent = "Register as a " + roleName;
      }
      
      if (role === "donor" || role === "seeker") {
        formIndividual.style.display = "block";
        formOrganization.style.display = "none";
        document.getElementById("individual-role-input").value = role;
        document.getElementById("btn-text-individual").textContent = roleName;
      } else {
        formIndividual.style.display = "none";
        formOrganization.style.display = "block";
        document.getElementById("organization-role-input").value = role;
        document.getElementById("btn-text-organization").textContent = roleName;
      }
    };

    roleSelect.addEventListener("change", updateForms);
    updateForms();
    
    // Form submission logic
    document.querySelectorAll(".multi-role-form").forEach(form => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        // Hide forms
        formIndividual.style.display = "none";
        formOrganization.style.display = "none";
        document.querySelector(".role-switcher").style.display = "none";
        
        // Show success message
        const successMsg = document.getElementById("registration-success-msg");
        if (successMsg) {
          successMsg.style.display = "block";
        }
      });
    });
  }
});