// Main application logic for DubADubDub frontend

class DubbingApp {
    constructor() {
        this.api = new DubbingAPI();
        this.currentSessionId = null;
        this.isProcessing = false;
        this.currentYouTubeUrl = null;
        
        this.initializeElements();
        this.bindEvents();
        this.loadUserPreferences();
    }

    initializeElements() {
        // Form elements
        this.form = document.getElementById('dubbingForm');
        this.urlInput = document.getElementById('youtubeUrl');
        this.languageSelect = document.getElementById('targetLanguage');
        this.submitBtn = document.getElementById('submitBtn');

        // Drag-and-drop elements
        this.dropZone = document.getElementById('dropZone');

        // Advanced settings elements
        this.toggleSettingsBtn = document.getElementById('toggleSettings');
        this.settingsPanel = document.getElementById('settingsPanel');
        this.toggleArrow = this.toggleSettingsBtn.querySelector('.toggle-arrow');
        this.videoQualitySelect = document.getElementById('videoQuality');
        this.audioQualitySelect = document.getElementById('audioQuality');
        this.exportFormatSelect = document.getElementById('exportFormat');
        this.preserveOriginalCheckbox = document.getElementById('preserveOriginal');
        this.autoRetryCheckbox = document.getElementById('autoRetry');


        // Status elements
        this.statusSection = document.getElementById('statusSection');
        this.statusMessage = document.getElementById('statusMessage');
        this.progressBar = document.getElementById('progressBar');
        this.progressFill = document.getElementById('progressFill');
        this.estimatedTime = document.getElementById('estimatedTime');
        this.funFact = document.getElementById('funFact');

        // Progress step elements
        this.progressSteps = {
            download: document.getElementById('step-download'),
            transcribe: document.getElementById('step-transcribe'),
            translate: document.getElementById('step-translate'),
            synthesize: document.getElementById('step-synthesize'),
            overlay: document.getElementById('step-overlay')
        };

        // Error elements
        this.errorSection = document.getElementById('errorSection');
        this.errorMessage = document.getElementById('errorMessage');
        this.retryBtn = document.getElementById('retryBtn');

        // Result elements
        this.resultSection = document.getElementById('resultSection');
        this.resultMessage = document.getElementById('resultMessage');
        this.downloadLink = document.getElementById('downloadLink');
        this.newDubbingBtn = document.getElementById('newDubbingBtn');
        
        // Video preview elements
        this.dubbedVideoPreview = document.getElementById('dubbedVideoPreview');
        this.videoSource = document.getElementById('videoSource');
        this.playVideoBtn = document.getElementById('playVideoBtn');
        this.videoLoadingMessage = document.getElementById('videoLoadingMessage');
        this.videoPreviewContainer = document.querySelector('.video-preview-container');

        // Before/After comparison elements
        this.previewTab = document.getElementById('previewTab');
        this.comparisonTab = document.getElementById('comparisonTab');
        this.singlePreview = document.getElementById('singlePreview');
        this.beforeAfterComparison = document.getElementById('beforeAfterComparison');
        this.originalVideoLink = document.getElementById('originalVideoLink');
        this.dubbedVideoComparison = document.getElementById('dubbedVideoComparison');
        this.videoSourceComparison = document.getElementById('videoSourceComparison');
        this.syncPlaybackBtn = document.getElementById('syncPlayback');
        this.toggleMuteBtn = document.getElementById('toggleMute');

        // Initialize fun facts
        this.funFacts = [
            "Did you know? Our AI can detect and translate over 100 languages automatically!",
            "Fun fact: ElevenLabs can generate incredibly realistic voices in multiple languages.",
            "Interesting: The AI translation preserves the original speaking style and tone.",
            "Cool feature: The system can handle background music and sound effects separately.",
            "Amazing: Each dubbed video is processed through 5 specialized AI stages.",
            "Did you know? The voice synthesis can match different accents and speaking patterns.",
            "Fun fact: Our pipeline can process videos up to several hours long!",
            "Interesting: The AI preserves timing and emotional nuances during translation."
        ];
        this.currentFactIndex = 0;
        this.factInterval = null;
    }

