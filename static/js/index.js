document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const messageInput = document.getElementById('messageInput');
    const chatForm = document.getElementById('chatForm');
    const typingIndicator = document.getElementById('typingIndicator');
    scrollToBottom();
    function addMessage(content, sender) {
        let messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');

        let messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.textContent = content;

        let timestamp = document.createElement('div');
        timestamp.classList.add('message-timestamp');
        timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });

        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(timestamp);
        chatContainer.appendChild(messageDiv);

        scrollToBottom();
    }

    function scrollToBottom() {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: "smooth"
        });
}

    async function sendMessage(event) {
        event.preventDefault();
        const userMessage = messageInput.value.trim();
        if (!userMessage) return;

        messageInput.disabled = true;
        typingIndicator.style.display = 'inline-block';
        addMessage(userMessage, 'user');
        messageInput.value = '';

        try {
            const response = await fetch('http://localhost:8000/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: userMessage })
            });

            const data = await response.json();
            if (data.bot_response) {
                addMessage(data.bot_response, 'ai');
            } else {
                addMessage(`Error: ${data.error || 'Unexpected response'}`, 'ai');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Something went wrong. Please try again.', 'ai');
        } finally {
            messageInput.disabled = false;
            typingIndicator.style.display = 'none';
            messageInput.focus();
        }
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(cookie => {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                }
            });
        }
        return cookieValue;
    }

    chatForm.addEventListener('submit', sendMessage);
});