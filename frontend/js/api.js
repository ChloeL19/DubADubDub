// API communication module for DubADubDub frontend

class DubbingAPI {
    constructor() {
        // Use the same host as the frontend, assuming backend serves on same domain
        this.baseUrl = window.location.origin;
        this.pollInterval = 2000; // Poll every 2 seconds for status updates
        this.maxRetries = 3;
    }

    /**
     * Submit a video for dubbing
     * @param {string} youtubeUrl - The YouTube URL to process
     * @param {string} targetLanguage - Target language for dubbing
     * @returns {Promise<Object>} Response containing session ID or error
     */
    async submitVideo(youtubeUrl, targetLanguage) {
        try {
            const response = await fetch(`${this.baseUrl}/process-video`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    target_language: targetLanguage
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('Error submitting video:', error);
            throw new Error(`Failed to submit video: ${error.message}`);
        }
    }

    /**
     * Check the status of a dubbing job
     * @param {string} sessionId - The session ID from video submission
     * @returns {Promise<Object>} Status information
     */
    async checkStatus(sessionId) {
        try {
            const response = await fetch(`${this.baseUrl}/status/${sessionId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('Error checking status:', error);
            throw new Error(`Failed to check status: ${error.message}`);
        }
    }

    /**
     * Get download URL for completed video
     * @param {string} sessionId - The session ID
     * @returns {Promise<string>} Download URL
     */
    async getDownloadUrl(sessionId) {
        try {
            const response = await fetch(`${this.baseUrl}/download/${sessionId}`, {
                method: 'GET'
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            // Return the URL for download
            return `${this.baseUrl}/download/${sessionId}`;
        } catch (error) {
            console.error('Error getting download URL:', error);
            throw new Error(`Failed to get download URL: ${error.message}`);
        }
    }

    /**
     * Poll for status updates until completion or error
     * @param {string} sessionId - The session ID
     * @param {Function} onUpdate - Callback for status updates
     * @returns {Promise<Object>} Final status
     */
    async pollForCompletion(sessionId, onUpdate) {
        let retries = 0;
        
        while (retries < this.maxRetries) {
            try {
                const status = await this.checkStatus(sessionId);
                
                if (onUpdate) {
                    onUpdate(status);
                }

                // Check if processing is complete
                if (status.status === 'completed') {
                    return status;
                } else if (status.status === 'error' || status.status === 'failed') {
                    throw new Error(status.error || 'Processing failed');
                }

                // Wait before next poll
                await this.sleep(this.pollInterval);
                retries = 0; // Reset retries on successful poll
                
            } catch (error) {
                retries++;
                console.warn(`Status check attempt ${retries} failed:`, error.message);
                
                if (retries >= this.maxRetries) {
                    throw new Error(`Status polling failed after ${this.maxRetries} retries: ${error.message}`);
                }
                
                // Wait before retry
                await this.sleep(this.pollInterval * retries);
            }
        }
    }

    /**
     * Utility function to sleep for a given duration
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Validate YouTube URL format
     * @param {string} url - URL to validate
     * @returns {boolean} True if valid YouTube URL
     */
    isValidYouTubeUrl(url) {
        const patterns = [
            /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
            /^https?:\/\/youtu\.be\/[\w-]+/,
            /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+/,
            /^https?:\/\/(www\.)?youtube\.com\/v\/[\w-]+/
        ];
        
        return patterns.some(pattern => pattern.test(url));
    }

    /**
     * Extract video ID from YouTube URL
     * @param {string} url - YouTube URL
     * @returns {string|null} Video ID or null if invalid
     */
    extractVideoId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) {
                return match[1];
            }
        }
        
        return null;
    }

    /**
     * Format error message for display
     * @param {Error} error - Error object
     * @returns {string} Formatted error message
     */
    formatErrorMessage(error) {
        if (error.message.includes('rate limit')) {
            return 'API rate limit exceeded. Please wait a few minutes and try again.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
            return 'Network connection error. Please check your internet connection and try again.';
        } else if (error.message.includes('unauthorized') || error.message.includes('auth')) {
            return 'Authentication error. Please contact support.';
        } else if (error.message.includes('not found') || error.message.includes('404')) {
            return 'Video not found or unavailable. Please check the YouTube URL.';
        } else {
            return error.message || 'An unexpected error occurred. Please try again.';
        }
    }
}