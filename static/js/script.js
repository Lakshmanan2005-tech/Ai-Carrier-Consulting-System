document.addEventListener('DOMContentLoaded', () => {
    // Sidebar & Profile Logic
    const burgerToggle = document.getElementById('burgerToggle');
    const sidebar = document.getElementById('sidebar');
    const mainWrapper = document.getElementById('mainWrapper');
    const overlay = document.getElementById('mobileOverlay');
    const profileMenuToggle = document.getElementById('profileMenuToggle');

    if (burgerToggle && sidebar && mainWrapper) {
        burgerToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (window.innerWidth <= 768) {
                sidebar.classList.add('mobile-open');
                sidebar.classList.remove('collapsed');
                if(overlay) overlay.classList.add('active');
            } else {
                sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed');
            }
        });
    }

    if (overlay && sidebar) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        });
    }

    if (profileMenuToggle) {
        profileMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            profileMenuToggle.classList.toggle('active');
        });
    }

    document.addEventListener('click', (e) => {
        if (profileMenuToggle && !profileMenuToggle.contains(e.target)) {
            profileMenuToggle.classList.remove('active');
        }
        if (window.innerWidth <= 768 && sidebar && overlay && burgerToggle) {
            if (!sidebar.contains(e.target) && !burgerToggle.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
                overlay.classList.remove('active');
            }
        }
    });

    // Chatbot Toggle
    const cbToggle = document.getElementById('chatbotToggle');
    const cbWindow = document.getElementById('chatbotWindow');
    const closeChat = document.getElementById('closeChat');
    const chatInput = document.getElementById('chatInput');
    const chatSend = document.getElementById('chatSend');
    const chatBody = document.getElementById('chatBody');

    if (cbToggle && cbWindow) {
        cbToggle.addEventListener('click', () => {
             cbWindow.classList.toggle('active');
        });

        closeChat.addEventListener('click', () => {
            cbWindow.classList.remove('active');
        });

        chatSend.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    function appendMessage(sender, text) {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble', sender);
        bubble.innerText = text;
        chatBody.appendChild(bubble);
        chatBody.scrollTop = 0;
    }

    async function sendMessage() {
        const msg = chatInput.value.trim();
        if(!msg) return;

        appendMessage('user', msg);
        chatInput.value = '';

        // loading indication
        const loadingBubble = document.createElement('div');
        loadingBubble.classList.add('chat-bubble', 'ai');
        loadingBubble.innerText = 'Thinking...';
        loadingBubble.id = 'loadingIndicator';
        chatBody.appendChild(loadingBubble);
        chatBody.scrollTop = 0;

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            document.getElementById('loadingIndicator')?.remove();
            
            if (data.reply) {
                appendMessage('ai', data.reply);
            } else {
                appendMessage('ai', 'Error: No response from server.');
            }
        } catch(err) {
            console.error("Fetch error:", err);
            document.getElementById('loadingIndicator')?.remove();
            appendMessage('ai', 'AI assistant is temporarily unavailable. Please try again later.');
        }
    }

    // Search Suggestions
    const searchInput = document.getElementById('skillSearch');
    const suggestionsBox = document.getElementById('suggestionsBox');

    if (searchInput) {
        searchInput.addEventListener('input', async (e) => {
            const val = e.target.value.trim();
            if (val.length < 2) {
                suggestionsBox.style.display = 'none';
                return;
            }

            try {
                const res = await fetch(`/api/suggest?q=${encodeURIComponent(val)}`);
                const data = await res.json();
                
                if (data.length > 0) {
                    suggestionsBox.innerHTML = '';
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'suggestion-item';
                        div.innerText = item;
                        div.onclick = () => {
                            searchInput.value = item;
                            suggestionsBox.style.display = 'none';
                        };
                        suggestionsBox.appendChild(div);
                    });
                    suggestionsBox.style.display = 'block';
                } else {
                    suggestionsBox.style.display = 'none';
                }
            } catch(e) {}
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-wrapper')) {
                suggestionsBox.style.display = 'none';
            }
        });
    }
});
