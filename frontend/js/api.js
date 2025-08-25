// API communication module for DubADubDub frontend

class DubbingAPI {
    constructor() {
        // Use the same host as the frontend, assuming backend serves on same domain
        this.baseUrl = window.location.origin;
        this.pollInterval = 2000; // Poll every 2 seconds for status updates
        this.maxRetries = 3;
        this.autoRetryEnabled = true; // Default to enabled
        this.retryDelays = [1000, 3000, 5000]; // Retry delays in ms
    }

    /**
     * Submit a video for dubbing with auto-retry
     * @param {string} youtubeUrl - The YouTube URL to process
     * @param {string} targetLanguage - Target language for dubbing
     * @param {Object} options - Additional options (quality, format, etc.)
     * @returns {Promise<Object>} Response containing session ID or error
     */
    async submitVideo(youtubeUrl, targetLanguage, options = {}) {
        return await this.withRetry(async () => {
            const response = await fetch(`${this.baseUrl}/process-video`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    target_language: targetLanguage,
                    ...options
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        }, 'video submission');
    }

    /**
     * Submit multiple videos for batch processing
     * @param {Array<string>} youtubeUrls - Array of YouTube URLs
     * @param {string} targetLanguage - Target language for all videos
     * @param {Object} options - Additional options
     * @param {Function} onProgress - Progress callback
     * @returns {Promise<Array>} Array of results
     */
    async submitBatch(youtubeUrls, targetLanguage, options = {}, onProgress = null) {
        const results = [];
        const total = youtubeUrls.length;
        
        for (let i = 0; i < youtubeUrls.length; i++) {
            const url = youtubeUrls[i];
            if (onProgress) {
                onProgress({ current: i + 1, total, currentUrl: url });
            }
            
            try {
                const result = await this.submitVideo(url, targetLanguage, options);
                results.push({ url, success: true, result });
            } catch (error) {
                results.push({ url, success: false, error: error.message });
            }
        }
        
        return results;
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
     * Enable or disable automatic retry
     * @param {boolean} enabled - Whether to enable auto-retry
     */
    setAutoRetry(enabled) {
        this.autoRetryEnabled = enabled;
    }

    /**
     * Wrapper for operations with automatic retry
     * @param {Function} operation - The async operation to retry
     * @param {string} operationName - Name for logging
     * @param {number} maxRetries - Max retry attempts
     * @returns {Promise} Operation result
     */
    async withRetry(operation, operationName = 'operation', maxRetries = null) {
        if (!this.autoRetryEnabled) {
            return await operation();
        }
        
        const maxAttempts = maxRetries || this.maxRetries;
        let lastError;
        
        for (let attempt = 0; attempt <= maxAttempts; attempt++) {
            try {
                if (attempt > 0) {
                    console.log(`Retrying ${operationName} (attempt ${attempt + 1}/${maxAttempts + 1})`);
                }
                return await operation();
            } catch (error) {
                lastError = error;
                console.warn(`${operationName} attempt ${attempt + 1} failed:`, error.message);
                
                // Don't retry on certain errors
                if (this.isNonRetryableError(error)) {
                    throw error;
                }
                
                // Don't wait after the last attempt
                if (attempt < maxAttempts) {
                    const delay = this.retryDelays[Math.min(attempt, this.retryDelays.length - 1)];
                    await this.sleep(delay);
                }
            }
        }
        
        throw new Error(`${operationName} failed after ${maxAttempts + 1} attempts: ${lastError.message}`);
    }

    /**
     * Check if an error should not be retried
     * @param {Error} error - The error to check
     * @returns {boolean} True if error is non-retryable
     */
    isNonRetryableError(error) {
        const message = error.message.toLowerCase();
        return (
            message.includes('unauthorized') ||
            message.includes('forbidden') ||
            message.includes('not found') ||
            message.includes('bad request') ||
            message.includes('invalid') ||
            message.includes('malformed')
        );
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
        } else if (error.message.includes('failed after')) {
            return error.message + ' Auto-retry was attempted but unsuccessful.';
        } else {
            return error.message || 'An unexpected error occurred. Please try again.';
        }
    }

    /**
     * Parse YouTube URL to extract video ID and normalize format
     * @param {string} url - URL or video ID
     * @returns {string} Normalized YouTube URL
     */
    normalizeYouTubeUrl(url) {
        // If it's just a video ID, convert to full URL
        if (/^[\w-]{11}$/.test(url.trim())) {
            return `https://www.youtube.com/watch?v=${url.trim()}`;
        }
        
        // If it's already a URL, return as is
        return url.trim();
    }

    /**
     * Validate and parse multiple YouTube URLs
     * @param {string} urlsText - Text containing URLs (one per line)
     * @returns {Array<string>} Array of valid YouTube URLs
     */
    parseYouTubeUrls(urlsText) {
        const lines = urlsText.split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);
        
        const validUrls = [];
        const invalidUrls = [];
        
        for (const line of lines) {
            try {
                const normalizedUrl = this.normalizeYouTubeUrl(line);
                if (this.isValidYouTubeUrl(normalizedUrl)) {
                    validUrls.push(normalizedUrl);
                } else {
                    invalidUrls.push(line);
                }
            } catch (error) {
                invalidUrls.push(line);
            }
        }
        
        if (invalidUrls.length > 0) {
            console.warn('Invalid URLs found:', invalidUrls);
        }
        
        return validUrls;
    }
}