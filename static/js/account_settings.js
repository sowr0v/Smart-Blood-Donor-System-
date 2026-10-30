(() => {
  const form = document.getElementById('accountProfileForm');
  if (!form) return;

  const status = document.getElementById('accountSettingsStatus');
  const currentPhone = document.getElementById('accountCurrentPhone');
  const newPhone = document.getElementById('accountNewPhone');
  const otpCode = document.getElementById('accountPhoneOtp');
  const requestButton = document.getElementById('requestPhoneOtp');
  const verifyButton = document.getElementById('verifyPhoneOtp');

  function showStatus(message, isError = false) {
    if (!status) return;
    status.textContent = message;
    status.style.color = isError ? 'var(--danger-red, #b91c1c)' : 'var(--success-green, #15803d)';
  }

  async function sendRequest(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((item) => item.msg).join(', ')
        : data.detail;
      throw new Error(detail || 'The request could not be completed.');
    }
    return data;
  }

  async function loadProfile() {
    try {
      const data = await sendRequest('/api/v1/account/profile');
      const profile = data.profile;
      document.getElementById('accountName').value = profile.name || '';
      document.getElementById('accountEmail').value = profile.email || '';
      document.getElementById('accountDistrict').value = profile.district || '';
      document.getElementById('accountArea').value = profile.area || '';
      document.getElementById('accountAddress').value = profile.address || '';
      if (currentPhone) currentPhone.value = profile.phone || '';
    } catch (error) {
      showStatus(error.message || 'Could not load your account information.', true);
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    try {
      const data = await sendRequest('/api/v1/account/profile', {
        method: 'PUT',
        body: JSON.stringify({
          name: document.getElementById('accountName').value.trim(),
          email: document.getElementById('accountEmail').value.trim(),
          district: document.getElementById('accountDistrict').value.trim(),
          area: document.getElementById('accountArea').value.trim(),
          address: document.getElementById('accountAddress').value.trim()
        })
      });
      showStatus(data.message || 'Personal information saved.');
    } catch (error) {
      showStatus(error.message || 'Could not save your personal information.', true);
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });

  if (requestButton) {
    requestButton.addEventListener('click', async () => {
      requestButton.disabled = true;
      try {
        const data = await sendRequest('/api/v1/account/phone-update/request', {
          method: 'POST',
          body: JSON.stringify({ phone: newPhone?.value.trim() || '' })
        });
        showStatus(data.message || 'Verification code sent.');
      } catch (error) {
        showStatus(error.message || 'Could not send the verification code.', true);
      } finally {
        requestButton.disabled = false;
      }
    });
  }

  if (verifyButton) {
    verifyButton.addEventListener('click', async () => {
      verifyButton.disabled = true;
      try {
        const data = await sendRequest('/api/v1/account/phone-update/verify', {
          method: 'POST',
          body: JSON.stringify({ code: otpCode?.value.trim() || '' })
        });
        if (currentPhone) currentPhone.value = data.phone || '';
        if (newPhone) newPhone.value = '';
        if (otpCode) otpCode.value = '';
        showStatus(data.message || 'Phone number verified and updated.');
      } catch (error) {
        showStatus(error.message || 'Could not verify the phone number.', true);
      } finally {
        verifyButton.disabled = false;
      }
    });
  }

  loadProfile();
})();
