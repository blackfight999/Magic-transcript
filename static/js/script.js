document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('youtube-url');
    const transcribeBtn = document.getElementById('transcribe-btn');
    const copyTranscriptBtn = document.getElementById('copy-transcript-btn');
    const copyAnalysisBtn = document.getElementById('copy-analysis-btn');
    const loader = document.getElementById('loader');
    const resultSection = document.getElementById('result-section');
    const transcriptContent = document.getElementById('transcript-content');
    const analysisContent = document.getElementById('analysis-content');
    const errorMessage = document.getElementById('error-message');
    const themeToggle = document.getElementById('theme-toggle');
    const languageContainer = document.getElementById('language-container');
    const languageSelect = document.getElementById('language-select');
    const apiKeyModal = document.getElementById('api-key-modal');
    const apiServiceSelect = document.getElementById('ai-service');
    const apiKeyInput = document.getElementById('api-key');
    const saveApiKeyBtn = document.getElementById('save-api-key');
    const cancelApiKeyBtn = document.getElementById('cancel-api-key');
    const togglePasswordBtn = document.getElementById('toggle-password');
    const changeServiceBtn = document.getElementById('change-service-btn');
    const currentServiceLabel = document.getElementById('current-service-label');
    const aiServiceIndicator = document.getElementById('ai-service-indicator');

    // Theme Management
    const theme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', theme);
    themeToggle.querySelector('.theme-icon').textContent = theme === 'light' ? '☀️' : '🌙';

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        themeToggle.querySelector('.theme-icon').textContent = newTheme === 'light' ? '☀️' : '🌙';
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        resultSection.style.display = 'none';
        loader.style.display = 'none';
    }

    function clearError() {
        errorMessage.style.display = 'none';
        errorMessage.textContent = '';
    }

    async function getLanguages(url) {
        try {
            const response = await fetch('/get_languages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get languages');
            }

            return data.languages;
        } catch (error) {
            throw new Error(error.message || 'An unexpected error occurred');
        }
    }

    let currentService = localStorage.getItem('aiService') || null;

    function showApiKeyModal() {
        apiKeyModal.style.display = 'flex';
        if (currentService) {
            apiServiceSelect.value = currentService;
        }
    }

    function hideApiKeyModal() {
        apiKeyModal.style.display = 'none';
    }

    function updateServiceIndicator() {
        if (currentService) {
            currentServiceLabel.textContent = `Current Service: ${currentService.charAt(0).toUpperCase() + currentService.slice(1)}`;
            aiServiceIndicator.style.display = 'flex';
        } else {
            currentServiceLabel.textContent = 'No AI Service Selected';
            aiServiceIndicator.style.display = 'none';
        }
    }

    // Toggle password visibility
    togglePasswordBtn.addEventListener('click', () => {
        apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
    });

    // Save API Key
    saveApiKeyBtn.addEventListener('click', async () => {
        const service = apiServiceSelect.value;
        const apiKey = apiKeyInput.value.trim();

        if (!service || !apiKey) {
            alert('Please select a service and enter an API key');
            return;
        }

        try {
            const response = await fetch('/set_api_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ service, api_key: apiKey })
            });

            const result = await response.json();

            if (response.ok) {
                currentService = service;
                localStorage.setItem('aiService', service);
                updateServiceIndicator();
                hideApiKeyModal();
                apiKeyInput.value = '';
                alert(result.message);
            } else {
                alert(result.error || 'Failed to set API key');
            }
        } catch (error) {
            console.error('Error setting API key:', error);
            alert('An error occurred while setting the API key');
        }
    });

    // Cancel API Key Input
    cancelApiKeyBtn.addEventListener('click', () => {
        hideApiKeyModal();
    });

    // Change Service Button
    changeServiceBtn.addEventListener('click', showApiKeyModal);

    // Initial service indicator setup
    updateServiceIndicator();

    async function getTranscript(url, language = '') {
        try {
            if (!currentService) {
                showApiKeyModal();
                return;
            }

            loader.style.display = 'flex';
            clearError();

            const response = await fetch('/get_transcript', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url, 
                    lang_code: language,
                    service: currentService  // Add selected service
                }),
            });

            const data = await response.json();

            if (response.ok) {
                transcriptContent.textContent = data.transcript;
                analysisContent.innerHTML = data.processed_content.replace(/\n/g, '<br>');
                resultSection.style.display = 'block';
            } else {
                showError(data.error || 'Failed to get transcript');
            }
        } catch (error) {
            console.error('Transcript Error:', error);
            showError('An error occurred while fetching the transcript');
        } finally {
            loader.style.display = 'none';
        }
    }

    async function copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            const originalIcon = button.querySelector('.copy-icon').textContent;
            button.querySelector('.copy-icon').textContent = '✓';
            setTimeout(() => {
                button.querySelector('.copy-icon').textContent = originalIcon;
            }, 2000);
        } catch (err) {
            showError('Failed to copy text. Please try again.');
        }
    }

    async function loadLanguages(url) {
        try {
            const languages = await getLanguages(url);
            
            // Clear previous options
            languageSelect.innerHTML = '<option value="">Select Language</option>';
            
            // Add new language options
            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.code;
                option.textContent = `${lang.name} (${lang.type})`;
                languageSelect.appendChild(option);
            });
            
            // Show language selector if languages are available
            languageContainer.style.display = languages.length > 0 ? 'block' : 'none';
            
            return languages.length > 0;
        } catch (error) {
            showError(error.message);
            return false;
        }
    }

    urlInput.addEventListener('blur', async () => {
        const url = urlInput.value.trim();
        if (url) {
            await loadLanguages(url);
        }
    });

    transcribeBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const selectedLanguage = languageSelect.value;
        
        if (!url) {
            showError('Please enter a YouTube URL');
            return;
        }

        clearError();
        loader.style.display = 'flex';
        resultSection.style.display = 'none';

        try {
            const result = await getTranscript(url, selectedLanguage);
        } catch (error) {
            showError(error.message);
        } finally {
            loader.style.display = 'none';
        }
    });

    copyTranscriptBtn.addEventListener('click', async () => {
        await copyToClipboard(transcriptContent.textContent, copyTranscriptBtn);
    });

    copyAnalysisBtn.addEventListener('click', async () => {
        await copyToClipboard(analysisContent.textContent, copyAnalysisBtn);
    });

    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            transcribeBtn.click();
        }
    });

    // Add smooth transitions for result sections
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });

    [analysisContent, transcriptContent].forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(element);
    });
});
