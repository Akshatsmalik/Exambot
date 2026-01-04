# from youtube_transcript_api import YouTubeTranscriptApi
# from langchain_community.document_loaders import YoutubeLoader
# from langchain.text_splitter import CharacterTextSplitter
# from langchain_community.document_loaders.youtube import TranscriptFormat
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, parse_qs
import yt_dlp
import requests   
import time  

load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.getenv('GEMINI_API_KEY')

model = ChatGoogleGenerativeAI(model = 'gemini-2.5-flash-lite', temperature = 0.7)

# def extract_youtube_transcript(video_url):
#     ydl_options = {
#         'skip_download':True,
#         'writesubtitles':True,
#         'writeautomaticsub':True,
#         'subtitleslangs':['en'],
#         'quiet':True
#     }

#     with yt_dlp.YoutubeDL(ydl_options) as ydl:
#         info = ydl.extract_info(video_url, download=False)
#         if 'subtitles' in info and 'en' in info['subtitles']:
#             sub_url = info['subtitles']['en'][0]['url']
#         elif 'automatic_captions' in info and 'en' in info['automatic_captions']:
#             sub_url = info['automatic_captions']['en'][0]['url']
#         else:
#             raise ValueError("No English subtitles found")
        
#         response = requests.get(sub_url)
#         return response.text

import json
import requests
import yt_dlp

def format_time(ms):
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

        transcript = []
        for event in data.get("events", []):
            for seg in event.get("segs", []):
                text = seg.get("utf8", "").strip()
                if text:
                    transcript.append(text)

        return " ".join(transcript)



# def extract_youtube_transcript(video_url):
#     video_id = parse_qs(urlparse(video_url).query).get("v", [None])[0]
#     if not video_id:
#         raise ValueError("Invalid YouTube URL")

#     transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
#     return " ".join(chunk["text"] for chunk in transcript)

def ask_questions(transcription_text,question):
    try:
        prompt = PromptTemplate.from_template(
            template = """ you are a helpful assitant who can answer the questions of the user :{question}, from the given transcript thats extracted 
            from a youtube video:{transcription_text}, answer any questions in bullet poitns and a little summary and a little intro and end with summary or outro and make sure to include bullet points """
        )
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({
            'question':question,
            'transcription_text':transcription_text
        })
        return response
    
    except Exception as e:
        return f'exeection occured {e}'

def main():
    video_url = input('Please enter your video url:- ')
    transcription_text=''
    try:
        transcription_text=extract_youtube_transcript(video_url)
        # print(transcription_text)
    except Exception as e:
        print(f'Yt transcripts not extracted {e}')
        return
    try:
        questions = input('Ask your questoins regarding the video: ')
        answers = ask_questions(transcription_text,questions)
        print(answers)
    except Exception as e:
        print(f'Error occured as {e}')
        return

if __name__ == '__main__':
    main()