/**
 * Speech recognition functionality for the Badevel Living Lab Assistant
 * using Microsoft Cognitive Services Speech SDK
 */

// DOM elements
const speechBtn = document.getElementById('speech-btn');
// Use userInput from chat.js instead of redeclaring it
// const userInput = document.getElementById('user-input');
const speechStatus = document.getElementById('speech-status');

// Speech recognition state
const speechState = {
    recognizer: null,
    isRecording: false,
    sdkLoaded: false,
    loadingTimeout: null
};

// Define checkSdkLoaded once before it's used
const checkSdkLoaded = () => {
    console.log("Checking if SDK is loaded...");
    
    // Try multiple ways to detect the SDK
    const hasMicrosoftSDK = typeof Microsoft !== 'undefined' && 
                           Microsoft.CognitiveServices && 
                           Microsoft.CognitiveServices.Speech &&
                           typeof Microsoft.CognitiveServices.Speech.SpeechConfig === 'object' &&
                           typeof Microsoft.CognitiveServices.Speech.SpeechConfig.fromAuthorizationToken === 'function';
                           
    const hasGlobalSDK = typeof SpeechSDK !== 'undefined' &&
                       typeof SpeechSDK.SpeechConfig === 'object' &&
                       typeof SpeechSDK.SpeechConfig.fromAuthorizationToken === 'function';
    
    // Log detailed SDK status for debugging
    console.log("SDK detection status:", {
        hasMicrosoftSDK,
        hasGlobalSDK,
        MicrosoftDefined: typeof Microsoft !== 'undefined',
        CognitiveServicesDefined: typeof Microsoft !== 'undefined' && typeof Microsoft.CognitiveServices !== 'undefined',
        SpeechDefined: typeof Microsoft !== 'undefined' && 
                      typeof Microsoft.CognitiveServices !== 'undefined' && 
                      typeof Microsoft.CognitiveServices.Speech !== 'undefined',
        SpeechSDKDefined: typeof SpeechSDK !== 'undefined'
    });
    
    // Check if fromAuthorizationToken is available
    if (hasMicrosoftSDK) {
        console.log("fromAuthorizationToken available in Microsoft namespace:", 
                    typeof Microsoft.CognitiveServices.Speech.SpeechConfig.fromAuthorizationToken);
    }
    
    if (hasGlobalSDK) {
        console.log("fromAuthorizationToken available in global SpeechSDK:", 
                   typeof SpeechSDK.SpeechConfig.fromAuthorizationToken);
    }
    
    // If SDK is loaded in any form
    if (hasMicrosoftSDK || hasGlobalSDK) {
        // Clear timeout as SDK is loaded
        if (speechState.loadingTimeout) {
            clearTimeout(speechState.loadingTimeout);
            speechState.loadingTimeout = null;
        }
        
        // SDK is loaded, enable the button
        speechState.sdkLoaded = true;
        speechStatus.textContent = "Cliquez sur le microphone pour parler";
        speechBtn.addEventListener('click', toggleSpeechRecognition);
        console.log("Speech SDK loaded successfully");
        return;
    }
    
    // Set a timeout to prevent infinite loading
    if (!speechState.loadingTimeout) {
        speechState.loadingTimeout = setTimeout(() => {
            speechStatus.textContent = "SDK non disponible. Résolution vocale impossible.";
            speechStatus.style.color = "#dc3545";
            speechBtn.disabled = true;
            speechBtn.title = "SDK failed to load";
            console.error("SDK loading timeout - giving up");
        }, 5000); // Give up after 5 seconds
    }
    
    speechStatus.textContent = "Chargement du SDK...";
    setTimeout(checkSdkLoaded, 500); // Check again in 500ms
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("Speech.js initialized");
    
    // Identify where speech-sdk-mock.js might be loaded from
    const allScripts = document.getElementsByTagName('script');
    for (let i = 0; i < allScripts.length; i++) {
        const src = allScripts[i].src || '';
        if (src.includes('speech-sdk-mock.js')) {
            console.error("FOUND MOCK SCRIPT:", src);
        }
        if (src.includes('microsoft.cognitiveservices.speech.sdk')) {
            console.log("FOUND REAL SDK SCRIPT:", src);
        }
    }
    
    // Log window.sdkLoaded if it exists
    console.log("window.sdkLoaded:", window.sdkLoaded);
    
    console.log("Speech config:", window.speechConfig);
    
    // Check if speech services are available
    if (!window.speechConfig || !window.speechConfig.token || window.speechConfig.error) {
        console.error("Speech config check failed:", {
            hasConfig: !!window.speechConfig,
            hasToken: !!(window.speechConfig && window.speechConfig.token),
            error: window.speechConfig?.error
        });
        
        // Disable speech button and show error message
        speechBtn.disabled = true;
        speechBtn.title = window.speechConfig?.error || "Speech services not available";
        speechStatus.textContent = "Speech recognition unavailable";
        speechStatus.style.color = "#dc3545";
        return;
    }
    
    // Start checking if SDK is loaded
    checkSdkLoaded();
});

/**
 * Toggle speech recognition on/off
 */
