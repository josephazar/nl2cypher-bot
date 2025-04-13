/**
 * Chat functionality for the Badevel Living Lab Assistant
 */

// Chat state
const chatState = {
    threadId: null,
    isProcessing: false,
};

// DOM elements
const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');

// Initialize chat
document.addEventListener('DOMContentLoaded', () => {
    // Scroll to bottom of chat
    scrollChatToBottom();
    
    // Set up event listeners
    chatForm.addEventListener('submit', handleChatSubmit);
    
    // Set up suggestion buttons
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            if (query) {
                userInput.value = query;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });
});

/**
 * Handle chat form submission
 * @param {Event} e - Form submission event
 */
async function handleChatSubmit(e) {
    e.preventDefault();
    
    // Get user message
    const message = userInput.value.trim();
    
    // Don't process empty messages or if already processing
    if (!message || chatState.isProcessing) return;
    
    // Clear input
    userInput.value = '';
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Set processing state
    chatState.isProcessing = true;
    
    // Add assistant "thinking" message
    const thinkingId = addThinkingMessage();
    
    try {
        // Send message to backend
        const response = await sendMessageToBackend(message);
        
        // Remove thinking message
        removeThinkingMessage(thinkingId);
        
        // Add assistant response to chat
        addMessageToChat('assistant', response.response);
        
        // Update thread ID
        chatState.threadId = response.thread_id;
        
        // If there's a Cypher query, visualize it
        if (response.cypher_query) {
            visualizeGraph(response.cypher_query);
        }
    } catch (error) {
        // Remove thinking message
        removeThinkingMessage(thinkingId);
        
        // Add error message
        addMessageToChat('assistant', `Sorry, I encountered an error: ${error.message}`);
        console.error('Chat error:', error);
    } finally {
        // Reset processing state
        chatState.isProcessing = false;
    }
}

/**
 * Send a message to the backend API
 * @param {string} message - User message
 * @returns {Promise<Object>} - Response data
 */
async function sendMessageToBackend(message) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message,
            thread_id: chatState.threadId,
        }),
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    return await response.json();
}

/**
 * Add a message to the chat container
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message content
 */
function addMessageToChat(role, content) {
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', `${role}-message`);
    
    // Create message content
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    
    // Process content (handle markdown, code, etc.)
    contentDiv.innerHTML = processMessageContent(content);
    
    // Add content to message
    messageDiv.appendChild(contentDiv);
    
    // Add message to chat
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    scrollChatToBottom();
}

/**
 * Process message content to handle formatting
 * @param {string} content - Raw message content
 * @returns {string} - Processed HTML content
 */
function processMessageContent(content) {
    // Replace newlines with <br>
    let processed = content.replace(/\n/g, '<br>');
    
    // Simple code block highlighting (could be enhanced with a proper markdown/syntax highlighting library)
    processed = processed.replace(/```(\w*)([\s\S]*?)```/g, (match, language, code) => {
        return `<pre class="code-block ${language}"><code>${code.trim()}</code></pre>`;
    });
    
    return processed;
}

/**
 * Add a "thinking" message while waiting for the assistant's response
 * @returns {string} - ID of the thinking message element
 */
function addThinkingMessage() {
    // Create unique ID
    const id = 'thinking-' + Date.now();
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', 'assistant-message');
    messageDiv.id = id;
    
    // Create message content
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    
    // Add loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.classList.add('loading');
    contentDiv.appendChild(loadingDiv);
    
    // Add content to message
    messageDiv.appendChild(contentDiv);
    
    // Add message to chat
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    scrollChatToBottom();
    
    return id;
}

/**
 * Remove the "thinking" message
 * @param {string} id - ID of the thinking message element
 */
function removeThinkingMessage(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

/**
 * Scroll to the bottom of the chat container
 */
function scrollChatToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Export functions for use in other scripts
window.chatFunctions = {
    addMessageToChat,
    sendMessageToBackend,
};