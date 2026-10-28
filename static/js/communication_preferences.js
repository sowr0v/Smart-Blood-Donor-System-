(() => {
  const saveButton = document.getElementById('saveCommunicationPreferences');
  if (!saveButton) return;

  const status = document.getElementById('communicationPreferencesStatus');
  const frequency = document.getElementById('communicationFrequency');
  const channelInputs = Array.from(
    document.querySelectorAll('[data-communication-channel]')
  );
  const alertInputs = Array.from(
    document.querySelectorAll('[data-communication-alert]')
  );

  function showStatus(message, isError = false) {
    if (!status) return;
    status.textContent = message;
    status.style.color = isError
      ? 'var(--danger-red, #b91c1c)'
      : 'var(--success-green, #15803d)';
  }

  function applyPreferences(preferences) {
    channelInputs.forEach((input) => {
      const channel = input.dataset.communicationChannel;
      if (channel && typeof preferences.channels?.[channel] === 'boolean') {
        input.checked = preferences.channels[channel];
      }
    });
    alertInputs.forEach((input) => {
      const alertType = input.dataset.communicationAlert;
      if (alertType && typeof preferences.alert_types?.[alertType] === 'boolean') {
        input.checked = preferences.alert_types[alertType];
      }
    });
    const criticalAlert = alertInputs.find(
      (input) => input.dataset.communicationAlert === 'critical_emergency'
    );
    if (criticalAlert) {
      criticalAlert.checked = true;
      criticalAlert.disabled = true;
    }
    if (frequency && preferences.frequency) frequency.value = preferences.frequency;
  }

  async function loadPreferences() {
    try {
      const response = await fetch('/api/v1/account/communication-preferences', {
        credentials: 'same-origin',
        cache: 'no-store'
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        throw new Error(result.detail || 'Could not load communication preferences.');
      }
      applyPreferences(result.preferences);
      if (result.preferences.privacy_restrictions?.length) {
        showStatus('Phone and WhatsApp channels are disabled by your current contact privacy settings.', true);
      }
    } catch (error) {
      showStatus(error.message || 'Could not load communication preferences.', true);
    }
  }

  let saveInProgress = false;

  async function savePreferences() {
    if (saveInProgress) return;
    saveInProgress = true;
    saveButton.disabled = true;
    const requestedPreferences = {
      channels: Object.fromEntries(
        channelInputs.map((input) => [input.dataset.communicationChannel, input.checked])
      ),
      alert_types: Object.fromEntries(
        alertInputs.map((input) => [input.dataset.communicationAlert, input.checked])
      ),
      frequency: frequency?.value || 'immediate'
    };
    requestedPreferences.alert_types.critical_emergency = true;

    try {
      const response = await fetch('/api/v1/account/communication-preferences', {
        method: 'PUT',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestedPreferences)
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        throw new Error(result.detail || 'Could not save communication preferences.');
      }
      applyPreferences(result.preferences);
      showStatus(result.message || 'Communication preferences saved.');
    } catch (error) {
      showStatus(error.message || 'Could not save communication preferences.', true);
    } finally {
      saveButton.disabled = false;
      saveInProgress = false;
    }
  }

  saveButton.addEventListener('click', savePreferences);
  const donorSaveButton = document.getElementById('saveSettingsBtn');
  if (donorSaveButton) donorSaveButton.addEventListener('click', savePreferences);
  const seekerSettingsForm = document.getElementById('seekerSettingsForm');
  if (seekerSettingsForm) {
    seekerSettingsForm.addEventListener('submit', savePreferences);
  }

  loadPreferences();
})();
