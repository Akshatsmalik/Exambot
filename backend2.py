from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging
from yttranscriber import extract_youtube_transcript as get_youtube_transcript
from yttranscriber import ask_questions as answer_question
from yttranscriber import model 
from notes import generate_questions, evaluate, total_evaluate, extract_weak_topics

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MainRequest(BaseModel):
    video_url: str
    question: str

class TopicsRequest(BaseModel):
    user_topics: str

class AnswerRequest(BaseModel):
    question_text: str 
    answer_text: str
    topic: str         

class FinalRequest(BaseModel):
    topics: str
    full_conversation: str

class NotesRequest(BaseModel):
    topic: str


def parse_questions_to_list(questions_text: str):
    """
    Parses the raw numbered string from the AI into a clean list of strings.
    """
    lines = questions_text.split('\n')
    questions = []
    for line in lines:
        clean_line = line.strip()
        if clean_line and any(char.isdigit() for char in clean_line[:3]):
            if '.' in clean_line:
                clean_line = clean_line.split('.', 1)[-1].strip()
            questions.append(clean_line)
    return questions

def generate_notes_stateless(topics: str, focus_areas: str) -> str:
    """
    Re-implementation of make_notes from notes.py to be stateless.
    It does not rely on the global 'memory' object.
    """
    prompt_template = """You are a exam bot for a university creating comprehensive study materials.
    
    Create detailed, exam-focused notes on: {topics} and if the user asks for short notes then make it short but still detailed. like flashcards
    
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
        raw_response = generate_questions.invoke({'topics': request.user_topics})
        
        questions_list = parse_questions_to_list(raw_response)
        
        if not questions_list:
            questions_list = [raw_response]

        return {
            "session_id": "session_" + str(hash(request.user_topics)), 
            "total_questions": len(questions_list),
            "questions": questions_list, 
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
        total_eval_report = total_evaluate.invoke({
            'conversation_history': request.full_conversation,
            'topics': request.topics
        })
        weak_topics = extract_weak_topics(total_eval_report)
        study_notes = generate_notes_stateless(request.topics, weak_topics)
        
        return {
            "total_evaluation": total_eval_report,
            "weak_topics": weak_topics,
            "notes": study_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Final evaluation failed: {str(e)}")

@app.post("/generate_notes_only")
def generate_notes_only(request: NotesRequest):
    """Generates notes without an exam session"""
    try:
        notes = generate_notes_stateless(request.topic, "General Overview & Core Concepts")
        return {"notes": notes, "topic": request.topic}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Note generation failed: {str(e)}")
