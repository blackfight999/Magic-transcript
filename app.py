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
from pytube import YouTube
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

def get_transcript_pytube(video_id):
    """Get transcript using pytube"""
    try:
        logger.info("Attempting pytube transcript method...")
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        captions = yt.captions
        
        if not captions:
            logger.warning("No captions found via pytube")
            return None
            
        # Try to get English captions first, then fall back to any available caption
        caption = captions.get('en', next(iter(captions.values())) if captions else None)
        
        if caption:
            logger.info(f"Found caption track: {caption.code}")
            transcript = caption.generate_srt_captions()
            # Clean up the SRT format to plain text
            cleaned_transcript = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', transcript)
            cleaned_transcript = cleaned_transcript.replace('\n\n', ' ').strip()
            return cleaned_transcript
            
        return None
    except Exception as e:
        logger.error(f"Pytube transcript retrieval failed: {str(e)}")
        return None

def get_transcript_youtube_api(video_id):
    """Get transcript using YouTube Data API"""
    try:
        logger.info("Attempting YouTube Data API method...")
        # You'll need to set this in your environment variables
        api_key = os.getenv('YOUTUBE_API_KEY')
        
        if not api_key:
            logger.error("YouTube API key not found")
            return None
            
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Get video details including caption status
        video_response = youtube.videos().list(
            part='contentDetails',
            id=video_id
        ).execute()
        
        if not video_response.get('items'):
            logger.error("Video not found")
            return None
            
        video_item = video_response['items'][0]
        has_captions = video_item['contentDetails'].get('caption', 'false') == 'true'
        
        if not has_captions:
            logger.warning("Video does not have captions according to YouTube API")
            return None
            
        # Get caption track
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()
        
        if not captions_response.get('items'):
            logger.warning("No caption tracks found via YouTube API")
            return None
            
        # Get the first available caption track
        caption_id = captions_response['items'][0]['id']
        
        # Download the caption track
        caption = youtube.captions().download(
            id=caption_id,
            tfmt='srt'
        ).execute()
        
        # Clean up the SRT format
        cleaned_transcript = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', caption.decode())
        cleaned_transcript = cleaned_transcript.replace('\n\n', ' ').strip()
        
        logger.info("Successfully retrieved transcript via YouTube API")
        return cleaned_transcript
        
    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error in YouTube API method: {str(e)}")
        return None

def get_transcript(video_id, lang_code=None):
    """Get transcript using multiple methods"""
    logger.info(f"Starting transcript retrieval for video ID: {video_id}")
    
    # First check video availability
    is_available, message = check_video_availability(video_id)
    if not is_available:
        logger.error(f"Video availability check failed: {message}")
        return f"Error: {message}"
    
    try:
        # 1. Try YouTube Data API first
        youtube_api_transcript = get_transcript_youtube_api(video_id)
        if youtube_api_transcript:
            return youtube_api_transcript
            
        # 2. Try YouTube Transcript API
        try:
            logger.info("Attempting YouTube Transcript API method...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            generated_transcripts = list(transcript_list._generated_transcripts.values())
            
            if generated_transcripts:
                if lang_code:
                    for transcript in generated_transcripts:
                        if transcript.language_code == lang_code:
                            return TextFormatter().format_transcript(transcript.fetch())
                return TextFormatter().format_transcript(generated_transcripts[0].fetch())
        except Exception as e:
            logger.error(f"YouTube Transcript API failed: {str(e)}")
        
        # 3. Try pytube method
        pytube_transcript = get_transcript_pytube(video_id)
        if pytube_transcript:
            logger.info("Successfully retrieved transcript using pytube")
            return pytube_transcript
        
        # 4. Try web scraping method as last resort
        logger.info("Attempting web scraping method...")
        alternative_transcript = extract_captions_from_video_page(video_id, lang_code)
        if alternative_transcript:
            logger.info("Successfully retrieved transcript using web scraping")
            return alternative_transcript
        
        # If all methods fail
        logger.error("All transcript retrieval methods failed")
        return "Error: Could not retrieve captions. This video might not have captions enabled. Please try a different video that has captions or subtitles."
        
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
        service = data.get('service', 'gemini')  # Default to gemini if not specified
        
        logger.info(f"Processing URL: {url}, Language: {lang_code}, Service: {service}")
        
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

def extract_captions_from_video_page(video_id, lang_code=None):
    """Extract auto-generated captions using web scraping"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.info(f"Fetching video page: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch video page. Status code: {response.status_code}")
            return None
            
        # Look for both manual and auto-generated captions
        logger.info("Searching for caption data in page source")
        patterns = [
            r'"captions":({[^}]+})',  # Pattern for newer YouTube format
            r'{"captionTracks":(\[.*?\])}',  # Pattern for older format
            r'"playerCaptionsTracklistRenderer":({.*?})\}'  # Another possible format
        ]
        
        caption_data = None
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                try:
                    caption_data = json.loads(match.group(1))
                    break
                except json.JSONDecodeError:
                    continue
        
        if not caption_data:
            logger.warning("No caption data found in any format")
            return None
            
        # Extract caption tracks
        caption_tracks = []
        if 'captionTracks' in caption_data:
            caption_tracks = caption_data['captionTracks']
        elif 'playerCaptionsTracklistRenderer' in caption_data:
            caption_tracks = caption_data.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not caption_tracks:
            logger.warning("No caption tracks found")
            return None
            
        logger.info(f"Found {len(caption_tracks)} caption tracks")
        
        # First try to find auto-generated captions
        auto_captions = [
            track for track in caption_tracks
            if track.get('kind', '').lower() == 'asr' or
               track.get('vssId', '').startswith('a.') or
               track.get('isAutoGenerated') == True
        ]
        
        # If no auto-generated captions, try any available captions
        target_tracks = auto_captions if auto_captions else caption_tracks
        
        if not target_tracks:
            logger.warning("No suitable caption tracks found")
            return None
            
        # Select appropriate caption track
        selected_track = None
        if lang_code:
            # Try to find caption in requested language
            for track in target_tracks:
                track_lang = track.get('languageCode', '').split('-')[0]
                if track_lang == lang_code:
                    selected_track = track
                    break
        
        # If no language match or no language specified, use first available
        if not selected_track:
            selected_track = target_tracks[0]
        
        logger.info(f"Selected caption track: {selected_track.get('languageCode')}")
        
        # Get the caption content
        caption_url = selected_track.get('baseUrl')
        if not caption_url:
            logger.error("No baseUrl found in caption track")
            return None
            
        # Add necessary parameters to URL
        caption_url += '&fmt=srv3'  # Request transcript in XML format
        
        logger.info("Fetching caption content")
        caption_response = requests.get(caption_url, headers=headers)
        
        if caption_response.status_code != 200:
            logger.error(f"Failed to fetch caption content. Status code: {caption_response.status_code}")
            return None
            
        # Parse XML content
        try:
            root = ET.fromstring(caption_response.text)
            transcript_parts = []
            
            for text in root.findall('.//text'):
                if text.text:
                    transcript_parts.append(text.text.strip())
            
            if not transcript_parts:
                logger.warning("No text content found in captions")
                return None
                
            transcript = ' '.join(transcript_parts)
            logger.info("Successfully extracted caption text")
            return transcript
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse caption XML: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting captions: {str(e)}")
        return None

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

if __name__ == '__main__':
    app.run(debug=True, port=3000)
