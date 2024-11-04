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

    async function getTranscript(url, language = '') {
        try {
            const response = await fetch('/get_transcript', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, language }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get transcript');
            }

            return data;
        } catch (error) {
            throw new Error(error.message || 'An unexpected error occurred');
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
            
            transcriptContent.textContent = result.transcript;
            analysisContent.innerHTML = result.processed_content.replace(/\n/g, '<br>');
            
            resultSection.style.display = 'block';
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
