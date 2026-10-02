// ================= DONOR PERSONAL DASHBOARD SCRIPT =================
document.addEventListener('DOMContentLoaded', () => {
  // Navigation & Tab Switching
  const navItems = document.querySelectorAll('.donor-nav-item');
  const sections = document.querySelectorAll('.dashboard-content-section');
  const mobileSidebar = document.getElementById('donorSidebar');
  const mobileToggleBtn = document.getElementById('mobileSidebarToggle');
  const availabilityToggle = document.getElementById('availability-toggle');
  const availabilityState = document.getElementById('availability-state');
  const availabilitySaveStatus = document.getElementById('availability-save-status');
  const availabilityPreferencesForm = document.getElementById('availability-preferences-form');
  const unavailabilityMode = document.getElementById('unavailability-mode');
  const temporaryUntilField = document.getElementById('temporary-unavailable-field');
  const scheduledStartField = document.getElementById('scheduled-start-field');
  const scheduledEndField = document.getElementById('scheduled-end-field');

  function updateUnavailabilityFields() {
    if (!unavailabilityMode) return;
    const mode = unavailabilityMode.value;
    if (temporaryUntilField) temporaryUntilField.hidden = mode !== 'temporary';
    if (scheduledStartField) scheduledStartField.hidden = mode !== 'scheduled';
    if (scheduledEndField) scheduledEndField.hidden = mode !== 'scheduled';
  }

  if (unavailabilityMode) {
    unavailabilityMode.addEventListener('change', updateUnavailabilityFields);
    updateUnavailabilityFields();
  }

  function renderAvailabilityStatus(result) {
    availabilityState.textContent = result.matching_status;
    availabilityState.classList.toggle('is-available', result.is_matchable);
  }

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

  if (availabilityToggle && availabilityState && availabilitySaveStatus) {
    availabilityToggle.addEventListener('change', async () => {
      const previousValue = !availabilityToggle.checked;
      availabilityToggle.disabled = true;
      availabilitySaveStatus.textContent = 'Saving availability...';

      try {
        const response = await fetch('/api/v1/donor/availability', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_available: availabilityToggle.checked })
        });
        if (!response.ok) throw new Error('Availability could not be saved.');

        const result = await response.json();
        availabilityToggle.checked = result.is_available;
        renderAvailabilityStatus(result);
        availabilitySaveStatus.textContent = 'Availability saved.';
      } catch (error) {
        availabilityToggle.checked = previousValue;
        availabilitySaveStatus.textContent = error.message;
      } finally {
        availabilityToggle.disabled = false;
      }
    });
  }

  if (availabilityPreferencesForm && availabilityToggle && availabilityState && availabilitySaveStatus) {
    availabilityPreferencesForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const mode = unavailabilityMode.value;
      const payload = {
        is_available: availabilityToggle.checked,
        unavailability_mode: mode,
        temporary_unavailable_until: mode === 'temporary'
          ? document.getElementById('temporary-unavailable-until').value || null
          : null,
        scheduled_unavailable_start: mode === 'scheduled'
          ? document.getElementById('scheduled-unavailable-start').value || null
          : null,
        scheduled_unavailable_end: mode === 'scheduled'
          ? document.getElementById('scheduled-unavailable-end').value || null
          : null,
        emergency_contact_preference: document.getElementById('emergency-contact-preference').value
      };
      const saveButton = availabilityPreferencesForm.querySelector('button[type="submit"]');
      saveButton.disabled = true;
      availabilitySaveStatus.textContent = 'Saving preferences...';

      try {
        const response = await fetch('/api/v1/donor/availability', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Preferences could not be saved.');
        renderAvailabilityStatus(result);
        availabilitySaveStatus.textContent = 'Preferences saved.';
      } catch (error) {
        availabilitySaveStatus.textContent = error.message;
      } finally {
        saveButton.disabled = false;
      }
    });
  }

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

    // Update URL hash without jump
    if (history.pushState) {
      history.pushState(null, null, `#${cleanId}`);
    } else {
      location.hash = `#${cleanId}`;
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Bind clicks on sidebar items
  navItems.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-target') || btn.getAttribute('href');
      activateSection(target);
    });
  });

  // Check URL hash on load
  if (window.location.hash) {
    activateSection(window.location.hash);
  } else {
    activateSection('section-personal-dashboard');
  }

  // Mobile sidebar drawer toggle
  if (mobileToggleBtn && mobileSidebar) {
    mobileToggleBtn.addEventListener('click', () => {
      mobileSidebar.classList.toggle('mobile-open');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (mobileSidebar.classList.contains('mobile-open')) {
        if (!mobileSidebar.contains(e.target) && !mobileToggleBtn.contains(e.target)) {
          mobileSidebar.classList.remove('mobile-open');
        }
      }
    });
  }

  window.activateSection = activateSection;
  window.showToast = showToast;
});
