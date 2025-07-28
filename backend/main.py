import os
import re
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# --- Initial Setup ---
# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI()

# --- CORS Configuration ---
# Allow frontend to communicate with this backend (essential for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Load ML Model & API Key ---
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("YouTube API Key is missing. Please set it in your .env file.")

try:
    logging.info("Loading sentiment analysis model. This may take a moment...")
    # Using a robust, general-purpose sentiment model
    sentiment_classifier = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load sentiment model: {e}")
    sentiment_classifier = None

# --- Pydantic Model for Request Validation ---
class VideoRequest(BaseModel):
    url: str

# --- Helper Functions ---
def extract_video_id(url: str) -> str | None:
    """Extracts the YouTube video ID from various URL formats."""
    # This regex covers standard, shortened, and embedded YouTube URLs
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_video_comments(video_id: str, max_results=100) -> list:
    """Fetches comments from a YouTube video using the YouTube Data API."""
    try:
        # Build the YouTube API service object
        youtube_service = build('youtube', 'v3', developerKey=API_KEY)
        
        # Request comments for the specified video
        request = youtube_service.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=max_results,
            textFormat='plainText'
        )
        response = request.execute()
        
        # Extract the text from each comment
        comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in response.get('items', [])]
        return comments
        
    except HttpError as e:
        logging.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
        # Gracefully handle specific, common errors
        if 'commentsDisabled' in str(e.content):
            raise HTTPException(status_code=403, detail="Comments are disabled for this video.")
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch comments. Check the video URL and your API key.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in get_video_comments: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


# --- API Endpoint ---
@app.post("/analyze")
async def analyze_video_comments(request: VideoRequest):
    """
    Main endpoint to analyze comments from a YouTube video URL.
    """
    if not sentiment_classifier:
        raise HTTPException(status_code=503, detail="Sentiment model is not available.")

    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid or unsupported YouTube URL.")

    comments = get_video_comments(video_id)
    if not comments:
        # It's not an error if a video has no comments, so we return a successful response
        return {"positive": 0, "negative": 0}

    sentiment_counts = {"positive": 0, "negative": 0}
    
    for comment in comments:
        # Skip empty or invalid comments
        if not comment or not isinstance(comment, str) or not comment.strip():
            continue
            
        try:
            # Feed raw comment text directly to the model
            result = sentiment_classifier(comment)[0]
            sentiment = result['label']
            
            if sentiment == 'POSITIVE':
                sentiment_counts["positive"] += 1
            elif sentiment == 'NEGATIVE':
                sentiment_counts["negative"] += 1
        except Exception as e:
            # Log errors for individual comment analysis but don't stop the whole process
            logging.warning(f"Could not analyze comment: '{comment}'. Error: {e}")

    return sentiment_counts

@app.get("/")
def read_root():
    return {"status": "Sentiment Analyzer API is running."}
