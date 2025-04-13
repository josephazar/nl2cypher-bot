/**
 * Configuration utilities for the application
 */

export default {
    /**
     * Get GPT model name
     * @returns {string} - Model name
     */
    gpt_model() {
      return localStorage.getItem('gpt_model') || 'gpt-4'
    },
  
    /**
     * Get system prompt for GPT
     * @returns {string} - System prompt
     */
    gpt_system_prompt() {
      return localStorage.getItem('gpt_system_prompt') || 'You are a helpful assistant.'
    },
  
    /**
     * Get Azure speech region
     * @returns {string} - Azure region
     */
    azure_region() {
      return localStorage.getItem('azure_region') || 'westeurope'
    },
  
    /**
     * Get Azure speech language
     * @returns {string} - Language code
     */
    azure_language() {
      return localStorage.getItem('azure_language') || 'fr-FR'
    }
  }