function toggleSpeechRecognition() {
    console.log("Toggle speech recognition called");
    if (speechState.isRecording) {
        stopSpeechRecognition();
    } else {
        startSpeechRecognition();
    }
}

/**
 * Start speech recognition
 */
async function startSpeechRecognition() {
    try {
        // Check for mock flag FIRST
        if (window.FromMock === true) {
            console.error("CRITICAL ERROR: Using mock implementation instead of real SDK!");
            throw new Error('Real Speech SDK not loaded - using mock implementation');
        }
        
        // Detailed SDK presence check
        const hasMicrosoftSDK = typeof Microsoft !== 'undefined' && 
                               Microsoft.CognitiveServices && 
                               Microsoft.CognitiveServices.Speech &&
                               typeof Microsoft.CognitiveServices.Speech.SpeechConfig === 'object' &&
                               typeof Microsoft.CognitiveServices.Speech.SpeechConfig.fromAuthorizationToken === 'function';
                               
        const hasGlobalSDK = typeof SpeechSDK !== 'undefined' &&
                           typeof SpeechSDK.SpeechConfig === 'object' &&
                           typeof SpeechSDK.SpeechConfig.fromAuthorizationToken === 'function';
        
        console.log("SDK check before starting recognition:", {
            hasMicrosoftSDK,
            hasGlobalSDK,
            MicrosoftDefined: typeof Microsoft !== 'undefined',
            CognitiveServicesDefined: typeof Microsoft !== 'undefined' && typeof Microsoft.CognitiveServices !== 'undefined',
            SpeechDefined: typeof Microsoft !== 'undefined' && 
                          typeof Microsoft.CognitiveServices !== 'undefined' && 
                          typeof Microsoft.CognitiveServices.Speech !== 'undefined',
            SpeechSDKDefined: typeof SpeechSDK !== 'undefined'
        });
        
        if (!hasMicrosoftSDK && !hasGlobalSDK) {
            console.error("SDK not properly loaded - required methods missing");
            throw new Error('Speech SDK not loaded yet or missing required methods');
        }
        
        // Update UI
        speechBtn.classList.add('recording');
        speechStatus.textContent = 'Écoute en cours...';
        speechState.isRecording = true;
        
        // Get token from global variable
        const tokenObj = window.speechConfig;
        console.log("Using speech token:", tokenObj.token.substring(0, 10) + "...");
        
        // Access the Speech SDK via the appropriate object
        let sdk;
        if (hasMicrosoftSDK) {
            sdk = Microsoft.CognitiveServices.Speech;
            console.log("Using Microsoft namespace SDK");
        } else {
            sdk = SpeechSDK;
            console.log("Using global SpeechSDK");
        }
        
        console.log("Creating speech config with token and region:", tokenObj.region);
        
        // Create speech config
        const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(tokenObj.token, tokenObj.region);
        speechConfig.speechRecognitionLanguage = tokenObj.language || 'fr-FR';
        
        // Create audio config using default microphone
        const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
        
        // Create speech recognizer
        console.log("Creating speech recognizer");
        speechState.recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
        
        // Set up event handlers
        speechState.recognizer.recognized = (s, e) => {
            if (e.result.reason === sdk.ResultReason.RecognizedSpeech) {
                const text = e.result.text.trim();
                console.log("Recognized text:", text);
                if (text) {
                    // Add recognized text to input field
                    userInput.value += (userInput.value ? ' ' : '') + text;
                }
            }
        };
        
        // Start continuous recognition
        console.log("Starting continuous recognition");
        speechState.recognizer.startContinuousRecognitionAsync(
            () => {
                console.log('Speech recognition started successfully');
            },
            (error) => {
                console.error('Error starting speech recognition:', error);
                stopSpeechRecognition();
                speechStatus.textContent = 'Erreur de reconnaissance vocale';
            }
        );
        
    } catch (error) {
        console.error('Speech recognition error:', error);
        speechStatus.textContent = 'Erreur: ' + error.message;
        stopSpeechRecognition();
    }
}

/**
 * Stop speech recognition
 */
function stopSpeechRecognition() {
    // Update UI
    speechBtn.classList.remove('recording');
    speechStatus.textContent = 'Cliquez sur le microphone pour parler';
    speechState.isRecording = false;
    
    // Stop recognizer if it exists
    if (speechState.recognizer) {
        try {
            console.log("Stopping speech recognition");
            speechState.recognizer.stopContinuousRecognitionAsync(
                () => {
                    console.log('Speech recognition stopped');
                    speechState.recognizer = null;
                },
                (error) => {
                    console.error('Error stopping speech recognition:', error);
                    speechState.recognizer = null;
                }
            );
        } catch (error) {
            console.error('Error when stopping recognizer:', error);
            speechState.recognizer = null;
        }
    }
}

/**
 * Fetch speech token from backend if not already provided
 * @returns {Promise<Object>} - Speech token and configuration
 */
async function fetchSpeechToken() {
    const response = await fetch('/api/speech-token');
    if (!response.ok) {
        throw new Error('Failed to fetch speech token');
    }
    return await response.json();
}