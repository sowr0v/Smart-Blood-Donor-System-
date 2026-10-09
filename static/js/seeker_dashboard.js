// ================= BLOOD SEEKER PORTAL SCRIPT =================
// Implementation for Section 1: Blood Seeker Personal Dashboard
// Sections 2 through 9 remain modular shells until requested.

document.addEventListener('DOMContentLoaded', () => {
  // Navigation & Tab Switching
  const navItems = document.querySelectorAll('.seeker-nav-item');
  const sections = document.querySelectorAll('.dashboard-content-section');
  const mobileSidebar = document.getElementById('seekerSidebar');
  const mobileToggleBtn = document.getElementById('mobileSidebarToggle');

  // Global Toast
  function showToast(message, type = 'info') {
    const toast = document.getElementById('dashboardToast');
    const toastText = document.getElementById('toastText');
    if (!toast || !toastText) return;
    toastText.textContent = message;
    toast.className = 'dashboard-toast show';
    clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }
  window.showToast = showToast;

  // Activate Section
  function activateSection(targetId) {
    if (!targetId) return;
    const cleanId = targetId.replace('#', '');
    const targetSection = document.getElementById(cleanId);
    if (!targetSection) return;

    sections.forEach(sec => sec.classList.remove('active-section'));
    targetSection.classList.add('active-section');

    navItems.forEach(item => {
      const target = item.getAttribute('data-target') || item.getAttribute('href');
      if (target && target.replace('#', '') === cleanId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (mobileSidebar && mobileSidebar.classList.contains('mobile-open')) {
      mobileSidebar.classList.remove('mobile-open');
    }

    if (history.pushState) {
      history.pushState(null, null, `#${cleanId}`);
    } else {
      location.hash = `#${cleanId}`;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  window.activateSection = activateSection;

  // Bind clicks on sidebar items
  navItems.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-target') || btn.getAttribute('href');
      activateSection(target);
    });
  });

  // Mobile drawer toggle
  if (mobileToggleBtn && mobileSidebar) {
    mobileToggleBtn.addEventListener('click', () => {
      mobileSidebar.classList.toggle('mobile-open');
    });

    document.addEventListener('click', (e) => {
      if (mobileSidebar.classList.contains('mobile-open')) {
        if (!mobileSidebar.contains(e.target) && !mobileToggleBtn.contains(e.target)) {
          mobileSidebar.classList.remove('mobile-open');
        }
      }
    });
  }

  // Quick action buttons linking to sections
  document.querySelectorAll('[data-goto]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-goto');
      activateSection(target);
    });
  });

  // Modal controls
  window.closeSosModal = function() {
    const modal = document.getElementById('sosBroadcastModal');
    if (modal) modal.style.display = 'none';
    activateSection('section-seeker-dashboard');
  };

  window.showSosModal = function(group = 'O+', hospital = 'Square Hospital') {
    const modal = document.getElementById('sosBroadcastModal');
    const groupEl = document.getElementById('sosBroadcastGroup');
    const hospEl = document.getElementById('sosBroadcastHospital');
    if (groupEl) groupEl.textContent = group;
    if (hospEl) hospEl.textContent = hospital;
    if (modal) modal.style.display = 'flex';
  };

  // =========================================================================
  // 1. BLOOD SEEKER PERSONAL DASHBOARD: RECENT REQUESTS & METRICS
  // =========================================================================
  let seekerRequests = [
    {
      id: 101,
      patient_name: "Mrs. Salma Begum",
      blood_group: "A+",
      hospital: "Square Hospital",
      area: "Panthapath",
      units: 2,
      needed_date: "Today, 4:00 PM",
      status: "Active",
      is_emergency: 0,
      responses_count: 3,
      created_at: "2 hours ago"
    },
    {
      id: 102,
      patient_name: "Arif Chowdhury",
      blood_group: "O+",
      hospital: "Dhaka Medical College Hospital",
      area: "Shahbagh",
      units: 1,
      needed_date: "Urgent (ICU)",
      status: "Emergency",
      is_emergency: 1,
      responses_count: 5,
      created_at: "35 mins ago"
    },
    {
      id: 98,
      patient_name: "Taslima Khanam",
      blood_group: "B+",
      hospital: "Bangladesh Specialized Hospital",
      area: "Kalyanpur",
      units: 2,
      needed_date: "28 Sep 2026",
      status: "Fulfilled",
      is_emergency: 0,
      responses_count: 2,
      created_at: "10 days ago"
    }
  ];

  function updateMetrics() {
    const activeCount = seekerRequests.filter(r => r.status === 'Active' || r.status === 'Emergency').length;
    const emergencyCount = seekerRequests.filter(r => r.is_emergency === 1 || r.status === 'Emergency').length;
    const fulfilledBags = seekerRequests.filter(r => r.status === 'Fulfilled').reduce((sum, r) => sum + (r.units || 1), 3);

    const activeEl = document.getElementById('metricActiveReqs');
    if (activeEl) activeEl.textContent = `${activeCount} Active`;

    const donorsEl = document.getElementById('metricMatchedDonors');
    if (donorsEl) donorsEl.textContent = "14 Nearby";

    const emergencyEl = document.getElementById('metricEmergencyAlerts');
    if (emergencyEl) emergencyEl.textContent = `${emergencyCount} Broadcast`;

    const fulfilledEl = document.getElementById('metricFulfilledUnits');
    if (fulfilledEl) fulfilledEl.textContent = `${fulfilledBags} Bags`;
  }

  function renderSeekerRequestsTable(filter = 'all') {
    const tableBody = document.getElementById('seekerRequestsTableBody');
    if (!tableBody) return;

    let filtered = seekerRequests;
    if (filter === 'active') {
      filtered = seekerRequests.filter(r => r.status === 'Active');
    } else if (filter === 'emergency') {
      filtered = seekerRequests.filter(r => r.is_emergency === 1 || r.status === 'Emergency');
    } else if (filter === 'fulfilled') {
      filtered = seekerRequests.filter(r => r.status === 'Fulfilled');
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 28px; color: var(--text-muted); font-size: 0.92rem;">
            No blood requests found under the <strong>${filter}</strong> filter.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = filtered.map(req => {
      const isSos = req.is_emergency === 1 || req.status === 'Emergency';
      const statusBadge = isSos
        ? `<span class="nav-badge-emergency">● SOS EMERGENCY</span>`
        : req.status === 'Fulfilled'
        ? `<span class="nav-pill-badge pill-green">✓ Fulfilled</span>`
        : `<span class="nav-pill-badge pill-blue">Active</span>`;

      const hospitalName = req.hospital || req.hospital_name || 'Dhaka Hospital';
      const areaName = req.area || req.district || 'Dhaka';
      const patient = req.patient_name || 'Patient';
      const units = req.units || 1;
      const responses = req.responses_count || (isSos ? 5 : 2);

      return `
        <tr>
          <td style="font-weight: 700; color: var(--text-primary);">#REQ-${req.id}</td>
          <td><strong>${patient}</strong></td>
          <td>
            <span class="blood-group-badge" style="background: #FFE4E6; color: #BE123C; font-weight: 800; padding: 3px 8px; border-radius: 6px; font-size: 0.85rem; display: inline-block;">
              ${req.blood_group}
            </span>
          </td>
          <td>
            <div style="font-weight: 600; font-size: 0.88rem;">${hospitalName}</div>
            <div style="font-size: 0.76rem; color: var(--text-secondary);">${areaName} • ${units} Bag(s)</div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <span style="font-weight: 700; color: #0284C7;">${responses} Donors Responded</span>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button type="button" class="btn-card-action primary" onclick="window.viewRequestDonors('${req.blood_group}')">
                View Donors
              </button>
              <button type="button" class="btn-card-action" onclick="window.openChatWithDonor('dn-001')">
                Chat
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Filter Tab Button Listeners
  document.querySelectorAll('.request-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.request-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderSeekerRequestsTable(btn.getAttribute('data-filter'));
    });
  });

  // Action handlers
  window.viewRequestDonors = function(bloodGroup) {
    activateSection('section-donor-directory');
    const bloodSelect = document.getElementById('dirBloodFilter');
    if (bloodSelect) {
      bloodSelect.value = bloodGroup;
      if (typeof window.filterDonorDirectory === 'function') {
        window.filterDonorDirectory();
      }
    } else {
      showToast(`Viewing available donors matching blood group ${bloodGroup}`);
    }
  };

  window.openChatWithDonor = function(donorId) {
    activateSection('section-seeker-chat');
    if (typeof window.selectSeekerChatThread === 'function') {
      window.selectSeekerChatThread('thread-ayesha');
    } else {
      showToast('Opening live chat coordinator with donor...');
    }
  };

  // Sync with API to load any dynamic requests from server
  async function loadSeekerRequestsFromApi() {
    try {
      const res = await fetch('/api/v1/seeker/requests');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && Array.isArray(data.requests) && data.requests.length > 0) {
          data.requests.forEach(apiReq => {
            if (!seekerRequests.some(r => r.id === apiReq.id)) {
              seekerRequests.unshift({
                id: apiReq.id,
                patient_name: apiReq.patient_name || `Recipient (${apiReq.blood_group})`,
                blood_group: apiReq.blood_group,
                hospital: apiReq.hospital_name,
                area: apiReq.area || apiReq.district || 'Dhaka',
                units: apiReq.units || 1,
                needed_date: 'Immediate',
                status: apiReq.is_emergency ? 'Emergency' : 'Active',
                is_emergency: apiReq.is_emergency ? 1 : 0,
                responses_count: apiReq.is_emergency ? 4 : 2,
                created_at: 'Recently'
              });
            }
          });
          updateMetrics();
          renderSeekerRequestsTable('all');
        }
      }
    } catch (err) {
      console.warn('Seeker requests API fetch skipped:', err);
    }
  }

  // Initialize Section 1
  updateMetrics();
  renderSeekerRequestsTable('all');
  loadSeekerRequestsFromApi();

  // Initialize view from URL hash if provided
  if (window.location.hash) {
    activateSection(window.location.hash);
  } else {
    activateSection('section-seeker-dashboard');
  }
});
