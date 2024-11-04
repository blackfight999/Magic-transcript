from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from langdetect import detect
import google.generativeai as genai
import re

app = Flask(__name__)

# Configure Google Gemini AI
GOOGLE_API_KEY = 'AIzaSyCGameQtidVffHen8mv61kEHfd_-SXKvkw'
genai.configure(api_key=GOOGLE_API_KEY)

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

def get_transcript(video_id, lang_code=None):
    """Get transcript in specified language or original language"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        if lang_code:
            try:
                transcript = transcript_list.find_transcript([lang_code])
            except:
                # Fallback to any available transcript
                try:
                    transcript = transcript_list.find_manually_created_transcript()
                except:
                    transcript = list(transcript_list._generated_transcripts.values())[0]
        else:
            # Get original language transcript
            try:
                transcript = transcript_list.find_manually_created_transcript()
            except:
                transcript = list(transcript_list._generated_transcripts.values())[0]
        
        transcript_data = transcript.fetch()
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript_data)
        detected_language = detect(formatted_transcript)
        
        return formatted_transcript, detected_language, transcript.language
    except Exception as e:
        raise Exception(f"Error getting transcript: {str(e)}")

def summarize_with_gemini(transcript):
    """Summarize transcript using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = """You are given a youtube transcript containing complex information about a specific topic, your role is to act as an expert summarizer with 20 years experience.

Start by reading through the provided content to fully understand its scope and depth. Identify the key themes and critical details that are central to the topic.

Next, create a structured summary by organizing these key points in a logical order. Each point should be clear, concise, and reflect the essential information comprehensively. Please aids users in understanding 80% of a video's content by focusing on the most important 20% of the information, simplifying complex ideas into easy-to-understand terms, making learning more accessible and efficient, and breaking down the content into key points.

Present these points in a manner that anyone unfamiliar with the material can grasp the main ideas and significance of the topic effortlessly. To apply this summarization, use bullet points or numbered lists to enhance readability and ensure that each key point stands out for easy comprehension.

Here's the transcript to summarize:

""" + transcript

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Error in summarization: {str(e)}")

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
    try:
        url = request.json.get('url', '')
        lang_code = request.json.get('language', '')
        video_id = extract_video_id(url)
        
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        try:
            transcript, detected_language, transcript_language = get_transcript(video_id, lang_code)
            summary = summarize_with_gemini(transcript)
            
            return jsonify({
                'transcript': transcript,
                'processed_content': summary,
                'detected_language': detected_language,
                'transcript_language': transcript_language
            })
                
        except (TranscriptsDisabled, NoTranscriptFound):
            return jsonify({'error': 'Transcript not available for this video'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
