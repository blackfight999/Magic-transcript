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

## DigitalOcean Deployment 🌊

1. **Create a Droplet**:
   - Sign up/login to [DigitalOcean](https://www.digitalocean.com)
   - Create a new Droplet
   - Choose Ubuntu 22.04 LTS
   - Select Basic plan (minimum 1GB RAM)
   - Choose a datacenter region
   - Add your SSH key or create a password
   - Click "Create Droplet"

2. **Connect to Your Droplet**:
```bash
ssh root@your_droplet_ip
```

3. **Install Dependencies**:
```bash
# Update system packages
apt update && apt upgrade -y

# Install Python and required packages
apt install python3-pip python3-venv nginx -y

# Install Git
apt install git -y
```

4. **Clone and Setup Application**:
```bash
# Clone repository
git clone https://github.com/blackfight999/Magic-transcript.git
cd Magic-transcript

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

5. **Create Systemd Service**:
```bash
# Create service file
cat > /etc/systemd/system/magictranscript.service << EOL
[Unit]
Description=Magic Transcript Gunicorn Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/Magic-transcript
Environment="PATH=/root/Magic-transcript/venv/bin"
ExecStart=/root/Magic-transcript/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
EOL

# Start and enable service
systemctl start magictranscript
systemctl enable magictranscript
```

6. **Configure Nginx**:
```bash
# Create Nginx config
cat > /etc/nginx/sites-available/magictranscript << EOL
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL

# Create symlink and test config
ln -s /etc/nginx/sites-available/magictranscript /etc/nginx/sites-enabled/
nginx -t

# Remove default nginx site and restart
rm /etc/nginx/sites-enabled/default
systemctl restart nginx
```

7. **Setup Firewall**:
```bash
# Configure UFW
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

8. **SSL Certificate (Optional)**:
```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Obtain SSL certificate
certbot --nginx -d your_domain
```

Your application should now be accessible at `http://your_domain_or_ip` (or `https://` if you configured SSL).

## Maintenance and Monitoring 🔧

- **View Application Logs**:
```bash
journalctl -u magictranscript.service
```

- **Restart Application**:
```bash
systemctl restart magictranscript
```

- **Monitor System Resources**:
```bash
htop  # Install with: apt install htop
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
