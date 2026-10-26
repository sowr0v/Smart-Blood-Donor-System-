/**
 * Admin User Management & Role Control Interactive Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
  let allUsers = [];
  let currentUser = null;

  // DOM Elements
  const searchInput = document.getElementById('adminUserSearch');
  const roleFilter = document.getElementById('adminRoleFilter');
  const statusFilter = document.getElementById('adminStatusFilter');
  const userTableBody = document.getElementById('adminUserTableBody');
  const refreshBtn = document.getElementById('btnRefreshUsers');
  const auditTableBody = document.getElementById('adminAuditTableBody');

  // Metrics elements
  const metricTotalUsers = document.getElementById('metricTotalUsers');
  const metricActiveUsers = document.getElementById('metricActiveUsers');
  const metricSuspendedUsers = document.getElementById('metricSuspendedUsers');
  const metricAdminCount = document.getElementById('metricAdminCount');

  // Modals
  const userDetailsModal = document.getElementById('userDetailsModal');
  const editRoleModal = document.getElementById('editRoleModal');
  const editStatusModal = document.getElementById('editStatusModal');
  const createUserModal = document.getElementById('createUserModal');

  // Nav Items
  const navItems = document.querySelectorAll('.admin-nav-item');
  const sections = document.querySelectorAll('.admin-section');

  // Sidebar navigation switching
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(n => n.classList.remove('active'));
      sections.forEach(s => s.classList.remove('active'));

      item.classList.add('active');
      const targetId = item.getAttribute('data-target');
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.classList.add('active');
      }

      if (targetId === 'section-audit-logs') {
        fetchAuditLogs();
      } else if (targetId === 'section-stock-thresholds') {
        loadAdminStockAlerts();
      }
    });
  });

  // Facility stock alert functions
  const stockTableBody = document.getElementById("adminStockAlertsTableBody");
  const stockSummary = document.getElementById("adminStockAlertSummary");
  const stockStatus = document.getElementById("bloodStockAdminStatus");

  async function loadAdminStockAlerts() {
    if (!stockTableBody) return;
    try {
      const response = await fetch("/api/v1/admin/facility/inventory/alerts", { cache: "no-store" });
      const result = await response.json();
      if (!response.ok || result.status !== "success") {
        throw new Error(result.detail || "Could not load facility stock alerts.");
      }
      stockTableBody.innerHTML = '';
      const activeAlerts = (result.facilities || []).flatMap((facility) =>
        (facility.alerts || [])
          .filter((alert) => alert.status === "active")
          .map((alert) => ({ facility: facility.facility_name, ...alert }))
      );
      if (stockSummary) {
        stockSummary.textContent = `${result.active_count} active low stock alert(s) across ${result.facility_count} facility account(s).`;
      }
      if (activeAlerts.length === 0) {
        stockTableBody.innerHTML = '<tr><td colspan="5" style="padding: 14px; text-align: center; color: var(--admin-text-muted);">No facilities are currently at or below the minimum stock threshold.</td></tr>';
        return;
      }
      activeAlerts.forEach((item) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${escapeHtml(item.facility)}</td>
          <td><strong style="color: #E11D48;">${escapeHtml(item.blood_group)}</strong></td>
          <td>${item.quantity} units</td>
          <td>${item.threshold} units</td>
          <td><span class="badge-status status-suspended"><span class="status-dot-indicator"></span>Low Stock</span></td>
        `;
        stockTableBody.appendChild(row);
      });
    } catch (err) {
      if (stockSummary) stockSummary.textContent = err.message;
    }
  }

  document.querySelectorAll("[data-save-stock-threshold]").forEach((button) => {
    button.addEventListener("click", async () => {
      const group = button.getAttribute("data-save-stock-threshold");
      const input = document.querySelector(`[data-stock-threshold="${group}"]`);
      if (!input) return;
      const threshold = parseInt(input.value, 10);
      try {
        const response = await fetch(`/api/v1/admin/blood-stock-thresholds/${encodeURIComponent(group)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ threshold }),
        });
        const result = await response.json();
        if (!response.ok || result.status !== "success") {
          throw new Error(result.detail || "Could not update threshold.");
        }
        showToast(`Minimum stock threshold for ${group} updated to ${threshold} units.`, 'success');
        loadAdminStockAlerts();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  });

  // Fetch users with current filters
  async function fetchUsers() {
    try {
      const q = encodeURIComponent(searchInput ? searchInput.value.trim() : '');
      const r = encodeURIComponent(roleFilter ? roleFilter.value : 'all');
      const s = encodeURIComponent(statusFilter ? statusFilter.value : 'all');

      const res = await fetch(`/api/v1/admin/users?query=${q}&role=${r}&status=${s}`);
      if (!res.ok) {
        if (res.status === 403) {
          showToast('Unauthorized: Administrative privileges required.', 'error');
        }
        return;
      }
      const data = await res.json();
      allUsers = data.users || [];

      // Update metrics
      if (data.metrics) {
        if (metricTotalUsers) metricTotalUsers.textContent = data.metrics.total_users;
        if (metricActiveUsers) metricActiveUsers.textContent = data.metrics.active_users;
        if (metricSuspendedUsers) metricSuspendedUsers.textContent = data.metrics.suspended_users;
        if (metricAdminCount) metricAdminCount.textContent = data.metrics.admin_count;
      }

      renderUserTable(allUsers);
    } catch (err) {
      console.error('Failed to load admin users:', err);
      showToast('Error loading user accounts.', 'error');
    }
  }

  // Render Table Rows
  function renderUserTable(users) {
    if (!userTableBody) return;
    userTableBody.innerHTML = '';

    if (!users || users.length === 0) {
      userTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 40px; color: var(--admin-text-muted);">
            <svg style="width: 48px; height: 48px; margin: 0 auto 12px; display: block; opacity: 0.5;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <p style="font-weight: 600; font-size: 1rem;">No users found matching the filter criteria.</p>
          </td>
        </tr>
      `;
      return;
    }

    users.forEach(u => {
      const tr = document.createElement('tr');
      const initial = (u.name || 'U')[0].toUpperCase();
      const roleBadgeClass = `role-${u.role}`;
      const statusBadgeClass = `status-${u.status}`;

      tr.innerHTML = `
        <td>
          <div class="user-name-cell">
            <div class="user-avatar-small">${initial}</div>
            <div class="user-text-info">
              <strong>${escapeHtml(u.name || 'User')}</strong>
              <span>${escapeHtml(u.phone)}</span>
            </div>
          </div>
        </td>
        <td>
          <span class="badge-role ${roleBadgeClass}">
            ${escapeHtml(u.role.toUpperCase())}
          </span>
        </td>
        <td>
          <span class="badge-status ${statusBadgeClass}">
            <span class="status-dot-indicator"></span>
            ${escapeHtml(u.status.toUpperCase())}
          </span>
        </td>
        <td>
          <span style="font-weight: 600; color: #E11D48;">${escapeHtml(u.blood_group || 'N/A')}</span>
        </td>
        <td>
          <span style="font-size: 0.84rem; color: var(--admin-text-muted);">
            ${u.org_name ? escapeHtml(u.org_name) : (u.address ? escapeHtml(u.address) : 'Standard Member')}
          </span>
        </td>
        <td>
          <div class="table-actions">
            <button type="button" class="btn-action-icon btn-view-user" data-phone="${escapeHtml(u.phone)}" title="View Account Details">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              View
            </button>
            <button type="button" class="btn-action-icon btn-change-role" data-phone="${escapeHtml(u.phone)}" data-role="${escapeHtml(u.role)}" title="Change Assigned Role">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              Role
            </button>
            <button type="button" class="btn-action-icon btn-change-status" data-phone="${escapeHtml(u.phone)}" data-status="${escapeHtml(u.status)}" title="Manage Account Status">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              Status
            </button>
          </div>
        </td>
      `;

      userTableBody.appendChild(tr);
    });

    // Attach event listeners to buttons
    document.querySelectorAll('.btn-view-user').forEach(btn => {
      btn.addEventListener('click', () => openUserDetails(btn.getAttribute('data-phone')));
    });

    document.querySelectorAll('.btn-change-role').forEach(btn => {
      btn.addEventListener('click', () => openEditRole(btn.getAttribute('data-phone'), btn.getAttribute('data-role')));
    });

    document.querySelectorAll('.btn-change-status').forEach(btn => {
      btn.addEventListener('click', () => openEditStatus(btn.getAttribute('data-phone'), btn.getAttribute('data-status')));
    });
  }

  // Open User Details Modal
  async function openUserDetails(phone) {
    try {
      const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}`);
      if (!res.ok) {
        showToast('Failed to load user details.', 'error');
        return;
      }
      const data = await res.json();
      const u = data.user;
      currentUser = u;

      document.getElementById('detailUserPhone').textContent = u.phone;
      document.getElementById('detailUserName').textContent = u.name;
      document.getElementById('detailUserRole').textContent = u.role.toUpperCase();
      document.getElementById('detailUserStatus').textContent = u.status.toUpperCase();
      document.getElementById('detailUserBlood').textContent = u.blood_group || 'N/A';
      document.getElementById('detailUserOrg').textContent = u.org_name || 'None';
      document.getElementById('detailUserAddress').textContent = u.address || 'Not specified';

      // Audit list
      const auditContainer = document.getElementById('detailUserAuditList');
      if (auditContainer) {
        auditContainer.innerHTML = '';
        if (data.audit_history && data.audit_history.length > 0) {
          data.audit_history.forEach(item => {
            const timeStr = new Date(item.created_at * 1000).toLocaleString();
            const div = document.createElement('div');
            div.style.padding = '8px 0';
            div.style.borderBottom = '1px solid var(--admin-border)';
            div.style.fontSize = '0.82rem';
            div.innerHTML = `
              <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <strong style="color: var(--admin-primary);">${escapeHtml(item.action)}</strong>
                <span style="color: var(--admin-text-muted);">${timeStr}</span>
              </div>
              <div style="color: var(--admin-text-main);">${escapeHtml(item.details)}</div>
              <div style="color: var(--admin-text-muted); font-size: 0.75rem;">By: ${escapeHtml(item.admin_phone)}</div>
            `;
            auditContainer.appendChild(div);
          });
        } else {
          auditContainer.innerHTML = '<p style="color: var(--admin-text-muted); font-size: 0.85rem; padding: 8px 0;">No prior administrative logs for this account.</p>';
        }
      }

      userDetailsModal.classList.add('open');
    } catch (err) {
      console.error(err);
      showToast('Error opening user details.', 'error');
    }
  }

  // Open Edit Role Modal
  function openEditRole(phone, currentRole) {
    document.getElementById('editRolePhone').value = phone;
    document.getElementById('editRoleTargetPhoneDisplay').textContent = phone;
    document.getElementById('editRoleSelect').value = currentRole;
    document.getElementById('editRoleReason').value = '';
    editRoleModal.classList.add('open');
  }

  // Handle Edit Role Submit
  const editRoleForm = document.getElementById('editRoleForm');
  if (editRoleForm) {
    editRoleForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const phone = document.getElementById('editRolePhone').value;
      const role = document.getElementById('editRoleSelect').value;
      const reason = document.getElementById('editRoleReason').value;

      try {
        const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}/role`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role, reason }),
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || 'Failed to update role.', 'error');
          return;
        }

        showToast(data.message || 'Role updated successfully!', 'success');
        editRoleModal.classList.remove('open');
        fetchUsers();
      } catch (err) {
        console.error(err);
        showToast('Error modifying user role.', 'error');
      }
    });
  }

  // Open Edit Status Modal
  function openEditStatus(phone, currentStatus) {
    document.getElementById('editStatusPhone').value = phone;
    document.getElementById('editStatusTargetPhoneDisplay').textContent = phone;
    document.getElementById('editStatusSelect').value = currentStatus;
    document.getElementById('editStatusReason').value = '';
    editStatusModal.classList.add('open');
  }

  // Handle Edit Status Submit
  const editStatusForm = document.getElementById('editStatusForm');
  if (editStatusForm) {
    editStatusForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const phone = document.getElementById('editStatusPhone').value;
      const status = document.getElementById('editStatusSelect').value;
      const reason = document.getElementById('editStatusReason').value;

      try {
        const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(phone)}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status, reason }),
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || 'Failed to update account status.', 'error');
          return;
        }

        showToast(data.message || 'Account status updated!', 'success');
        editStatusModal.classList.remove('open');
        fetchUsers();
      } catch (err) {
        console.error(err);
        showToast('Error updating account status.', 'error');
      }
    });
  }

  // Create New User Form
  const btnOpenCreateUser = document.getElementById('btnOpenCreateUser');
  if (btnOpenCreateUser) {
    btnOpenCreateUser.addEventListener('click', () => {
      createUserModal.classList.add('open');
    });
  }

  const createUserForm = document.getElementById('createUserForm');
  if (createUserForm) {
    createUserForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const phone = document.getElementById('createPhone').value.trim();
      const name = document.getElementById('createName').value.trim();
      const role = document.getElementById('createRole').value;
      const bloodGroup = document.getElementById('createBloodGroup').value;
      const status = document.getElementById('createStatus').value;
      const password = document.getElementById('createPassword').value;

      try {
        const res = await fetch('/api/v1/admin/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            phone,
            name,
            role,
            blood_group: bloodGroup,
            status,
            password,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || 'Failed to create user.', 'error');
          return;
        }

        showToast('User created successfully!', 'success');
        createUserModal.classList.remove('open');
        createUserForm.reset();
        fetchUsers();
      } catch (err) {
        console.error(err);
        showToast('Error creating user account.', 'error');
      }
    });
  }

  // Fetch Global Audit Logs
  async function fetchAuditLogs() {
    if (!auditTableBody) return;
    try {
      const res = await fetch('/api/v1/admin/audit-logs?limit=50');
      if (!res.ok) return;
      const data = await res.json();
      const logs = data.logs || [];

      auditTableBody.innerHTML = '';
      if (logs.length === 0) {
        auditTableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; padding: 30px; color: var(--admin-text-muted);">
              No administrative actions recorded yet.
            </td>
          </tr>
        `;
        return;
      }

      logs.forEach(log => {
        const tr = document.createElement('tr');
        const timeStr = new Date(log.created_at * 1000).toLocaleString();
        let actionClass = 'created';
        if (log.action.includes('ROLE')) actionClass = 'role';
        if (log.action.includes('STATUS')) actionClass = 'status';

        tr.innerHTML = `
          <td><span style="font-size: 0.82rem; color: var(--admin-text-muted);">${timeStr}</span></td>
          <td><strong>${escapeHtml(log.admin_phone)}</strong></td>
          <td><span class="audit-log-badge ${actionClass}">${escapeHtml(log.action)}</span></td>
          <td><span>${escapeHtml(log.target_phone)}</span></td>
          <td style="color: var(--admin-text-main);">${escapeHtml(log.details)}</td>
        `;
        auditTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    }
  }

  // Close modals when clicking backdrop or close button
  document.querySelectorAll('.admin-modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('open');
      }
    });
  });

  document.querySelectorAll('.btn-close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.admin-modal-backdrop');
      if (modal) modal.classList.remove('open');
    });
  });

  // Filter & Search input handlers
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(fetchUsers, 300);
    });
  }

  if (roleFilter) {
    roleFilter.addEventListener('change', fetchUsers);
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', fetchUsers);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', fetchUsers);
  }

  // Toast notification utility
  function showToast(message, type = 'success') {
    const container = document.getElementById('adminToastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `admin-toast ${type}`;
    toast.innerHTML = `
      <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s ease';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // Helper escape function
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Initial load
  fetchUsers();
});
