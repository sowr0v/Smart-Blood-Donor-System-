// ================= BLOOD SEEKER PORTAL SCRIPT =================
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

    // Leaflet map refresh when map section becomes visible
    if (cleanId === 'section-nearby-map' && window._seekerMapInstance) {
      setTimeout(() => {
        window._seekerMapInstance.invalidateSize();
      }, 250);
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
  // MOCK DONORS DATA (Dhaka Region)
  // =========================================================================
  const DONORS_DATA = [
    {
      id: "dn-001",
      name: "Ayesha Rahman",
      blood_group: "A+",
      phone: "+8801712345678",
      formatted_phone: "+880 1712-345678",
      district: "Dhaka",
      area: "Dhanmondi",
      lat: 23.7461,
      lng: 90.3742,
      distance_km: 1.2,
      is_available: true,
      badge_tier: "Gold Life Saver",
      total_donations: 8,
      rating: 4.9,
      reviews_count: 18,
      last_donation: "110 days ago",
      response_time: "6 mins",
      bio: "Voluntary blood donor for 4 years. Close to Square & Bangladesh Medical. Ready for emergencies.",
      nid_verified: true,
      hemoglobin: "14.2 g/dL",
      weight_bp: "58 kg | BP 118/78 mmHg",
      screening: "Hepatitis B/C, HIV, Syphilis Tested Negative (Sept 2026)",
      reliability: "100% (No no-shows)",
      reviews: [
        { author: "Nabil Hasan", text: "Ayesha apu responded within 10 minutes when my mother needed blood at Square Hospital. Lifesaver!", rating: 5, date: "1 month ago" },
        { author: "Dr. Farhan (Square)", text: "Punctual, cooperative donor with clean screening reports.", rating: 5, date: "3 months ago" }
      ]
    },
    {
      id: "dn-002",
      name: "Tanvir Ahmed",
      blood_group: "O+",
      phone: "+8801711223344",
      formatted_phone: "+880 1711-223344",
      district: "Dhaka",
      area: "Panthapath",
      lat: 23.7518,
      lng: 90.3879,
      distance_km: 0.8,
      is_available: true,
      badge_tier: "Platinum Donor",
      total_donations: 12,
      rating: 5.0,
      reviews_count: 26,
      last_donation: "95 days ago",
      response_time: "4 mins",
      bio: "Registered universal donor. Works near Panthapath. Available anytime for critical trauma/surgery.",
      nid_verified: true,
      hemoglobin: "15.1 g/dL",
      weight_bp: "72 kg | BP 120/80 mmHg",
      screening: "All blood tests cleared (Oct 2026)",
      reliability: "100%",
      reviews: [
        { author: "Kamrul Islam", text: "Tanvir brother arrived within 25 minutes of calling him for my brother's ICU emergency.", rating: 5, date: "2 weeks ago" }
      ]
    },
    {
      id: "dn-003",
      name: "Sadia Islam",
      blood_group: "B+",
      phone: "+8801722334455",
      formatted_phone: "+880 1722-334455",
      district: "Dhaka",
      area: "Shahbagh",
      lat: 23.7380,
      lng: 90.3956,
      distance_km: 2.1,
      is_available: true,
      badge_tier: "Silver Donor",
      total_donations: 5,
      rating: 4.8,
      reviews_count: 12,
      last_donation: "130 days ago",
      response_time: "8 mins",
      bio: "DU student, situated 5 mins away from DMCH and BSMMU (PG Hospital).",
      nid_verified: true,
      hemoglobin: "13.8 g/dL",
      weight_bp: "54 kg | BP 115/75 mmHg",
      screening: "Cleared & verified at DMCH Transfusion",
      reliability: "98%",
      reviews: [
        { author: "Rehana Begum", text: "Very polite student, came straight from campus to donate for child surgery.", rating: 5, date: "2 months ago" }
      ]
    },
    {
      id: "dn-004",
      name: "Rafiqul Islam",
      blood_group: "O-",
      phone: "+8801733445566",
      formatted_phone: "+880 1733-445566",
      district: "Dhaka",
      area: "Farmgate",
      lat: 23.7561,
      lng: 90.3872,
      distance_km: 1.5,
      is_available: true,
      badge_tier: "Rare Hero Tier",
      total_donations: 15,
      rating: 5.0,
      reviews_count: 32,
      last_donation: "105 days ago",
      response_time: "5 mins",
      bio: "Rare O- donor. Dedicated to critical neonatal and emergency transfusions across Dhaka.",
      nid_verified: true,
      hemoglobin: "14.9 g/dL",
      weight_bp: "68 kg | BP 118/76 mmHg",
      screening: "Certified Rare Donor Certificate by Red Crescent",
      reliability: "100%",
      reviews: [
        { author: "Dr. Shamim", text: "Saved a preterm baby with emergency O negative blood in NICU.", rating: 5, date: "1 month ago" }
      ]
    },
    {
      id: "dn-005",
      name: "Farhan Kabir",
      blood_group: "AB+",
      phone: "+8801744556677",
      formatted_phone: "+880 1744-556677",
      district: "Dhaka",
      area: "Mohakhali",
      lat: 23.7776,
      lng: 90.4054,
      distance_km: 3.8,
      is_available: true,
      badge_tier: "Gold Life Saver",
      total_donations: 7,
      rating: 4.9,
      reviews_count: 14,
      last_donation: "140 days ago",
      response_time: "10 mins",
      bio: "Platelets (PRP) and Whole Blood donor. Located near TB Gate / Cancer Hospital Mohakhali.",
      nid_verified: true,
      hemoglobin: "14.5 g/dL",
      weight_bp: "70 kg | BP 122/82 mmHg",
      screening: "Lab tested negative for all viral markers",
      reliability: "99%",
      reviews: [
        { author: "Ashraf Ali", text: "Great coordination and verified reports.", rating: 5, date: "3 weeks ago" }
      ]
    },
    {
      id: "dn-006",
      name: "Nusrat Jahan",
      blood_group: "A-",
      phone: "+8801755667788",
      formatted_phone: "+880 1755-667788",
      district: "Dhaka",
      area: "Mirpur-10",
      lat: 23.8071,
      lng: 90.3686,
      distance_km: 5.4,
      is_available: false,
      badge_tier: "Silver Donor",
      total_donations: 4,
      rating: 4.7,
      reviews_count: 9,
      last_donation: "45 days ago",
      response_time: "15 mins",
      bio: "A Negative donor. Currently in rest recovery period, eligible next month.",
      nid_verified: true,
      hemoglobin: "13.5 g/dL",
      weight_bp: "52 kg | BP 114/74 mmHg",
      screening: "Screening valid",
      reliability: "96%",
      reviews: [
        { author: "Nazmul", text: "Helpful donor.", rating: 5, date: "2 months ago" }
      ]
    },
    {
      id: "dn-007",
      name: "Mahfuzur Rahman",
      blood_group: "B-",
      phone: "+8801766778899",
      formatted_phone: "+880 1766-778899",
      district: "Dhaka",
      area: "Gulshan-1",
      lat: 23.7788,
      lng: 90.4182,
      distance_km: 4.2,
      is_available: true,
      badge_tier: "Gold Life Saver",
      total_donations: 9,
      rating: 4.9,
      reviews_count: 20,
      last_donation: "115 days ago",
      response_time: "7 mins",
      bio: "Corporate volunteer. Available with personal transportation to reach hospitals quickly.",
      nid_verified: true,
      hemoglobin: "15.0 g/dL",
      weight_bp: "75 kg | BP 120/78 mmHg",
      screening: "Full screening cleared at United Hospital",
      reliability: "100%",
      reviews: [
        { author: "Tareq Hasan", text: "Reached United Hospital within 15 mins with his motorbike.", rating: 5, date: "1 month ago" }
      ]
    },
    {
      id: "dn-008",
      name: "Sumaiya Akter",
      blood_group: "AB-",
      phone: "+8801777889900",
      formatted_phone: "+880 1777-889900",
      district: "Dhaka",
      area: "Banani",
      lat: 23.7937,
      lng: 90.4043,
      distance_km: 4.9,
      is_available: true,
      badge_tier: "Rare Hero Tier",
      total_donations: 6,
      rating: 5.0,
      reviews_count: 15,
      last_donation: "120 days ago",
      response_time: "9 mins",
      bio: "Rare AB- donor. Active in thalassemia support and emergency blood networks.",
      nid_verified: true,
      hemoglobin: "13.9 g/dL",
      weight_bp: "56 kg | BP 116/76 mmHg",
      screening: "Clean reports verified by Blood Bank",
      reliability: "100%",
      reviews: [
        { author: "Shamima", text: "Extremely kind donor for my niece's surgery.", rating: 5, date: "4 weeks ago" }
      ]
    }
  ];

  // =========================================================================
  // 1. SEEKER PERSONAL DASHBOARD: RECENT REQUESTS & RESPONSES
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

  function renderSeekerRequestsTable(filter = 'all') {
    const tableBody = document.getElementById('seekerRequestsTableBody');
    if (!tableBody) return;

    let filtered = seekerRequests;
    if (filter === 'active') filtered = seekerRequests.filter(r => r.status === 'Active');
    else if (filter === 'emergency') filtered = seekerRequests.filter(r => r.is_emergency === 1);
    else if (filter === 'fulfilled') filtered = seekerRequests.filter(r => r.status === 'Fulfilled');

    if (filtered.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">
            No blood requests found under this filter.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = filtered.map(req => {
      const statusBadge = req.is_emergency
        ? `<span class="nav-badge-emergency">● SOS EMERGENCY</span>`
        : req.status === 'Fulfilled'
        ? `<span class="nav-pill-badge pill-green">✓ Fulfilled</span>`
        : `<span class="nav-pill-badge pill-blue">Active</span>`;

      return `
        <tr>
          <td style="font-weight: 700; color: var(--text-primary);">#REQ-${req.id}</td>
          <td><strong>${req.patient_name}</strong></td>
          <td>
            <span style="background: #FFE4E6; color: #BE123C; font-weight: 800; padding: 3px 8px; border-radius: 6px; font-size: 0.85rem;">
              ${req.blood_group}
            </span>
          </td>
          <td>
            <div style="font-weight: 600; font-size: 0.88rem;">${req.hospital}</div>
            <div style="font-size: 0.76rem; color: var(--text-secondary);">${req.area} • ${req.units} Bag(s)</div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <span style="font-weight: 700; color: #0284C7;">${req.responses_count} Donors Responded</span>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn-card-action primary" onclick="window.viewRequestDonors('${req.blood_group}')" style="padding: 5px 10px; font-size: 0.78rem;">
                View Donors
              </button>
              <button class="btn-card-action" onclick="window.openChatWithDonor('dn-001')" style="padding: 5px 10px; font-size: 0.78rem;">
                Chat
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Requests Filter Tabs
  document.querySelectorAll('.request-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.request-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderSeekerRequestsTable(btn.getAttribute('data-filter'));
    });
  });

  window.viewRequestDonors = function(bloodGroup) {
    activateSection('section-donor-directory');
    const bloodSelect = document.getElementById('dirBloodFilter');
    if (bloodSelect) {
      bloodSelect.value = bloodGroup;
      filterDonorDirectory();
    }
  };

  // =========================================================================
  // 2. CREATE STANDARD BLOOD REQUEST
  // =========================================================================
  const stdForm = document.getElementById('createStandardRequestForm');
  const previewPatient = document.getElementById('previewPatientName');
  const previewGroup = document.getElementById('previewBloodGroup');
  const previewHospital = document.getElementById('previewHospital');
  const previewUnits = document.getElementById('previewUnits');
  const previewDate = document.getElementById('previewDate');

  if (stdForm) {
    // Live Preview updates
    stdForm.addEventListener('input', () => {
      const patient = document.getElementById('stdPatientName')?.value.trim();
      const group = stdForm.querySelector('input[name="blood_group"]:checked')?.value || 'A+';
      const hospital = document.getElementById('stdHospitalName')?.value.trim();
      const units = document.getElementById('stdUnitsCount')?.value || '1';
      const date = document.getElementById('stdRequiredDate')?.value || 'As soon as possible';

      if (previewPatient) previewPatient.textContent = patient || 'Patient Name';
      if (previewGroup) previewGroup.textContent = group;
      if (previewHospital) previewHospital.textContent = hospital || 'Hospital / Clinic';
      if (previewUnits) previewUnits.textContent = `${units} Bag(s) Needed`;
      if (previewDate) previewDate.textContent = date ? `Needed: ${date}` : 'Standard Schedule';
    });

    stdForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const patient = document.getElementById('stdPatientName').value.trim();
      const group = stdForm.querySelector('input[name="blood_group"]:checked')?.value || 'A+';
      const hospital = document.getElementById('stdHospitalName').value.trim();
      const area = document.getElementById('stdAreaName').value.trim();
      const units = parseInt(document.getElementById('stdUnitsCount').value, 10) || 1;
      const phone = document.getElementById('stdContactPhone').value.trim();
      const reason = document.getElementById('stdCaseReason')?.value || 'Surgery / Medical';

      if (!patient || !hospital || !phone) {
        showToast('Please fill in required patient, hospital, and phone fields.', 'error');
        return;
      }

      const newReq = {
        id: Math.floor(Math.random() * 900) + 110,
        patient_name: patient,
        blood_group: group,
        hospital: hospital,
        area: area || 'Dhaka',
        units: units,
        needed_date: 'Scheduled',
        status: 'Active',
        is_emergency: 0,
        responses_count: 0,
        created_at: 'Just now'
      };

      try {
        // Submit to API
        await fetch('/api/v1/seeker/requests', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            patient_name: patient,
            blood_group: group,
            hospital_name: hospital,
            area: area,
            units: units,
            contact_phone: phone,
            reason: reason,
            is_emergency: false
          })
        }).catch(() => {});
      } catch (err) {}

      seekerRequests.unshift(newReq);
      renderSeekerRequestsTable('all');
      showToast('Standard Blood Request posted successfully! Notifying matching donors.');
      stdForm.reset();
      activateSection('section-seeker-dashboard');
    });
  }

  // =========================================================================
  // 3. CREATE EMERGENCY BLOOD REQUEST
  // =========================================================================
  const emgForm = document.getElementById('createEmergencyRequestForm');
  if (emgForm) {
    emgForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const patient = document.getElementById('emgPatientName').value.trim();
      const group = emgForm.querySelector('input[name="emg_blood_group"]:checked')?.value || 'O-';
      const hospital = document.getElementById('emgHospitalName').value.trim();
      const area = document.getElementById('emgAreaName').value.trim();
      const urgency = emgForm.querySelector('input[name="emg_urgency"]:checked')?.value || 'Code Red (Within 1 Hour)';
      const phone = document.getElementById('emgEmergencyPhone').value.trim();

      if (!patient || !hospital || !phone) {
        showToast('Critical fields missing. Please provide Patient, Hospital, and Emergency Phone.', 'error');
        return;
      }

      const emgReq = {
        id: Math.floor(Math.random() * 900) + 200,
        patient_name: patient,
        blood_group: group,
        hospital: hospital,
        area: area || 'Dhaka',
        units: 2,
        needed_date: urgency,
        status: 'Emergency',
        is_emergency: 1,
        responses_count: 1,
        created_at: 'Just now'
      };

      try {
        await fetch('/api/v1/seeker/requests/emergency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            patient_name: patient,
            blood_group: group,
            hospital_name: hospital,
            area: area,
            urgency_level: urgency,
            contact_phone: phone
          })
        }).catch(() => {});
      } catch (err) {}

      seekerRequests.unshift(emgReq);
      renderSeekerRequestsTable('emergency');

      // Emergency audio simulation feedback
      playEmergencySirenBeep();

      const modal = document.getElementById('sosBroadcastModal');
      if (modal) {
        document.getElementById('sosBroadcastGroup').textContent = group;
        document.getElementById('sosBroadcastHospital').textContent = hospital;
        modal.style.display = 'flex';
      } else {
        showToast('🚨 SOS EMERGENCY BROADCASTED TO 18 NEARBY DONORS!', 'urgent');
        activateSection('section-seeker-dashboard');
      }
      emgForm.reset();
    });
  }

  function playEmergencySirenBeep() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.3);
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {}
  }

  window.closeSosModal = function() {
    const modal = document.getElementById('sosBroadcastModal');
    if (modal) modal.style.display = 'none';
    activateSection('section-seeker-dashboard');
  };

  // =========================================================================
  // 4. NEARBY DONORS INTERACTIVE MAP VIEW
  // =========================================================================
  let mapInstance = null;
  let mapMarkers = [];

  function initSeekerMap() {
    const mapEl = document.getElementById('seekerDonorMap');
    if (!mapEl) return;

    // Check if Leaflet is loaded
    if (typeof L === 'undefined') {
      mapEl.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; padding: 24px;">
          <div style="font-size: 2.5rem; margin-bottom: 12px;">🗺️</div>
          <h3 style="font-size: 1.15rem; color: var(--text-primary); margin-bottom: 6px;">Dhaka Metro Live Radar Active</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); max-width: 480px;">
            Rendering verified donors within 5 km of Dhanmondi &amp; Shahbagh medical clusters.
          </p>
          <div style="display: flex; gap: 8px; margin-top: 14px;">
            <button class="btn btn-primary" onclick="window.activateSection('section-donor-directory')">Open Donor Directory</button>
          </div>
        </div>
      `;
      return;
    }

    if (mapInstance) {
      mapInstance.invalidateSize();
      return;
    }

    // Centered around Dhaka central medical zone
    const center = [23.7461, 90.3800];
    mapInstance = L.map('seekerDonorMap').setView(center, 13);
    window._seekerMapInstance = mapInstance;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors | SBDS Dhaka Radar'
    }).addTo(mapInstance);

    // Seeker/Hospital Center Marker
    const seekerIcon = L.divIcon({
      className: 'custom-center-pin',
      html: `<div style="background: #0284C7; color: #FFF; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1rem; border: 3px solid #FFF; box-shadow: 0 4px 12px rgba(2,132,199,0.5);">📍</div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 34]
    });

    L.marker(center, { icon: seekerIcon })
      .addTo(mapInstance)
      .bindPopup(`<strong>Your Request Location</strong><br>Square Hospital / Dhanmondi Zone`);

    renderMapMarkers(DONORS_DATA);
  }

  function renderMapMarkers(donors) {
    if (!mapInstance || typeof L === 'undefined') return;

    // Clear existing
    mapMarkers.forEach(m => mapInstance.removeLayer(m));
    mapMarkers = [];

    donors.forEach(donor => {
      const pinClass = donor.is_available ? 'custom-donor-pin available' : 'custom-donor-pin';
      const pinIcon = L.divIcon({
        className: 'custom-pin-wrapper',
        html: `<div class="${pinClass}">${donor.blood_group}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const popupHtml = `
        <div style="font-family: 'Inter', sans-serif; padding: 4px; min-width: 200px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <strong style="font-size: 0.95rem; color: #0F172A;">${donor.name}</strong>
            <span style="background: #FFE4E6; color: #BE123C; font-weight: 800; padding: 2px 6px; border-radius: 6px; font-size: 0.75rem;">${donor.blood_group}</span>
          </div>
          <div style="font-size: 0.8rem; color: #475569; margin-bottom: 4px;">
            📍 ${donor.area} • <strong>${donor.distance_km} km away</strong>
          </div>
          <div style="font-size: 0.76rem; color: #047857; margin-bottom: 10px;">
            ✓ ${donor.total_donations} Donations • ★ ${donor.rating} (${donor.reviews_count})
          </div>
          <div style="display: flex; gap: 6px;">
            <button onclick="window.viewDonorDetails('${donor.id}')" style="flex: 1; padding: 5px 8px; font-size: 0.75rem; background: #E11D48; color: #FFF; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
              View Profile
            </button>
            <a href="tel:${donor.phone}" onclick="window.logContactAction('${donor.name}', '${donor.phone}', '${donor.blood_group}', 'call')" style="padding: 5px 8px; font-size: 0.75rem; background: #10B981; color: #FFF; border: none; border-radius: 6px; text-decoration: none; font-weight: 600;">
              📞 Call
            </a>
          </div>
        </div>
      `;

      const marker = L.marker([donor.lat, donor.lng], { icon: pinIcon })
        .addTo(mapInstance)
        .bindPopup(popupHtml);

      mapMarkers.push(marker);
    });
  }

  // Map Filter bindings
  const mapBloodFilter = document.getElementById('mapBloodGroupFilter');
  const mapRadiusSlider = document.getElementById('mapRadiusSlider');
  const mapRadiusVal = document.getElementById('mapRadiusValue');

  if (mapBloodFilter) {
    mapBloodFilter.addEventListener('change', () => filterNearbyMap());
  }

  if (mapRadiusSlider) {
    mapRadiusSlider.addEventListener('input', () => {
      if (mapRadiusVal) mapRadiusVal.textContent = `${mapRadiusSlider.value} km`;
      filterNearbyMap();
    });
  }

  function filterNearbyMap() {
    const selectedGroup = mapBloodFilter?.value || '';
    const radius = parseFloat(mapRadiusSlider?.value || 15);

    const filtered = DONORS_DATA.filter(d => {
      const matchGroup = !selectedGroup || d.blood_group === selectedGroup;
      const matchRadius = d.distance_km <= radius;
      return matchGroup && matchRadius;
    });

    renderMapMarkers(filtered);
    renderMapNearbyList(filtered);
  }

  function renderMapNearbyList(donors) {
    const listEl = document.getElementById('mapNearbyDonorsList');
    if (!listEl) return;

    if (donors.length === 0) {
      listEl.innerHTML = `<div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">No donors found within this radar radius.</div>`;
      return;
    }

    listEl.innerHTML = donors.map(d => `
      <div style="padding: 12px 14px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; gap: 10px;">
        <div>
          <div style="font-weight: 700; font-size: 0.88rem; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
            ${d.name}
            <span style="background: #FFE4E6; color: #BE123C; padding: 1px 6px; border-radius: 4px; font-size: 0.72rem;">${d.blood_group}</span>
          </div>
          <div style="font-size: 0.76rem; color: var(--text-secondary); margin-top: 2px;">
            ${d.area} • <strong>${d.distance_km} km</strong> • Avg response ${d.response_time}
          </div>
        </div>
        <div style="display: flex; gap: 6px;">
          <button class="btn-card-action" onclick="window.viewDonorDetails('${d.id}')" style="padding: 5px 8px; font-size: 0.76rem;">Profile</button>
          <a class="btn-cta-call" href="tel:${d.phone}" onclick="window.logContactAction('${d.name}', '${d.phone}', '${d.blood_group}', 'call')" style="padding: 5px 8px; font-size: 0.76rem;">📞</a>
        </div>
      </div>
    `).join('');
  }

  // =========================================================================
  // 5. DONOR DIRECTORY SEARCH & PROXIMITY FILTERING
  // =========================================================================
  const dirSearchInput = document.getElementById('dirSearchInput');
  const dirBloodFilter = document.getElementById('dirBloodFilter');
  const dirRadiusSlider = document.getElementById('dirRadiusSlider');
  const dirRadiusValue = document.getElementById('dirRadiusValue');
  const dirAvailFilter = document.getElementById('dirAvailFilter');
  const dirSortSelect = document.getElementById('dirSortSelect');
  const dirResultsCount = document.getElementById('dirResultsCount');
  const dirGrid = document.getElementById('donorDirectoryGrid');

  function filterDonorDirectory() {
    if (!dirGrid) return;

    const query = dirSearchInput?.value.toLowerCase().trim() || '';
    const bloodGroup = dirBloodFilter?.value || '';
    const radius = parseFloat(dirRadiusSlider?.value || 30);
    const availOnly = dirAvailFilter?.checked;
    const sortBy = dirSortSelect?.value || 'proximity';

    let list = DONORS_DATA.filter(d => {
      const matchQuery = !query || d.name.toLowerCase().includes(query) || d.area.toLowerCase().includes(query) || d.district.toLowerCase().includes(query);
      const matchBlood = !bloodGroup || d.blood_group === bloodGroup;
      const matchRadius = d.distance_km <= radius;
      const matchAvail = !availOnly || d.is_available;
      return matchQuery && matchBlood && matchRadius && matchAvail;
    });

    // Sorting
    if (sortBy === 'proximity') {
      list.sort((a, b) => a.distance_km - b.distance_km);
    } else if (sortBy === 'rating') {
      list.sort((a, b) => b.rating - a.rating);
    } else if (sortBy === 'donations') {
      list.sort((a, b) => b.total_donations - a.total_donations);
    }

    if (dirResultsCount) {
      dirResultsCount.textContent = `Showing ${list.length} verified donors near Dhaka`;
    }

    if (list.length === 0) {
      dirGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border-color);">
          <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
          <h3 style="font-size: 1.1rem; color: var(--text-primary); margin-bottom: 4px;">No donors matched your filters</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary);">Try expanding the proximity slider radius or selecting All Blood Groups.</p>
        </div>
      `;
      return;
    }

    dirGrid.innerHTML = list.map(d => `
      <article class="donor-card">
        <div>
          <div class="donor-card-top">
            <div class="donor-card-avatar-combo">
              <div class="donor-card-avatar">${d.name.charAt(0)}</div>
              <div>
                <div class="donor-card-name">
                  <span>${d.name}</span>
                  <svg width="15" height="15" viewBox="0 0 20 20" fill="#0284C7" title="Verified Donor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                </div>
                <div class="donor-card-loc">
                  <span>📍 ${d.area}, ${d.district}</span>
                  <span>• <strong>${d.distance_km} km</strong></span>
                </div>
              </div>
            </div>
            <span class="donor-badge-group">${d.blood_group}</span>
          </div>

          <div class="donor-card-stats">
            <div>
              <div class="stat-item-val">${d.total_donations}</div>
              <div class="stat-item-lbl">Donations</div>
            </div>
            <div>
              <div class="stat-item-val">★ ${d.rating}</div>
              <div class="stat-item-lbl">${d.reviews_count} Reviews</div>
            </div>
            <div>
              <div class="stat-item-val" style="color: ${d.is_available ? '#047857' : '#B45309'}; font-size: 0.78rem;">
                ${d.is_available ? 'Available' : 'Resting'}
              </div>
              <div class="stat-item-lbl">${d.response_time}</div>
            </div>
          </div>

          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.4; margin-bottom: 16px;">
            ${d.bio}
          </p>
        </div>

        <div class="donor-card-actions">
          <button type="button" class="btn-card-action primary" onclick="window.viewDonorDetails('${d.id}')">
            View Credentials
          </button>
          <a href="tel:${d.phone}" class="btn-card-action" onclick="window.logContactAction('${d.name}', '${d.phone}', '${d.blood_group}', 'call')">
            📞 Call
          </a>
          <button type="button" class="btn-card-action" onclick="window.openChatWithDonor('${d.id}')">
            💬 Chat
          </button>
        </div>
      </article>
    `).join('');
  }

  if (dirSearchInput) dirSearchInput.addEventListener('input', filterDonorDirectory);
  if (dirBloodFilter) dirBloodFilter.addEventListener('change', filterDonorDirectory);
  if (dirRadiusSlider) {
    dirRadiusSlider.addEventListener('input', () => {
      if (dirRadiusValue) dirRadiusValue.textContent = `${dirRadiusSlider.value} km`;
      filterDonorDirectory();
    });
  }
  if (dirAvailFilter) dirAvailFilter.addEventListener('change', filterDonorDirectory);
  if (dirSortSelect) dirSortSelect.addEventListener('change', filterDonorDirectory);

  // =========================================================================
  // 6. DONOR PUBLIC PROFILE & CREDENTIALS VIEW
  // =========================================================================
  window.viewDonorDetails = function(donorId) {
    const donor = DONORS_DATA.find(d => d.id === donorId) || DONORS_DATA[0];
    activateSection('section-donor-credentials');

    const heroName = document.getElementById('credHeroName');
    const heroBlood = document.getElementById('credHeroBlood');
    const heroTier = document.getElementById('credHeroTier');
    const heroAvatar = document.getElementById('credHeroAvatar');
    const heroLoc = document.getElementById('credHeroLoc');
    const heroDonations = document.getElementById('credHeroDonations');
    const heroRating = document.getElementById('credHeroRating');
    const heroReliability = document.getElementById('credHeroReliability');
    const heroBio = document.getElementById('credHeroBio');
    const heroHemoglobin = document.getElementById('credHemoglobin');
    const heroWeightBp = document.getElementById('credWeightBp');
    const heroScreening = document.getElementById('credScreening');
    const heroCallBtn = document.getElementById('credCallBtn');
    const heroWaBtn = document.getElementById('credWaBtn');
    const heroChatBtn = document.getElementById('credChatBtn');
    const reviewsContainer = document.getElementById('credReviewsList');

    if (heroName) heroName.textContent = donor.name;
    if (heroBlood) heroBlood.textContent = donor.blood_group;
    if (heroTier) heroTier.textContent = donor.badge_tier;
    if (heroAvatar) heroAvatar.textContent = donor.name.charAt(0);
    if (heroLoc) heroLoc.textContent = `${donor.area}, ${donor.district} (${donor.distance_km} km away)`;
    if (heroDonations) heroDonations.textContent = `${donor.total_donations} Completed Donations`;
    if (heroRating) heroRating.textContent = `★ ${donor.rating} / 5.0 (${donor.reviews_count} reviews)`;
    if (heroReliability) heroReliability.textContent = donor.reliability;
    if (heroBio) heroBio.textContent = donor.bio;
    if (heroHemoglobin) heroHemoglobin.textContent = donor.hemoglobin;
    if (heroWeightBp) heroWeightBp.textContent = donor.weight_bp;
    if (heroScreening) heroScreening.textContent = donor.screening;

    if (heroCallBtn) {
      heroCallBtn.href = `tel:${donor.phone}`;
      heroCallBtn.onclick = () => window.logContactAction(donor.name, donor.phone, donor.blood_group, 'call');
    }
    if (heroWaBtn) {
      const waText = encodeURIComponent(`Hello ${donor.name}, urgent blood required: ${donor.blood_group} at hospital. Can you help save a life?`);
      heroWaBtn.href = `https://wa.me/${donor.phone.replace(/[^0-9]/g, '')}?text=${waText}`;
      heroWaBtn.onclick = () => window.logContactAction(donor.name, donor.phone, donor.blood_group, 'whatsapp');
    }
    if (heroChatBtn) {
      heroChatBtn.onclick = () => window.openChatWithDonor(donor.id);
    }

    if (reviewsContainer) {
      reviewsContainer.innerHTML = donor.reviews.map(r => `
        <div style="padding: 14px 16px; border-radius: 10px; background: var(--bg-card); border: 1px solid var(--border-color); margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="font-size: 0.9rem; color: var(--text-primary);">${r.author}</strong>
            <span style="font-size: 0.82rem; color: #F59E0B; font-weight: 700;">★ ${r.rating}.0</span>
          </div>
          <p style="font-size: 0.84rem; color: var(--text-secondary); margin: 0 0 6px 0; line-height: 1.45;">"${r.text}"</p>
          <span style="font-size: 0.74rem; color: var(--text-muted);">${r.date}</span>
        </div>
      `).join('');
    }

    showToast(`Loaded verified profile credentials for ${donor.name}`);
  };

  // Donor selector dropdown inside Credentials view
  const credDonorSelect = document.getElementById('credDonorSelect');
  if (credDonorSelect) {
    credDonorSelect.addEventListener('change', (e) => {
      window.viewDonorDetails(e.target.value);
    });
  }

  // =========================================================================
  // 7. DIRECT CONTACT ACTION (CALL / WHATSAPP CTA)
  // =========================================================================
  let contactLogs = [
    {
      donor_name: "Ayesha Rahman",
      donor_phone: "+880 1712-345678",
      blood_group: "A+",
      type: "Call Dialed",
      time: "20 mins ago",
      outcome: "Donor answered • Confirmed arriving in 35 mins"
    },
    {
      donor_name: "Tanvir Ahmed",
      donor_phone: "+880 1711-223344",
      blood_group: "O+",
      type: "WhatsApp Sent",
      time: "1 hour ago",
      outcome: "Message delivered • Awaiting acknowledgment"
    }
  ];

  window.logContactAction = function(name, phone, bloodGroup, type) {
    const newLog = {
      donor_name: name,
      donor_phone: phone,
      blood_group: bloodGroup,
      type: type === 'call' ? 'Call Dialed' : 'WhatsApp Sent',
      time: 'Just now',
      outcome: 'Contact dispatched via 1-click CTA'
    };
    contactLogs.unshift(newLog);
    renderContactLogsTable();
    showToast(`Contact action logged: Dispatched ${type.toUpperCase()} to ${name}`);

    // Send to backend API
    fetch('/api/v1/seeker/contact/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        donor_name: name,
        donor_phone: phone,
        blood_group: bloodGroup,
        contact_type: type
      })
    }).catch(() => {});
  };

  function renderContactLogsTable() {
    const tableBody = document.getElementById('contactLogsTableBody');
    if (!tableBody) return;

    tableBody.innerHTML = contactLogs.map(log => `
      <tr>
        <td style="font-weight: 700; color: var(--text-primary);">${log.donor_name}</td>
        <td>
          <span style="background: #FFE4E6; color: #BE123C; font-weight: 800; padding: 2px 6px; border-radius: 4px; font-size: 0.78rem;">
            ${log.blood_group}
          </span>
        </td>
        <td>${log.donor_phone}</td>
        <td>
          <span class="nav-pill-badge ${log.type.includes('Call') ? 'pill-green' : 'pill-blue'}">
            ${log.type}
          </span>
        </td>
        <td style="font-size: 0.82rem; color: var(--text-secondary);">${log.outcome}</td>
        <td style="font-size: 0.76rem; color: var(--text-muted);">${log.time}</td>
      </tr>
    `).join('');
  }

  window.copyPhoneToClipboard = function(phone) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(phone);
      showToast(`Copied ${phone} to clipboard!`);
    } else {
      showToast(`Phone number: ${phone}`);
    }
  };

  // Speed Dial list generator
  function renderSpeedDialList() {
    const speedGrid = document.getElementById('speedDialGrid');
    if (!speedGrid) return;

    speedGrid.innerHTML = DONORS_DATA.slice(0, 4).map(d => {
      const waMsg = encodeURIComponent(`Emergency: Urgent ${d.blood_group} blood requested at hospital. Can you donate?`);
      return `
        <div class="speed-dial-card">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="donor-card-avatar" style="width: 44px; height: 44px; font-size: 1rem;">${d.name.charAt(0)}</div>
            <div>
              <div style="font-weight: 700; font-size: 0.92rem; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                ${d.name}
                <span style="background: #FFE4E6; color: #BE123C; padding: 1px 5px; border-radius: 4px; font-size: 0.72rem;">${d.blood_group}</span>
              </div>
              <div style="font-size: 0.76rem; color: var(--text-secondary);">${d.formatted_phone} • ${d.area}</div>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <a href="tel:${d.phone}" class="btn-cta-call" onclick="window.logContactAction('${d.name}', '${d.phone}', '${d.blood_group}', 'call')">
              📞 Call
            </a>
            <a href="https://wa.me/${d.phone.replace(/[^0-9]/g, '')}?text=${waMsg}" target="_blank" class="btn-cta-wa" onclick="window.logContactAction('${d.name}', '${d.phone}', '${d.blood_group}', 'whatsapp')">
              💬 WhatsApp
            </a>
          </div>
        </div>
      `;
    }).join('');
  }

  // =========================================================================
  // 8. REAL-TIME IN-APP 1-ON-1 CHAT
  // =========================================================================
  const CHAT_THREADS = [
    {
      id: "thread-ayesha",
      name: "Ayesha Rahman",
      donor_id: "dn-001",
      blood_group: "A+",
      phone: "+880 1712-345678",
      last_msg: "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.",
      time: "10:14 AM",
      unread: 1,
      messages: [
        { id: 1, sender: "you", text: "Assalamu Alaikum Ayesha apu, we urgently need 1 bag A+ blood at Square Hospital 3rd Floor.", time: "10:05 AM" },
        { id: 2, sender: "donor", text: "Wa Alaikum Assalam Nabil bhai! I just saw the alert. I am eligible and nearby.", time: "10:08 AM" },
        { id: 3, sender: "you", text: "Alhamdulillah! Can you please reach as soon as possible? Requisition is ready.", time: "10:10 AM" },
        { id: 4, sender: "donor", text: "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.", time: "10:14 AM" }
      ]
    },
    {
      id: "thread-tanvir",
      name: "Tanvir Ahmed",
      donor_id: "dn-002",
      blood_group: "O+",
      phone: "+880 1711-223344",
      last_msg: "Please keep the blood test requisition slip ready at counter.",
      time: "9:45 AM",
      unread: 0,
      messages: [
        { id: 1, sender: "you", text: "Hello Tanvir brother, are you available for O+ donation today?", time: "9:30 AM" },
        { id: 2, sender: "donor", text: "Yes Nabil brother, I am free after 11 AM.", time: "9:35 AM" },
        { id: 3, sender: "donor", text: "Please keep the blood test requisition slip ready at counter.", time: "9:45 AM" }
      ]
    },
    {
      id: "thread-desk",
      name: "Square Blood Desk Coordinator",
      donor_id: "coord-01",
      blood_group: "Hospital",
      phone: "+880 1700-000001",
      last_msg: "Donor verification room 204 is open for your recipient.",
      time: "Yesterday",
      unread: 0,
      messages: [
        { id: 1, sender: "donor", text: "Donor verification room 204 is open for your recipient.", time: "Yesterday" }
      ]
    }
  ];

  let currentThreadId = "thread-ayesha";

  function escapeHtml(text) {
    if (!text) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  function playChatNotificationSound() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.16);
    } catch (e) {}
  }

  function updateSeekerSidebarChatBadge() {
    const badge = document.getElementById('sidebarSeekerChatBadge');
    if (!badge) return;
    const totalUnread = CHAT_THREADS.reduce((sum, t) => sum + (t.unread || 0), 0);
    badge.textContent = totalUnread;
    badge.style.display = totalUnread > 0 ? 'inline-flex' : 'none';
  }

  function renderChatThreads() {
    const listEl = document.getElementById('chatThreadsScrollList');
    if (!listEl) return;

    listEl.innerHTML = CHAT_THREADS.map(t => {
      const initial = (t.name || 'D').charAt(0);
      const lastMsgText = t.last_msg || t.last_message || 'Chat initiated';
      const timeText = t.time || t.last_time || '';
      const unreadCount = t.unread !== undefined ? t.unread : (t.unread_count || 0);
      return `
        <div class="chat-thread-item ${t.id === currentThreadId ? 'active' : ''}" onclick="window.selectChatThread('${t.id}')">
          <div class="chat-thread-avatar">
            ${escapeHtml(initial)}
            <div class="chat-online-indicator"></div>
          </div>
          <div class="thread-details-col">
            <div class="thread-row-top">
              <span class="thread-name">${escapeHtml(t.name)}</span>
              <span class="thread-time">${escapeHtml(timeText)}</span>
            </div>
            <div class="thread-snippet">${escapeHtml(lastMsgText)}</div>
          </div>
          ${unreadCount > 0 ? `<span class="nav-badge-count">${unreadCount}</span>` : ''}
        </div>
      `;
    }).join('');
    updateSeekerSidebarChatBadge();
  }

  function renderActiveThreadMessages() {
    const thread = CHAT_THREADS.find(t => t.id === currentThreadId);
    if (!thread) return;

    const chatHeaderName = document.getElementById('activeChatDonorName');
    const chatHeaderInfo = document.getElementById('activeChatDonorInfo');
    const chatHeaderCall = document.getElementById('activeChatCallBtn');
    const msgsContainer = document.getElementById('chatMessagesContainer');

    if (chatHeaderName) chatHeaderName.textContent = thread.name;
    if (chatHeaderInfo) chatHeaderInfo.textContent = `${thread.blood_group || 'Verified'} Donor • ${thread.phone || 'Available'}`;
    if (chatHeaderCall && thread.phone) chatHeaderCall.href = `tel:${thread.phone}`;

    if (msgsContainer) {
      const messagesList = thread.messages || [];
      msgsContainer.innerHTML = messagesList.map(msg => `
        <div class="chat-msg-row ${msg.sender === 'you' ? 'outgoing' : 'incoming'}">
          <div class="chat-msg-bubble">${escapeHtml(msg.text)}</div>
          <div class="chat-msg-meta">
            <span>${escapeHtml(msg.time || '')}</span>
            ${msg.sender === 'you' ? '<span>✓✓</span>' : ''}
          </div>
        </div>
      `).join('');

      let typingInd = document.getElementById('seekerTypingIndicator');
      if (!typingInd) {
        typingInd = document.createElement('div');
        typingInd.id = 'seekerTypingIndicator';
        typingInd.className = 'typing-indicator';
        typingInd.style.display = 'none';
        typingInd.innerHTML = `
          <span class="typing-text" style="color:var(--text-secondary);">Donor is typing</span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        `;
      }
      msgsContainer.appendChild(typingInd);
      msgsContainer.scrollTop = msgsContainer.scrollHeight;
    }
  }

  window.selectChatThread = function(threadId) {
    currentThreadId = threadId;
    const thread = CHAT_THREADS.find(t => t.id === threadId);
    if (thread) thread.unread = 0;
    renderChatThreads();
    renderActiveThreadMessages();
    updateSeekerSidebarChatBadge();

    // Mark as read on backend
    fetch(`/api/v1/seeker/chat/${threadId}/read`, { method: 'POST' }).catch(() => {});
    if (seekerWs && seekerWs.readyState === WebSocket.OPEN) {
      seekerWs.send(JSON.stringify({ action: 'read', thread_id: threadId }));
    }
  };

  window.openChatWithDonor = function(donorId) {
    activateSection('section-seeker-chat');
    const existing = CHAT_THREADS.find(t => t.donor_id === donorId);
    if (existing) {
      window.selectChatThread(existing.id);
    } else {
      const donor = DONORS_DATA.find(d => d.id === donorId);
      if (donor) {
        const newThread = {
          id: `thread-${donor.id}`,
          name: donor.name,
          donor_id: donor.id,
          blood_group: donor.blood_group,
          phone: donor.formatted_phone,
          last_msg: "Chat initiated",
          time: "Just now",
          unread: 0,
          messages: [
            { id: 1, sender: "you", text: `Hello ${donor.name}, I found your profile on SBDS. Needed ${donor.blood_group} blood.`, time: "Just now" }
          ]
        };
        CHAT_THREADS.unshift(newThread);
        renderChatThreads();
        window.selectChatThread(newThread.id);
      }
    }
  };

  // =========================================================================
  // SEEKER REAL-TIME CHAT WEBSOCKET & SYNC (SBDS-89)
  // =========================================================================
  let seekerWs = null;
  let seekerWsReconnectTimer = null;
  let seekerWsPingInterval = null;
  let seekerTypingTimeout = null;

  function initSeekerChatWebSocket() {
    if (seekerWs && (seekerWs.readyState === WebSocket.OPEN || seekerWs.readyState === WebSocket.CONNECTING)) {
      return;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/seeker`;

    try {
      seekerWs = new WebSocket(wsUrl);

      seekerWs.onopen = () => {
        clearInterval(seekerWsPingInterval);
        seekerWsPingInterval = setInterval(() => {
          if (seekerWs && seekerWs.readyState === WebSocket.OPEN) {
            seekerWs.send(JSON.stringify({ action: 'ping' }));
          }
        }, 25000);

        const statusBadge = document.getElementById('seekerWsStatusBadge');
        if (statusBadge) {
          statusBadge.innerHTML = '<span class="pulse-dot" style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#10B981; margin-right:4px;"></span> Real-Time Connected';
        }
      };

      seekerWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') return;

          if (data.type === 'typing') {
            if (data.thread_id === currentThreadId) {
              const typingInd = document.getElementById('seekerTypingIndicator');
              if (typingInd) {
                const typingText = typingInd.querySelector('.typing-text');
                if (typingText) typingText.textContent = `${data.sender_name || 'Donor'} is typing`;
                if (data.typing) {
                  typingInd.style.display = 'inline-flex';
                  const msgsContainer = document.getElementById('chatMessagesContainer');
                  if (msgsContainer) msgsContainer.scrollTop = msgsContainer.scrollHeight;
                  clearTimeout(seekerTypingTimeout);
                  seekerTypingTimeout = setTimeout(() => {
                    typingInd.style.display = 'none';
                  }, 3500);
                } else {
                  typingInd.style.display = 'none';
                }
              }
            }
            return;
          }

          if (data.type === 'chat_message') {
            const threadId = data.thread_id || 'thread-ayesha';
            let thread = CHAT_THREADS.find(t => t.id === threadId || (threadId === 'thread-ayesha' && t.donor_id === 'dn-001'));
            if (!thread) {
              thread = {
                id: threadId,
                name: data.sender_name || 'Ayesha Rahman',
                donor_id: 'dn-001',
                blood_group: 'A+',
                phone: '+880 1712-345678',
                last_msg: data.text,
                time: data.time || 'Just now',
                unread: 0,
                messages: []
              };
              CHAT_THREADS.unshift(thread);
            }

            if (!thread.messages) thread.messages = [];
            const msgId = data.message?.id || ('msg-s-' + Date.now());
            const alreadyExists = thread.messages.some(m => m.id === msgId || (m.text === data.text && m.sender !== 'you'));
            if (!alreadyExists) {
              thread.messages.push({
                id: msgId,
                sender: 'donor',
                text: data.text,
                time: data.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              });
            }
            thread.last_msg = data.text;
            thread.time = data.time || 'Just now';

            const isChatActive = document.getElementById('section-seeker-chat')?.classList.contains('active-section');
            if (currentThreadId === thread.id && isChatActive) {
              const typingInd = document.getElementById('seekerTypingIndicator');
              if (typingInd) typingInd.style.display = 'none';

              const msgsContainer = document.getElementById('chatMessagesContainer');
              if (msgsContainer) {
                const msgRow = document.createElement('div');
                msgRow.className = 'chat-msg-row incoming';
                msgRow.innerHTML = `
                  <div class="chat-msg-bubble">${escapeHtml(data.text)}</div>
                  <div class="chat-msg-meta">
                    <span>${escapeHtml(data.time || 'Just now')}</span>
                  </div>
                `;
                if (typingInd) {
                  msgsContainer.insertBefore(msgRow, typingInd);
                } else {
                  msgsContainer.appendChild(msgRow);
                }
                msgsContainer.scrollTop = msgsContainer.scrollHeight;
              }
              // Mark read on server
              fetch(`/api/v1/seeker/chat/${thread.id}/read`, { method: 'POST' }).catch(() => {});
            } else {
              thread.unread = (thread.unread || 0) + 1;
              playChatNotificationSound();
              showToast(`💬 New message from ${data.sender_name || thread.name}: "${data.text.substring(0, 45)}"`);
            }

            renderChatThreads();
            updateSeekerSidebarChatBadge();
          }
        } catch (err) {}
      };

      seekerWs.onclose = () => {
        clearInterval(seekerWsPingInterval);
        clearTimeout(seekerWsReconnectTimer);
        seekerWsReconnectTimer = setTimeout(() => {
          initSeekerChatWebSocket();
        }, 3000);
      };

      seekerWs.onerror = () => {
        seekerWs?.close();
      };
    } catch (e) {
      clearTimeout(seekerWsReconnectTimer);
      seekerWsReconnectTimer = setTimeout(() => {
        initSeekerChatWebSocket();
      }, 3000);
    }
  }

  // Send Chat message
  const chatForm = document.getElementById('chatMessageForm');
  const chatInput = document.getElementById('chatMessageInput');

  if (chatForm && chatInput) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;

      const thread = CHAT_THREADS.find(t => t.id === currentThreadId);
      if (!thread) return;

      const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const newMsg = {
        id: 'msg-s-' + Date.now(),
        sender: "you",
        text: text,
        time: nowTime
      };

      if (!thread.messages) thread.messages = [];
      thread.messages.push(newMsg);
      thread.last_msg = text;
      thread.time = nowTime;
      chatInput.value = '';
      renderActiveThreadMessages();
      renderChatThreads();

      // Emit stop typing
      if (seekerWs && seekerWs.readyState === WebSocket.OPEN) {
        seekerWs.send(JSON.stringify({ action: 'typing', thread_id: currentThreadId, typing: false }));
      }

      // Send to backend API
      fetch(`/api/v1/seeker/chat/${currentThreadId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      })
        .then(res => res.json())
        .then(data => {
          // Only simulate reply if not communicating with live donor (e.g. mock hospital desk)
          if (currentThreadId !== 'thread-ayesha' && currentThreadId !== 'thread-dn-001') {
            setTimeout(() => {
              const replyText = data?.reply?.text || "Desk Coordinator: Received! We will update shortly.";
              const replyTime = data?.reply?.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              thread.messages.push({
                id: 'reply-' + Date.now(),
                sender: "donor",
                text: replyText,
                time: replyTime
              });
              thread.last_msg = replyText;
              renderActiveThreadMessages();
              renderChatThreads();
              showToast(`New reply from ${thread.name}`);
            }, 1200);
          }
        })
        .catch(() => {});
    });

    // Typing emitter on seeker input
    let lastSeekerTypingSent = 0;
    chatInput.addEventListener('input', () => {
      const now = Date.now();
      if (now - lastSeekerTypingSent > 1800 && seekerWs && seekerWs.readyState === WebSocket.OPEN) {
        lastSeekerTypingSent = now;
        seekerWs.send(JSON.stringify({
          action: 'typing',
          thread_id: currentThreadId,
          typing: true
        }));
      }
    });
  }

  // Quick Chat reply chips
  document.querySelectorAll('.quick-chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (chatInput) {
        chatInput.value = btn.textContent.replace(/"/g, '');
        chatInput.focus();
      }
    });
  });

  // Fetch initial threads from API if available
  fetch('/api/v1/seeker/chat/threads')
    .then(r => r.json())
    .then(data => {
      if (data && data.threads && Array.isArray(data.threads)) {
        data.threads.forEach(remote => {
          const local = CHAT_THREADS.find(l => l.id === remote.id);
          if (local) {
            if (remote.last_message) local.last_msg = remote.last_message;
            if (remote.last_time) local.time = remote.last_time;
            if (remote.unread_count !== undefined) local.unread = remote.unread_count;
          } else {
            CHAT_THREADS.push({
              id: remote.id,
              name: remote.name,
              donor_id: remote.donor_id || '',
              blood_group: remote.blood_group || '',
              phone: remote.phone || '',
              last_msg: remote.last_message || 'Chat initiated',
              time: remote.last_time || '',
              unread: remote.unread_count || 0,
              messages: []
            });
          }
        });
        renderChatThreads();
        updateSeekerSidebarChatBadge();
      }
    })
    .catch(() => {});

  // Initialize Seeker WebSocket
  initSeekerChatWebSocket();

  // =========================================================================
  // 9. SEEKER PORTAL SETTINGS & PREFERENCES
  // =========================================================================
  const settingsForm = document.getElementById('seekerSettingsForm');
  if (settingsForm) {
    settingsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      showToast('Settings & preferences saved successfully!');

      // Save to API
      const settingsPayload = {
        full_name: document.getElementById('setSeekerName')?.value || 'Nabil Hasan',
        phone: document.getElementById('setSeekerPhone')?.value || '+8801723456789',
        default_hospital: document.getElementById('setDefaultHospital')?.value || 'Square Hospital',
        sms_alerts: document.getElementById('toggleSmsAlerts')?.checked ?? true,
        push_alerts: document.getElementById('togglePushAlerts')?.checked ?? true,
        audio_siren: document.getElementById('toggleAudioSiren')?.checked ?? true,
        default_radius: document.getElementById('setDefaultRadius')?.value || '10'
      };

      fetch('/api/v1/seeker/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsPayload)
      }).catch(() => {});
    });
  }

  // Theme toggle button integration
  const themeToggle = document.getElementById('seekerThemeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('change', () => {
      const isDark = themeToggle.checked;
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
      localStorage.setItem('sbds-theme', isDark ? 'dark' : 'light');
      showToast(`Switched to ${isDark ? 'Dark' : 'Light'} Mode`);
    });

    if (localStorage.getItem('sbds-theme') === 'dark') {
      themeToggle.checked = true;
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  // =========================================================================
  // INITIALIZATION ON PAGE LOAD
  // =========================================================================
  renderSeekerRequestsTable('all');
  filterDonorDirectory();
  renderSpeedDialList();
  renderContactLogsTable();
  renderChatThreads();
  renderActiveThreadMessages();

  // Handle URL hash or default to personal dashboard
  if (window.location.hash) {
    activateSection(window.location.hash);
  } else {
    activateSection('section-seeker-dashboard');
  }

  // Initialize Map when user visits map section or DOM is ready
  setTimeout(initSeekerMap, 500);
});