    bindEvents() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Retry button
        this.retryBtn.addEventListener('click', () => this.handleRetry());
        
        // New dubbing button
        this.newDubbingBtn.addEventListener('click', () => this.resetForm());

        // Drag-and-drop events
        this.bindDragDropEvents();

        // Advanced settings events
        this.toggleSettingsBtn.addEventListener('click', () => this.toggleSettings());
        this.autoRetryCheckbox.addEventListener('change', () => this.updateAutoRetryPreference());


        // Comparison view events
        this.previewTab.addEventListener('click', () => this.switchToPreviewView());
        this.comparisonTab.addEventListener('click', () => this.switchToComparisonView());
        this.syncPlaybackBtn.addEventListener('click', () => this.syncVideoPlayback());
        this.toggleMuteBtn.addEventListener('click', () => this.toggleOriginalMute());
        
        // Video preview controls
        this.playVideoBtn.addEventListener('click', () => this.toggleVideoPlayback());
        this.dubbedVideoPreview.addEventListener('loadstart', () => this.handleVideoLoadStart());
        this.dubbedVideoPreview.addEventListener('loadeddata', () => this.handleVideoLoaded());
        this.dubbedVideoPreview.addEventListener('error', () => this.handleVideoError());
        this.dubbedVideoPreview.addEventListener('play', () => this.updatePlayButtonText());
        this.dubbedVideoPreview.addEventListener('pause', () => this.updatePlayButtonText());
        this.dubbedVideoPreview.addEventListener('ended', () => this.updatePlayButtonText());
        
        // URL input validation
        this.urlInput.addEventListener('blur', () => this.validateUrl());
        this.urlInput.addEventListener('input', () => this.clearUrlError());

