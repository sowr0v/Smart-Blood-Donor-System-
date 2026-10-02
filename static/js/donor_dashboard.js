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
  // DONOR IN-APP CHAT MODULE
  // =========================================================
  const chatThreads = document.querySelectorAll('.chat-thread-item');
  const chatMessagesContainer = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSearchInput = document.getElementById('chatSearchInput');
  const currentChatUserTitle = document.getElementById('currentChatUserTitle');
  const currentChatUserSub = document.getElementById('currentChatUserSub');
  const activeChatAvatar = document.getElementById('activeChatAvatar');
  const chatCallBtn = document.getElementById('chatCallBtn');

  // Conversation data store for seamless switching
  const conversationStore = {
    'thread-square': [
      { sender: 'coordinator', text: 'Hello Ayesha, we saw you accepted the urgent A+ requirement at Square Hospital (Panthapath, Dhaka).', time: '10:08 AM' },
      { sender: 'you', text: 'Yes, I am available and preparing to come. Is the patient at Cabin 402 or the Blood Bank unit?', time: '10:10 AM' },
      { sender: 'coordinator', text: 'Please report directly to 2nd Floor, Blood Transfusion Dept. Coordinator Dr. Farhan is on duty and waiting.', time: '10:12 AM' }
    ],
    'thread-dmc': [
      { sender: 'coordinator', text: 'Warm greetings from Dhaka Medical College Blood Bank.', time: 'Yesterday 3:15 PM' },
      { sender: 'coordinator', text: 'Your whole blood donation certificate from Jan 14 has been verified and registered on your national donor card.', time: 'Yesterday 3:16 PM' },
      { sender: 'you', text: 'Thank you! When will I be eligible to donate whole blood again?', time: 'Yesterday 3:45 PM' },
      { sender: 'coordinator', text: 'You completed your 56-day gap and are officially eligible right now!', time: 'Yesterday 4:00 PM' }
    ],
    'thread-nabil': [
      { sender: 'coordinator', text: 'Assalamu Alaikum Ayesha apu, I am Nabil. You donated blood for my mother last month.', time: '2 days ago' },
      { sender: 'coordinator', text: 'I just wanted to let you know she was discharged today and is healthy. We cannot thank you enough for saving her life.', time: '2 days ago' },
      { sender: 'you', text: 'Alhamdulillah, so relieved to hear this news! Praying for her continued strength and health.', time: '2 days ago' }
    ],
    'thread-support': [
      { sender: 'coordinator', text: 'Welcome to the Smart Blood Donor System Donor Support channel.', time: '18 Jan' },
      { sender: 'coordinator', text: 'Congratulations on reaching your 8th verified donation! Your account has been upgraded to Gold Tier.', time: '18 Jan' },
      { sender: 'you', text: 'Thank you SBDS team! Appreciate the fast verification.', time: '18 Jan' }
    ]
  };

  let activeThreadId = 'thread-square';

  function renderMessages(threadId) {
    if (!chatMessagesContainer) return;
    const messages = conversationStore[threadId] || [];
    chatMessagesContainer.innerHTML = `
      <div style="text-align: center; font-size: 0.74rem; color: var(--text-muted); margin: 4px 0 10px;">
        Encrypted Volunteer Blood Coordination Channel
      </div>
    `;

    messages.forEach(msg => {
      const bubble = document.createElement('div');
      bubble.className = `chat-bubble ${msg.sender === 'you' ? 'bubble-sent' : 'bubble-received'}`;
      bubble.innerHTML = `
        <div>${msg.text}</div>
        <div class="chat-bubble-time">${msg.time} · ${msg.sender === 'you' ? 'You' : 'Coordinator'}</div>
      `;
      chatMessagesContainer.appendChild(bubble);
    });

    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  // Bind thread selection
  chatThreads.forEach(thread => {
    thread.addEventListener('click', () => {
      chatThreads.forEach(t => t.classList.remove('active'));
      thread.classList.add('active');

      const threadId = thread.getAttribute('data-thread-id');
      const userName = thread.getAttribute('data-name');
      const avatar = thread.getAttribute('data-avatar');
      const status = thread.getAttribute('data-status');
      const phone = thread.getAttribute('data-phone');

      activeThreadId = threadId;

      if (currentChatUserTitle) currentChatUserTitle.textContent = userName;
      if (activeChatAvatar) activeChatAvatar.textContent = avatar;
      if (currentChatUserSub) currentChatUserSub.innerHTML = `<span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--success-green);"></span> <span>${status}</span>`;
      if (chatCallBtn && phone) chatCallBtn.setAttribute('href', `tel:${phone}`);

      renderMessages(threadId);
      showToast(`Switched chat to ${userName}`);
    });
  });

  // Sending message
  window.sendChatMessage = function() {
    if (!chatInput) return;
    const text = chatInput.value.trim();
    if (!text) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Store sent message
    if (!conversationStore[activeThreadId]) {
      conversationStore[activeThreadId] = [];
    }
    conversationStore[activeThreadId].push({ sender: 'you', text, time: timeStr });

    // Append to UI
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble bubble-sent';
    bubble.innerHTML = `
      <div>${text}</div>
      <div class="chat-bubble-time">${timeStr} · You</div>
    `;
    chatMessagesContainer.appendChild(bubble);
    chatInput.value = '';
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;

    // Update snippet in thread list
    const currentThreadItem = document.querySelector(`.chat-thread-item[data-thread-id="${activeThreadId}"]`);
    if (currentThreadItem) {
      const snippet = currentThreadItem.querySelector('.thread-preview-snippet');
      if (snippet) snippet.textContent = text;
      const timeElem = currentThreadItem.querySelector('.thread-time');
      if (timeElem) timeElem.textContent = 'Just now';
    }

    // Auto-reply simulation
    setTimeout(() => {
      let replyText = 'Received your message! We have notified the medical staff on the floor.';
      if (activeThreadId === 'thread-square') {
        replyText = 'Coordinator Dr. Farhan: "Received! The patient attendants are ready. See you shortly!"';
      } else if (activeThreadId === 'thread-dmc') {
        replyText = 'Desk Officer: "Acknowledged! Feel free to reach out whenever you want to schedule your next visit."';
      } else if (activeThreadId === 'thread-nabil') {
        replyText = 'Nabil: "Thank you again Ayesha apu, truly indebted to donors like you!"';
      } else if (activeThreadId === 'thread-support') {
        replyText = 'SBDS Support: "We have updated your record. Let us know if you need assistance with transportation."';
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
        chatMessagesContainer.appendChild(replyBubble);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
      }
    }, 1200);
  };

  // Chat filter search
  if (chatSearchInput) {
    chatSearchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      chatThreads.forEach(thread => {
        const name = (thread.getAttribute('data-name') || '').toLowerCase();
        const snippet = (thread.querySelector('.thread-preview-snippet')?.textContent || '').toLowerCase();
        if (name.includes(q) || snippet.includes(q)) {
          thread.style.display = 'flex';
        } else {
          thread.style.display = 'none';
        }
      });
    });
  }

  window.activateSection = activateSection;
  window.showToast = showToast;
});
