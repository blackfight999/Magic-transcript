from flask import Flask, render_template, request, jsonify, session
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from langdetect import detect
import google.generativeai as genai
import openai
import anthropic
import re
import os
import requests
import json
import xml.etree.ElementTree as ET
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For secure session management

def configure_ai_service(service, api_key):
    """Configure AI service based on the selected provider"""
    if service == 'gemini':
        genai.configure(api_key=api_key)
    elif service == 'openai':
        openai.api_key = api_key
    elif service == 'claude':
        return anthropic.Anthropic(api_key=api_key)
    return None

def summarize_with_ai(transcript, service, api_key):
    """Flexible AI summarization based on selected service"""
    SUMMARY_PROMPT = """Given a text containing complex information about a specific topic, your role is to act as an expert summarizer with 20 years experience.

Start by reading through the provided content to fully understand its scope and depth. Identify the key themes and critical details that are central to the topic.

Next, create a structured summary by organizing these key points in a logical order. Each point should be clear, concise, and reflect the essential information comprehensively. Please aids users in understanding 80% of a video's content by focusing on the most important 20% of the information, simplifying complex ideas into easy-to-understand terms, making learning more accessible and efficient, and breaking down the content into key points.

Present these points in a manner that anyone unfamiliar with the material can grasp the main ideas and significance of the topic effortlessly. To apply this summarization, use bullet points or numbered lists to enhance readability and ensure that each key point stands out for easy comprehension.

The objective is to produce a summary that effectively communicates the core elements of the topic without necessitating a review of the full text.

Here's the text to summarize:
{transcript}"""

    try:
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
                ]
            )
            return response.choices[0].message.content
        
        elif service == 'claude':
            try:
                # Try the newer method first
                response = ai_client.messages.create(
                    model="claude-2.1",
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}
                    ]
                )
                return response.content[0].text
            except AttributeError:
                # Fallback to older method if messages attribute doesn't exist
                response = ai_client.completion.create(
                    model="claude-2.1",
                    max_tokens_to_sample=1000,
                    prompt=SUMMARY_PROMPT.format(transcript=transcript)
                )
                return response.completion
        
    except Exception as e:
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
    """Get transcript using alternative method"""
    logger.info(f"Starting transcript retrieval for video ID: {video_id}")
    try:
        # First, try YouTube Transcript API
        try:
            logger.info("Attempting YouTube Transcript API method...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get generated transcripts first
            generated_transcripts = list(transcript_list._generated_transcripts.values())
            logger.info(f"Found {len(generated_transcripts)} generated transcripts")
            
            if generated_transcripts:
                # If language is specified, try to find a match
                if lang_code:
                    logger.info(f"Looking for transcript in language: {lang_code}")
                    for transcript in generated_transcripts:
                        if transcript.language_code == lang_code:
                            logger.info(f"Found matching language transcript")
                            return TextFormatter().format_transcript(transcript.fetch())
                
                # Otherwise, use the first generated transcript
                logger.info("Using first available generated transcript")
                return TextFormatter().format_transcript(generated_transcripts[0].fetch())
        except Exception as e:
            logger.error(f"YouTube Transcript API failed: {str(e)}")
        
        # Alternative method: Extract captions from video page
        logger.info("Attempting alternative caption extraction method...")
        def extract_captions_from_video_page(video_id):
            try:
                # Fetch the video page
                url = f"https://www.youtube.com/watch?v={video_id}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                logger.info(f"Fetching video page: {url}")
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch video page. Status code: {response.status_code}")
                    return None
                
                # Look for captions in the page source
                logger.info("Searching for caption data in page source")
                caption_pattern = r'{"captionTracks":(\[.*?\]),'
                match = re.search(caption_pattern, response.text)
                
                if match:
                    logger.info("Found caption tracks in page source")
                    # Parse the captions
                    captions_json = match.group(1)
                    captions = json.loads(captions_json)
                    
                    # Log available caption types
                    logger.info(f"Found {len(captions)} caption tracks")
                    for cap in captions:
                        logger.info(f"Caption type: {cap.get('kind')}, language: {cap.get('languageCode')}")
                    
                    # Prioritize auto-generated captions
                    auto_captions = [
                        caption for caption in captions 
                        if caption.get('kind', '').lower() == 'asr'
                    ]
                    
                    if auto_captions:
                        logger.info(f"Found {len(auto_captions)} auto-generated captions")
                        # Select appropriate caption
                        if lang_code:
                            lang_captions = [
                                caption for caption in auto_captions 
                                if caption.get('languageCode') == lang_code
                            ]
                            if lang_captions:
                                caption = lang_captions[0]
                                logger.info(f"Using language-specific caption: {lang_code}")
                            else:
                                caption = auto_captions[0]
                                logger.info("Using first available auto-generated caption")
                        else:
                            caption = auto_captions[0]
                            logger.info("Using first available auto-generated caption")
                        
                        # Fetch the caption file
                        caption_url = caption.get('baseUrl')
                        if caption_url:
                            logger.info(f"Fetching caption file from URL")
                            caption_response = requests.get(caption_url, headers=headers)
                            
                            if caption_response.status_code != 200:
                                logger.error(f"Failed to fetch caption file. Status code: {caption_response.status_code}")
                                return None
                            
                            # Parse XML captions
                            try:
                                root = ET.fromstring(caption_response.text)
                                
                                # Extract text from XML
                                texts = root.findall('.//text')
                                logger.info(f"Found {len(texts)} caption segments")
                                
                                transcript_text = ' '.join([
                                    text.text for text in texts if text.text
                                ])
                                
                                logger.info("Successfully extracted caption text")
                                return transcript_text
                            except ET.ParseError as e:
                                logger.error(f"XML parsing error: {str(e)}")
                                return None
                
                logger.warning("No caption tracks found in page source")
                return None
            except Exception as e:
                logger.error(f"Alternative caption extraction failed: {str(e)}")
                return None
        
        # Try alternative method
        logger.info("Attempting alternative caption extraction")
        alternative_transcript = extract_captions_from_video_page(video_id)
        if alternative_transcript:
            logger.info("Successfully retrieved transcript using alternative method")
            return alternative_transcript
        
        # If all methods fail
        logger.error("All transcript retrieval methods failed")
        return "Error: Could not retrieve transcript. No captions available."
    
    except Exception as e:
        logger.error(f"Transcript retrieval error: {str(e)}")
        return f"Error: Unable to retrieve transcript. Details: {str(e)}"

def get_available_languages(video_id):
    """Get list of available transcript languages"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        languages = []
        
        # Get manual transcripts
        for transcript in transcript_list._manually_created_transcripts.values():
            languages.append({
                'code': transcript.language_code,
                'name': transcript.language,
                'type': 'manual'
            })
            
        # Get generated transcripts
        for transcript in transcript_list._generated_transcripts.values():
            languages.append({
                'code': transcript.language_code,
                'name': transcript.language,
                'type': 'generated'
            })
            
        return languages
    except Exception as e:
        return []

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
        
        logger.info(f"Processing URL: {url}, Language: {lang_code}")
        
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'No URL provided'}), 400
            
        video_id = extract_video_id(url)
        if not video_id:
            logger.error("Invalid YouTube URL format")
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
            
        logger.info(f"Extracted video ID: {video_id}")
        transcript = get_transcript(video_id, lang_code)
        
        if transcript.startswith('Error:'):
            logger.error(f"Transcript error: {transcript}")
            return jsonify({'error': transcript}), 400
            
        logger.info("Successfully retrieved transcript")
        return jsonify({'transcript': transcript})
        
    except Exception as e:
        logger.error(f"Unexpected error in transcript route: {str(e)}")
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