        // Settings change handlers
        this.bindSettingsChangeEvents();
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isProcessing) {
            return;
        }

        const youtubeUrl = this.urlInput.value.trim();
        const targetLanguage = this.languageSelect.value;

        // Validate inputs
        if (!this.validateInputs(youtubeUrl, targetLanguage)) {
            return;
        }

        try {
            await this.startDubbing(youtubeUrl, targetLanguage);
        } catch (error) {
            this.showError(error);
        }
    }

    validateInputs(youtubeUrl, targetLanguage) {
        // Reset previous errors
        this.clearErrors();

        let isValid = true;

        // Validate YouTube URL
        if (!youtubeUrl) {
            this.showFieldError(this.urlInput, 'Please enter a YouTube URL');
            isValid = false;
        } else if (!this.api.isValidYouTubeUrl(youtubeUrl)) {
            this.showFieldError(this.urlInput, 'Please enter a valid YouTube URL');
            isValid = false;
        }

        // Validate language selection
        if (!targetLanguage) {
            this.showFieldError(this.languageSelect, 'Please select a target language');
            isValid = false;
        }

        return isValid;
    }

    validateUrl() {
        const url = this.urlInput.value.trim();
        if (url && !this.api.isValidYouTubeUrl(url)) {
            this.showFieldError(this.urlInput, 'Please enter a valid YouTube URL');
            return false;
        }
        this.clearFieldError(this.urlInput);
        return true;
    }

    clearUrlError() {
        this.clearFieldError(this.urlInput);
    }

    showFieldError(field, message) {
        field.style.borderColor = '#e74c3c';
        
        // Remove existing error message
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.style.color = '#e74c3c';
        errorDiv.style.fontSize = '14px';
        errorDiv.style.marginTop = '5px';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.style.borderColor = '#e1e5e9';
        const errorDiv = field.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    clearErrors() {
        this.clearFieldError(this.urlInput);
        this.clearFieldError(this.languageSelect);
    }

    async startDubbing(youtubeUrl, targetLanguage) {
        this.isProcessing = true;
        this.setProcessingState(true);
        this.currentYouTubeUrl = youtubeUrl;
        
        try {
            // Get user settings
            const options = this.getUserSettings();
            
            // Submit video for processing
            this.updateStatus('Submitting video for processing...', 10);
            
            const response = await this.api.submitVideo(youtubeUrl, targetLanguage, options);
            this.currentSessionId = response.session_id;
            
            // Start polling for status
            this.updateStatus('Processing video...', 20);
            
            await this.api.pollForCompletion(
                this.currentSessionId,
                (status) => this.handleStatusUpdate(status)
            );
            
        } catch (error) {
            console.error('Dubbing process failed:', error);
            this.showError(error);
        } finally {
            this.isProcessing = false;
            this.setProcessingState(false);
        }
    }

    handleStatusUpdate(status) {
        let message = 'Processing...';
        let progress = 20;
        let currentStage = status.current_stage;

        // Map status to user-friendly messages and progress
        switch (currentStage) {
            case 'download':
                message = 'Downloading video from YouTube...';
                progress = 20;
                this.updateProgressSteps('download');
                break;
            case 'transcribe':
                message = 'Converting speech to text...';
                progress = 35;
                this.updateProgressSteps('transcribe');
                break;
            case 'translate':
                message = `Translating to ${status.target_language || 'target language'}...`;
                progress = 55;
                this.updateProgressSteps('translate');
                break;
            case 'synthesize':
                message = 'Generating natural-sounding speech...';
                progress = 75;
                this.updateProgressSteps('synthesize');
                break;
            case 'overlay':
                message = 'Combining dubbed audio with video...';
                progress = 90;
                this.updateProgressSteps('overlay');
                break;
            case 'completed':
                // Mark all steps as completed
                Object.values(this.progressSteps).forEach(step => {
                    step.classList.remove('active');
                    step.classList.add('completed');
                });
                this.stopFunFactRotation();
                this.showSuccess(status);
                return;
            default:
                message = `Processing: ${currentStage || 'Preparing'}...`;
                if (!currentStage) progress = 10;
        }

        if (status.progress) {
            progress = Math.min(status.progress, 99);
        }

        this.updateStatus(message, progress);
        
        // Update estimated time based on progress
        this.updateEstimatedTime(progress);
    }

    updateStatus(message, progress = 0) {
        this.hideAllSections();
        this.statusSection.style.display = 'block';
        
        // Smooth status message update
        this.updateStatusMessage(message);
        
        // Smooth progress update
        setTimeout(() => {
            this.progressFill.style.width = `${progress}%`;
        }, 50); // Small delay to ensure smooth transition
        
        // Start fun fact rotation if not already started
        if (!this.factInterval) {
            this.startFunFactRotation();
        }
    }
    
    updateStatusMessage(newMessage) {
        // Only update if message actually changed to avoid unnecessary transitions
        if (this.statusMessage.textContent !== newMessage) {
            // Fade out current message
            this.statusMessage.style.opacity = '0.6';
            
            setTimeout(() => {
                this.statusMessage.textContent = newMessage;
                // Fade back in
                this.statusMessage.style.opacity = '1';
            }, 150);
        }
    }

    updateProgressSteps(currentStage) {
        // Reset all steps
        Object.values(this.progressSteps).forEach(step => {
            step.classList.remove('active', 'completed');
        });

        // Define step order
        const stepOrder = ['download', 'transcribe', 'translate', 'synthesize', 'overlay'];
        const currentIndex = stepOrder.indexOf(currentStage);

        // Mark completed steps
        for (let i = 0; i < currentIndex; i++) {
            const stepName = stepOrder[i];
            if (this.progressSteps[stepName]) {
                this.progressSteps[stepName].classList.add('completed');
            }
        }

        // Mark current active step
        if (currentIndex >= 0 && this.progressSteps[currentStage]) {
            this.progressSteps[currentStage].classList.add('active');
        }
    }

    updateEstimatedTime(progress) {
        let timeText = '';
        
        if (progress < 20) {
            timeText = 'Estimated time: ~2-3 minutes';
        } else if (progress < 40) {
            timeText = 'Estimated time: ~2 minutes remaining';
        } else if (progress < 70) {
            timeText = 'Estimated time: ~1-2 minutes remaining';
        } else if (progress < 90) {
            timeText = 'Estimated time: ~30-60 seconds remaining';
        } else {
            timeText = 'Almost done! Finalizing your video...';
        }
        
        // Only update if the text actually changed
        if (this.estimatedTime.textContent !== timeText) {
            // Smooth transition for time updates
            this.estimatedTime.style.opacity = '0.7';
            this.estimatedTime.style.transform = 'translateY(2px)';
            
            setTimeout(() => {
                this.estimatedTime.textContent = timeText;
                this.estimatedTime.style.opacity = '1';
                this.estimatedTime.style.transform = 'translateY(0)';
            }, 150);
        }
    }

    startFunFactRotation() {
        // Show first fact immediately
        this.showNextFunFact();
        
        // Rotate facts every 8 seconds
        this.factInterval = setInterval(() => {
            this.showNextFunFact();
        }, 8000);
    }

    showNextFunFact() {
        const factTextElement = this.funFact.querySelector('.fun-fact-text') || this.funFact;
        
        // Add changing class to fade out current text
        this.funFact.classList.add('changing');
        
        setTimeout(() => {
            // Update to next fact
            factTextElement.textContent = this.funFacts[this.currentFactIndex];
            this.currentFactIndex = (this.currentFactIndex + 1) % this.funFacts.length;
            
            // Remove changing class to fade in new text
            this.funFact.classList.remove('changing');
            
            // Ensure the container is visible
            if (!this.funFact.classList.contains('show')) {
                this.funFact.classList.add('show');
            }
        }, 300); // Wait for fade out transition
    }

    stopFunFactRotation() {
        if (this.factInterval) {
            clearInterval(this.factInterval);
            this.factInterval = null;
        }
        this.funFact.classList.remove('show');
    }

    async showSuccess(status) {
        try {
            // Get download URL
            const downloadUrl = await this.api.getDownloadUrl(this.currentSessionId);
            
            // Show success section
            this.hideAllSections();
            this.resultSection.style.display = 'block';
            
            const duration = status.duration ? ` (${Math.round(status.duration)}s)` : '';
            this.resultMessage.innerHTML = `
                <strong>Success!</strong> Your video has been dubbed successfully${duration}.<br>
                <strong>Original Language:</strong> ${status.source_language || 'Auto-detected'}<br>
                <strong>Target Language:</strong> ${status.target_language}
            `;
            
            // Set up download link
            this.downloadLink.href = downloadUrl;
            this.downloadLink.download = `dubbed_video_${this.currentSessionId}.mp4`;
            
            // Set up video preview
            await this.setupVideoPreview(downloadUrl);
            
        } catch (error) {
            console.error('Error setting up download:', error);
            this.showError(new Error('Video processed successfully, but download setup failed. Please try again.'));
        }
    }

    showError(error) {
        this.stopFunFactRotation();
        this.hideAllSections();
        this.errorSection.style.display = 'block';
        this.errorMessage.textContent = this.api.formatErrorMessage(error);
        
        // Log detailed error for debugging
        console.error('Detailed error:', error);
    }

    handleRetry() {
        // Clear current session and retry
        this.currentSessionId = null;
        this.resetForm();
    }

    resetForm() {
        // Stop any ongoing processes
        this.stopFunFactRotation();
        
        // Reset video preview
        this.resetVideoPreview();
        
        // Reset form
        this.form.reset();
        this.currentSessionId = null;
        this.isProcessing = false;
        
        // Reset progress steps
        Object.values(this.progressSteps).forEach(step => {
            step.classList.remove('active', 'completed');
        });
        
        // Hide all sections and show form
        this.hideAllSections();
        this.form.style.display = 'block';
        
        // Clear any field errors
        this.clearErrors();
        
        // Reset button state
        this.setProcessingState(false);
    }
    
    resetVideoPreview() {
        // Reset video elements
        if (this.dubbedVideoPreview) {
            this.dubbedVideoPreview.pause();
            this.dubbedVideoPreview.currentTime = 0;
            this.videoSource.src = '';
        }
        
        // Hide video elements
        if (this.dubbedVideoPreview) this.dubbedVideoPreview.style.display = 'none';
        if (this.playVideoBtn) this.playVideoBtn.style.display = 'none';
        if (this.videoLoadingMessage) this.videoLoadingMessage.style.display = 'none';
        if (this.videoPreviewContainer) this.videoPreviewContainer.classList.remove('loading');
        
        // Reset button text
        if (this.playVideoBtn) this.playVideoBtn.textContent = '▶️ Play Preview';
    }

    hideAllSections() {
        this.statusSection.style.display = 'none';
        this.errorSection.style.display = 'none';
        this.resultSection.style.display = 'none';
    }

    setProcessingState(isProcessing) {
        if (isProcessing) {
            this.submitBtn.disabled = true;
            this.submitBtn.innerHTML = '<span class="loading"></span>Processing...';
            this.urlInput.disabled = true;
            this.languageSelect.disabled = true;
        } else {
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = 'Start Dubbing';
            this.urlInput.disabled = false;
            this.languageSelect.disabled = false;
        }
    }

    // Video preview methods
    async setupVideoPreview(videoUrl) {
        try {
            // Show loading state
            this.videoLoadingMessage.style.display = 'block';
            this.dubbedVideoPreview.style.display = 'none';
            this.playVideoBtn.style.display = 'none';
            this.videoPreviewContainer.classList.add('loading');
            
            // Set video source
            this.videoSource.src = videoUrl;
            this.dubbedVideoPreview.load();
            
            // The video will trigger loadeddata event when ready
        } catch (error) {
            console.error('Error setting up video preview:', error);
            this.handleVideoError();
        }
    }
    
    handleVideoLoadStart() {
        this.videoLoadingMessage.style.display = 'block';
        this.dubbedVideoPreview.style.display = 'none';
        this.playVideoBtn.style.display = 'none';
    }
    
    handleVideoLoaded() {
        // Hide loading, show video and play button
        this.videoLoadingMessage.style.display = 'none';
        this.dubbedVideoPreview.style.display = 'block';
        this.playVideoBtn.style.display = 'inline-block';
        this.videoPreviewContainer.classList.remove('loading');
        
        // Update play button text
        this.updatePlayButtonText();
    }
    
    handleVideoError() {
        this.videoLoadingMessage.style.display = 'none';
        this.videoLoadingMessage.textContent = 'Error loading video preview. You can still download the file.';
        this.videoLoadingMessage.style.display = 'block';
        this.dubbedVideoPreview.style.display = 'none';
        this.playVideoBtn.style.display = 'none';
        this.videoPreviewContainer.classList.remove('loading');
    }
    
    toggleVideoPlayback() {
        if (this.dubbedVideoPreview.paused) {
            this.dubbedVideoPreview.play();
        } else {
            this.dubbedVideoPreview.pause();
        }
        this.updatePlayButtonText();
    }
    
    updatePlayButtonText() {
        if (this.dubbedVideoPreview.paused) {
            this.playVideoBtn.textContent = '▶️ Play Preview';
        } else {
            this.playVideoBtn.textContent = '⏸️ Pause Preview';
        }
    }

    // Utility method to show notifications (can be enhanced)
    showNotification(message, type = 'info') {
        // Simple notification - can be enhanced with a proper notification system
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    // === NEW PR#5 METHODS ===

    // Drag-and-drop functionality
    bindDragDropEvents() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => this.highlight(), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => this.unhighlight(), false);
        });

        // Handle dropped files/text
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e), false);
        
        // Handle click to paste
        this.dropZone.addEventListener('click', () => this.handleDropZoneClick());
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight() {
        this.dropZone.classList.add('drag-over');
    }

    unhighlight() {
        this.dropZone.classList.remove('drag-over');
    }

    async handleDrop(e) {
        const dt = e.dataTransfer;
        
        // Handle text data (URLs)
        if (dt.types.includes('text/plain')) {
            const text = dt.getData('text/plain').trim();
            if (this.api.isValidYouTubeUrl(text)) {
                this.setUrlValue(text);
                return;
            }
        }
        
        // Handle files (not implemented for now, but ready for future)
        if (dt.files.length > 0) {
            this.showNotification('File uploads are not yet supported. Please paste a YouTube URL instead.', 'info');
        }
    }

    async handleDropZoneClick() {
        try {
            // Try to read clipboard
            if (navigator.clipboard && navigator.clipboard.readText) {
                const clipboardText = await navigator.clipboard.readText();
                if (this.api.isValidYouTubeUrl(clipboardText.trim())) {
                    this.setUrlValue(clipboardText.trim());
                } else {
                    this.showNotification('No valid YouTube URL found in clipboard', 'info');
                }
            } else {
                // Fallback: focus on input field
                this.urlInput.focus();
                this.urlInput.select();
            }
        } catch (error) {
            // User denied clipboard access or other error
            this.urlInput.focus();
            this.urlInput.select();
        }
    }

    setUrlValue(url) {
        this.urlInput.value = url;
        this.dropZone.classList.add('has-url');
        this.dropZone.querySelector('.drop-zone-text').textContent = 'URL set! Ready to dub.';
        this.dropZone.querySelector('.drop-zone-subtext').textContent = 'Click to change URL';
        
        // Validate the URL
        this.validateUrl();
    }

    clearUrlValue() {
        this.urlInput.value = '';
        this.dropZone.classList.remove('has-url');
        this.dropZone.querySelector('.drop-zone-text').textContent = 'Drop YouTube URL here or click to paste';
        this.dropZone.querySelector('.drop-zone-subtext').textContent = 'Supports YouTube links, video IDs, and share URLs';
    }

    // Advanced settings functionality
    toggleSettings() {
        const isVisible = this.settingsPanel.style.display !== 'none';
        this.settingsPanel.style.display = isVisible ? 'none' : 'block';
        this.toggleArrow.classList.toggle('rotated', !isVisible);
    }

    bindSettingsChangeEvents() {
        // Save settings when changed
        [this.videoQualitySelect, this.audioQualitySelect, this.exportFormatSelect, 
         this.preserveOriginalCheckbox, this.autoRetryCheckbox].forEach(element => {
            element.addEventListener('change', () => this.saveUserPreferences());
        });
    }

    getUserSettings() {
        return {
            video_quality: this.videoQualitySelect.value,
            audio_quality: this.audioQualitySelect.value,
            export_format: this.exportFormatSelect.value,
            preserve_original: this.preserveOriginalCheckbox.checked,
            auto_retry: this.autoRetryCheckbox.checked
        };
    }

    updateAutoRetryPreference() {
        this.api.setAutoRetry(this.autoRetryCheckbox.checked);
        this.saveUserPreferences();
    }


    // Before/After comparison functionality
    switchToPreviewView() {
        this.previewTab.classList.add('active');
        this.comparisonTab.classList.remove('active');
        this.singlePreview.style.display = 'block';
        this.beforeAfterComparison.style.display = 'none';
    }

    switchToComparisonView() {
        this.previewTab.classList.remove('active');
        this.comparisonTab.classList.add('active');
        this.singlePreview.style.display = 'none';
        this.beforeAfterComparison.style.display = 'block';
        
        // Set up comparison view
        this.setupComparisonView();
    }

    setupComparisonView() {
        if (this.currentYouTubeUrl) {
            this.originalVideoLink.href = this.currentYouTubeUrl;
        }
        
        // Copy dubbed video to comparison side
        if (this.videoSource.src) {
            this.videoSourceComparison.src = this.videoSource.src;
            this.dubbedVideoComparison.load();
        }
    }

    syncVideoPlayback() {
        // Sync playback between original and dubbed (if both are available)
        if (this.dubbedVideoComparison && !this.dubbedVideoComparison.paused) {
            const currentTime = this.dubbedVideoComparison.currentTime;
            // Could sync with original video if we had it loaded
            console.log('Sync playback at time:', currentTime);
        }
    }

    toggleOriginalMute() {
        // This would control original video muting if we had it
        const isMuted = this.toggleMuteBtn.textContent.includes('Unmute');
        this.toggleMuteBtn.textContent = isMuted ? '🔊 Mute Original' : '🔇 Unmute Original';
    }

    // User preferences
    loadUserPreferences() {
        const prefs = localStorage.getItem('dubadubdub-preferences');
        if (prefs) {
            try {
                const preferences = JSON.parse(prefs);
                
                if (preferences.videoQuality) this.videoQualitySelect.value = preferences.videoQuality;
                if (preferences.audioQuality) this.audioQualitySelect.value = preferences.audioQuality;
                if (preferences.exportFormat) this.exportFormatSelect.value = preferences.exportFormat;
                if (preferences.preserveOriginal !== undefined) this.preserveOriginalCheckbox.checked = preferences.preserveOriginal;
                if (preferences.autoRetry !== undefined) {
                    this.autoRetryCheckbox.checked = preferences.autoRetry;
                    this.api.setAutoRetry(preferences.autoRetry);
                }
            } catch (error) {
                console.warn('Could not load user preferences:', error);
            }
        }
    }

    saveUserPreferences() {
        const preferences = {
            videoQuality: this.videoQualitySelect.value,
            audioQuality: this.audioQualitySelect.value,
            exportFormat: this.exportFormatSelect.value,
            preserveOriginal: this.preserveOriginalCheckbox.checked,
            autoRetry: this.autoRetryCheckbox.checked
        };
        
        localStorage.setItem('dubadubdub-preferences', JSON.stringify(preferences));
    }

    // Enhanced showSuccess to support comparison view
    async showSuccess(status) {
        try {
            // Get download URL
            const downloadUrl = await this.api.getDownloadUrl(this.currentSessionId);
            
            // Show success section
            this.hideAllSections();
            this.resultSection.style.display = 'block';
            
            const duration = status.duration ? ` (${Math.round(status.duration)}s)` : '';
            this.resultMessage.innerHTML = `
                <strong>Success!</strong> Your video has been dubbed successfully${duration}.<br>
                <strong>Original Language:</strong> ${status.source_language || 'Auto-detected'}<br>
                <strong>Target Language:</strong> ${status.target_language}
            `;
            
            // Set up download link
            this.downloadLink.href = downloadUrl;
            this.downloadLink.download = `dubbed_video_${this.currentSessionId}.mp4`;
            
            // Set up video preview
            await this.setupVideoPreview(downloadUrl);
            
            // Initialize comparison view
            this.switchToPreviewView(); // Default to preview view
            
        } catch (error) {
            console.error('Error setting up download:', error);
            this.showError(new Error('Video processed successfully, but download setup failed. Please try again.'));
        }
    }

    // Override resetForm to handle new elements
    resetForm() {
        // Stop any ongoing processes
        this.stopFunFactRotation();
        
        // Reset video preview
        this.resetVideoPreview();
        
        // Reset form
        this.form.reset();
        this.currentSessionId = null;
        this.currentYouTubeUrl = null;
        this.isProcessing = false;
        
        // Reset drag-and-drop zone
        this.clearUrlValue();
        
        // Reset progress steps
        Object.values(this.progressSteps).forEach(step => {
            step.classList.remove('active', 'completed');
        });
        
        // Hide all sections and show form
        this.hideAllSections();
        this.form.style.display = 'block';
        
        // Clear any field errors
        this.clearErrors();
        
        // Reset button state
        this.setProcessingState(false);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dubbingApp = new DubbingApp();
});

// Handle any unhandled errors
window.addEventListener('error', (event) => {
    console.error('Unhandled error:', event.error);
    if (window.dubbingApp && !window.dubbingApp.isProcessing) {
        window.dubbingApp.showError(new Error('An unexpected error occurred. Please refresh the page and try again.'));
    }
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    event.preventDefault(); // Prevent default browser handling
    if (window.dubbingApp && !window.dubbingApp.isProcessing) {
        window.dubbingApp.showError(new Error('An unexpected error occurred. Please try again.'));
    }
});