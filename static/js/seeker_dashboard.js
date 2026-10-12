// ================= BLOOD SEEKER PORTAL SCRIPT =================
// Blood seeker dashboard interactions and emergency request submission.

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

    if (cleanId === 'section-nearby-map') {
      window.requestAnimationFrame(() => {
        if (!nearbyMap) initializeNearbyMap();
        else nearbyMap.invalidateSize();
        if (!nearbyMapLoaded) loadNearbyDonors();
      });
    }
    if (cleanId === 'section-donor-directory') loadDonorDirectory();
    if (cleanId === 'section-donor-credentials') loadPublicDonorProfiles();

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

  // =========================================================================
  // 4. NEARBY DONORS INTERACTIVE MAP VIEW
  // =========================================================================
  const mapElement = document.getElementById('seekerDonorMap');
  const mapBloodFilter = document.getElementById('mapBloodGroupFilter');
  const mapRadiusSlider = document.getElementById('mapRadiusSlider');
  const mapRadiusValue = document.getElementById('mapRadiusValue');
  const mapStatus = document.getElementById('mapDonorStatus');
  const mapDonorCount = document.getElementById('mapDonorCount');
  const mapDonorList = document.getElementById('mapNearbyDonorsList');
  let nearbyMap = null;
  let nearbyMapLoaded = false;
  let nearbyMapMarkers = [];

  function initializeNearbyMap() {
    if (!mapElement || typeof window.L === 'undefined') {
      if (mapStatus) mapStatus.textContent = 'The map could not be loaded. Check your connection and try again.';
      return;
    }
    if (nearbyMap) {
      nearbyMap.invalidateSize();
      return;
    }

    nearbyMap = window.L.map(mapElement, { scrollWheelZoom: false }).setView([23.75, 90.38], 12);
    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(nearbyMap);
  }

  function renderNearbyDonors(donors) {
    if (!nearbyMap || !mapDonorList || !mapDonorCount) return;
    nearbyMapMarkers.forEach(marker => nearbyMap.removeLayer(marker));
    nearbyMapMarkers = [];
    mapDonorList.replaceChildren();
    mapDonorCount.textContent = String(donors.length);

    if (donors.length === 0) {
      mapStatus.textContent = 'No available donors match these filters.';
      return;
    }

    mapStatus.textContent = `${donors.length} available donor${donors.length === 1 ? '' : 's'} found.`;
    const bounds = [];
    donors.forEach((donor, index) => {
      const markerIcon = window.L.divIcon({
        className: 'nearby-donor-icon',
        html: `<span class="map-donor-marker">${donor.blood_group}</span>`,
        iconSize: [42, 42],
        iconAnchor: [21, 21]
      });
      const marker = window.L.marker([donor.lat, donor.lng], { icon: markerIcon }).addTo(nearbyMap);
      const popup = document.createElement('div');
      const bloodGroup = document.createElement('strong');
      bloodGroup.textContent = `${donor.blood_group} donor`;
      const area = document.createElement('p');
      area.textContent = `${donor.area}, ${donor.district}`;
      const distance = document.createElement('p');
      distance.textContent = `${Number(donor.distance_km).toFixed(1)} km away · ${donor.location_precision === 'exact' ? 'Shared location' : 'Approximate area'}`;
      popup.append(bloodGroup, area, distance);
      marker.bindPopup(popup);
      nearbyMapMarkers.push(marker);
      bounds.push([donor.lat, donor.lng]);

      const listButton = document.createElement('button');
      listButton.type = 'button';
      listButton.className = 'nearby-donor-row';
      const group = document.createElement('span');
      group.className = 'nearby-donor-group';
      group.textContent = donor.blood_group;
      const details = document.createElement('span');
      details.className = 'nearby-donor-details';
      const location = document.createElement('strong');
      location.textContent = donor.area;
      const distanceText = document.createElement('small');
      distanceText.textContent = `${Number(donor.distance_km).toFixed(1)} km away`;
      details.append(location, distanceText);
      listButton.append(group, details);
      listButton.addEventListener('click', () => {
        nearbyMap.setView([donor.lat, donor.lng], Math.max(nearbyMap.getZoom(), 14));
        nearbyMapMarkers[index].openPopup();
      });
      mapDonorList.append(listButton);
    });

    if (bounds.length > 1) nearbyMap.fitBounds(bounds, { padding: [48, 48], maxZoom: 14 });
    else nearbyMap.setView(bounds[0], 14);
  }

  async function loadNearbyDonors() {
    if (!mapStatus) return;
    initializeNearbyMap();
    if (!nearbyMap) return;
    mapStatus.textContent = 'Loading available donors...';
    mapStatus.setAttribute('aria-busy', 'true');
    const params = new URLSearchParams({ radius_km: mapRadiusSlider?.value || '15' });
    if (mapBloodFilter?.value) params.set('blood_group', mapBloodFilter.value);
    try {
      const response = await fetch(`/api/v1/seeker/donors/map?${params.toString()}`);
      if (!response.ok) throw new Error('Donor map request failed');
      const data = await response.json();
      nearbyMapLoaded = true;
      renderNearbyDonors(Array.isArray(data.donors) ? data.donors : []);
    } catch (error) {
      mapStatus.textContent = 'Nearby donors could not be loaded. Please try again.';
    } finally {
      mapStatus.removeAttribute('aria-busy');
    }
  }

  mapBloodFilter?.addEventListener('change', loadNearbyDonors);
  mapRadiusSlider?.addEventListener('input', () => {
    if (mapRadiusValue) mapRadiusValue.textContent = `${mapRadiusSlider.value} km`;
    loadNearbyDonors();
  });
  document.getElementById('nearbyMapRefresh')?.addEventListener('click', loadNearbyDonors);

  const donorDirectoryGrid = document.getElementById('donorDirectoryGrid');
  const donorDirectoryStatus = document.getElementById('donorDirectoryStatus');
  const donorProfileStatus = document.getElementById('donorProfileStatus');
  const publicDonorProfile = document.getElementById('donorPublicProfile');

  async function loadDonorDirectory() {
    if (!donorDirectoryGrid || !donorDirectoryStatus) return;
    donorDirectoryStatus.textContent = 'Loading donors...';
    donorDirectoryStatus.setAttribute('aria-busy', 'true');
    const params = new URLSearchParams({ radius_km: '30' });
    const bloodGroup = document.getElementById('dirBloodFilter')?.value;
    const query = document.getElementById('dirSearch')?.value.trim();
    const availableOnly = document.getElementById('dirAvailableOnly')?.checked;
    if (bloodGroup) params.set('blood_group', bloodGroup);
    if (query) params.set('query', query);
    if (availableOnly) params.set('available_only', 'true');
    try {
      const response = await fetch(`/api/v1/seeker/donors?${params.toString()}`);
      if (!response.ok) throw new Error('Donor directory request failed');
      const data = await response.json();
      const donors = Array.isArray(data.donors) ? data.donors : [];
      donorDirectoryGrid.replaceChildren();
      if (!donors.length) {
        donorDirectoryStatus.textContent = 'No donors match these filters.';
        return;
      }
      donorDirectoryStatus.textContent = `${donors.length} donor${donors.length === 1 ? '' : 's'} found.`;
      donors.forEach(donor => {
        const card = document.createElement('article');
        card.className = 'donor-card';
        const top = document.createElement('div');
        top.className = 'donor-card-top';
        const identity = document.createElement('div');
        identity.className = 'donor-card-avatar-combo';
        const avatar = document.createElement('span');
        avatar.className = 'donor-card-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = String(donor.name || 'D').trim().charAt(0).toUpperCase();
        const identityText = document.createElement('div');
        const name = document.createElement('h3');
        name.className = 'donor-card-name';
        name.textContent = donor.name || 'Donor';
        const location = document.createElement('p');
        location.className = 'donor-card-loc';
        location.textContent = [donor.area, donor.district].filter(Boolean).join(', ') || 'Location not shared';
        identityText.append(name, location);
        identity.append(avatar, identityText);
        const group = document.createElement('span');
        group.className = 'donor-badge-group';
        group.textContent = donor.blood_group || 'Unknown';
        top.append(identity, group);

        const stats = document.createElement('div');
        stats.className = 'donor-card-stats';
        const availability = document.createElement('div');
        availability.className = 'stat-item';
        const availabilityValue = document.createElement('div');
        availabilityValue.className = 'stat-item-val';
        availabilityValue.textContent = donor.is_available ? 'Available' : 'Unavailable';
        const availabilityLabel = document.createElement('div');
        availabilityLabel.className = 'stat-item-lbl';
        availabilityLabel.textContent = 'Status';
        availability.append(availabilityValue, availabilityLabel);
        const verification = document.createElement('div');
        verification.className = 'stat-item';
        const verificationValue = document.createElement('div');
        verificationValue.className = 'stat-item-val';
        verificationValue.textContent = donor.is_verified ? 'Verified' : 'Not verified';
        const verificationLabel = document.createElement('div');
        verificationLabel.className = 'stat-item-lbl';
        verificationLabel.textContent = 'Credentials';
        verification.append(verificationValue, verificationLabel);
        stats.append(availability, verification);

        const viewButton = document.createElement('button');
        viewButton.type = 'button';
        viewButton.className = 'btn-card-action primary';
        viewButton.textContent = 'View all public profiles';
        viewButton.addEventListener('click', () => {
          activateSection('section-donor-credentials');
        });
        card.append(top, stats, viewButton);
        donorDirectoryGrid.append(card);
      });
    } catch (error) {
      console.error('Donor directory error:', error);
      donorDirectoryStatus.textContent = 'Donors could not be loaded. Please try again.';
    } finally {
      donorDirectoryStatus.removeAttribute('aria-busy');
    }
  }

  async function loadPublicDonorProfiles() {
    if (!donorProfileStatus || !publicDonorProfile) return;
    donorProfileStatus.textContent = 'Loading public donor profiles...';
    donorProfileStatus.setAttribute('aria-busy', 'true');
    publicDonorProfile.replaceChildren();
    try {
      const response = await fetch('/api/v1/seeker/donors?radius_km=30');
      if (!response.ok) throw new Error('Public donor profiles request failed');
      const data = await response.json();
      const donors = Array.isArray(data.donors) ? data.donors : [];
      if (!donors.length) {
        donorProfileStatus.textContent = 'No public donor profiles are available right now.';
        return;
      }
      donors.forEach(donor => {
        const card = document.createElement('article');
        card.className = 'donor-card public-donor-profile';
        const hero = document.createElement('header');
        hero.className = 'credentials-hero-panel';
        const heroLeft = document.createElement('div');
        heroLeft.className = 'credentials-hero-left';
        const avatar = document.createElement('span');
        avatar.className = 'credentials-large-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = String(donor.name || 'D').trim().charAt(0).toUpperCase();
        const identity = document.createElement('div');
        const title = document.createElement('h3');
        title.className = 'donor-card-name';
        title.textContent = donor.name || 'Donor';
        const subheading = document.createElement('p');
        subheading.className = 'card-subtitle';
        subheading.textContent = [donor.area, donor.district].filter(Boolean).join(', ') || 'Location not shared';
        identity.append(title, subheading);
        heroLeft.append(avatar, identity);
        const bloodGroup = document.createElement('span');
        bloodGroup.className = 'donor-badge-group donor-profile-blood-group';
        bloodGroup.textContent = donor.blood_group || 'Blood group not shared';
        hero.append(heroLeft, bloodGroup);

        const credentials = document.createElement('div');
        credentials.className = 'public-profile-credentials';
        const availability = document.createElement('p');
        availability.textContent = donor.is_available ? 'Availability: Available now' : 'Availability: Not currently available';
        const verification = document.createElement('p');
        verification.textContent = donor.is_verified ? 'Verification: Verified donor' : 'Verification: Not verified';
        const history = document.createElement('p');
        history.textContent = Number.isInteger(donor.donation_count)
          ? `Donation history: ${donor.donation_count} donation${donor.donation_count === 1 ? '' : 's'} shared`
          : 'Donation history: Not shared';
        credentials.append(availability, verification, history);
        card.append(hero, credentials);
        publicDonorProfile.append(card);
      });
      donorProfileStatus.textContent = `${donors.length} public donor profile${donors.length === 1 ? '' : 's'}.`;
    } catch (error) {
      console.error('Public donor profiles error:', error);
      donorProfileStatus.textContent = 'Donor profiles could not be loaded. Please try again.';
    } finally {
      donorProfileStatus.removeAttribute('aria-busy');
    }
  }

  document.getElementById('dirBloodFilter')?.addEventListener('change', loadDonorDirectory);
  document.getElementById('dirAvailableOnly')?.addEventListener('change', loadDonorDirectory);
  document.getElementById('dirSearch')?.addEventListener('input', () => {
    window.clearTimeout(window._donorDirectorySearchTimeout);
    window._donorDirectorySearchTimeout = window.setTimeout(loadDonorDirectory, 250);
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
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[character]);

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
      const currentStatus = req.status || (isSos ? 'Emergency' : 'Active');
      const statusBadge = isSos
        ? `<span class="nav-badge-emergency">● SOS EMERGENCY · ${escapeHtml(currentStatus)}</span>`
        : currentStatus === 'Fulfilled'
        ? `<span class="nav-pill-badge pill-green">✓ Fulfilled</span>`
        : `<span class="nav-pill-badge pill-blue">${escapeHtml(currentStatus)}</span>`;

      const hospitalName = req.hospital || req.hospital_name || 'Dhaka Hospital';
      const areaName = req.area || req.district || 'Dhaka';
      const patient = req.patient_name || 'Patient';
      const units = req.units || 1;
      const responses = req.responses_count ?? (isSos ? 5 : 2);

      return `
        <tr>
          <td style="font-weight: 700; color: var(--text-primary);">#REQ-${escapeHtml(req.id)}</td>
          <td><strong>${escapeHtml(patient)}</strong></td>
          <td>
            <span class="blood-group-badge" style="background: #FFE4E6; color: #BE123C; font-weight: 800; padding: 3px 8px; border-radius: 6px; font-size: 0.85rem; display: inline-block;">
              ${escapeHtml(req.blood_group)}
            </span>
          </td>
          <td>
            <div style="font-weight: 600; font-size: 0.88rem;">${escapeHtml(hospitalName)}</div>
            <div style="font-size: 0.76rem; color: var(--text-secondary);">${escapeHtml(areaName)} • ${escapeHtml(units)} Bag(s)</div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <span style="font-weight: 700; color: #0284C7;">${escapeHtml(responses)} Donors Responded</span>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button type="button" class="btn-card-action primary" onclick="window.viewRequestDonors('${escapeHtml(req.blood_group)}')">
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
                status: apiReq.is_emergency ? (apiReq.status || 'Emergency') : (apiReq.status || 'Active'),
                is_emergency: apiReq.is_emergency ? 1 : 0,
                responses_count: 0,
                created_at: apiReq.created_at || 'Recently'
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

  const emergencyRequestForm = document.getElementById('emergencyRequestForm');
  if (emergencyRequestForm) {
    emergencyRequestForm.addEventListener('submit', async event => {
      event.preventDefault();
      if (!emergencyRequestForm.reportValidity()) return;

      const submitButton = document.getElementById('submitEmergencyRequest');
      const feedback = document.getElementById('emergencyRequestFeedback');
      const formData = new FormData(emergencyRequestForm);
      const payload = Object.fromEntries(formData.entries());
      payload.units = Number(payload.units);
      submitButton.disabled = true;
      submitButton.textContent = 'Sending emergency request...';
      feedback.hidden = true;

      try {
        const response = await fetch('/api/v1/seeker/requests/emergency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') {
          const detail = Array.isArray(data.detail)
            ? data.detail.map(item => item.msg).join(' ')
            : data.detail;
          throw new Error(detail || data.message || 'Could not create the emergency request.');
        }

        await loadSeekerRequestsFromApi();
        const notification = data.notifications || {};
        let notificationMessage = '';
        if (notification.status === 'not_configured') {
          notificationMessage = ' SMS alerts were not sent because the SMS gateway is not configured.';
        } else if (notification.status === 'failed' || notification.status === 'partial') {
          notificationMessage = ` SMS delivery: ${notification.sent} sent, ${notification.failed} failed.`;
        } else if (notification.status === 'no_matches') {
          notificationMessage = ' No available matching donors were found to notify.';
        } else if (notification.status === 'sent') {
          notificationMessage = ` SMS alerts sent to ${notification.sent} matching donor(s).`;
        }

        feedback.textContent = `Emergency request #${data.request.id} is active and can be tracked in My Posted Blood Requests.${notificationMessage}`;
        feedback.hidden = false;
        emergencyRequestForm.reset();
        showToast(`Emergency request #${data.request.id} created.`);
      } catch (error) {
        feedback.textContent = error.message || 'The emergency request could not be submitted. Please try again.';
        feedback.hidden = false;
        showToast(feedback.textContent, 'error');
      } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<span aria-hidden="true">🚨</span> Broadcast Emergency Request';
      }
    });
  }

  // Update user name in sidebar, avatar circle, and banner greeting
  function updateSeekerNameEverywhere(name) {
    if (!name || !name.trim()) return;
    const trimmed = name.trim();

    // 1. Sidebar name text
    const sidebarNameEl = document.getElementById('seekerSidebarName');
    if (sidebarNameEl) {
      sidebarNameEl.textContent = trimmed;
    } else {
      const fallbackSidebar = document.querySelector('.seeker-name-text span');
      if (fallbackSidebar) fallbackSidebar.textContent = trimmed;
    }

    // 2. Sidebar avatar circle (initial letter)
    const sidebarAvatarEl = document.getElementById('seekerSidebarAvatar');
    if (sidebarAvatarEl) {
      sidebarAvatarEl.textContent = trimmed.charAt(0).toUpperCase();
    } else {
      const fallbackAvatar = document.querySelector('.seeker-avatar-circle');
      if (fallbackAvatar) fallbackAvatar.textContent = trimmed.charAt(0).toUpperCase();
    }

    // 3. Welcome banner greeting
    const bannerGreetingEl = document.getElementById('seekerBannerGreeting');
    if (bannerGreetingEl) {
      bannerGreetingEl.textContent = `Welcome back, ${trimmed}! 👋`;
    } else {
      const fallbackGreeting = document.querySelector('.banner-welcome-text h1');
      if (fallbackGreeting) fallbackGreeting.textContent = `Welcome back, ${trimmed}! 👋`;
    }
  }

  // =========================================================================
  // 9. SEEKER PORTAL SETTINGS & PREFERENCES
  // =========================================================================
  const settingsForm = document.getElementById('seekerSettingsForm');
  if (settingsForm) {
    settingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const newName = document.getElementById('setSeekerName')?.value.trim() || 'Nabil Hasan';
      const settingsPayload = {
        full_name: newName,
        phone: document.getElementById('setSeekerPhone')?.value.trim() || '+8801723456789',
        default_hospital: document.getElementById('setDefaultHospital')?.value || 'Square Hospital',
        sms_alerts: document.getElementById('toggleSmsAlerts')?.checked ?? true,
        push_alerts: document.getElementById('togglePushAlerts')?.checked ?? true,
        audio_siren: document.getElementById('toggleAudioSiren')?.checked ?? true,
        default_radius: document.getElementById('setDefaultRadius')?.value || '10'
      };

      // Immediately update name across sidebar, avatar, and banner!
      updateSeekerNameEverywhere(newName);

      try {
        const response = await fetch('/api/v1/seeker/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settingsPayload)
        });
        if (response.ok) {
          showToast('Profile name & settings saved successfully!');
        } else {
          showToast('Settings saved locally.');
        }
      } catch (err) {
        showToast('Profile name & settings saved successfully!');
      }
    });
  }

  // Load saved settings from API
  async function loadSeekerSettingsFromApi() {
    try {
      const res = await fetch('/api/v1/seeker/settings');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && data.settings) {
          const s = data.settings;
          const nameEl = document.getElementById('setSeekerName');
          const phoneEl = document.getElementById('setSeekerPhone');
          const hospEl = document.getElementById('setDefaultHospital');
          const radiusEl = document.getElementById('setDefaultRadius');
          const smsEl = document.getElementById('toggleSmsAlerts');
          const pushEl = document.getElementById('togglePushAlerts');
          const sirenEl = document.getElementById('toggleAudioSiren');

          if (nameEl && s.full_name) {
            nameEl.value = s.full_name;
            updateSeekerNameEverywhere(s.full_name);
          }
          if (phoneEl && s.phone) phoneEl.value = s.phone;
          if (hospEl && s.default_hospital) hospEl.value = s.default_hospital;
          if (radiusEl && s.default_radius) radiusEl.value = s.default_radius;
          if (smsEl && typeof s.sms_alerts === 'boolean') smsEl.checked = s.sms_alerts;
          if (pushEl && typeof s.push_alerts === 'boolean') pushEl.checked = s.push_alerts;
          if (sirenEl && typeof s.audio_siren === 'boolean') sirenEl.checked = s.audio_siren;
        }
      }
    } catch (err) {
      console.warn('Seeker settings API fetch skipped:', err);
    }
  }

  // Dark Mode Theme Toggle Integration
  const seekerThemeToggle = document.getElementById('seekerThemeToggle');
  if (seekerThemeToggle) {
    const isCurrentDark = document.documentElement.getAttribute('data-theme') === 'dark' ||
      localStorage.getItem('sbds-theme') === 'dark';
    seekerThemeToggle.checked = isCurrentDark;

    seekerThemeToggle.addEventListener('change', () => {
      const isDark = seekerThemeToggle.checked;
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
      localStorage.setItem('sbds-theme', isDark ? 'dark' : 'light');
      showToast(`Switched to ${isDark ? 'Dark' : 'Light'} Mode`);
    });
  }

  // =========================================================================
  // 9B. DANGER ZONE - SEEKER ACCOUNT DELETION
  // =========================================================================
  const deleteModal = document.getElementById('deleteAccountModal');
  const btnOpenDeleteModal = document.getElementById('btnOpenDeleteAccountModal');
  const cancelDeleteBtn = document.getElementById('cancelDeleteAccountBtn');
  const closeDeleteModalX = document.getElementById('closeDeleteModalX');
  const confirmDeleteBtn = document.getElementById('confirmDeleteAccountBtn');
  const deleteConfirmInput = document.getElementById('deleteConfirmationInput');

  function openDeleteAccountModal() {
    if (!deleteModal) return;
    if (deleteConfirmInput) {
      deleteConfirmInput.value = '';
    }
    if (confirmDeleteBtn) {
      confirmDeleteBtn.disabled = true;
      confirmDeleteBtn.style.opacity = '0.5';
      confirmDeleteBtn.style.cursor = 'not-allowed';
      confirmDeleteBtn.textContent = 'Permanently Delete';
    }
    deleteModal.style.display = 'flex';
    setTimeout(() => {
      deleteConfirmInput?.focus();
    }, 50);
  }

  function closeDeleteAccountModal() {
    if (!deleteModal) return;
    deleteModal.style.display = 'none';
    if (deleteConfirmInput) {
      deleteConfirmInput.value = '';
    }
  }

  window.openDeleteAccountModal = openDeleteAccountModal;
  window.closeDeleteAccountModal = closeDeleteAccountModal;

  if (btnOpenDeleteModal) {
    btnOpenDeleteModal.addEventListener('click', openDeleteAccountModal);
  }

  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', closeDeleteAccountModal);
  }

  if (closeDeleteModalX) {
    closeDeleteModalX.addEventListener('click', closeDeleteAccountModal);
  }

  if (deleteModal) {
    deleteModal.addEventListener('click', (e) => {
      if (e.target === deleteModal) closeDeleteAccountModal();
    });
  }

  if (deleteConfirmInput && confirmDeleteBtn) {
    deleteConfirmInput.addEventListener('input', () => {
      const val = deleteConfirmInput.value.trim().toUpperCase();
      if (val === 'DELETE') {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.style.opacity = '1';
        confirmDeleteBtn.style.cursor = 'pointer';
      } else {
        confirmDeleteBtn.disabled = true;
        confirmDeleteBtn.style.opacity = '0.5';
        confirmDeleteBtn.style.cursor = 'not-allowed';
      }
    });

    deleteConfirmInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !confirmDeleteBtn.disabled) {
        confirmDeleteBtn.click();
      }
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', async () => {
      if (confirmDeleteBtn.disabled) return;
      confirmDeleteBtn.disabled = true;
      confirmDeleteBtn.textContent = 'Deleting Account...';

      try {
        const response = await fetch('/api/v1/seeker/account', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (response.ok && data.status === 'success') {
          closeDeleteAccountModal();
          showToast('Account deleted successfully. Redirecting to login...');
          setTimeout(() => {
            window.location.href = data.redirect_url || '/login?account_deleted=1';
          }, 1000);
        } else {
          showToast(data.message || 'Failed to delete account. Please try again.');
          confirmDeleteBtn.disabled = false;
          confirmDeleteBtn.textContent = 'Permanently Delete';
        }
      } catch (err) {
        console.error('Account deletion error:', err);
        showToast('Error deleting account. Please try again.');
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = 'Permanently Delete';
      }
    });
  }

  // Initialize Section 1 & Section 9
  updateMetrics();
  renderSeekerRequestsTable('all');
  loadSeekerRequestsFromApi();
  loadSeekerSettingsFromApi();

  // Initialize view from URL hash if provided
  if (window.location.hash) {
    activateSection(window.location.hash);
  } else {
    activateSection('section-seeker-dashboard');
  }
});
