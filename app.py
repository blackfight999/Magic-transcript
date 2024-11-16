# Standard library imports
import re
import os
import json
import logging
import functools
import threading
import queue
import time
from urllib.parse import urlparse
import requests

# Third-party library imports
from flask import Flask, render_template, request, jsonify, session
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai
import openai
import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def timeout_with_queue(func, timeout_seconds):
    """
    Run a function with a timeout using threading and queue
    
    Args:
        func (callable): Function to run
        timeout_seconds (int): Maximum time to allow function to run
    
    Returns:
        Result of the function or raises an exception
    """
    result_queue = queue.Queue()
    exception_queue = queue.Queue()

    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            result_queue.put(result)
        except Exception as e:
            exception_queue.put(e)

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        raise TimeoutError(f"Function call timed out after {timeout_seconds} seconds")

    if not exception_queue.empty():
        raise exception_queue.get()

    if not result_queue.empty():
        return result_queue.get()

    raise TimeoutError("Function did not return a result")

# Timeout decorator
class TimeoutError(Exception):
    """Timeout exception for long-running operations"""
    pass

def timeout(seconds):
    """
    Decorator to add timeout to functions
    
    Args:
        seconds (int): Maximum time to allow function to run
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return timeout_with_queue(func, seconds)(*args, **kwargs)
        return wrapper
    return decorator

def validate_youtube_url(url):
    """
    Validate YouTube URL format
    
    Args:
        url (str): URL to validate
    
    Returns:
        bool: Whether URL is a valid YouTube URL
    """
    try:
        parsed_url = urlparse(url)
        valid_domains = ['youtube.com', 'www.youtube.com', 'youtu.be']
        
        # Check domain
        if parsed_url.netloc not in valid_domains:
            return False
        
        # Check for video ID in different URL formats
        if 'youtu.be' in parsed_url.netloc:
            return bool(re.match(r'^/[a-zA-Z0-9_-]{11}$', parsed_url.path))
        
        # Check for video ID in standard YouTube URL
        return bool(re.search(r'(v=|embed/|v/)[a-zA-Z0-9_-]{11}', url))
    
    except Exception:
        return False

def configure_ai_service(service, api_key=None):
    """
    Configure AI service based on the selected provider
    
    Args:
        service (str): AI service to configure
        api_key (str, optional): API key for the service
    
    Returns:
        Configured client or None
    """
    try:
        # Use session API key if not provided
        if not api_key and service in session:
            api_key = session.get(f'{service}_api_key')
        
        # Validate API key
        if not api_key:
            raise ValueError(f"No API key provided for {service}")
        
        # Configure specific AI services
        if service == 'gemini':
            genai.configure(api_key=api_key)
            return None  # Gemini doesn't require a client object
        
        elif service == 'openai':
            openai.api_key = api_key
            return None  # OpenAI uses global configuration
        
        elif service == 'claude':
            return anthropic.Anthropic(api_key=api_key)
        
        else:
            raise ValueError(f"Unsupported AI service: {service}")
    
    except Exception as e:
        logger.error(f"Error configuring {service} service: {str(e)}")
        raise

def summarize_with_ai(transcript, service, api_key):
    """
    Flexible AI summarization with improved error handling and token management
    
    Args:
        transcript (str): Text to summarize
        service (str): AI service to use
        api_key (str): API key for the service
    
    Returns:
        str: Summarized text or error message
    """
    # Truncate transcript if too long
    MAX_TOKENS = 4000  # Adjust based on model limits
    if len(transcript) > MAX_TOKENS * 4:  # Rough token estimation
        logger.warning(f"Transcript truncated from {len(transcript)} to {MAX_TOKENS * 4} characters")
        transcript = transcript[:MAX_TOKENS * 4] + "... [Transcript truncated]"
    
    SUMMARY_PROMPT = """Given a text containing complex information about a specific topic, your role is to act as an expert summarizer with 20 years experience.

Summarize the following transcript, focusing on the most important 20% of the information. Break down complex ideas into easy-to-understand terms. Use bullet points or numbered lists to enhance readability.

