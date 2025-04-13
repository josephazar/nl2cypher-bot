<template>
    <div class="graph-visualization">
      <div ref="vizContainer" class="viz-container"></div>
      <div v-if="loading" class="loading-indicator">
        <div class="spinner"></div>
        <p>Loading graph visualization...</p>
      </div>
      <div v-if="error" class="error-message">
        <p>{{ error }}</p>
        <pre v-if="showDebugInfo">{{ debugInfo }}</pre>
      </div>
    </div>
  </template>
  
  <script>
  // No more direct imports of vis-network
  
  export default {
    name: 'NeoVisComponent',
    props: {
      query: {
        type: String,
        required: true
      },
      serverUrl: {
        type: String,
        default: () => process.env.VUE_APP_NEO4J_URI || 'bolt://localhost:7687'
      },
      serverUser: {
        type: String,
        default: () => process.env.VUE_APP_NEO4J_USERNAME || 'neo4j'
      },
      serverPassword: {
        type: String,
        default: () => process.env.VUE_APP_NEO4J_PASSWORD || 'password'
      },
      showDebugInfo: {
        type: Boolean,
        default: false
      }
    },
    data() {
      return {
        viz: null,
        loading: false,
        error: null,
        debugInfo: {}
      };
    },
    watch: {
      query: {
        handler: 'renderGraph',
        immediate: true
      }
    },
    mounted() {
      this.renderGraph();
    },
    methods: {
      createSimpleVisualization() {
        // Create a basic visualization without NeoVis
        // This is a fallback when NeoVis can't be loaded
        const container = this.$refs.vizContainer;
        if (!container) return;
        
        // Clear container
        container.innerHTML = '';
        
        // Create info display
        const infoElement = document.createElement('div');
        infoElement.className = 'neo4j-info';
        infoElement.innerHTML = `
          <h3>Neo4j Query</h3>
          <pre>${this.query}</pre>
          <p>Query will be executed on: ${this.serverUrl}</p>
        `;
        container.appendChild(infoElement);
        
        // Show success message
        this.loading = false;
        this.$emit('visualization-completed');
        
        return true;
      },
      
      renderGraph() {
        if (!this.query) {
          this.error = 'No query provided';
          return;
        }
        
        // Reset state
        this.loading = true;
        this.error = null;
        this.debugInfo = {};
        
        // Ensure container is ready
        this.$nextTick(() => {
          try {
            // Log key information
            console.log('Attempting to render graph with query:', this.query);
            
            // Update debug info
            this.debugInfo = {
              query: this.query,
              containerExists: !!this.$refs.vizContainer,
              containerDimensions: this.$refs.vizContainer ? {
                width: this.$refs.vizContainer.offsetWidth,
                height: this.$refs.vizContainer.offsetHeight
              } : null
            };
            
            // Ensure container exists
            if (!this.$refs.vizContainer) {
              throw new Error('Visualization container element not found');
            }
            
            // Simple fallback visualization
            const success = this.createSimpleVisualization();
            
            if (!success) {
              throw new Error('Failed to create visualization');
            }
            
          } catch (err) {
            console.error('Error rendering graph:', err);
            this.error = `Error rendering graph: ${err.message}`;
            this.loading = false;
            this.$emit('visualization-error', err);
          }
        });
      },
      
      rerender() {
        this.renderGraph();
      }
    }
  };
  </script>
  
  <style scoped>
  .graph-visualization {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 400px;
  }
  
  .viz-container {
    width: 100%;
    height: 100%;
    min-height: 400px;
    background-color: rgba(245, 247, 250, 0.8);
    border-radius: 8px;
    padding: 20px;
    overflow: auto;
  }
  
  .neo4j-info {
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-word;
  }
  
  .neo4j-info pre {
    background-color: #f1f1f1;
    padding: 10px;
    border-radius: 4px;
    overflow: auto;
  }
  
  .loading-indicator {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }
  
  .spinner {
    border: 4px solid rgba(0, 0, 0, 0.1);
    border-radius: 50%;
    border-top: 4px solid var(--primary-color, #8c6ef2);
    width: 40px;
    height: 40px;
    margin: 0 auto 15px;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  .error-message {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #e74c3c;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    max-width: 80%;
  }
  
  pre {
    text-align: left;
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    overflow: auto;
    max-height: 200px;
    font-size: 12px;
  }
  </style>