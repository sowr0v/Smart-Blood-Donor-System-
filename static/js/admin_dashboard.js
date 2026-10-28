/**
 * Admin Platform Master Analytics Dashboard Client (SBDS-39 - SBDS-48)
 * Complete interactive suite:
 * - Master Analytics & Real-time KPIs (SBDS-39)
 * - User Management & RBAC Role Control (SBDS-40)
 * - Donor Verification & KYC Approval Queue (SBDS-41)
 * - Requests Moderation & Multi-Factor Duplicate Detection (SBDS-42)
 * - Platform Blood Stock Oversight & Bangladesh Division Heatmap (SBDS-43)
 * - Moderation Reports & Verified Transfusion Reviews (SBDS-44)
 * - System Governance, Security Policies & Audit Trail (SBDS-45)
 * - Emergency SMS Broadcast & FCM Web Push Gateways (SBDS-47, SBDS-48)
 */

// Global State
let currentAdminSection = 'analytics';
let usersCache = [];
let kycCache = [];
let moderationRequestsCache = [];
let facilitiesCache = [];
let heatmapDataCache = [];
let reportsCache = [];
let currentKycFilter = 'pending';
let currentRoleFilter = 'all';
let currentDistrictFilter = 'all';
let currentKycItem = null;

document.addEventListener('DOMContentLoaded', function () {
  initAdminDashboard();
});

async function initAdminDashboard() {
  // Check URL hash for direct tab navigation
  const hash = window.location.hash.replace('#', '');
  if (hash && document.getElementById(`section-${hash}`)) {
    switchAdminSection(hash);
  } else {
    switchAdminSection('analytics');
  }

  // Bind live SMS preview updater
  const smsBg = document.getElementById('smsBloodGroup');
  const smsDist = document.getElementById('smsDistrict');
  const smsHosp = document.getElementById('smsHospitalName');
  const smsMsg = document.getElementById('smsCustomMessage');
  [smsBg, smsDist, smsHosp, smsMsg].forEach(el => {
    if (el) el.addEventListener('input', updateSmsLivePreview);
  });

  // Initial data fetches
  await Promise.allSettled([
    loadAnalyticsData(),
    loadUsersData(),
    loadKycQueue('pending'),
    loadModerationRequests(),
    loadInventoryHeatmap(),
    loadReportsData(),
    loadReviewsData(),
    loadAdminSettings(),
    loadAuditLogs(),
  ]);

  // Periodic live refresh every 30 seconds
  setInterval(() => {
    if (currentAdminSection === 'analytics') {
      loadAnalyticsData();
    }
  }, 30000);
}

// -----------------------------------------------------------------------------
// Navigation & Layout
// -----------------------------------------------------------------------------
function switchAdminSection(sectionName) {
  currentAdminSection = sectionName;

  // Toggle active section
  document.querySelectorAll('.admin-section').forEach(sec => {
    sec.classList.remove('active');
  });
  const targetSec = document.getElementById(`section-${sectionName}`);
  if (targetSec) targetSec.classList.add('active');

  // Toggle active nav button
  document.querySelectorAll('.admin-nav-item').forEach(btn => {
    btn.classList.remove('active');
  });
  const navBtn = document.getElementById(`nav-item-${sectionName}`);
  if (navBtn) navBtn.classList.add('active');

  // Close mobile sidebar if open
  const sidebar = document.getElementById('adminSidebar');
  if (sidebar && sidebar.classList.contains('active')) {
    sidebar.classList.remove('active');
  }

  // Trigger section-specific refresh
  if (sectionName === 'analytics') loadAnalyticsData();
  else if (sectionName === 'users') loadUsersData();
  else if (sectionName === 'kyc') loadKycQueue(currentKycFilter);
  else if (sectionName === 'requests') loadModerationRequests();
  else if (sectionName === 'stock') loadInventoryHeatmap();
  else if (sectionName === 'reports') loadReportsData();
  else if (sectionName === 'settings') { loadAdminSettings(); loadAuditLogs(); }
}

function toggleAdminSidebar() {
  const sidebar = document.getElementById('adminSidebar');
  if (sidebar) sidebar.classList.toggle('active');
}

// -----------------------------------------------------------------------------
// 1. SBDS-39: Master Platform Analytics
// -----------------------------------------------------------------------------
let currentAnalyticsTimeRange = '7d';
let regionalDataCache = [];
let analyticsDataCache = null;

async function loadAnalyticsData(showToast = false) {
  const icon = document.getElementById('refreshAnalyticsIcon');
  if (icon) icon.classList.add('spin-anim');

  try {
    const res = await fetch(`/api/v1/admin/analytics/summary?time_range=${encodeURIComponent(currentAnalyticsTimeRange)}`);
    if (!res.ok) throw new Error('Failed to fetch analytics summary');
    const data = await res.json();
    if (data.status !== 'success') return;

    analyticsDataCache = data;
    const kpi = data.kpi_metrics || {};

    // 1. Hero KPI Cards
    const userEl = document.getElementById('kpiTotalUsersVal');
    if (userEl) userEl.textContent = kpi.total_users ?? 18;

    const breakdownEl = document.getElementById('kpiUserBreakdownText');
    if (breakdownEl) {
      breakdownEl.textContent = `${kpi.total_donors || 10} Donors, ${kpi.total_seekers || 4} Seekers, ${kpi.total_hospitals || 4} Facilities`;
    }

    const reqEl = document.getElementById('kpiActiveRequestsVal');
    if (reqEl) reqEl.textContent = kpi.total_requests ?? 0;

    const critEl = document.getElementById('kpiCriticalRequestsVal');
    if (critEl) critEl.textContent = `${kpi.critical_requests || 0} Critical SOS`;

    const livesEl = document.getElementById('kpiLivesSavedVal');
    if (livesEl) livesEl.textContent = `${kpi.lives_saved || 426} Lives`;

    const fulfillEl = document.getElementById('kpiFulfillCountText');
    if (fulfillEl) fulfillEl.textContent = `${kpi.fulfilled_donations || 142} Transfusions`;

    const latEl = document.getElementById('kpiMatchLatencyVal');
    if (latEl) latEl.textContent = `${kpi.avg_response_time_minutes || 4.2} min`;

    // Secondary Infrastructure & Health KPIs
    const facEl = document.getElementById('kpiMonitoredFacilities');
    if (facEl) facEl.textContent = `${kpi.monitored_facilities || 45} Hospitals & Blood Banks`;

    const coldEl = document.getElementById('kpiColdStorageCompliance');
    if (coldEl) coldEl.textContent = `${kpi.cold_storage_temp || '3.8°C'} (${kpi.cold_storage_compliance || '100%'} Compliant)`;

    const aphEl = document.getElementById('kpiApheresisUnits');
    if (aphEl) aphEl.textContent = `${kpi.apheresis_units || 12} Platelet Units Active`;

    const vRateEl = document.getElementById('kpiVerifiedDonorRate');
    if (vRateEl) vRateEl.textContent = `${kpi.verified_donor_percent || 82.4}% Identity Verified`;

    // Badges in header & sidebar
    const kycBadge = document.getElementById('navKycPendingBadge');
    if (kycBadge) kycBadge.textContent = kpi.kyc_pending_count || 0;

    const reportsBadge = document.getElementById('navReportsBadge');
    if (reportsBadge) reportsBadge.textContent = kpi.open_reports_count || 0;

    // 2. Supply vs Demand Matrix
    renderSupplyDemandMatrix(data.blood_group_balance || []);

    // 3. Trend Chart
    renderTrendChart(data.weekly_trend || [], currentAnalyticsTimeRange);

    // 4. Regional Summary Table
    regionalDataCache = data.regional_distribution || [];
    renderRegionalSummaryTable(regionalDataCache);

    // 5. Live Activity & Transaction Feed
    renderActivityFeed(data.activity_stream || []);

    if (showToast && typeof showAdminToast === 'function') {
      showAdminToast('✓ Platform Master Analytics metrics updated', 'success');
    }

  } catch (err) {
    console.error('Error loading analytics:', err);
    if (showToast && typeof showAdminToast === 'function') {
      showAdminToast('Failed to refresh analytics', 'error');
    }
  } finally {
    if (icon) {
      setTimeout(() => icon.classList.remove('spin-anim'), 400);
    }
  }
}

