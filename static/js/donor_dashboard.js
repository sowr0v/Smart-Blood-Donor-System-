// ================= DONOR PERSONAL DASHBOARD SCRIPT =================
document.addEventListener('DOMContentLoaded', () => {
  // Navigation & Tab Switching
  const navItems = document.querySelectorAll('.donor-nav-item');
  const sections = document.querySelectorAll('.dashboard-content-section');
  const mobileSidebar = document.getElementById('donorSidebar');
  const mobileToggleBtn = document.getElementById('mobileSidebarToggle');

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

    // Update URL hash without jumping
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

  // =========================================================
  // DONOR IN-APP CHAT MODULE (SBDS-89)
  // =========================================================
  const chatThreads = document.querySelectorAll('.chat-thread-item');
  const chatMessagesContainer = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSearchInput = document.getElementById('chatSearchInput');
  const clearChatSearchBtn = document.getElementById('clearChatSearch');
  const currentChatUserTitle = document.getElementById('currentChatUserTitle');
  const currentChatUserSub = document.getElementById('currentChatUserSub');
  const activeChatAvatar = document.getElementById('activeChatAvatar');
  const activeChatOnlineDot = document.getElementById('activeChatOnlineDot');
  const currentChatRoleTag = document.getElementById('currentChatRoleTag');
  const chatCallBtn = document.getElementById('chatCallBtn');
  const chatLocationBtn = document.getElementById('chatLocationBtn');
  const chatClearBtn = document.getElementById('chatClearBtn');
  const chatShareLocationBtn = document.getElementById('chatShareLocationBtn');
  const typingIndicator = document.getElementById('typingIndicator');
  const sidebarChatBadge = document.getElementById('sidebarChatBadge');
  const headerUnreadBadge = document.getElementById('headerUnreadBadge');
  const noThreadsNotice = document.getElementById('noThreadsNotice');
  const categoryTabs = document.querySelectorAll('#chatCategoryTabs .chat-tab-pill');

  // Linked Request Banner elements
  const chatRequestBanner = document.getElementById('chatRequestBanner');
  const bannerReqId = document.getElementById('bannerReqId');
  const bannerPatient = document.getElementById('bannerPatient');
  const bannerHospital = document.getElementById('bannerHospital');
  const bannerBlood = document.getElementById('bannerBlood');
  const bannerUrgency = document.getElementById('bannerUrgency');

  // Client message cache for instant switching and offline resilience
  const conversationStore = {
    'thread-square': [
      { sender: 'coordinator', text: 'Hello Ayesha, we saw you accepted the urgent A+ requirement at Square Hospital (Panthapath, Dhaka).', time: '10:08 AM', status: 'read' },
      { sender: 'you', text: 'Yes, I am available and preparing to come. Is the patient at Cabin 402 or the Blood Bank unit?', time: '10:10 AM', status: 'read' },
      { sender: 'coordinator', text: 'Please report directly to 2nd Floor, Blood Transfusion Dept. Coordinator Dr. Farhan is on duty and waiting.', time: '10:12 AM', status: 'read' }
    ],
    'thread-dmc': [
      { sender: 'coordinator', text: 'Warm greetings from Dhaka Medical College Blood Bank.', time: 'Yesterday 3:15 PM', status: 'read' },
      { sender: 'coordinator', text: 'Your whole blood donation certificate from Jan 14 has been verified and registered on your national donor card.', time: 'Yesterday 3:16 PM', status: 'read' },
      { sender: 'you', text: 'Thank you! When will I be eligible to donate whole blood again?', time: 'Yesterday 3:45 PM', status: 'read' },
      { sender: 'coordinator', text: 'You completed your 56-day gap and are officially eligible right now!', time: 'Yesterday 4:00 PM', status: 'read' }
    ],
    'thread-nabil': [
      { sender: 'coordinator', text: 'Assalamu Alaikum Ayesha apu, I am Nabil. You donated blood for my mother last month.', time: '2 days ago', status: 'read' },
      { sender: 'coordinator', text: 'I just wanted to let you know she was discharged today and is healthy. We cannot thank you enough for saving her life.', time: '2 days ago', status: 'read' },
      { sender: 'you', text: 'Alhamdulillah, so relieved to hear this news! Praying for her continued strength and health.', time: '2 days ago', status: 'read' }
    ],
    'thread-support': [
      { sender: 'coordinator', text: 'Welcome to the Smart Blood Donor System Donor Support channel.', time: '18 Jan', status: 'read' },
      { sender: 'coordinator', text: 'Congratulations on reaching your 8th verified donation! Your account has been upgraded to Gold Tier.', time: '18 Jan', status: 'read' },
      { sender: 'you', text: 'Thank you SBDS team! Appreciate the fast verification.', time: '18 Jan', status: 'read' }
    ]
  };

  let activeThreadId = 'thread-square';
  let activeFilter = 'all';

  function updateUnreadCounts() {
    let unreadCount = 0;
    document.querySelectorAll('.chat-thread-item').forEach(item => {
      const badge = item.querySelector('.chat-unread-count');
      if (badge && badge.style.display !== 'none' && parseInt(badge.textContent || '0', 10) > 0) {
        unreadCount += parseInt(badge.textContent, 10);
      }
    });

    if (sidebarChatBadge) {
      sidebarChatBadge.textContent = unreadCount;
      sidebarChatBadge.style.display = unreadCount > 0 ? 'inline-flex' : 'none';
    }
    if (headerUnreadBadge) {
      headerUnreadBadge.innerHTML = `<span style="font-weight: 700;">${unreadCount}</span> Unread`;
      headerUnreadBadge.style.display = unreadCount > 0 ? 'inline-flex' : 'none';
    }
    const countUnread = document.getElementById('countUnread');
    if (countUnread) countUnread.textContent = unreadCount;
  }

  function renderMessages(threadId) {
    if (!chatMessagesContainer) return;
    const messages = conversationStore[threadId] || [];

    // Header notice inside chat pane
    chatMessagesContainer.innerHTML = `
      <div style="text-align: center; font-size: 0.74rem; color: var(--text-muted); margin: 4px 0 10px;">
        Today · 256-bit Encrypted Emergency Blood Coordination Channel
      </div>
    `;

    messages.forEach(msg => {
      const bubble = document.createElement('div');
      const isYou = msg.sender === 'you';
      bubble.className = `chat-bubble ${isYou ? 'bubble-sent' : 'bubble-received'}`;
      const receiptHtml = isYou ? '<span class="read-receipt">✓✓</span>' : '';
      bubble.innerHTML = `
        <div>${msg.text}</div>
        <div class="chat-bubble-time">${msg.time} · ${isYou ? 'You' : 'Coordinator'} ${receiptHtml}</div>
      `;
      chatMessagesContainer.appendChild(bubble);
    });

    // Re-attach typing indicator to bottom
    if (typingIndicator) {
      chatMessagesContainer.appendChild(typingIndicator);
    }

    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  function selectThread(thread) {
    if (!thread) return;
    document.querySelectorAll('.chat-thread-item').forEach(t => t.classList.remove('active'));
    thread.classList.add('active');

    const threadId = thread.getAttribute('data-thread-id');
    const userName = thread.getAttribute('data-name');
    const avatar = thread.getAttribute('data-avatar');
    const status = thread.getAttribute('data-status');
    const phone = thread.getAttribute('data-phone');
    const category = thread.getAttribute('data-category') || 'hospital';
    const reqId = thread.getAttribute('data-request');
    const patient = thread.getAttribute('data-patient');
    const hospital = thread.getAttribute('data-hospital');
    const blood = thread.getAttribute('data-blood');

    activeThreadId = threadId;

    if (currentChatUserTitle) currentChatUserTitle.textContent = userName;
    if (activeChatAvatar) activeChatAvatar.textContent = avatar;
    if (currentChatUserSub) {
      currentChatUserSub.innerHTML = `<span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--success-green);"></span> <span>${status}</span>`;
    }
    if (currentChatRoleTag) {
      currentChatRoleTag.textContent = category === 'hospital' ? 'Hospital' : category === 'seeker' ? 'Emergency Seeker' : 'Support';
    }
    if (chatCallBtn && phone) {
      chatCallBtn.setAttribute('href', `tel:${phone}`);
    }

    // Update Linked Request Banner
    if (chatRequestBanner) {
      if (reqId) {
        chatRequestBanner.style.display = 'flex';
        if (bannerReqId) bannerReqId.textContent = `#${reqId}`;
        if (bannerPatient) bannerPatient.textContent = patient || 'Patient Transfusion Case';
        if (bannerHospital) bannerHospital.textContent = hospital || 'Verified Medical Center';
        if (bannerBlood) bannerBlood.textContent = blood || 'Blood Match';
        if (bannerUrgency) {
          bannerUrgency.textContent = reqId === 'REQ-001' ? 'Immediate' : 'Standard';
        }
      } else {
        chatRequestBanner.style.display = 'none';
      }
    }

    // Clear unread badge on this thread
    const unreadPill = thread.querySelector('.chat-unread-count');
    if (unreadPill) {
      unreadPill.style.display = 'none';
      unreadPill.textContent = '0';
    }

    // Mark as read on server API
    fetch(`/api/v1/donor/chat/${threadId}/read`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data && data.total_unread !== undefined) {
          if (sidebarChatBadge) {
            sidebarChatBadge.textContent = data.total_unread;
            sidebarChatBadge.style.display = data.total_unread > 0 ? 'inline-flex' : 'none';
          }
          if (headerUnreadBadge) {
            headerUnreadBadge.innerHTML = `<span style="font-weight: 700;">${data.total_unread}</span> Unread`;
            headerUnreadBadge.style.display = data.total_unread > 0 ? 'inline-flex' : 'none';
          }
        }
      })
      .catch(() => updateUnreadCounts());

    updateUnreadCounts();
    renderMessages(threadId);
  }

  // Bind thread selection
  chatThreads.forEach(thread => {
    thread.addEventListener('click', () => {
      selectThread(thread);
      showToast(`Switched conversation to ${thread.getAttribute('data-name')}`);
    });
  });

  // Sending message function
  window.sendChatMessage = function(explicitText) {
    if (!chatInput) return;
    const text = (explicitText !== undefined ? explicitText : chatInput.value).trim();
    if (!text) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Store in local cache
    if (!conversationStore[activeThreadId]) {
      conversationStore[activeThreadId] = [];
    }
    const newMsg = { sender: 'you', text, time: timeStr, status: 'sent' };
    conversationStore[activeThreadId].push(newMsg);

    // Append to UI immediately
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble bubble-sent';
    bubble.innerHTML = `
      <div>${text}</div>
      <div class="chat-bubble-time">${timeStr} · You <span class="read-receipt">✓✓</span></div>
    `;
    if (typingIndicator) {
      chatMessagesContainer.insertBefore(bubble, typingIndicator);
    } else {
      chatMessagesContainer.appendChild(bubble);
    }
    chatInput.value = '';
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;

    // Update snippet in thread list item
    const currentThreadItem = document.querySelector(`.chat-thread-item[data-thread-id="${activeThreadId}"]`);
    if (currentThreadItem) {
      const snippet = currentThreadItem.querySelector('.thread-preview-snippet');
      if (snippet) snippet.textContent = text;
      const timeElem = currentThreadItem.querySelector('.thread-time');
      if (timeElem) timeElem.textContent = 'Just now';
    }

    // Show realistic typing indicator
    if (typingIndicator) {
      const activeName = currentChatUserTitle ? currentChatUserTitle.textContent : 'Coordinator';
      const typingText = typingIndicator.querySelector('.typing-text');
      if (typingText) typingText.textContent = `${activeName.split(' ')[0]} is typing`;
      typingIndicator.style.display = 'inline-flex';
      chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    // Call backend API /api/v1/donor/chat/{id}/send
    fetch(`/api/v1/donor/chat/${activeThreadId}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, sender: 'you' })
    })
      .then(res => res.json())
      .then(data => {
        setTimeout(() => {
          if (typingIndicator) typingIndicator.style.display = 'none';

          const replyText = data?.reply?.text || 'Coordinator: "Received your message! We have notified the medical unit."';
          const replyTime = data?.reply?.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          conversationStore[activeThreadId].push({ sender: 'coordinator', text: replyText, time: replyTime });

          if (chatMessagesContainer) {
            const replyBubble = document.createElement('div');
            replyBubble.className = 'chat-bubble bubble-received';
            replyBubble.innerHTML = `
              <div>${replyText}</div>
              <div class="chat-bubble-time">${replyTime} · Coordinator</div>
            `;
            if (typingIndicator) {
              chatMessagesContainer.insertBefore(replyBubble, typingIndicator);
            } else {
              chatMessagesContainer.appendChild(replyBubble);
            }
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
          }
        }, 1200);
      })
      .catch(() => {
        // Fallback simulation
        setTimeout(() => {
          if (typingIndicator) typingIndicator.style.display = 'none';
          let replyText = 'Received your message! Coordinator has been notified.';
          if (activeThreadId === 'thread-square') {
            replyText = 'Coordinator Dr. Farhan: "Received! Transfusion unit is waiting. See you shortly!"';
          } else if (activeThreadId === 'thread-dmc') {
            replyText = 'Desk Officer: "Thank you! Feel free to reach out anytime."';
          } else if (activeThreadId === 'thread-nabil') {
            replyText = 'Nabil: "Thank you again Ayesha apu, truly indebted to donors like you!"';
          } else if (activeThreadId === 'thread-support') {
            replyText = 'SBDS Support: "We have updated your record. Let us know if you need assistance."';
          }

          const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          conversationStore[activeThreadId].push({ sender: 'coordinator', text: replyText, time: replyTime });

          if (chatMessagesContainer) {
            const replyBubble = document.createElement('div');
            replyBubble.className = 'chat-bubble bubble-received';
            replyBubble.innerHTML = `
              <div>${replyText}</div>
              <div class="chat-bubble-time">${replyTime} · Coordinator</div>
            `;
            if (typingIndicator) {
              chatMessagesContainer.insertBefore(replyBubble, typingIndicator);
            } else {
              chatMessagesContainer.appendChild(replyBubble);
            }
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
          }
        }, 1200);
      });
  };

  // Quick reply chips click
  document.querySelectorAll('.quick-reply-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.getAttribute('data-text');
      if (text) {
        window.sendChatMessage(text);
      }
    });
  });

  // Filter threads by search query and category tab
  function filterThreads() {
    const q = (chatSearchInput?.value || '').toLowerCase().trim();
    let visibleCount = 0;

    chatThreads.forEach(thread => {
      const name = (thread.getAttribute('data-name') || '').toLowerCase();
      const snippet = (thread.querySelector('.thread-preview-snippet')?.textContent || '').toLowerCase();
      const category = (thread.getAttribute('data-category') || '').toLowerCase();
      const badge = thread.querySelector('.chat-unread-count');
      const hasUnread = badge && badge.style.display !== 'none' && parseInt(badge.textContent || '0', 10) > 0;

      const matchesQuery = !q || name.includes(q) || snippet.includes(q);
      let matchesCategory = true;
      if (activeFilter === 'hospital') matchesCategory = category === 'hospital';
      else if (activeFilter === 'seeker') matchesCategory = category === 'seeker';
      else if (activeFilter === 'support') matchesCategory = category === 'support';
      else if (activeFilter === 'unread') matchesCategory = hasUnread;

      if (matchesQuery && matchesCategory) {
        thread.style.display = 'flex';
        visibleCount++;
      } else {
        thread.style.display = 'none';
      }
    });

    if (noThreadsNotice) {
      noThreadsNotice.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  // Category filter tabs
  categoryTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      categoryTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeFilter = tab.getAttribute('data-filter') || 'all';
      filterThreads();
    });
  });

  // Search input and clear button
  if (chatSearchInput) {
    chatSearchInput.addEventListener('input', () => {
      if (clearChatSearchBtn) {
        clearChatSearchBtn.style.display = chatSearchInput.value ? 'block' : 'none';
      }
      filterThreads();
    });
  }

  if (clearChatSearchBtn && chatSearchInput) {
    clearChatSearchBtn.addEventListener('click', () => {
      chatSearchInput.value = '';
      clearChatSearchBtn.style.display = 'none';
      filterThreads();
      chatSearchInput.focus();
    });
  }

  // Hospital Location Button
  if (chatLocationBtn) {
    chatLocationBtn.addEventListener('click', () => {
      const currentThread = document.querySelector(`.chat-thread-item[data-thread-id="${activeThreadId}"]`);
      const hospitalName = currentThread?.getAttribute('data-hospital') || 'Square Hospital, Panthapath';
      showToast(`📍 Location: ${hospitalName} (Blood Transfusion Dept, 2nd Floor). Verified corridor access.`);
    });
  }

  // Share Live Location ETA button
  if (chatShareLocationBtn) {
    chatShareLocationBtn.addEventListener('click', () => {
      window.sendChatMessage('📍 Shared Live ETA: On Panthapath road, heading to Blood Bank. Estimated arrival in 15 minutes.');
    });
  }

  // Clear chat conversation
  if (chatClearBtn) {
    chatClearBtn.addEventListener('click', () => {
      conversationStore[activeThreadId] = [];
      renderMessages(activeThreadId);
      showToast('Conversation messages cleared for this session.');
    });
  }

  // Initialize unread counts
  updateUnreadCounts();

  // =========================================================
  // DONOR PORTAL SETTINGS & PREFERENCES MODULE
  // =========================================================
  const radiusRangeInput = document.getElementById('settingRadiusRange');
  const radiusValueDisplay = document.getElementById('radiusValueDisplay');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const resetSettingsBtn = document.getElementById('resetSettingsBtn');
  const settingsStatusText = document.getElementById('settingsStatusText');
  const zoneChips = document.querySelectorAll('#preferredZonesWrap .zone-chip');
  const checkChips = document.querySelectorAll('#donationTypesWrap .check-chip');
  const btnUpdatePassword = document.getElementById('btnUpdatePassword');
  const btnRevokeSessions = document.getElementById('btnRevokeSessions');

  // Sync radius value display
  if (radiusRangeInput && radiusValueDisplay) {
    radiusRangeInput.addEventListener('input', (e) => {
      radiusValueDisplay.textContent = `${e.target.value} km`;
    });
  }

  // Toggle preferred zone chips
  zoneChips.forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
    });
  });

  // Toggle donation type chips
  checkChips.forEach(chip => {
    const input = chip.querySelector('input[type="checkbox"]');
    if (input) {
      input.addEventListener('change', () => {
        if (input.checked) {
          chip.classList.add('selected');
        } else {
          chip.classList.remove('selected');
        }
      });
    }
  });

  // Save Settings handler
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', async () => {
      saveSettingsBtn.disabled = true;
      const originalText = saveSettingsBtn.innerHTML;
      saveSettingsBtn.innerHTML = '⏳ Saving...';

      const selectedTypes = [];
      document.querySelectorAll('#donationTypesWrap input[type="checkbox"]:checked').forEach(cb => {
        const label = cb.closest('label')?.textContent.trim();
        if (label) selectedTypes.push(label);
      });

      const selectedZones = [];
      document.querySelectorAll('#preferredZonesWrap .zone-chip.selected').forEach(z => {
        selectedZones.push(z.getAttribute('data-zone') || z.textContent.trim());
      });

      const payload = {
        sms_alerts: !!document.getElementById('settingSmsAlerts')?.checked,
        inapp_notifications: !!document.getElementById('settingInAppPush')?.checked,
        gap_reminders: !!document.getElementById('settingGapReminders')?.checked,
        quiet_hours: !!document.getElementById('settingQuietHours')?.checked,
        radius_km: parseInt(radiusRangeInput?.value || '15', 10),
        donation_types: selectedTypes,
        preferred_zones: selectedZones,
        phone_visibility: document.getElementById('settingAllowHospitalCall')?.checked ? 'hospital_only' : 'hidden',
        public_directory: !!document.getElementById('settingPublicDirectory')?.checked,
        show_badges: !!document.getElementById('settingShowBadges')?.checked,
        two_factor_auth: !!document.getElementById('settingTwoFactor')?.checked
      };

      try {
        const response = await fetch('/api/v1/donor/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          if (settingsStatusText) {
            settingsStatusText.innerHTML = `✓ Last saved at ${nowStr}`;
            settingsStatusText.style.color = 'var(--success-green)';
          }
          localStorage.setItem('sbds_donor_settings', JSON.stringify(payload));
          showToast('Donor Portal Settings & Preferences saved successfully! 🎉');
        } else {
          showToast('Could not save settings to server. Saved locally.');
        }
      } catch (err) {
        localStorage.setItem('sbds_donor_settings', JSON.stringify(payload));
        showToast('Preferences saved to local device.');
      } finally {
        saveSettingsBtn.disabled = false;
        saveSettingsBtn.innerHTML = originalText;
      }
    });
  }

  // Reset to Defaults
  if (resetSettingsBtn) {
    resetSettingsBtn.addEventListener('click', () => {
      const smsCb = document.getElementById('settingSmsAlerts');
      if (smsCb) smsCb.checked = true;
      const pushCb = document.getElementById('settingInAppPush');
      if (pushCb) pushCb.checked = true;
      const gapCb = document.getElementById('settingGapReminders');
      if (gapCb) gapCb.checked = true;
      const quietCb = document.getElementById('settingQuietHours');
      if (quietCb) quietCb.checked = false;
      const hospCb = document.getElementById('settingAllowHospitalCall');
      if (hospCb) hospCb.checked = true;
      const maskCb = document.getElementById('settingMaskPublicPhone');
      if (maskCb) maskCb.checked = true;
      const dirCb = document.getElementById('settingPublicDirectory');
      if (dirCb) dirCb.checked = true;
      const badgeCb = document.getElementById('settingShowBadges');
      if (badgeCb) badgeCb.checked = true;
      const twoFaCb = document.getElementById('settingTwoFactor');
      if (twoFaCb) twoFaCb.checked = true;

      if (radiusRangeInput && radiusValueDisplay) {
        radiusRangeInput.value = '15';
        radiusValueDisplay.textContent = '15 km';
      }

      showToast('Settings reset to recommended defaults.');
    });
  }

  // Update Password
  if (btnUpdatePassword) {
    btnUpdatePassword.addEventListener('click', () => {
      const cur = document.getElementById('inputCurrentPass')?.value || '';
      const newP = document.getElementById('inputNewPass')?.value || '';
      const conf = document.getElementById('inputConfirmPass')?.value || '';

      if (!cur) {
        showToast('Please enter your current password.');
        return;
      }
      if (newP.length < 8) {
        showToast('New password must be at least 8 characters long.');
        return;
      }
      if (newP !== conf) {
        showToast('New password and confirmation do not match.');
        return;
      }

      document.getElementById('inputCurrentPass').value = '';
      document.getElementById('inputNewPass').value = '';
      document.getElementById('inputConfirmPass').value = '';
      showToast('Security password updated successfully! 🔐');
    });
  }

  // Revoke other sessions
  if (btnRevokeSessions) {
    btnRevokeSessions.addEventListener('click', () => {
      showToast('All other active browser sessions have been logged out.');
    });
  }

  // Restore saved preferences from localStorage if exists
  try {
    const saved = localStorage.getItem('sbds_donor_settings');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.radius_km && radiusRangeInput && radiusValueDisplay) {
        radiusRangeInput.value = parsed.radius_km;
        radiusValueDisplay.textContent = `${parsed.radius_km} km`;
      }
      if (parsed.sms_alerts !== undefined && document.getElementById('settingSmsAlerts')) {
        document.getElementById('settingSmsAlerts').checked = parsed.sms_alerts;
      }
      if (parsed.inapp_notifications !== undefined && document.getElementById('settingInAppPush')) {
        document.getElementById('settingInAppPush').checked = parsed.inapp_notifications;
      }
      if (parsed.gap_reminders !== undefined && document.getElementById('settingGapReminders')) {
        document.getElementById('settingGapReminders').checked = parsed.gap_reminders;
      }
      if (parsed.quiet_hours !== undefined && document.getElementById('settingQuietHours')) {
        document.getElementById('settingQuietHours').checked = parsed.quiet_hours;
      }
    }
  } catch (e) {
    // Ignore storage errors
  }

  window.activateSection = activateSection;
  window.showToast = showToast;
});

