// Fallback object to prevent errors if Microsoft Speech SDK fails to load
console.error("MOCK SPEECH SDK IS BEING LOADED!");

// Add a flag to identify this is from the mock
window.FromMock = true;

window.Microsoft = window.Microsoft || {};
Microsoft.CognitiveServices = Microsoft.CognitiveServices || {};
Microsoft.CognitiveServices.Speech = Microsoft.CognitiveServices.Speech || {
    // Minimal implementation to prevent errors
    SpeechConfig: {
        fromAuthorizationToken: function() {
            console.warn('Using Speech SDK mock implementation');
            return {};
        }
    },
    AudioConfig: {
        fromDefaultMicrophoneInput: function() {
            return {};
        }
    },
    SpeechRecognizer: function() {
        return {
            startContinuousRecognitionAsync: function(onSuccess, onError) {
                onError(new Error('Speech SDK not properly loaded'));
            },
            stopContinuousRecognitionAsync: function(onSuccess) {
                if (onSuccess) onSuccess();
            }
        };
    },
    ResultReason: {
        RecognizedSpeech: 'RecognizedSpeech'
    }
};

// Update UI to indicate speech is not available
document.addEventListener('DOMContentLoaded', function() {
    const speechBtn = document.getElementById('speech-btn');
    const speechStatus = document.getElementById('speech-status');
    
    if (speechBtn && speechStatus) {
        speechBtn.disabled = true;
        speechBtn.title = "Speech SDK failed to load";
        speechStatus.textContent = "Speech recognition unavailable";
        speechStatus.style.color = "#dc3545";
    }
    
    console.warn('Speech SDK mock loaded - speech recognition will not work.');
});