Transcript:
{transcript}"""

    def generate_summary():
        # Configure AI service
        ai_client = configure_ai_service(service, api_key)
        
        if service == 'gemini':
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(SUMMARY_PROMPT.format(transcript=transcript))
            return response.text
        
        elif service == 'openai':
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert transcript summarizer with 20 years of experience."},
                    {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        
        elif service == 'claude':
            try:
                response = ai_client.messages.create(
                    model="claude-2.1",
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}
                    ]
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Claude API error: {str(e)}")
                return f"Error in Claude summarization: {str(e)}"
        
        # Add a fallback for unsupported services
        raise ValueError(f"Unsupported AI service: {service}")
    
    try:
        # Directly call the function instead of wrapping it
        return generate_summary()
    
    except Exception as e:
        logger.error(f"Error in AI summarization: {str(e)}")
        return f"Error in AI summarization: {str(e)}"

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu.be\/)([^&\n?]*)',
        r'(?:youtube\.com\/embed\/)([^&\n?]*)',
        r'(?:youtube\.com\/v\/)([^&\n?]*)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_transcript(video_id, lang_code=None):
    """
    Extract transcript from a YouTube video using YouTube Transcript API.
    
    Args:
        video_id (str): YouTube video ID
        lang_code (str, optional): Specific language code
    
    Returns:
        str: Extracted transcript text
    """
    try:
        # Retrieve all available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Get list of available language codes
        available_languages = []
        for transcript in transcript_list._manually_created_transcripts.values():
            available_languages.append(transcript.language_code)
        for transcript in transcript_list._generated_transcripts.values():
            available_languages.append(transcript.language_code)
        
        # If language specified, try to find that specific transcript
        if lang_code:
            try:
                # Attempt to find exact language match
                transcript = transcript_list.find_transcript([lang_code])
            except Exception:
                # Fallback to first generated transcript in available languages
                if available_languages:
                    transcript = transcript_list.find_generated_transcript(available_languages)
                else:
                    return "Error: No transcripts available for this video."
        else:
            # Get first available generated transcript
            if available_languages:
                transcript = transcript_list.find_generated_transcript(available_languages)
            else:
                return "Error: No transcripts available for this video."
        
        # Fetch transcript data
        transcript_data = transcript.fetch()
        
        # Validate transcript
        if not transcript_data:
            return "Error: Empty transcript retrieved."
        
        # Format transcript
        formatted_transcript = ' '.join([entry['text'] for entry in transcript_data])
        
        # Limit transcript length
        MAX_TRANSCRIPT_LENGTH = 10000  # Adjust as needed
        if len(formatted_transcript) > MAX_TRANSCRIPT_LENGTH:
            logger.warning(f"Transcript truncated from {len(formatted_transcript)} to {MAX_TRANSCRIPT_LENGTH} characters")
            formatted_transcript = formatted_transcript[:MAX_TRANSCRIPT_LENGTH] + "... [Transcript truncated]"
        
        return formatted_transcript
    
    except TranscriptsDisabled:
        logger.error("Transcripts are disabled for this video")
        return "Error: Transcripts are disabled for this video."
    
    except NoTranscriptFound:
        logger.error("No transcript found for this video")
        return "Error: No transcript found for this video."
    
    except Exception as e:
        logger.error(f"Unexpected error in transcript retrieval: {str(e)}")
        return f"Error: Unable to retrieve transcript. {str(e)}"

def get_available_languages(video_id):
    """
    Get list of available transcript languages for a video.
    
    Args:
        video_id (str): YouTube video ID
    
    Returns:
        list: Available transcript languages
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        languages = []
        for transcript in transcript_list._manually_created_transcripts.values():
            languages.append({
                'code': transcript.language_code,
                'name': transcript.language,
                'type': 'manual'
            })
        for transcript in transcript_list._generated_transcripts.values():
            languages.append({
                'code': transcript.language_code,
                'name': transcript.language,
                'type': 'generated'
            })
        
        return languages
    except Exception:
        return []  # Return empty list if no transcripts are available

def check_video_availability(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return True, None
        else:
            return False, f"Failed to retrieve video. Status code: {response.status_code}"
    except Exception as e:
        return False, f"Failed to check video availability: {str(e)}"

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For secure session management

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    """Set API key for the selected AI service in the session"""
    data = request.json
    service = data.get('service')
    api_key = data.get('api_key')
    
    if not service or not api_key:
        return jsonify({"error": "Service and API key are required"}), 400
    
    session[f'{service}_api_key'] = api_key
    return jsonify({"message": f"{service.capitalize()} API key set successfully"}), 200

@app.route('/summarize', methods=['POST'])
def summarize_transcript():
    """Summarize transcript using the selected AI service"""
    data = request.json
    transcript = data.get('transcript')
    service = data.get('service', 'gemini')
    
    # Retrieve API key from session
    api_key = session.get(f'{service}_api_key')
    
    if not api_key:
        return jsonify({"error": f"No API key found for {service}. Please set an API key first."}), 401
    
    summary = summarize_with_ai(transcript, service, api_key)
    return jsonify({"summary": summary})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_languages', methods=['POST'])
def get_languages():
    try:
        url = request.json.get('url', '')
        video_id = extract_video_id(url)
        
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        languages = get_available_languages(video_id)
        return jsonify({'languages': languages})
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_transcript', methods=['POST'])
def get_transcript_route():
    """Route to get transcript"""
    try:
        logger.info("Received transcript request")
        data = request.get_json()
        url = data.get('url')
        lang_code = data.get('language')
        service = data.get('service', 'gemini')  # Default to gemini if not specified
        
        logger.info(f"Processing URL: {url}, Language: {lang_code}, Service: {service}")
        
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'No URL provided'}), 400
            
        if not validate_youtube_url(url):
            logger.error("Invalid YouTube URL format")
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
            
        video_id = extract_video_id(url)
        if not video_id:
            logger.error("Invalid YouTube URL format")
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
            
        logger.info(f"Extracted video ID: {video_id}")
        
        # Check video availability
        available, error = check_video_availability(video_id)
        if not available:
            logger.error(f"Video unavailable: {error}")
            return jsonify({'error': error}), 400
        
        transcript = get_transcript(video_id, lang_code)
        
        if transcript.startswith('Error:'):
            logger.error(f"Transcript error: {transcript}")
            return jsonify({'error': transcript}), 400
        
        # Get API key from session
        api_key = session.get(f'{service}_api_key')
        if not api_key:
            logger.error(f"No API key found for {service}")
            return jsonify({"error": f"No API key found for {service}. Please set an API key first."}), 401
        
        # Generate summary
        logger.info("Generating summary with AI")
        summary = summarize_with_ai(transcript, service, api_key)
        
        logger.info("Successfully processed transcript and summary")
        return jsonify({
            'transcript': transcript,
            'processed_content': summary
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in transcript route: {str(e)}")
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
