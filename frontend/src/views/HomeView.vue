<template>
  <div class="homeview_container">
    <div class="row g-4">
      <!-- Chat Area -->
      <div class="col-lg-7">
        <div class="card chat-card">
          <div class="card-header">
            <h5 class="card-title mb-0">Chat avec l'Assistant du Living Lab</h5>
          </div>
          <div class="card-body">
            <div class="chat-container" id="chat-container">
              <!-- Welcome message -->
              <div class="chat-message assistant-message">
                <div class="message-content">
                  <p>Bonjour ! Je suis l'Assistant du Living Lab de Badevel. Comment puis-je vous aider aujourd'hui ?</p>
                </div>
              </div>
              
              <!-- User messages -->
              <div v-for="(message, index) in chatMessages" :key="index" 
                   :class="['chat-message', message.role === 'user' ? 'user-message' : 'assistant-message']">
                <div class="message-content" v-html="formatMessage(message.content)"></div>
              </div>
              
              <!-- "Thinking" message if needed -->
              <div v-if="isProcessing" class="chat-message assistant-message">
                <div class="message-content">
                  <LoadingIcon />
                </div>
              </div>
            </div>
            
            <!-- Input area -->
            <div class="chat-input-container">
              <form @submit.prevent="sendMessage" class="d-flex">
                <input v-model="userInput" type="text" class="form-control" 
                       placeholder="Posez une question sur le village intelligent..." 
                       autocomplete="off">
                <button type="submit" class="btn btn-primary send-btn" 
                        :disabled="isProcessing || !userInput.trim()">
                  <i class="fas fa-paper-plane"></i>
                </button>
                <button type="button" class="btn btn-secondary speech-btn" 
                        @click="toggleSpeechRecognition"
                        :class="{ 'recording': isRecording }"
                        :disabled="!speechEnabled"
                        :title="!speechEnabled ? 'Service vocal indisponible' : 'Reconnaissance vocale'">
                  <i class="fas fa-microphone"></i>
                </button>
              </form>
              <div class="speech-status">{{ speechStatusText }}</div>
            </div>
          </div>
        </div>
        
        <!-- Suggestion buttons -->
        <div class="suggestion-container mt-4">
          <h5>Suggestions de questions:</h5>
          <div class="row g-2">
            <div v-for="(example, index) in examples" :key="index" class="col-md-6 mb-2">
              <button class="suggestion-btn w-100" @click="useExample(example)">{{ example }}</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Graph visualization -->
      <div class="col-lg-5">
        <div class="card viz-card h-100">
          <div class="card-header">
            <h5 class="card-title mb-0">Visualisation</h5>
            
            <!-- Debug controls -->
            <div class="debug-controls" v-if="hasVisualizedGraph">
              <button class="btn btn-sm btn-outline-secondary" @click="toggleDebugInfo">
                {{ showDebugInfo ? 'Masquer' : 'Afficher' }} infos
              </button>
              <button class="btn btn-sm btn-outline-primary ms-2" @click="rerenderGraph">
                Réessayer
              </button>
            </div>
          </div>
          <div class="card-body">
            <div id="viz-placeholder" class="viz-placeholder" v-if="!hasVisualizedGraph">
              <i class="fas fa-project-diagram viz-icon"></i>
              <p>La visualisation du graphe apparaîtra ici lorsque des données seront disponibles.</p>
            </div>
            
            <NeoVisComponent
              v-if="hasVisualizedGraph && currentCypherQuery"
              :query="currentCypherQuery"
              :show-debug-info="showDebugInfo"
              @visualization-completed="onVisualizationCompleted"
              @visualization-error="onVisualizationError"
              ref="neovis"
            />
            
            <div v-if="visualizationError" class="alert alert-danger mt-3">
              <strong>Erreur de visualisation :</strong> {{ visualizationError }}
            </div>
            
            <div v-if="showDebugInfo && hasVisualizedGraph" class="debug-info mt-3">
              <div class="card">
                <div class="card-header">Informations de débogage</div>
                <div class="card-body">
                  <h6>Requête Cypher actuelle :</h6>
                  <pre>{{ currentCypherQuery }}</pre>
                  
                  <h6>Réponse de l'API :</h6>
                  <pre style="max-height: 200px; overflow: auto;">{{ lastResponseDebug }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Assert from "assert-js";
import LoadingIcon from "@/components/LoadingIcon.vue";
import NeoVisComponent from "@/components/NeoVisComponent.vue";
import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";
import config_util from "../utils/config_util";
import axios from "axios";

export default {
  name: 'HomeView',
  components: { LoadingIcon, NeoVisComponent },
  data() {
    return {
      // Chat state
      chatMessages: [],
      userInput: "",
      isProcessing: false,
      threadId: null,
      examples: [],
      
      // Visualization state
      hasVisualizedGraph: false,
      currentCypherQuery: null,
      lastResponseDebug: null,
      visualizationError: null,
      showDebugInfo: false,
      
      // Speech recognition state
      isRecording: false,
      speechEnabled: true,
      
      // Azure Speech SDK
      recognizer: null,
      speechToken: null,
      speechRegion: null
    };
  },
  computed: {
    isDevMode() {
      return (process.env.NODE_ENV === 'development');
    },
    speechStatusText() {
      if (!this.speechEnabled) {
        return "Service de reconnaissance vocale indisponible";
      }
      if (this.isRecording) {
        return "Écoute en cours...";
      }
      return "Cliquez sur le microphone pour parler";
    }
  },
  async mounted() {
    console.log("HomeView mounted");
    
    // Load example questions
    this.fetchExamples();
    
    // Get speech token
    this.fetchSpeechToken();
  },
  beforeDestroy() {
    if (this.recognizer) {
      this.stopSpeechRecognition();
    }
  },
  methods: {
    // Fetch example questions from the backend
    async fetchExamples() {
      try {
        const response = await axios.get('/api/examples');
        this.examples = response.data;
      } catch (error) {
        console.error("Error fetching examples:", error);
        this.examples = [
          "Quels sont les capteurs présents à l'école maternelle?",
          "Quelle est la température actuelle dans la mairie?",
          "Montre-moi la consommation d'énergie de tous les bâtiments",
          "Quelles sont les relations entre les capteurs et les bâtiments?"
        ];
      }
    },
    
    // Fetch speech token from the backend
    async fetchSpeechToken() {
      try {
        const response = await axios.get('/api/speech-token');
        console.log("Raw speech token response:", response.data);
        
        if (response.data && response.data.token) {
          this.speechToken = response.data.token;
          this.speechRegion = response.data.region;
          this.speechEnabled = true;
          console.log("Speech token fetched successfully - length:", this.speechToken.length);
          return true;
        } else {
          console.error("Speech token response contained no token:", response.data);
          this.speechEnabled = false;
          return false;
        }
      } catch (error) {
        console.error("Error fetching speech token:", error);
        this.speechEnabled = false;
        return false;
      }
    },
    
    // Use an example question
    useExample(example) {
      this.userInput = example;
      this.sendMessage();
    },
    
    // Send a message to the assistant
    async sendMessage() {
      if (!this.userInput.trim() || this.isProcessing) {
        return;
      }
      
      const message = this.userInput.trim();
      this.userInput = "";
      
      // Add message to chat
      this.chatMessages.push({
        role: "user",
        content: message
      });
      
      // Scroll to bottom
      this.$nextTick(() => {
        const container = document.getElementById('chat-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
      
      // Set processing state
      this.isProcessing = true;
      
      try {
        // Send message to backend
        console.log("Sending message to backend:", message);
        const response = await axios.post('/api/chat', {
          message,
          thread_id: this.threadId
        });
        
        console.log("Received response from backend:", response.data);
        
        // Add assistant response to chat
        this.chatMessages.push({
          role: "assistant",
          content: response.data.response
        });
        
        // Update thread ID
        this.threadId = response.data.thread_id;
        
        // Store debug info
        this.lastResponseDebug = JSON.stringify(response.data, null, 2);
        
        // If there's a Cypher query, visualize it
        if (response.data.cypher_query) {
          console.log("Received Cypher query from API:", response.data.cypher_query);
          this.currentCypherQuery = response.data.cypher_query;
          this.hasVisualizedGraph = true;
          this.visualizationError = null;
        } else {
          console.warn("No Cypher query returned from API");
        }
        
        // Scroll to bottom
        this.$nextTick(() => {
          const container = document.getElementById('chat-container');
          if (container) {
            container.scrollTop = container.scrollHeight;
          }
        });
      } catch (error) {
        console.error("Error sending message:", error);
        
        // Add error message
        this.chatMessages.push({
          role: "assistant",
          content: `Désolé, j'ai rencontré une erreur: ${error.message || "Erreur inconnue"}`
        });
      } finally {
        // Reset processing state
        this.isProcessing = false;
      }
    },
    
    // Format message content (convert newlines to <br>, etc.)
    formatMessage(content) {
      if (!content) return '';
      
      // Replace newlines with <br>
      let processed = content.replace(/\n/g, '<br>');
      
      // Simple code block highlighting
      processed = processed.replace(/```(\w*)([\s\S]*?)```/g, (match, language, code) => {
        return `<pre class="code-block ${language}"><code>${code.trim()}</code></pre>`;
      });
      
      return processed;
    },
    
    // Toggle debug info
    toggleDebugInfo() {
      this.showDebugInfo = !this.showDebugInfo;
    },
    
    // Rerender graph
    rerenderGraph() {
      if (this.$refs.neovis) {
        this.$refs.neovis.rerender();
      }
    },
    
    // Visualization event handlers
    onVisualizationCompleted() {
      console.log("Visualization completed successfully");
      this.visualizationError = null;
    },
    
    onVisualizationError(error) {
      console.error("Visualization error:", error);
      this.visualizationError = error.message || "Une erreur s'est produite durant la visualisation";
    },
    
    // Speech recognition toggle
    toggleSpeechRecognition() {
      if (this.isRecording) {
        this.stopSpeechRecognition();
      } else {
        this.startSpeechRecognition();
      }
    },
    
    // Start speech recognition
    async startSpeechRecognition() {
      if (!this.speechEnabled) return;
      
      // Use the token from our backend
      if (!this.speechToken) {
        const tokenSuccess = await this.fetchSpeechToken();
        if (!tokenSuccess) {
          return;
        }
      }
      
      const token = this.speechToken;
      const region = this.speechRegion || config_util.azure_region();
      const language = config_util.azure_language();
      
      console.log("Starting speech recognition with:", { 
        hasToken: !!token, 
        tokenLength: token ? token.length : 0,
        region, 
        language 
      });
      
      try {
        if (!token) {
          throw new Error("Speech token is not available");
        }
        
        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
        speechConfig.speechRecognitionLanguage = language;
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        this.recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
        
        // Add extra debug here
        console.log("Recognizer created successfully:", !!this.recognizer);
        
      } catch (e) {
        console.error("Error creating speech recognizer:", e);
        this.isRecording = false;
        return;
      }
      
      const recognizer = this.recognizer;
      const sdk = SpeechSDK;
      
      // Update UI to show recording state
      this.isRecording = true;
      
      // Set up recognized speech handler - directly put text in input box
      recognizer.recognized = (sender, event) => {
        if (sdk.ResultReason.RecognizedSpeech === event.result.reason && event.result.text.length > 0) {
          const text = event.result.text;
          this.userInput += (this.userInput ? ' ' : '') + text;
        } else if (sdk.ResultReason.NoMatch === event.result.reason) {
          console.log("Speech could not be recognized");
        }
      };
      
      recognizer.startContinuousRecognitionAsync(
        () => {
          console.log("Recognition started");
        },
        (err) => {
          this.isRecording = false;
          console.error("Recognition start failed", err);
        }
      );
    },
    
    // Stop speech recognition
    stopSpeechRecognition() {
      this.isRecording = false;
      
      if (!this.recognizer) return;
      
      this.recognizer.stopContinuousRecognitionAsync(() => {
        console.log("Recognition stopped");
        this.recognizer = null;
      }, (err) => {
        console.error("Error stopping recognition:", err);
        this.recognizer = null;
      });
    }
  }
};
</script>

<style scoped>
.homeview_container {
  display: flex;
  flex-direction: column;
  padding: 0 10px; /* Add padding to ensure full width doesn't cause overflow */
}

/* Chat styles */
.chat-card {
  height: 550px;
  display: flex;
  flex-direction: column;
}

.chat-card .card-body {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.chat-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.chat-message {
  margin-bottom: 1.5rem;
  max-width: 85%;
}

.user-message {
  margin-left: auto;
}

.assistant-message {
  margin-right: auto;
}

.message-content {
  padding: 1rem;
  border-radius: 1rem;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.user-message .message-content {
  background-color: var(--primary-color);
  color: white;
  border-top-right-radius: 0;
}

.assistant-message .message-content {
  background-color: var(--chat-assistant-bg);
  border-top-left-radius: 0;
}

/* Chat input */
.chat-input-container {
  padding: 1rem;
  background-color: #f8f9fa;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

form {
  position: relative;
}

.form-control {
  border-radius: 2rem;
  padding-right: 5.5rem;
  height: 3rem;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.send-btn, .speech-btn {
  position: absolute;
  top: 0;
  height: 3rem;
  width: 3rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.send-btn {
  right: 3.5rem;
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.speech-btn {
  right: 0;
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
  color: #333;
}

.speech-btn.recording {
  background-color: #dc3545;
  border-color: #dc3545;
  color: white;
  animation: pulse 1.5s infinite;
}

.speech-btn.disabled {
  background-color: #6c757d;
  border-color: #6c757d;
  opacity: 0.5;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.speech-status {
  font-size: 0.8rem;
  color: #666;
  text-align: center;
  margin-top: 0.5rem;
  height: 1.2rem;
}

/* Suggestion buttons */
.suggestion-container {
  background-color: white;
  border-radius: var(--border-radius);
  padding: 1.5rem;
  box-shadow: var(--box-shadow);
}

.suggestion-btn {
  padding: 0.75rem 1rem;
  background-color: white;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.5rem;
  text-align: left;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 10px rgba(0, 0, 0, 0.1);
  border-color: var(--primary-color);
}

/* Visualization */
.viz-card {
  min-height: 550px;
  display: flex;
  flex-direction: column;
}

.viz-card .card-body {
  flex-grow: 1;
  padding: 0;
  position: relative;
}

.viz-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  z-index: 0;
}

.viz-icon {
  font-size: 3rem;
  color: var(--primary-color);
  opacity: 0.3;
  margin-bottom: 1rem;
}

/* Debug controls */
.debug-controls {
  position: absolute;
  right: 10px;
  top: 10px;
}

.debug-info {
  font-size: 12px;
}

.debug-info pre {
  font-size: 11px;
  background-color: #f8f9fa;
  padding: 8px;
  border-radius: 4px;
  max-width: 100%;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Code block styling */
.code-block {
  background-color: #f5f5f5;
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
  margin: 1rem 0;
  font-family: monospace;
}

/* Responsive adjustments */
@media (max-width: 992px) {
  .viz-card {
    margin-top: 1rem;
    min-height: 400px;
  }
  
  .chat-card {
    height: 500px;
  }
}
</style>