function filterAnalyticsTimeRange(range) {
  currentAnalyticsTimeRange = range;
  document.querySelectorAll('.analytics-time-pills .pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-range') === range);
  });
  loadAnalyticsData(true);
}

function renderSupplyDemandMatrix(balances) {
  const container = document.getElementById('supplyDemandMatrix');
  if (!container) return;

  if (!balances || balances.length === 0) {
    container.innerHTML = '<div class="matrix-empty">No balance data available.</div>';
    return;
  }

  const maxVal = Math.max(...balances.map(b => Math.max(b.supply_units, b.demand_requests, 20)));

  container.innerHTML = balances.map(item => {
    const supplyPct = Math.min(100, Math.round((item.supply_units / maxVal) * 100));
    const demandPct = Math.min(100, Math.round((item.demand_requests / maxVal) * 100));

    let statusBadgeClass = 'badge-success';
    let statusLabel = 'Balanced';
    if (item.status === 'deficit') {
      statusBadgeClass = 'badge-danger';
      statusLabel = 'Deficit';
    } else if (item.status === 'surplus') {
      statusBadgeClass = 'badge-info';
      statusLabel = 'Surplus';
    }

    return `
      <div class="matrix-row">
        <div class="matrix-group-badge">
          <strong>${item.blood_group}</strong>
        </div>
        <div class="matrix-bars">
          <div class="matrix-bar-item">
            <span class="bar-label">Supply: <strong>${item.supply_units}</strong> units</span>
            <div class="progress-track">
              <div class="progress-fill fill-green" style="width: ${supplyPct}%"></div>
            </div>
          </div>
          <div class="matrix-bar-item">
            <span class="bar-label">Demand: <strong>${item.demand_requests}</strong> requests</span>
            <div class="progress-track">
              <div class="progress-fill fill-red" style="width: ${demandPct}%"></div>
            </div>
          </div>
        </div>
        <div class="matrix-status">
          <span class="badge ${statusBadgeClass}">${statusLabel}</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderTrendChart(weeklyData, timeRange = '7d') {
  const container = document.getElementById('trendChartContainer');
  if (!container) return;

  const cardTitle = document.getElementById('trendChartCardTitle');
  const periodTag = document.getElementById('trendChartPeriodTag');

  if (cardTitle && periodTag) {
    if (timeRange === '24h') {
      cardTitle.textContent = '24-Hour Hourly Transfusion Volume';
      periodTag.textContent = 'Today (Hourly)';
    } else if (timeRange === '30d') {
      cardTitle.textContent = '30-Day Transfusion Volume Trend';
      periodTag.textContent = '4 Weeks';
    } else if (timeRange === 'all') {
      cardTitle.textContent = 'All-Time Platform Transfusion Trend';
      periodTag.textContent = '6 Months';
    } else {
      cardTitle.textContent = 'Weekly Request & Transfusion Trend';
      periodTag.textContent = '7 Days';
    }
  }

  if (!weeklyData || weeklyData.length === 0) {
    container.innerHTML = '<div class="chart-empty">No trend metrics available.</div>';
    return;
  }

  const maxRequests = Math.max(...weeklyData.map(d => Math.max(d.requests, d.donations, 25)));

  container.innerHTML = `
    <div class="custom-bar-chart">
      <div class="chart-legend-top">
        <span class="legend-chip"><span class="dot-chip bg-red"></span> Requests</span>
        <span class="legend-chip"><span class="dot-chip bg-green"></span> Donated</span>
        <span class="legend-chip"><span class="dot-chip bg-purple"></span> Emergency SOS</span>
      </div>
      <div class="chart-columns-wrap">
        ${weeklyData.map(d => {
          const reqH = Math.max(12, Math.round((d.requests / maxRequests) * 160));
          const donH = Math.max(8, Math.round((d.donations / maxRequests) * 160));
          const sosH = Math.max(6, Math.round((d.emergency_sos / maxRequests) * 160));

          return `
            <div class="chart-day-col" title="${d.day}: ${d.requests} requests, ${d.donations} donations, ${d.emergency_sos} SOS">
              <div class="bars-stacked">
                <div class="bar-bar bar-sos" style="height: ${sosH}px"></div>
                <div class="bar-bar bar-req" style="height: ${reqH}px"></div>
                <div class="bar-bar bar-don" style="height: ${donH}px"></div>
              </div>
              <span class="day-label">${d.day}</span>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function handleRegionalSearch(query) {
  const clean = (query || '').trim().toLowerCase();
  const filtered = clean
    ? regionalDataCache.filter(r => r.division.toLowerCase().includes(clean))
    : regionalDataCache;

  const countEl = document.getElementById('divisionSummaryCountText');
  if (countEl) {
    countEl.textContent = clean
      ? `Showing ${filtered.length} of ${regionalDataCache.length} Divisions`
      : `Showing ${regionalDataCache.length} Divisions`;
  }
  renderRegionalSummaryTable(filtered);
}

function renderRegionalSummaryTable(regions) {
  const tbody = document.getElementById('regionalSummaryTableBody');
  if (!tbody) return;

  if (!regions || regions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-muted">No division matching your search.</td></tr>';
    return;
  }

  tbody.innerHTML = regions.map(r => {
    let statusBadge = '<span class="badge badge-success">Adequate</span>';
    if (r.status === 'Critical Shortage') {
      statusBadge = '<span class="badge badge-danger">Critical Shortage</span>';
    } else if (r.status === 'Moderate') {
      statusBadge = '<span class="badge badge-warning">Moderate Supply</span>';
    }

    return `
      <tr>
        <td><strong>${r.division}</strong></td>
        <td><span class="badge badge-pill badge-outline">${r.stock_units} Units</span></td>
        <td>${r.active_requests} requests</td>
        <td>
          ${r.critical_deficits > 0
            ? `<span class="text-danger font-bold">⚠️ ${r.critical_deficits} Deficit Alert</span>`
            : '<span class="text-muted">None</span>'}
        </td>
        <td>${statusBadge}</td>
        <td>
          <button type="button" class="btn btn-xs btn-outline" onclick="drilldownDivision('${r.division}')">
            View Stock Drilldown →
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function renderActivityFeed(stream) {
  const container = document.getElementById('analyticsActivityFeed');
  if (!container) return;

  if (!stream || stream.length === 0) {
    container.innerHTML = '<div class="text-muted text-xs py-2">No recent platform activities recorded.</div>';
    return;
  }

  container.innerHTML = stream.map(item => {
    let badgeClass = 'badge-primary-soft';
    if (item.color === 'danger') badgeClass = 'badge-danger-soft';
    else if (item.color === 'success') badgeClass = 'badge-success-soft';
    else if (item.color === 'info') badgeClass = 'badge-info-soft';
    else if (item.color === 'warning') badgeClass = 'badge-warning-soft';

    return `
      <div class="activity-feed-item">
        <span class="activity-feed-time">${item.time}</span>
        <div class="activity-feed-body">
          <div class="activity-feed-title">${item.title}</div>
          <div class="activity-feed-desc">${item.details}</div>
        </div>
        <span class="activity-feed-badge ${badgeClass}">${item.badge}</span>
      </div>
    `;
  }).join('');
}

function exportAnalyticsCSV() {
  if (!analyticsDataCache) {
    if (typeof showAdminToast === 'function') showAdminToast('Analytics data not loaded yet', 'error');
    return;
  }

  const kpi = analyticsDataCache.kpi_metrics || {};
  let csv = 'SBDS Platform Master Analytics Report\n';
  csv += `Generated At,${new Date().toISOString()}\n`;
  csv += `Time Range,${currentAnalyticsTimeRange}\n\n`;

  csv += '--- HIGH LEVEL METRICS ---\n';
  csv += `Total Registered Users,${kpi.total_users || 0}\n`;
  csv += `Active Urgent Blood Requests,${kpi.total_requests || 0}\n`;
  csv += `Critical Emergency SOS Requests,${kpi.critical_requests || 0}\n`;
  csv += `Fulfilled Transfusions,${kpi.fulfilled_donations || 0}\n`;
  csv += `Estimated Lives Saved,${kpi.lives_saved || 0}\n`;
  csv += `Avg Match Latency (Minutes),${kpi.avg_response_time_minutes || 4.2}\n`;
  csv += `Fulfillment Rate (%),${kpi.fulfillment_rate_percent || 94.8}%\n`;
  csv += `Monitored Facilities,${kpi.monitored_facilities || 45}\n\n`;

  csv += '--- BLOOD GROUP SUPPLY VS DEMAND ---\n';
  csv += 'Blood Group,Supply Units,Demand Requests,Status\n';
  (analyticsDataCache.blood_group_balance || []).forEach(b => {
    csv += `"${b.blood_group}",${b.supply_units},${b.demand_requests},"${b.status}"\n`;
  });
  csv += '\n';

  csv += '--- REGIONAL ACTIVITY & DEFICITS (BANGLADESH DIVISIONS) ---\n';
  csv += 'Division,Stock Units Available,Active Requests,Critical Deficits,Status\n';
  (analyticsDataCache.regional_distribution || []).forEach(r => {
    csv += `"${r.division}",${r.stock_units},${r.active_requests},${r.critical_deficits},"${r.status}"\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sbds_platform_master_analytics_${currentAnalyticsTimeRange}_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  if (typeof showAdminToast === 'function') {
    showAdminToast('✓ Master Analytics CSV exported successfully', 'success');
  }
}

function printAnalyticsBrief() {
  window.print();
}

function drilldownDivision(division) {
  switchAdminSection('stock');
  const select = document.getElementById('districtFilterSelect');
  if (select) {
    select.value = division;
    filterFacilitiesByDistrict(division);
  }
}

// -----------------------------------------------------------------------------
// 2. SBDS-40: User Management & Role Control
// -----------------------------------------------------------------------------
async function loadUsersData() {
  try {
    const q = (document.getElementById('userSearchInput')?.value || '').trim();
    const status = document.getElementById('userStatusSelect')?.value || 'all';

    let url = `/api/v1/admin/users?role=${encodeURIComponent(currentRoleFilter)}&status=${encodeURIComponent(status)}`;
    if (q) url += `&query=${encodeURIComponent(q)}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load users');
    const data = await res.json();
    if (data.status !== 'success') return;

    usersCache = data.users || [];
    renderUsersTable(usersCache);
  } catch (err) {
    console.error('Error loading users:', err);
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById('usersTableBody');
  if (!tbody) return;

  if (!users || users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No users found matching query criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = users.map(u => {
    // Role Badge
    let roleBadge = '<span class="badge badge-pill badge-outline">Donor</span>';
    if (u.role === 'admin') roleBadge = '<span class="badge badge-pill badge-primary">Super Admin</span>';
    else if (u.role === 'seeker') roleBadge = '<span class="badge badge-pill badge-info">Seeker</span>';
    else if (u.role === 'hospital' || u.role === 'bank' || u.role === 'blood_bank') {
      roleBadge = '<span class="badge badge-pill badge-purple">Hospital / Bank</span>';
    }

    // Status Badge
    let statusBadge = '<span class="badge badge-success">Active</span>';
    if (u.status === 'suspended') statusBadge = '<span class="badge badge-warning">Suspended</span>';
    else if (u.status === 'banned') statusBadge = '<span class="badge badge-danger">Banned</span>';

    // Verified badge
    const verifiedIcon = u.is_verified
      ? '<span class="text-success font-semibold" title="KYC Verified">✓ Verified</span>'
      : '<span class="text-muted" title="Unverified">Unverified</span>';

    return `
      <tr>
        <td>
          <div class="user-cell-meta">
            <strong>${escapeHtml(u.name || 'Anonymous User')}</strong>
            <span class="user-sub-id">ID: #${u.id}</span>
          </div>
        </td>
        <td><code>${u.phone}</code></td>
        <td>${roleBadge}</td>
        <td><span class="badge badge-blood">${u.blood_group || '—'}</span></td>
        <td>${escapeHtml(u.district || 'Dhaka')}</td>
        <td>${statusBadge}</td>
        <td>${verifiedIcon}</td>
        <td>
          <div class="table-actions">
            <button type="button" class="btn btn-xs btn-outline" onclick="openUserEditModal('${u.phone}')">Edit Role</button>
            ${u.status === 'active'
              ? `<button type="button" class="btn btn-xs btn-warning-soft" onclick="quickToggleUserStatus('${u.phone}', 'suspended')">Suspend</button>`
              : `<button type="button" class="btn btn-xs btn-success-soft" onclick="quickToggleUserStatus('${u.phone}', 'active')">Activate</button>`
            }
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

let userSearchTimeout = null;
function handleUserSearch() {
  clearTimeout(userSearchTimeout);
  userSearchTimeout = setTimeout(() => {
    loadUsersData();
  }, 250);
}

function filterUsersByRole(role) {
  currentRoleFilter = role;
  document.querySelectorAll('#roleFilterPills .pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-role') === role);
  });
  loadUsersData();
}

function handleUserStatusFilter() {
  loadUsersData();
}

async function quickToggleUserStatus(phone, newStatus) {
  try {
    const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, reason: `Admin console quick-toggle status to ${newStatus}` }),
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast(`User ${phone} status changed to ${newStatus}.`, 'success');
      loadUsersData();
    } else {
      showAdminToast(data.detail || 'Failed to update user status', 'danger');
    }
  } catch (err) {
    console.error('Error toggling status:', err);
    showAdminToast('Network error while updating user status', 'danger');
  }
}

async function openUserEditModal(phone) {
  try {
    const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}`);
    if (!res.ok) throw new Error('User details fetch failed');
    const data = await res.json();
    const user = data.user;

    document.getElementById('editUserPhone').value = user.phone;
    document.getElementById('editUserPhoneDisplay').value = user.phone;
    document.getElementById('editUserName').value = user.name || '';
    document.getElementById('editUserRole').value = user.role || 'donor';
    document.getElementById('editUserStatus').value = user.status || 'active';
    document.getElementById('editUserBloodGroup').value = user.blood_group || 'A+';
    document.getElementById('editUserDistrict').value = user.district || 'Dhaka';

    const modal = document.getElementById('userEditModal');
    if (modal) {
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
    }
  } catch (err) {
    console.error('Error opening user edit modal:', err);
    showAdminToast('Could not load user details.', 'danger');
  }
}

function closeUserEditModal() {
  const modal = document.getElementById('userEditModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

async function saveUserEdit(event) {
  event.preventDefault();
  const phone = document.getElementById('editUserPhone').value;
  const name = document.getElementById('editUserName').value.trim();
  const role = document.getElementById('editUserRole').value;
  const status = document.getElementById('editUserStatus').value;
  const bloodGroup = document.getElementById('editUserBloodGroup').value;
  const district = document.getElementById('editUserDistrict').value;

  try {
    // 1. Update basic profile
    const profileRes = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, blood_group: bloodGroup, district, status }),
    });

    // 2. Update role
    const roleRes = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}/role`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });

    if (profileRes.ok && roleRes.ok) {
      showAdminToast(`Successfully updated profile & role for ${phone}.`, 'success');
      closeUserEditModal();
      loadUsersData();
      loadAnalyticsData();
    } else {
      showAdminToast('Could not save user modifications.', 'danger');
    }
  } catch (err) {
    console.error('Error saving user edit:', err);
    showAdminToast('Network error while updating user.', 'danger');
  }
}

// -----------------------------------------------------------------------------
// 3. SBDS-41: Donor KYC Approval Queue
// -----------------------------------------------------------------------------
async function loadKycQueue(status = 'pending', buttonEl = null) {
  currentKycFilter = status;
  if (buttonEl) {
    document.querySelectorAll('#section-kyc .tab-clean').forEach(t => t.classList.remove('active'));
    buttonEl.classList.add('active');
  }

  try {
    const res = await fetch(`/api/v1/admin/kyc/queue?status=${encodeURIComponent(status)}`);
    if (!res.ok) throw new Error('Failed to load KYC queue');
    const data = await res.json();
    if (data.status !== 'success') return;

    kycCache = data.kyc_requests || [];

    // Update pending count badges
    const pBadge = document.getElementById('kycPendingCountBadge');
    if (pBadge) pBadge.textContent = `${data.pending_count || 0} Pending Review`;

    const navBadge = document.getElementById('navKycPendingBadge');
    if (navBadge) navBadge.textContent = data.pending_count || 0;

    renderKycTable(kycCache);
  } catch (err) {
    console.error('Error loading KYC queue:', err);
  }
}

function renderKycTable(items) {
  const tbody = document.getElementById('kycTableBody');
  if (!tbody) return;

  if (!items || items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No donor KYC records found in this queue.</td></tr>';
    return;
  }

  tbody.innerHTML = items.map(k => {
    let statusBadge = '<span class="badge badge-warning">Pending Review</span>';
    if (k.status === 'approved') statusBadge = '<span class="badge badge-success">✓ Verified & Approved</span>';
    else if (k.status === 'rejected') statusBadge = '<span class="badge badge-danger">✕ Rejected</span>';

    const subDate = k.submitted_at ? k.submitted_at.substring(0, 16).replace('T', ' ') : 'Just now';

    return `
      <tr>
        <td><strong>${escapeHtml(k.donor_name)}</strong></td>
        <td><code>${k.donor_phone}</code></td>
        <td><span class="badge badge-blood">${k.blood_group}</span></td>
        <td><code>${escapeHtml(k.nid_number)}</code></td>
        <td><span class="badge badge-outline">${escapeHtml(k.document_type || 'National ID')}</span></td>
        <td><small class="text-muted">${subDate}</small></td>
        <td>${statusBadge}</td>
        <td>
          <button type="button" class="btn btn-xs btn-primary" onclick="openKycReviewModal(${k.id})">
            Inspect & Verify →
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

async function openKycReviewModal(kycId) {
  try {
    const res = await fetch(`/api/v1/admin/kyc/${kycId}`);
    if (!res.ok) throw new Error('Failed to load KYC item');
    const data = await res.json();
    currentKycItem = data.kyc;

    document.getElementById('kycModalTitle').textContent = `Review Document: ${currentKycItem.donor_name}`;
    document.getElementById('kycDonorName').textContent = currentKycItem.donor_name;
    document.getElementById('kycDonorPhone').textContent = currentKycItem.donor_phone;
    document.getElementById('kycBloodGroup').textContent = currentKycItem.blood_group;
    document.getElementById('kycDocType').textContent = currentKycItem.document_type || 'National ID (NID)';
    document.getElementById('kycNidNumber').textContent = currentKycItem.nid_number;
    document.getElementById('kycSubmissionDate').textContent = (currentKycItem.submitted_at || '').substring(0, 16).replace('T', ' ');

    const preview = document.getElementById('kycDocPreview');
    if (preview) {
      if (currentKycItem.document_url) {
        preview.innerHTML = `<img src="${currentKycItem.document_url}" alt="ID Document Preview" class="kyc-preview-img" onerror="this.onerror=null; this.src='/static/images/sample_nid_1.jpg';">`;
      } else {
        preview.innerHTML = `<div class="kyc-doc-placeholder"><span>📄 Official NID Document Scanned<br>Number: ${currentKycItem.nid_number}</span></div>`;
      }
    }

    const modal = document.getElementById('kycReviewModal');
    if (modal) {
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
    }
  } catch (err) {
    console.error('Error opening KYC modal:', err);
    showAdminToast('Could not load KYC verification item.', 'danger');
  }
}

function closeKycReviewModal() {
  const modal = document.getElementById('kycReviewModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
  currentKycItem = null;
}

async function submitKycDecision(action) {
  if (!currentKycItem) return;
  const reason = document.getElementById('kycRejectionReason')?.value.trim() || '';

  if (action === 'reject' && !reason) {
    showAdminToast('Please provide a reason or select a quick rejection template.', 'warning');
    return;
  }

  try {
    const res = await fetch(`/api/v1/admin/kyc/${currentKycItem.id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, reason, reviewer_name: 'System Admin' }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      const verb = action === 'approve' ? 'Approved & Granted Verified Badge' : 'Rejected';
      showAdminToast(`KYC submission #${currentKycItem.id} ${verb}.`, 'success');
      closeKycReviewModal();
      loadKycQueue(currentKycFilter);
      loadAnalyticsData();
    } else {
      showAdminToast(data.detail || 'Failed to submit KYC decision.', 'danger');
    }
  } catch (err) {
    console.error('Error submitting KYC decision:', err);
    showAdminToast('Network error while processing verification.', 'danger');
  }
}

// -----------------------------------------------------------------------------
// 4. SBDS-42: Blood Requests Moderation & Duplicate Detection
// -----------------------------------------------------------------------------
let moderationSearchTimeout = null;

async function loadModerationRequests(showToast = false) {
  const icon = document.getElementById('refreshModerationIcon');
  if (icon) icon.classList.add('spin-anim');

  try {
    const status = document.getElementById('moderationStatusFilter')?.value || 'all';
    const urgency = document.getElementById('moderationUrgencyFilter')?.value || 'all';
    const risk = document.getElementById('moderationRiskFilter')?.value || 'all';
    const search = document.getElementById('moderationSearchInput')?.value || '';

    const params = new URLSearchParams({ status, urgency, risk_level: risk });
    if (search.trim()) params.append('search', search.trim());

    const res = await fetch(`/api/v1/admin/requests/moderation?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load moderation requests');
    const data = await res.json();
    if (data.status !== 'success') return;

    moderationRequestsCache = data.requests || [];
    const stats = data.stats || {};

    // 1. Update KPI Summary Cards
    const totalEl = document.getElementById('modKpiTotalRequestsVal');
    if (totalEl) totalEl.textContent = stats.total_requests ?? moderationRequestsCache.length;

    const flaggedEl = document.getElementById('modKpiFlaggedVal');
    if (flaggedEl) flaggedEl.textContent = stats.flagged_count ?? 0;

    const dupEl = document.getElementById('modKpiDuplicatesVal');
    if (dupEl) dupEl.textContent = stats.high_risk_count ?? 0;

    const appEl = document.getElementById('modKpiApprovedVal');
    if (appEl) appEl.textContent = stats.approved_count ?? 0;

    const countText = document.getElementById('moderationCountText');
    if (countText) {
      countText.textContent = `Showing ${moderationRequestsCache.length} of ${stats.total_requests ?? moderationRequestsCache.length} blood requests`;
    }

    // 2. Update Sidebar Navigation Badge
    const dupBadge = document.getElementById('navDuplicateBadge');
    if (dupBadge) {
      const dupCount = stats.high_risk_count ?? moderationRequestsCache.filter(r => (r.duplicate_risk || 0) >= 65).length;
      dupBadge.textContent = dupCount > 0 ? `${dupCount} Dup` : 'Dup';
      dupBadge.style.display = 'inline-block';
    }

    renderModerationRequestsTable(moderationRequestsCache);
    if (showToast) showAdminToast('Blood requests moderation queue updated.', 'success');
  } catch (err) {
    console.error('Error loading moderation requests:', err);
    if (showToast) showAdminToast('Failed to load requests moderation queue.', 'danger');
  } finally {
    if (icon) icon.classList.remove('spin-anim');
  }
}

function handleModerationSearch(query) {
  clearTimeout(moderationSearchTimeout);
  moderationSearchTimeout = setTimeout(() => {
    loadModerationRequests();
  }, 250);
}

function handleModerationFiltersChange() {
  loadModerationRequests();
}

function renderModerationRequestsTable(requests) {
  const tbody = document.getElementById('moderationRequestsTableBody');
  if (!tbody) return;

  if (!requests || requests.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">No blood requests match current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = requests.map(r => {
    // Urgency badge
    const isEmergency = r.is_emergency === 1 || String(r.urgency_level || '').toLowerCase().includes('critical') || String(r.urgency_level || '').toLowerCase().includes('red');
    const urgencyBadge = isEmergency
      ? '<span class="badge badge-danger pulse">🚨 CRITICAL SOS</span>'
      : (String(r.urgency_level || '').toLowerCase().includes('urgent')
          ? '<span class="badge badge-warning">Urgent</span>'
          : '<span class="badge badge-outline">Standard</span>');

    // Duplicate risk score styling & indicator
    const score = Math.round(r.duplicate_risk || 0);
    let riskBadge = `<span class="badge badge-success">✓ ${score}% Unique</span>`;
    if (score >= 70) {
      riskBadge = `<span class="badge badge-danger font-bold">🚨 ${score}% High Risk</span>`;
    } else if (score >= 35) {
      riskBadge = `<span class="badge badge-warning font-bold">⚠️ ${score}% Possible Dup</span>`;
    }

    // Moderation status badge
    let statusBadge = `<span class="badge badge-success-soft">${r.moderation_status || 'approved'}</span>`;
    if (r.moderation_status === 'flagged') {
      statusBadge = '<span class="badge badge-danger">🚩 Flagged</span>';
    } else if (r.moderation_status === 'duplicate') {
      statusBadge = `<span class="badge badge-warning">Duplicate #${r.duplicate_of_id || ''}</span>`;
    }

    // Suspicious content alert chip
    const suspChip = r.is_suspicious
      ? `<span class="badge badge-danger-soft mt-1" title="${(r.suspicious_signals || []).join('; ')}">⚠️ Suspicious Content</span>`
      : '';

    // Request lifecycle status badge
    const reqStatusBadge = `<span class="badge badge-outline">${escapeHtml(r.status || 'Active')}</span>`;

    return `
      <tr id="req-row-${r.id}">
        <td><code>#${r.id}</code></td>
        <td>
          <div class="user-cell-meta">
            <strong>${escapeHtml(r.patient_name || 'Patient (Unspecified)')}</strong>
            <span class="user-sub-id">📞 ${escapeHtml(r.contact_phone || 'No Phone')}</span>
            ${suspChip}
          </div>
        </td>
        <td>
          <div class="user-cell-meta">
            <strong>${escapeHtml(r.hospital_name || 'Hospital')}</strong>
            <span class="user-sub-id">📍 ${escapeHtml(r.area ? `${r.area}, ${r.district}` : (r.district || 'Dhaka'))}</span>
          </div>
        </td>
        <td><span class="badge badge-blood">${escapeHtml(r.blood_group || '')}</span></td>
        <td><strong>${r.units || 1}</strong> Bag(s)</td>
        <td>${urgencyBadge}</td>
        <td>
          <button type="button" class="btn btn-xs btn-link-clean" onclick="inspectDuplicateRequest(${r.id})" title="Click to view heuristic similarity analysis">
            ${riskBadge}
          </button>
        </td>
        <td>${statusBadge}</td>
        <td>${reqStatusBadge}</td>
        <td>
          <div class="table-actions">
            ${r.moderation_status !== 'approved'
              ? `<button type="button" class="btn btn-xs btn-success" onclick="resolveRequestModeration(${r.id}, 'approve')">Approve</button>`
              : `<button type="button" class="btn btn-xs btn-warning-soft" onclick="promptFlagRequest(${r.id})">Flag</button>`
            }
            <button type="button" class="btn btn-xs btn-outline" onclick="openStatusUpdateModal(${r.id}, '${escapeHtml(r.status || 'Active')}')">Status</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="openRequestHistoryModal(${r.id})" title="View Moderation Trail">📜</button>
            <button type="button" class="btn btn-xs btn-secondary" onclick="inspectDuplicateRequest(${r.id})" title="Compare Duplicates">🔍</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function promptFlagRequest(reqId) {
  const reason = prompt('Enter justification or notes for flagging this blood request:', 'Suspicious or duplicate request pending moderation');
  if (reason !== null) {
    resolveRequestModeration(reqId, 'flag', null, reason);
  }
}

async function inspectDuplicateRequest(reqId) {
  try {
    const res = await fetch(`/api/v1/admin/requests/${reqId}/duplicates`);
    if (!res.ok) throw new Error('Duplicate inspection failed');
    const data = await res.json();

    const target = data.target_request || {};
    const candidates = data.candidates || [];
    const container = document.getElementById('duplicateModalContent');
    const footer = document.getElementById('duplicateModalFooter');

    if (!container) return;

    let candidateCardsHtml = '';
    if (candidates.length === 0) {
      candidateCardsHtml = `
        <div class="dup-safe-notice">
          <span class="text-success text-2xl">✓</span>
          <p><strong>No duplicate matches found.</strong> This request appears authentic and unique.</p>
        </div>
      `;
    } else {
      candidateCardsHtml = candidates.map(c => `
        <div class="dup-candidate-card">
          <div class="dup-candidate-head">
            <strong>Matching Blood Request #${c.request_id}</strong>
            <span class="badge ${c.risk_score >= 70 ? 'badge-danger' : 'badge-warning'} font-bold">${Math.round(c.risk_score)}% Similarity Match</span>
          </div>
          <div class="dup-candidate-details">
            <div><strong>Hospital:</strong> ${escapeHtml(c.hospital_name || '')}</div>
            <div><strong>Blood Group:</strong> <span class="badge badge-blood">${escapeHtml(c.blood_group || '')}</span></div>
            <div><strong>Contact:</strong> ${escapeHtml(c.contact_phone || '—')}</div>
            <div><strong>Patient:</strong> ${escapeHtml(c.patient_name || '—')}</div>
          </div>
          <div class="dup-reasons-list">
            <span class="reasons-label"><strong>Algorithm Signal Triggers:</strong></span>
            <ul>
              ${(c.reasons || []).map(r => `<li>⚠️ ${escapeHtml(r)}</li>`).join('')}
            </ul>
          </div>
          <div class="dup-card-actions">
            <button type="button" class="btn btn-xs btn-danger" onclick="resolveRequestModeration(${target.id}, 'duplicate', ${c.request_id}, 'Marked as duplicate of #${c.request_id}')">
              Mark #${target.id} as Duplicate of #${c.request_id}
            </button>
          </div>
        </div>
      `).join('');
    }

    const suspiciousNotice = data.is_suspicious
      ? `<div class="analytics-alert-banner mb-3" style="margin-bottom:12px;">
           <div class="alert-icon-pulse">⚠️</div>
           <div class="alert-banner-text"><strong>Suspicious Content Warning:</strong> ${(data.suspicious_signals || []).join(', ')}</div>
         </div>`
      : '';

    container.innerHTML = `
      ${suspiciousNotice}
      <div class="dup-target-summary mb-3">
        <h4>Inspecting Request #${target.id}: ${escapeHtml(target.patient_name || 'Patient')}</h4>
        <div class="dup-target-pills">
          <span class="badge badge-blood">${target.blood_group}</span>
          <span class="badge badge-outline">🏥 ${escapeHtml(target.hospital_name)}</span>
          <span class="badge badge-outline">📍 ${escapeHtml(target.area ? `${target.area}, ${target.district}` : (target.district || 'Dhaka'))}</span>
          <span class="badge badge-outline">📞 ${escapeHtml(target.contact_phone || '')}</span>
          <span class="badge badge-outline">Units: ${target.units || 1}</span>
          <span class="badge badge-outline">Status: ${target.status || 'Active'}</span>
        </div>
        <p class="mt-2 text-sm text-muted">Automated multi-factor evaluation comparing contact numbers, patient names, hospital locations, and request frequencies within the platform.</p>
      </div>
      <div class="dup-candidates-wrap">
        <h5 class="mb-2">Duplicate Detection Matches (${candidates.length} candidate${candidates.length === 1 ? '' : 's'})</h5>
        ${candidateCardsHtml}
      </div>
    `;

    if (footer) {
      footer.innerHTML = `
        <button type="button" class="btn btn-secondary" onclick="closeDuplicateModal()">Close</button>
        <button type="button" class="btn btn-outline" onclick="openRequestHistoryModal(${target.id})">📜 Action Trail</button>
        <button type="button" class="btn btn-outline" onclick="openStatusUpdateModal(${target.id}, '${escapeHtml(target.status || 'Active')}')">Update Status</button>
        <button type="button" class="btn btn-danger" onclick="resolveRequestModeration(${target.id}, 'flag', null, 'Flagged from inspection modal')">Flag Suspicious</button>
        <button type="button" class="btn btn-success" onclick="resolveRequestModeration(${target.id}, 'approve', null, 'Approved from inspection modal')">Clear &amp; Approve</button>
      `;
    }

    const modal = document.getElementById('duplicateInspectionModal');
    if (modal) {
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
    }
  } catch (err) {
    console.error('Error inspecting duplicates:', err);
    showAdminToast('Could not analyze request duplicates.', 'danger');
  }
}

function closeDuplicateModal() {
  const modal = document.getElementById('duplicateInspectionModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

async function resolveRequestModeration(reqId, action, duplicateOfId = null, notes = '') {
  try {
    const res = await fetch(`/api/v1/admin/requests/${reqId}/moderate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        duplicate_of_id: duplicateOfId,
        notes: notes || `Admin action: ${action}`,
      }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast(`Request #${reqId} successfully moderated (${action}).`, 'success');
      closeDuplicateModal();
      loadModerationRequests();
      loadAnalyticsData();
    } else {
      showAdminToast(data.detail || 'Could not moderate request.', 'danger');
    }
  } catch (err) {
    console.error('Error resolving request moderation:', err);
    showAdminToast('Network error while updating request.', 'danger');
  }
}

function openStatusUpdateModal(reqId, currentStatus) {
  const modal = document.getElementById('statusUpdateModal');
  const reqIdInput = document.getElementById('statusUpdateReqId');
  const summary = document.getElementById('statusUpdateReqSummary');
  const select = document.getElementById('newStatusSelect');
  const notes = document.getElementById('statusUpdateNotes');

  if (reqIdInput) reqIdInput.value = reqId;
  if (summary) summary.textContent = `Updating lifecycle status for Blood Request #${reqId}`;
  if (select) select.value = currentStatus || 'Active';
  if (notes) notes.value = '';

  if (modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
  }
}

function closeStatusUpdateModal() {
  const modal = document.getElementById('statusUpdateModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

async function submitRequestStatusUpdate(event) {
  event.preventDefault();
  const reqId = document.getElementById('statusUpdateReqId')?.value;
  const status = document.getElementById('newStatusSelect')?.value;
  const reason = document.getElementById('statusUpdateNotes')?.value || '';

  if (!reqId || !status) return;

  try {
    const res = await fetch(`/api/v1/admin/requests/${reqId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, reason }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast(`Request #${reqId} status changed to ${status}.`, 'success');
      closeStatusUpdateModal();
      loadModerationRequests();
      loadAnalyticsData();
    } else {
      showAdminToast(data.detail || 'Could not update status.', 'danger');
    }
  } catch (err) {
    console.error('Error updating request status:', err);
    showAdminToast('Network error while updating status.', 'danger');
  }
}

async function openRequestHistoryModal(reqId) {
  const modal = document.getElementById('requestHistoryModal');
  const content = document.getElementById('requestHistoryModalContent');
  if (!modal || !content) return;

  content.innerHTML = '<div class="loading-spinner-row">Loading moderation history records...</div>';
  modal.classList.add('active');
  modal.setAttribute('aria-hidden', 'false');

  try {
    const res = await fetch(`/api/v1/admin/requests/${reqId}/history`);
    if (!res.ok) throw new Error('Failed to load history');
    const data = await res.json();
    const records = data.history || [];

    if (records.length === 0) {
      content.innerHTML = `
        <div class="dup-safe-notice">
          <p>No moderation actions have been recorded for Request #${reqId} yet.</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="history-timeline">
        ${records.map(r => `
          <div class="history-item">
            <div class="history-time">${formatDatePretty(r.created_at)}</div>
            <div class="history-body">
              <div class="history-title">
                <span class="badge badge-primary-soft">${escapeHtml(r.action)}</span>
                by <strong>${escapeHtml(r.admin_name || 'System Admin')}</strong>
                ${r.new_status ? `&rarr; Status: <code>${escapeHtml(r.new_status)}</code>` : ''}
              </div>
              <div class="history-notes">${escapeHtml(r.notes || 'No explanation provided')}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    console.error('Error loading request history:', err);
    content.innerHTML = '<p class="text-danger">Could not load action history records.</p>';
  }
}

function closeRequestHistoryModal() {
  const modal = document.getElementById('requestHistoryModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

function exportModerationRequestsCSV() {
  if (!moderationRequestsCache || moderationRequestsCache.length === 0) {
    showAdminToast('No blood requests available to export.', 'warning');
    return;
  }

  let csv = 'Req ID,Patient,Contact Phone,Hospital,District,Area,Blood Group,Units,Urgency,Duplicate Risk (%),Duplicate Label,Moderation Status,Request Status\n';
  moderationRequestsCache.forEach(r => {
    csv += `"${r.id}","${escapeHtml(r.patient_name || '')}","${r.contact_phone || ''}","${escapeHtml(r.hospital_name || '')}","${r.district || ''}","${r.area || ''}","${r.blood_group || ''}",${r.units || 1},"${r.is_emergency ? 'Critical' : 'Standard'}",${r.duplicate_risk || 0},"${r.duplicate_label || ''}","${r.moderation_status || ''}","${r.status || ''}"\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `sbds_blood_requests_moderation_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showAdminToast('Moderation queue exported to CSV.', 'success');
}

function formatDatePretty(iso) {
  if (!iso) return 'Just now';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + d.toLocaleDateString();
  } catch {
    return iso;
  }
}

// -----------------------------------------------------------------------------
// 5. SBDS-43: Platform Blood Stock Oversight & Heatmap
// -----------------------------------------------------------------------------
async function loadInventoryHeatmap() {
  try {
    const [heatRes, facRes] = await Promise.all([
      fetch('/api/v1/admin/inventory/heatmap'),
      fetch(`/api/v1/admin/inventory/facilities?district=${encodeURIComponent(currentDistrictFilter)}`),
    ]);

    if (heatRes.ok) {
      const hData = await heatRes.json();
      heatmapDataCache = hData.heatmap || [];
      renderHeatmapGrid(heatmapDataCache);

      // Total units & facilities stats
      const totalUnits = heatmapDataCache.reduce((sum, d) => sum + (d.total_units || 0), 0);
      const totalFacs = heatmapDataCache.reduce((sum, d) => sum + (d.facilities_count || 0), 0);

      const totEl = document.getElementById('stockTotalUnitsVal');
      if (totEl) totEl.textContent = `${totalUnits} Units`;

      const facEl = document.getElementById('stockFacilitiesCountVal');
      if (facEl) facEl.textContent = `${totalFacs} Centers Connected`;

      const critDivs = heatmapDataCache.filter(d => d.critical_deficits > 0).map(d => d.division);
      const critEl = document.getElementById('stockCriticalGroupsVal');
      if (critEl) {
        critEl.textContent = critDivs.length > 0 ? `Critical: ${critDivs.join(', ')}` : 'All Divisions Balanced';
      }
    }

    if (facRes.ok) {
      const fData = await facRes.json();
      facilitiesCache = fData.facilities || [];
      renderFacilitiesTable(facilitiesCache);
    }
  } catch (err) {
    console.error('Error loading inventory heatmap:', err);
  }
}

function renderHeatmapGrid(heatmap) {
  const container = document.getElementById('heatmapDivisionsGrid');
  if (!container) return;

  if (!heatmap || heatmap.length === 0) {
    container.innerHTML = '<div class="heatmap-empty">No division heatmap records found.</div>';
    return;
  }

  container.innerHTML = heatmap.map(d => {
    let scoreColor = '#10B981';
    let cardClass = 'heatmap-card safe';
    if (d.shortage_score >= 75) {
      scoreColor = '#EF4444';
      cardClass = 'heatmap-card critical';
    } else if (d.shortage_score >= 40) {
      scoreColor = '#F59E0B';
      cardClass = 'heatmap-card warning';
    }

    return `
      <div class="${cardClass}" onclick="drilldownDivision('${d.division}')" title="Click to filter facilities in ${d.division}">
        <div class="heat-card-header">
          <strong class="division-title">${d.division}</strong>
          <span class="heat-score-badge" style="color: ${scoreColor}; border-color: ${scoreColor}">${d.shortage_score}/100 Risk</span>
        </div>
        <div class="heat-metrics-row">
          <div>
            <span class="metric-sublabel">Total Units:</span>
            <strong class="metric-subval">${d.total_units} units</strong>
          </div>
          <div>
            <span class="metric-sublabel">Centers:</span>
            <strong class="metric-subval">${d.facilities_count}</strong>
          </div>
        </div>
        <div class="heat-rare-groups">
          <span class="rare-chip ${d.o_minus_units <= 2 ? 'crit' : ''}">O-: ${d.o_minus_units}u</span>
          <span class="rare-chip ${d.b_minus_units <= 1 ? 'crit' : ''}">B-: ${d.b_minus_units}u</span>
        </div>
        <div class="heat-card-footer">
          <span class="severity-label" style="color: ${scoreColor}">${d.severity}</span>
          <span class="arrow-indicator">→</span>
        </div>
      </div>
    `;
  }).join('');
}

function filterFacilitiesByDistrict(district) {
  currentDistrictFilter = district;
  const titleEl = document.getElementById('facilityTableTitle');
  if (titleEl) {
    titleEl.textContent = district === 'all'
      ? 'Hospital & Blood Bank Inventories (All Divisions)'
      : `Hospital & Blood Bank Inventories (${district} Division)`;
  }
  loadInventoryHeatmap();
}

function renderFacilitiesTable(facilities) {
  const tbody = document.getElementById('facilitiesTableBody');
  if (!tbody) return;

  if (!facilities || facilities.length === 0) {
    tbody.innerHTML = '<tr><td colspan="14" class="text-center py-4 text-muted">No facility inventories available in this division.</td></tr>';
    return;
  }

  const groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

  tbody.innerHTML = facilities.map(f => {
    const stockCols = groups.map(g => {
      const u = f.stock[g] ?? 0;
      let cl = '';
      if (u === 0) cl = 'stock-zero';
      else if (u <= 2) cl = 'stock-low';
      return `<td class="${cl}">${u}</td>`;
    }).join('');

    const statusBadge = f.has_critical
      ? '<span class="badge badge-danger">Critical Shortage</span>'
      : (f.total_units < 20 ? '<span class="badge badge-warning">Low Stock</span>' : '<span class="badge badge-success">Adequate</span>');

    return `
      <tr>
        <td><strong>${escapeHtml(f.facility_name)}</strong></td>
        <td><span class="badge badge-outline">${escapeHtml(f.facility_type)}</span></td>
        <td>${escapeHtml(f.district)}</td>
        ${stockCols}
        <td><strong>${f.total_units}u</strong></td>
        <td>${statusBadge}</td>
        <td>
          <button type="button" class="btn btn-xs btn-danger-soft" onclick="openEmergencySmsForFacility('${escapeHtml(f.facility_name)}', '${f.district}')">
            ⚡ Low Stock SOS
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function openEmergencySmsForFacility(facilityName, district) {
  openEmergencySmsModal();
  const hospInput = document.getElementById('smsHospitalName');
  const distSelect = document.getElementById('smsDistrict');
  if (hospInput) hospInput.value = facilityName;
  if (distSelect) distSelect.value = district;
  updateSmsLivePreview();
}

// -----------------------------------------------------------------------------
// 6. SBDS-44: User Reviews, Flagged Reports & Moderation
// -----------------------------------------------------------------------------
function switchReportsSubTab(subtab, btn) {
  document.querySelectorAll('#section-reports .tab-clean').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');

  document.querySelectorAll('.reports-subtab').forEach(st => st.classList.remove('active'));
  const target = document.getElementById(`subtab-${subtab === 'reviews' ? 'user-reviews' : 'reports-queue'}`);
  if (target) target.classList.add('active');

  if (subtab === 'reviews') loadReviewsData();
  else loadReportsData();
}

async function loadReportsData() {
  try {
    const res = await fetch('/api/v1/admin/reports');
    if (!res.ok) throw new Error('Failed to load moderation reports');
    const data = await res.json();
    reportsCache = data.reports || [];

    const badge = document.getElementById('navReportsBadge');
    if (badge) badge.textContent = data.open_count || 0;

    renderReportsTable(reportsCache);
  } catch (err) {
    console.error('Error loading reports:', err);
  }
}

function renderReportsTable(reports) {
  const tbody = document.getElementById('reportsTableBody');
  if (!tbody) return;

  if (!reports || reports.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No pending user moderation reports.</td></tr>';
    return;
  }

  tbody.innerHTML = reports.map(r => {
    let pBadge = '<span class="badge badge-warning">Medium</span>';
    if (r.priority === 'high') pBadge = '<span class="badge badge-danger">High Priority</span>';
    else if (r.priority === 'low') pBadge = '<span class="badge badge-outline">Low</span>';

    let sBadge = '<span class="badge badge-danger">Open</span>';
    if (r.status === 'resolved') sBadge = '<span class="badge badge-success">Resolved</span>';
    else if (r.status === 'dismissed') sBadge = '<span class="badge badge-outline">Dismissed</span>';
    else if (r.status === 'under_review') sBadge = '<span class="badge badge-info">Under Review</span>';

    return `
      <tr>
        <td><code>#${r.id}</code></td>
        <td><span class="badge badge-purple">${escapeHtml(r.category)}</span></td>
        <td>
          <div class="user-cell-meta">
            <strong>${escapeHtml(r.reporter_name)}</strong>
            <span class="user-sub-id">${r.reporter_phone}</span>
          </div>
        </td>
        <td>
          <div class="user-cell-meta">
            <strong>${escapeHtml(r.target_name)} (${r.target_role})</strong>
            <span class="user-sub-id">${r.target_phone}</span>
          </div>
        </td>
        <td>${pBadge}</td>
        <td><div class="desc-cell-truncate">${escapeHtml(r.description)}</div></td>
        <td>${sBadge}</td>
        <td>
          <button type="button" class="btn btn-xs btn-primary" onclick="openReportResolutionModal(${r.id})">
            Investigate & Resolve →
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

async function openReportResolutionModal(reportId) {
  try {
    const res = await fetch(`/api/v1/admin/reports/${reportId}`);
    if (!res.ok) throw new Error('Report not found');
    const data = await res.json();
    const rep = data.report;

    document.getElementById('resolutionReportId').value = rep.id;
    const summary = document.getElementById('reportMetaSummary');
    if (summary) {
      summary.innerHTML = `
        <div class="report-meta-box">
          <div class="meta-row"><strong>Report ID:</strong> #${rep.id} (${rep.category})</div>
          <div class="meta-row"><strong>Reporter:</strong> ${escapeHtml(rep.reporter_name)} (${rep.reporter_phone})</div>
          <div class="meta-row"><strong>Target Accused:</strong> ${escapeHtml(rep.target_name)} (${rep.target_phone}) [${rep.target_role}]</div>
          <div class="meta-row mt-2"><strong>Grievance Allegation:</strong></div>
          <p class="allegation-quote">"${escapeHtml(rep.description)}"</p>
        </div>
      `;
    }

    const modal = document.getElementById('reportResolutionModal');
    if (modal) {
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
    }
  } catch (err) {
    console.error('Error opening resolution modal:', err);
    showAdminToast('Could not load report details.', 'danger');
  }
}

function closeReportResolutionModal() {
  const modal = document.getElementById('reportResolutionModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

async function submitReportAction(action) {
  const reportId = document.getElementById('resolutionReportId')?.value;
  const notes = document.getElementById('resolutionNotes')?.value.trim() || '';

  if (!reportId) return;

  try {
    const res = await fetch(`/api/v1/admin/reports/${reportId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, resolution_notes: notes }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast(`Report #${reportId} action '${action}' recorded.`, 'success');
      closeReportResolutionModal();
      loadReportsData();
      loadAnalyticsData();
    } else {
      showAdminToast(data.detail || 'Could not resolve report.', 'danger');
    }
  } catch (err) {
    console.error('Error submitting report action:', err);
    showAdminToast('Network error while resolving incident.', 'danger');
  }
}

async function loadReviewsData() {
  try {
    const res = await fetch('/api/v1/admin/reviews');
    if (!res.ok) throw new Error('Reviews fetch failed');
    const data = await res.json();

    const avgEl = document.getElementById('avgRatingNum');
    if (avgEl) avgEl.textContent = data.average_rating || '4.8';

    const cntEl = document.getElementById('totalReviewsCount');
    if (cntEl) cntEl.textContent = `Based on ${data.total_reviews || 0} Verified Transfusions`;

    const container = document.getElementById('reviewsListGrid');
    if (!container) return;

    const reviews = data.reviews || [];
    if (reviews.length === 0) {
      container.innerHTML = '<div class="reviews-empty">No donor reviews posted yet.</div>';
      return;
    }

    container.innerHTML = reviews.map(r => `
      <div class="review-item-card">
        <div class="review-card-head">
          <div>
            <strong>${escapeHtml(r.reviewer_name)}</strong>
            <span class="review-sub">for ${escapeHtml(r.target_name)}</span>
          </div>
          <div class="review-stars">${'★'.repeat(r.rating || 5)}${'☆'.repeat(5 - (r.rating || 5))}</div>
        </div>
        <p class="review-comment">"${escapeHtml(r.comment)}"</p>
        <span class="review-date text-muted text-xs">${(r.created_at || '').substring(0, 10)}</span>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading reviews:', err);
  }
}

// -----------------------------------------------------------------------------
// 7. SBDS-45: Settings & System Audit Trail
// -----------------------------------------------------------------------------
async function loadAdminSettings() {
  try {
    const res = await fetch('/api/v1/admin/settings');
    if (!res.ok) return;
    const data = await res.json();
    const s = data.settings || {};

    const el2fa = document.getElementById('setting2fa');
    if (el2fa) el2fa.checked = !!s.two_factor_auth;

    const elLock = document.getElementById('settingSmsLock');
    if (elLock) elLock.checked = !!s.emergency_broadcast_lock;

    const elAuto = document.getElementById('settingAutoModeration');
    if (elAuto) elAuto.checked = !!s.auto_moderation_enabled;

    const elTimeout = document.getElementById('settingSessionTimeout');
    if (elTimeout && s.session_timeout_minutes) elTimeout.value = String(s.session_timeout_minutes);

    const elMaxOtp = document.getElementById('settingMaxOtp');
    if (elMaxOtp && s.max_otp_attempts) elMaxOtp.value = String(s.max_otp_attempts);

    const elSms = document.getElementById('settingSmsProvider');
    if (elSms && s.sms_gateway_provider) elSms.value = s.sms_gateway_provider;
  } catch (err) {
    console.error('Error loading settings:', err);
  }
}

async function saveAdminSettings(event) {
  event.preventDefault();

  const payload = {
    two_factor_auth: document.getElementById('setting2fa')?.checked,
    emergency_broadcast_lock: document.getElementById('settingSmsLock')?.checked,
    auto_moderation_enabled: document.getElementById('settingAutoModeration')?.checked,
    session_timeout_minutes: parseInt(document.getElementById('settingSessionTimeout')?.value || '60', 10),
    max_otp_attempts: parseInt(document.getElementById('settingMaxOtp')?.value || '5', 10),
    sms_gateway_provider: document.getElementById('settingSmsProvider')?.value,
  };

  try {
    const res = await fetch('/api/v1/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast('Platform security and governance policies saved.', 'success');
      loadAuditLogs();
    } else {
      showAdminToast(data.detail || 'Failed to save settings.', 'danger');
    }
  } catch (err) {
    console.error('Error saving settings:', err);
    showAdminToast('Network error while saving settings.', 'danger');
  }
}

async function changeAdminPassword(event) {
  event.preventDefault();
  const currentPassword = document.getElementById('adminCurrentPassword')?.value || '';
  const newPassword = document.getElementById('adminNewPassword')?.value || '';
  const confirmPassword = document.getElementById('adminConfirmPassword')?.value || '';

  if (newPassword !== confirmPassword) {
    showAdminToast('New password confirmation does not match.', 'warning');
    return;
  }

  if (newPassword.length < 6) {
    showAdminToast('Password must be at least 6 characters.', 'warning');
    return;
  }

  try {
    const res = await fetch('/api/v1/admin/settings/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast('Administrator password updated successfully.', 'success');
      document.getElementById('adminPasswordForm')?.reset();
      loadAuditLogs();
    } else {
      showAdminToast(data.detail || 'Password update failed.', 'danger');
    }
  } catch (err) {
    console.error('Error changing password:', err);
    showAdminToast('Network error while updating password.', 'danger');
  }
}

async function loadAuditLogs() {
  try {
    const res = await fetch('/api/v1/admin/audit-logs?limit=50');
    if (!res.ok) return;
    const data = await res.json();
    const logs = data.logs || [];

    const tbody = document.getElementById('auditLogsTableBody');
    if (!tbody) return;

    if (logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No audit trail logs recorded.</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td><small class="text-muted">${(l.created_at || '').substring(0, 19).replace('T', ' ')}</small></td>
        <td><strong>${escapeHtml(l.admin_name)}</strong></td>
        <td><span class="badge badge-outline">${escapeHtml(l.action)}</span></td>
        <td><code>${escapeHtml(l.target)}</code></td>
        <td><span class="text-sm">${escapeHtml(l.details)}</span></td>
        <td><small class="text-muted">${escapeHtml(l.ip_address || '127.0.0.1')}</small></td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading audit logs:', err);
  }
}

async function exportAuditLogs() {
  try {
    const res = await fetch('/api/v1/admin/audit-logs/export');
    if (!res.ok) throw new Error('Export failed');
    const data = await res.json();

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sbds_admin_audit_trail_${new Date().toISOString().substring(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showAdminToast('Audit log JSON export downloaded.', 'success');
  } catch (err) {
    console.error('Error exporting audit logs:', err);
    showAdminToast('Failed to export audit logs.', 'danger');
  }
}

// -----------------------------------------------------------------------------
// 8. Emergency SMS & FCM Web Push Gateways (SBDS-47, SBDS-48)
// -----------------------------------------------------------------------------
function openEmergencySmsModal() {
  const modal = document.getElementById('emergencySmsModal');
  if (modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    updateSmsLivePreview();
  }
}

function closeEmergencySmsModal() {
  const modal = document.getElementById('emergencySmsModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

function updateSmsLivePreview() {
  const bg = document.getElementById('smsBloodGroup')?.value || 'O-';
  const dist = document.getElementById('smsDistrict')?.value || 'Dhaka';
  const hosp = document.getElementById('smsHospitalName')?.value || 'Dhaka Medical College Hospital';
  const custom = document.getElementById('smsCustomMessage')?.value.trim();

  const preview = document.getElementById('smsPreviewText');
  if (preview) {
    preview.textContent = custom || `[CRITICAL SBDS ALERT] Emergency ${bg} blood needed at ${hosp}, ${dist}. Reply YES or open app immediately.`;
  }
}

async function submitEmergencySms(event) {
  event.preventDefault();
  const bg = document.getElementById('smsBloodGroup')?.value;
  const dist = document.getElementById('smsDistrict')?.value;
  const hosp = document.getElementById('smsHospitalName')?.value.trim();
  const custom = document.getElementById('smsCustomMessage')?.value.trim();

  const btn = document.getElementById('submitSmsBtn');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/v1/notifications/sms/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blood_group: bg,
        district: dist,
        hospital_name: hosp,
        message: custom,
        is_critical: true,
      }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast(`Emergency SMS broadcast dispatched to ${data.recipients_count || 3} donors!`, 'success');
      closeEmergencySmsModal();
      loadAuditLogs();
      loadAnalyticsData();
    } else {
      showAdminToast(data.detail || 'Emergency SMS dispatch failed.', 'danger');
    }
  } catch (err) {
    console.error('Error dispatching SMS:', err);
    showAdminToast('Network error while dispatching emergency SMS.', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openPushModal() {
  const modal = document.getElementById('pushModal');
  if (modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
  }
}

function closePushModal() {
  const modal = document.getElementById('pushModal');
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
  }
}

async function submitWebPush(event) {
  event.preventDefault();
  const recipient = document.getElementById('pushRecipient')?.value || 'all';
  const title = document.getElementById('pushTitle')?.value.trim();
  const body = document.getElementById('pushBody')?.value.trim();

  try {
    const res = await fetch('/api/v1/notifications/push/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient_phone: recipient, title, body, click_url: '/admin/dashboard' }),
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showAdminToast('Web Push notification dispatched via FCM Gateway.', 'success');
      closePushModal();
      document.getElementById('pushNotificationForm')?.reset();
    } else {
      showAdminToast(data.detail || 'Push notification dispatch failed.', 'danger');
    }
  } catch (err) {
    console.error('Error dispatching push:', err);
    showAdminToast('Network error during push dispatch.', 'danger');
  }
}

function openNewNotificationModal() {
  const title = prompt('Enter Notification Title:');
  if (!title) return;
  const message = prompt('Enter Alert Message Body:');
  if (!message) return;
  const recipient = prompt('Recipient Phone (or enter "all" for broadcast):', 'all');
  if (!recipient) return;

  fetch('/api/v1/notifications/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient_phone: recipient, title, message, priority: 'high', type: 'system' }),
  })
    .then(r => r.json())
    .then(d => {
      showAdminToast('In-App Notification dispatched.', 'success');
      if (typeof fetchNotifications === 'function') fetchNotifications();
    })
    .catch(err => {
      console.error(err);
      showAdminToast('Failed to dispatch alert.', 'danger');
    });
}

// -----------------------------------------------------------------------------
// Toast Notifications
// -----------------------------------------------------------------------------
function showAdminToast(message, type = 'success') {
  const container = document.getElementById('adminToastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `admin-toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✓' : (type === 'danger' ? '✕' : 'ℹ')}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button type="button" class="toast-close" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
