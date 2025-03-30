// const host = 'https://verbagpt.azurewebsites.net/'

document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const messageInput = document.getElementById('messageInput');
    const chatForm = document.getElementById('chatForm');
    const typingIndicator = document.getElementById('typingIndicator');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    
    let currentFile = null;
    
    // Initialize chat
    scrollToBottom();

    // Add message to chat
    function addMessage(content, sender, isFile = false, fileName = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');

        // Add avatar
        const avatar = document.createElement('div');
        avatar.classList.add('message-avatar');
        avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        messageDiv.appendChild(avatar);

        const contentContainer = document.createElement('div');
        contentContainer.classList.add('message-content-container');

        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');

        if (isFile) {
            if (content.startsWith('data:image')) {
                // Image file
                const img = document.createElement('img');
                img.src = content;
                img.alt = fileName || 'Uploaded image';
                img.classList.add('uploaded-file');
                messageContent.appendChild(img);
            } else {
                // Other file type
                const fileLink = document.createElement('a');
                fileLink.href = content;
                fileLink.textContent = fileName || 'Download file';
                fileLink.target = '_blank';
                fileLink.classList.add('file-link');
                messageContent.appendChild(fileLink);
            }
        } else {
            // Text message
            messageContent.textContent = content;
        }

        const timestamp = document.createElement('div');
        timestamp.classList.add('message-timestamp');
        timestamp.textContent = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit', 
            hour12: true 
        });

        contentContainer.appendChild(messageContent);
        contentContainer.appendChild(timestamp);
        messageDiv.appendChild(contentContainer);
        chatContainer.appendChild(messageDiv);

        scrollToBottom();
    }

    // Scroll to bottom of chat
    function scrollToBottom() {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: "smooth"
        });
    }

    // Handle file selection
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            currentFile = e.target.files[0];
            showFilePreview(currentFile);
        }
    });

    // Show file preview before sending
    function showFilePreview(file) {
        filePreview.innerHTML = '';
        
        const previewDiv = document.createElement('div');
        previewDiv.classList.add('file-preview');
        
        const fileName = document.createElement('span');
        fileName.textContent = file.name;
        fileName.classList.add('file-name');
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.classList.add('btn', 'btn-sm', 'btn-outline-danger', 'remove-file');
        removeBtn.addEventListener('click', clearFileSelection);
        
        previewDiv.appendChild(fileName);
        previewDiv.appendChild(removeBtn);
        filePreview.appendChild(previewDiv);
    }

    // Clear file selection
    function clearFileSelection() {
        fileInput.value = '';
        currentFile = null;
        filePreview.innerHTML = '';
    }

    async function sendMessage(event) {
        console.log('Sending messages');
        event.preventDefault();
        const userMessage = messageInput.value.trim();
        console.log('Current file:', currentFile);
        
        if (!userMessage && !currentFile) return;
    
        messageInput.disabled = true;
        fileInput.disabled = true;
        typingIndicator.style.display = 'block';
    
        if (userMessage) addMessage(userMessage, 'user');
        let fileData = null;
        if (currentFile) {
            fileData = await readFileAsDataURL(currentFile);
            addMessage(fileData, 'user', true, currentFile.name);
        }
    
        messageInput.value = '';
        // clearFileSelection();
    
        try {
            const formData = new FormData();
            if (userMessage) formData.append('message', userMessage);
            if (currentFile) formData.append('file', currentFile);
            console.log('FormData:', formData.entries());
            
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });
    
            const text = await response.text();
            console.log('Raw response:', text, 'Status:', response.status);
    
            if (!response.ok) {
                throw new Error(`Server error: ${text || 'Unknown error'} (Status: ${response.status})`);
            }
    
            const data = text ? JSON.parse(text) : {};
            if (data.bot_response) {
                addMessage(data.bot_response, 'ai');
            } else {
                addMessage(`Error: ${data.error || 'Unexpected response'}`, 'ai');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage(`Something went wrong: ${error.message}`, 'ai');
        } finally {
            messageInput.disabled = false;
            fileInput.disabled = false;
            typingIndicator.style.display = 'none';
            messageInput.focus();
        }
    }
    // Helper to read file as Data URL
    function readFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // Helper to get CSRF token
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

    // Event listeners
    chatForm.addEventListener('submit', sendMessage);
    
    // Allow pressing Enter to send, but Shift+Enter for new line
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(e);
        }
    });
});