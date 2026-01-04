from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

# Import your existing utilities
# Ensure yttranscriber.py and notes.py are in the same directory
from yttranscriber import extract_youtube_transcript as get_youtube_transcript
from yttranscriber import ask_questions as answer_question
from yttranscriber import model 
from notes import generate_questions, evaluate, total_evaluate, extract_weak_topics

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Request/Response Validation ---

class MainRequest(BaseModel):
    video_url: str
    question: str

class TopicsRequest(BaseModel):
    user_topics: str

class AnswerRequest(BaseModel):
    question_text: str  # Frontend must send the text of the question being answered
    answer_text: str
    topic: str          # The general topic (e.g., "Machine Learning")

class FinalRequest(BaseModel):
    topics: str
    full_conversation: str # The accumulated string of Q&A history


def parse_questions_to_list(questions_text: str):
    """
    Parses the raw numbered string from the AI into a clean list of strings.
    """
    lines = questions_text.split('\n')
    questions = []
    for line in lines:
        clean_line = line.strip()
        # Check if line starts with a digit (e.g., "1. What is...")
        if clean_line and any(char.isdigit() for char in clean_line[:3]):
            # Remove the numbering (e.g., "1. ")
            if '.' in clean_line:
                clean_line = clean_line.split('.', 1)[-1].strip()
            questions.append(clean_line)
    return questions

def generate_notes_stateless(topics: str, focus_areas: str) -> str:
    """
    Re-implementation of make_notes from notes.py to be stateless.
    It does not rely on the global 'memory' object.
    """
    prompt_template = """You are a university professor creating comprehensive study materials.
    
    Create detailed, exam-focused notes on: {topics}
    
    PRIORITY FOCUS on these weak areas identified in the student's exam: {focus_areas}
    
    Structure:
    1. Quick Summary of {topics}
    2. DEEP DIVE into Weak Areas ({focus_areas}):
       - Detailed explanations
       - Common pitfalls/mistakes
       - Step-by-step breakdowns
    3. Exam Tips & Key Formulas
    
    Use bolding, bullet points, and clear headers."""
    
    prompt = PromptTemplate(
        input_variables=['topics', 'focus_areas'],
        template=prompt_template
    )
    chain = prompt | model | StrOutputParser()
    return chain.invoke({'topics': topics, 'focus_areas': focus_areas})

# --- Endpoints ---

@app.get("/")
def welcome(): 
    return {'message': 'University Exam Prep Backend is Running'}

@app.post("/main")
def main(request: MainRequest):
    """
    YouTube Transcription and Q&A Endpoint
    """
    try:
        transcription_text = get_youtube_transcript(request.video_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript extraction failed: {str(e)}")

    try:
        answer = answer_question(transcription_text, request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

    return {
        "video_url": request.video_url,
        "question": request.question,
        "answer": answer
    }

@app.post("/startsession")
def start_session(request: TopicsRequest):
    """
    Generates exam questions based on topics.
    Returns a list of questions for the frontend to manage.
    """
    try:
        # 1. Invoke the tool from notes.py
        raw_response = generate_questions.invoke({'topics': request.user_topics})
        
        # 2. Parse the raw string into a list
        questions_list = parse_questions_to_list(raw_response)
        
        # Fallback if parsing fails
        if not questions_list:
            questions_list = [raw_response]

        return {
            "session_id": "session_" + str(hash(request.user_topics)), # Simple session ID
            "total_questions": len(questions_list),
            "questions": questions_list, # Send all questions to frontend
            "topics": request.user_topics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@app.post("/submitanswer")
def submit_answer(request: AnswerRequest):
    """
    Evaluates a single answer.
    """
    try:
        # Invoke the evaluation tool from notes.py
        evaluation_result = evaluate.invoke({
            'question': request.question_text,
            'answer': request.answer_text,
            'topic': request.topic
        })
        
        return {
            "evaluation": evaluation_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.post("/finalevaluation")
def final_evaluation(request: FinalRequest):
    """
    Generates the final report and study notes.
    """
    try:
        # 1. Generate the total evaluation report
        total_eval_report = total_evaluate.invoke({
            'conversation_history': request.full_conversation,
            'topics': request.topics
        })
        
        # 2. Extract weak topics from the report
        weak_topics = extract_weak_topics(total_eval_report)
        
        # 3. Generate notes (using the stateless function defined above)
        study_notes = generate_notes_stateless(request.topics, weak_topics)
        
        return {
            "total_evaluation": total_eval_report,
            "weak_topics": weak_topics,
            "notes": study_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Final evaluation failed: {str(e)}")