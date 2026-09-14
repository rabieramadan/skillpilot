// Debug version - minimal functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Debug script loaded');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');

    if (!chatInput) {
        console.error('Chat input not found');
        return;
    }

    console.log('Elements found successfully');

    // Test input functionality
    chatInput.addEventListener('input', function() {
        console.log('Input detected:', this.value);
    });

    // Simple send function
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        console.log('Sending message:', message);

        // Add message to chat
        const messageDiv = document.createElement('div');
        messageDiv.innerHTML = `
            <div style="padding: 10px; margin: 10px; background: #f0f0f0; border-radius: 8px;">
                <strong>You:</strong> ${message}
            </div>
        `;
        chatMessages.appendChild(messageDiv);

        // Clear input
        chatInput.value = '';

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Mock AI response
        setTimeout(() => {
            const aiDiv = document.createElement('div');
            aiDiv.innerHTML = `
                <div style="padding: 10px; margin: 10px; background: #e8f4fd; border-radius: 8px;">
                    <strong>AI:</strong> I received your message: "${message}"
                </div>
            `;
            chatMessages.appendChild(aiDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 1000);
    }

    // Send button click
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
        console.log('Send button listener added');
    }

    // Enter key
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    console.log('Debug setup complete');
});