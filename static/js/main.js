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
    if (hamburgerBtn && mobileDrawer && !hamburgerBtn.contains(e.target) && !mobileDrawer.contains(e.target)) {
      hamburgerBtn.classList.remove("is-active");
      mobileDrawer.classList.remove("open");
      hamburgerBtn.setAttribute("aria-expanded", "false");
    }
  });

  const feed = document.getElementById("request-feed");
  const groupFilter = document.getElementById("blood-group-filter");
  const feedMessage = document.getElementById("feed-message");

  if (!feed || !groupFilter) return;

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
});