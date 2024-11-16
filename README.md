# Magic Transcript 🎥 ✨

A powerful web application that automatically generates AI-powered summaries of YouTube video transcripts. Get the key points of any YouTube video in seconds!

## Features 🚀

- **YouTube Transcript Extraction**: Automatically fetch transcripts from any YouTube video
- **Multi-Language Support**: Access transcripts in different available languages
- **AI-Powered Summarization**: Choose from multiple AI providers:
  - Google Gemini
  - OpenAI GPT
  - Anthropic Claude
- **Modern UI**: Clean, responsive interface with dark/light mode
- **Copy Functionality**: Easy one-click copy for both transcripts and summaries
- **Real-time Processing**: Watch the magic happen as your content is processed
- **Expert Summarization**: Utilizes AI to extract the most important 20% of information that covers 80% of the video's content

## Quick Start 🏃‍♂️

1. **Clone the Repository**:
```bash
git clone https://github.com/blackfight999/Magic-transcript.git
cd Magic-transcript
```

2. **Set Up Environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run Locally**:
```bash
python app.py
```

4. Visit `http://localhost:3000` in your browser

## AI Service Setup 🤖

You'll need to provide your own API key for your chosen AI service:

1. **Google Gemini**:
   - Get API key from: https://makersuite.google.com/app/apikey
   - Free tier available with generous limits
   - Recommended for best performance/cost ratio

2. **OpenAI**:
   - Get API key from: https://platform.openai.com/api-keys
   - Requires payment method
   - Provides high-quality summaries

3. **Anthropic Claude**:
   - Get API key from: https://console.anthropic.com/
   - Requires approved account
   - Excellent for detailed analysis

## Docker Deployment 🐳

```bash
# Build the image
docker build -t magic-transcript .

# Run the container
docker run -p 3000:3000 magic-transcript
```

## Tech Stack 💻

- **Backend**: Python/Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **AI Services**: 
  - Google Gemini Pro
  - OpenAI GPT
  - Anthropic Claude
- **APIs**: YouTube Transcript API
- **Dependencies**: 
  - Flask >= 2.3.2
  - youtube-transcript-api >= 0.6.1
  - Multiple AI service SDKs
  - See requirements.txt for full list

## Security 🔒

- API keys are stored in session storage only
- No persistent storage of sensitive data
- Clean session management
- Input validation and sanitization

## How It Works 🔍

1. **Transcript Extraction**:
   - Enter a YouTube URL
   - The app extracts available transcripts using the YouTube Transcript API
   - Select your preferred language if multiple options are available

2. **AI Processing**:
   - Choose your preferred AI service
   - Enter your API key (stored securely in session)
   - The app processes the transcript using expert prompting
   - Receive a structured summary focusing on key points

3. **Results**:
   - View both the original transcript and AI summary
   - Copy results with one click
   - Toggle between light and dark modes for comfortable viewing

## Contributing 🤝

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License 📝

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- YouTube Transcript API for transcript extraction
- Google, OpenAI, and Anthropic for AI services
- The open-source community for inspiration and tools
