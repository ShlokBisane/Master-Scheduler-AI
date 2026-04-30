/**
 * App Module — Main initialization, sidebar management, settings
 */

const App = (() => {
    let sidebarOpen = true;

    function init() {
        // Initialize all modules
        Chat.init();
        Calendar.init();
        Todo.init();
        Stress.init();
        Voice.init();
        Profile.init();

        setupSidebar();
        setupSettings();
        setupModeToggle();
        loadSettings();
        refreshChatList();

        // Close sidebar on mobile by default
        if (window.innerWidth <= 768) {
            sidebarOpen = false;
            document.getElementById('sidebar').classList.add('collapsed');
        }
    }

    // ─── Sidebar ────────────────────────────────────────

    function setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle');
        const closeBtn = document.getElementById('sidebar-close');
        const newChatBtn = document.getElementById('new-chat-btn');
        const profileBtn = document.getElementById('profile-btn');

        toggleBtn.addEventListener('click', () => {
            sidebarOpen = !sidebarOpen;
            sidebar.classList.toggle('collapsed', !sidebarOpen);
        });

        closeBtn.addEventListener('click', () => {
            sidebarOpen = false;
            sidebar.classList.add('collapsed');
        });

        newChatBtn.addEventListener('click', () => {
            Chat.newChat();
            // Deselect all chat items
            document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebarOpen = false;
                sidebar.classList.add('collapsed');
            }
        });

        // Mobile: close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && sidebarOpen) {
                if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebarOpen = false;
                    sidebar.classList.add('collapsed');
                }
            }
        });

        // Mobile: swipe to close
        let touchStartX = 0;
        sidebar.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });

        sidebar.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const diff = touchStartX - touchEndX;
            if (diff > 80) { // Swipe left
                sidebarOpen = false;
                sidebar.classList.add('collapsed');
            }
        }, { passive: true });
    }

    // ─── Chat List ──────────────────────────────────────

    async function refreshChatList() {
        const list = document.getElementById('chat-list');

        try {
            const data = await Api.getChats();
            const chats = data.chats || [];

            if (chats.length === 0) {
                list.innerHTML = '<div class="no-chats">No conversations yet</div>';
                return;
            }

            list.innerHTML = chats.map(chat => {
                const isActive = chat.id === Chat.getChatId();
                const icon = chat.mode === 'teacher' ? '👨‍🏫' : '💬';
                return `
                    <div class="chat-item ${isActive ? 'active' : ''}" data-chat-id="${chat.id}">
                        <span>${icon}</span>
                        <span style="flex:1; overflow:hidden; text-overflow:ellipsis">${chat.title}</span>
                        <button class="chat-delete" data-chat-id="${chat.id}" title="Delete chat">×</button>
                    </div>
                `;
            }).join('');

            // Click to load chat
            list.querySelectorAll('.chat-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    if (e.target.classList.contains('chat-delete')) return;
                    const chatId = parseInt(item.dataset.chatId);
                    
                    // Update active state
                    list.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    
                    Chat.loadChat(chatId);

                    // Update title
                    const titleSpan = item.querySelector('span:nth-child(2)');
                    document.getElementById('chat-title-display').textContent = titleSpan.textContent;

                    // Close sidebar on mobile
                    if (window.innerWidth <= 768) {
                        sidebarOpen = false;
                        document.getElementById('sidebar').classList.add('collapsed');
                    }
                });
            });

            // Delete chat
            list.querySelectorAll('.chat-delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const chatId = parseInt(btn.dataset.chatId);
                    if (confirm('Delete this chat?')) {
                        try {
                            await Api.deleteChat(chatId);
                            if (chatId === Chat.getChatId()) {
                                Chat.newChat();
                            }
                            refreshChatList();
                        } catch (err) {
                            showToast('Failed to delete chat');
                        }
                    }
                });
            });

        } catch (err) {
            list.innerHTML = '<div class="no-chats">Failed to load chats</div>';
        }
    }

    // ─── Mode Toggle ────────────────────────────────────

    function setupModeToggle() {
        const studentBtn = document.getElementById('mode-student');
        const teacherBtn = document.getElementById('mode-teacher');

        studentBtn.addEventListener('click', () => {
            studentBtn.classList.add('active');
            teacherBtn.classList.remove('active');
            Chat.setMode('student');
        });

        teacherBtn.addEventListener('click', () => {
            teacherBtn.classList.add('active');
            studentBtn.classList.remove('active');
            Chat.setMode('teacher');
        });
    }

    // ─── Settings (Footer Bar) ──────────────────────────

    function setupSettings() {
        const geminiInput = document.getElementById('gemini-key-input');
        const openrouterInput = document.getElementById('openrouter-key-input');
        const toggleGemini = document.getElementById('toggle-gemini');
        const toggleOpenrouter = document.getElementById('toggle-openrouter');
        const saveBtn = document.getElementById('save-keys-btn');
        const providerBadge = document.getElementById('provider-badge');

        // Provider toggle
        toggleGemini.addEventListener('click', () => {
            toggleGemini.classList.add('active');
            toggleOpenrouter.classList.remove('active');
            providerBadge.textContent = 'Gemini';
        });

        toggleOpenrouter.addEventListener('click', () => {
            toggleOpenrouter.classList.add('active');
            toggleGemini.classList.remove('active');
            providerBadge.textContent = 'OpenRouter';
        });

        // Save settings
        saveBtn.addEventListener('click', async () => {
            const settings = {};
            
            if (geminiInput.value) settings.gemini_api_key = geminiInput.value;
            if (openrouterInput.value) settings.openrouter_api_key = openrouterInput.value;
            settings.active_provider = toggleGemini.classList.contains('active') ? 'gemini' : 'openrouter';

            try {
                await Api.saveSettings(settings);
                showToast('Settings saved!', 'success');
                
                // Clear inputs (keys are now saved on server)
                if (geminiInput.value) geminiInput.value = '';
                if (openrouterInput.value) openrouterInput.value = '';
                
                // Reload settings to show masked keys
                loadSettings();
            } catch (err) {
                showToast('Failed to save settings');
            }
        });
    }

    async function loadSettings() {
        try {
            const settings = await Api.getSettings();
            
            const geminiInput = document.getElementById('gemini-key-input');
            const openrouterInput = document.getElementById('openrouter-key-input');
            const toggleGemini = document.getElementById('toggle-gemini');
            const toggleOpenrouter = document.getElementById('toggle-openrouter');
            const providerBadge = document.getElementById('provider-badge');

            // Show masked keys as placeholder
            if (settings.has_gemini_key) {
                geminiInput.placeholder = settings.gemini_api_key_masked || 'Key saved ✓';
            }
            if (settings.has_openrouter_key) {
                openrouterInput.placeholder = settings.openrouter_api_key_masked || 'Key saved ✓';
            }

            // Set active provider
            const provider = settings.active_provider || 'gemini';
            if (provider === 'openrouter') {
                toggleOpenrouter.classList.add('active');
                toggleGemini.classList.remove('active');
                providerBadge.textContent = 'OpenRouter';
            } else {
                toggleGemini.classList.add('active');
                toggleOpenrouter.classList.remove('active');
                providerBadge.textContent = 'Gemini';
            }
        } catch (err) {
            // Settings may not exist yet
        }
    }

    return { init, refreshChatList };
})();

// ─── Bootstrap ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
