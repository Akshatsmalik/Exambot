import yt_dlp
import requests
import json
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI    
import os
from dotenv import load_dotenv

load_dotenv()

model = ChatGoogleGenerativeAI(model = 'gemini-2.5-flash', temperature = 0.7)

def format_time(ms):
    """Helper to convert milliseconds to MM:SS format."""
    if ms is None:
        return "00:00"
    seconds = int(ms) / 1000
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"

def extract_youtube_transcript(video_url):
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "quiet": True
    }

    print(f"Extracting transcript for: {video_url}") 

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        if "subtitles" in info and "en" in info["subtitles"]:
            sub_url = info["subtitles"]["en"][0]["url"]
        elif "automatic_captions" in info and "en" in info["automatic_captions"]:
            sub_url = info["automatic_captions"]["en"][0]["url"]
        else:
            raise ValueError("No English subtitles found")

        raw_caption = requests.get(sub_url).text
        data = json.loads(raw_caption)

        transcript_with_timestamps = []
        
        for event in data.get("events", []):
            start_ms = event.get("tStartMs", 0) 
            timestamp = format_time(start_ms)
            
            text_segments = []
            for seg in event.get("segs", []):
                text_segments.append(seg.get("utf8", "").strip())
            
            full_text = " ".join(text_segments).strip()
            
            # This captures the timestamp so the AI can see it
            if full_text:
                transcript_with_timestamps.append(f"[{timestamp}] {full_text}")

        print("Transcript extracted successfully.") 
        return " ".join(transcript_with_timestamps)

def ask_questions(transcription_text, question):
    try:
        prompt = PromptTemplate.from_template(
            template="""You are a helpful video assistant. 
            
            Context: The user is asking a question about a video. You have the transcript 
            which includes timestamps in the format [MM:SS].
            
            Transcript: {transcription_text}
            
            Question: {question}
            
            Instructions:
            1. Answer the question in detail based ONLY on the transcript.
            2. VERY IMPORTANT: You MUST cite the timestamp for your answer in the format [MM:SS]. 
               For example: "At [05:30], the speaker explains..." or "The concept is discussed around [10:15]."
               Do not omit timestamps.
            """
        )
        
        chain = prompt | model | StrOutputParser()
        
        response = chain.invoke({
            'question': question,
            'transcription_text': transcription_text
        })
        
        return response
    
    except Exception as e:
        return f"Error generating answer: {e}"