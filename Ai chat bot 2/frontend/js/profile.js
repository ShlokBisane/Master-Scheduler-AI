/**
 * Profile Module — Personal profile page that opens in place of chat.
 * Helps AI understand user context for smarter scheduling.
 */

const Profile = (() => {

    function init() {
        // Profile link in sidebar
        const profileBtn = document.getElementById('profile-btn');
        if (profileBtn) {
            profileBtn.addEventListener('click', show);
        }
    }

    async function show() {
        // Hide chat area, show profile page
        const chatArea = document.getElementById('chat-area');
        const profilePage = document.getElementById('profile-page');
        const titleDisplay = document.getElementById('chat-title-display');

        if (chatArea) chatArea.style.display = 'none';
        if (profilePage) {
            profilePage.style.display = 'flex';
            titleDisplay.textContent = 'My Profile';
        }

        // Deselect chat items
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));

        // Load existing profile
        try {
            const data = await Api.getProfile();
            const profile = data.profile || {};
            fillForm(profile);
        } catch (err) {
            // Fresh profile
        }

        // Setup save handler (remove old listener to prevent duplicates)
        const saveBtn = document.getElementById('profile-save-btn');
        if (saveBtn) {
            const newBtn = saveBtn.cloneNode(true);
            saveBtn.parentNode.replaceChild(newBtn, saveBtn);
            newBtn.addEventListener('click', save);
        }
    }

    function fillForm(profile) {
        const fields = [
            'profile-name', 'profile-class', 'profile-board', 
            'profile-subjects', 'profile-daily-hours', 'profile-slots',
            'profile-sleep', 'profile-wake', 'profile-tuition',
            'profile-coaching', 'profile-college', 'profile-language'
        ];

        const keys = [
            'name', 'class_course', 'board_university',
            'subjects', 'daily_study_hours', 'preferred_slots',
            'sleep_time', 'wake_time', 'tuition_timings',
            'coaching_timings', 'college_timings', 'preferred_language'
        ];

        fields.forEach((fieldId, i) => {
            const el = document.getElementById(fieldId);
            if (el && profile[keys[i]]) {
                el.value = profile[keys[i]];
            }
        });

        // User type (student/teacher)
        const typeSelect = document.getElementById('profile-type');
        if (typeSelect && profile.user_type) {
            typeSelect.value = profile.user_type;
        }

        // Can study long
        const longStudy = document.getElementById('profile-long-study');
        if (longStudy && profile.can_study_long) {
            longStudy.value = profile.can_study_long;
        }
    }

    async function save() {
        const profileData = {
            name: getVal('profile-name'),
            user_type: getVal('profile-type') || 'student',
            class_course: getVal('profile-class'),
            board_university: getVal('profile-board'),
            subjects: getVal('profile-subjects'),
            daily_study_hours: getVal('profile-daily-hours'),
            preferred_slots: getVal('profile-slots'),
            sleep_time: getVal('profile-sleep'),
            wake_time: getVal('profile-wake'),
            tuition_timings: getVal('profile-tuition'),
            coaching_timings: getVal('profile-coaching'),
            college_timings: getVal('profile-college'),
            can_study_long: getVal('profile-long-study'),
            preferred_language: getVal('profile-language'),
        };

        try {
            await Api.saveProfile(profileData);
            showToast('Profile saved! AI will use this context for better scheduling.', 'success');
        } catch (err) {
            showToast('Failed to save profile: ' + err.message);
        }
    }

    function getVal(id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    function hide() {
        const chatArea = document.getElementById('chat-area');
        const profilePage = document.getElementById('profile-page');
        if (chatArea) chatArea.style.display = 'flex';
        if (profilePage) profilePage.style.display = 'none';
    }

    return { init, show, hide };
})();
