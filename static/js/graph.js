/**
 * Graph visualization functionality for the Badevel Living Lab Assistant
 * using NeoVis.js
 */

// DOM elements
const vizContainer = document.getElementById('viz-container');
const vizPlaceholder = document.getElementById('viz-placeholder');

// Visualization state
const vizState = {
    viz: null,
    isInitialized: false,
    lastQuery: null,
};

// Neo4j connection configuration
const neo4jConfig = {
    // These will be replaced with actual connection details from the backend
    // or will use environment variables on the client side
    serverUrl: 'bolt://localhost:7687',
    serverUser: 'neo4j',
    serverPassword: 'password',
};

/**
 * Initialize NeoVis
 * @returns {Promise<void>}
 */
async function initializeNeoVis() {
    if (vizState.isInitialized) return;
    
    try {
        // Check if NeoVis is loaded
        if (!window.NeoVis) {
            throw new Error('NeoVis.js not loaded');
        }
        
        // Create visualization
        vizState.viz = new NeoVis.default({
            container: vizContainer,
            serverUrl: neo4jConfig.serverUrl,
            serverUser: neo4jConfig.serverUser,
            serverPassword: neo4jConfig.serverPassword,
            labels: {
                // Default styling for all node labels
                '*': {
                    caption: 'name',
                    size: 'pagerank',
                    community: 'community',
                    title_properties: [
                        'name',
                        'identifier',
                        'latest_value',
                        'description',
                    ],
                },
                // Specific styling for important node types
                'Sensor': {
                    caption: 'name',
                    size: '15',
                    color: '#8c6ef2',
                },
                'Thing': {
                    caption: 'name',
                    size: '20',
                    color: '#e0d539',
                },
                'Location': {
                    caption: 'name',
                    size: '25',
                    color: '#4CAF50',
                },
            },
            relationships: {
                // Default styling for all relationships
                '*': {
                    caption: true,
                    thickness: '2',
                    color: '#999',
                },
                // Specific styling for important relationship types
                'HAS_SENSOR': {
                    caption: 'HAS_SENSOR',
                    thickness: '3',
                    color: '#8c6ef2',
                },
                'LOCATED_AT': {
                    caption: 'LOCATED_AT',
                    thickness: '3',
                    color: '#4CAF50',
                },
            },
            initialCypher: 'MATCH (n) RETURN n LIMIT 10', // Default query
            visConfig: {
                nodes: {
                    shape: 'dot',
                    font: {
                        size: 14,
                        face: 'Segoe UI',
                    },
                    scaling: {
                        min: 10,
                        max: 30,
                    },
                },
                edges: {
                    arrows: {
                        to: {enabled: true, scaleFactor: 0.5},
                    },
                    font: {
                        size: 12,
                        face: 'Segoe UI',
                    },
                },
                physics: {
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 100,
                        springConstant: 0.08,
                    },
                    stabilization: {
                        enabled: true,
                        iterations: 1000,
                        updateInterval: 100,
                    },
                },
            },
        });
        
        // Mark as initialized
        vizState.isInitialized = true;
        
        // Render the initial state
        await vizState.viz.render();
        
        // Hide placeholder, show visualization
        vizPlaceholder.style.display = 'none';
        vizContainer.classList.remove('d-none');
        
    } catch (error) {
        console.error('Error initializing NeoVis:', error);
        vizPlaceholder.innerHTML = `
            <i class="fas fa-exclamation-triangle viz-icon" style="color: #dc3545;"></i>
            <p>Error initializing visualization: ${error.message}</p>
        `;
    }
}

/**
 * Visualize a graph using a Cypher query
 * @param {string} query - Cypher query
 */
async function visualizeGraph(query) {
    try {
        // Initialize NeoVis if not already initialized
        if (!vizState.isInitialized) {
            await initializeNeoVis();
        }
        
        // Store last query
        vizState.lastQuery = query;
        
        // Show visualization container, hide placeholder
        vizPlaceholder.style.display = 'none';
        vizContainer.classList.remove('d-none');
        
        // Run the query
        vizState.viz.clearNetwork();
        vizState.viz.updateWithCypher(query);
        
    } catch (error) {
        console.error('Error visualizing graph:', error);
    }
}

// Expose functions globally
window.graphFunctions = {
    visualizeGraph,
    initializeNeoVis,
};