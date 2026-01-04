from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from yttranscriber import model

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# ==================== TOOL DEFINITIONS ====================

class QuestionGeneration(BaseModel):
    topics: str = Field(description="The topics provided by the user to generate questions from")

@tool("generate_questions", args_schema=QuestionGeneration)
def generate_questions(topics: str) -> str:
    """Generate university exam questions based on the topics provided by the user."""
    prompt = PromptTemplate(
        input_variables=['topics'],
        template="""You are a university professor preparing examination questions.
        
        Generate EXACTLY 15 examination questions based on these topics: {topics}
        
        Requirements:
        - Questions should be at university/competitive exam level
        - Mix of question types: conceptual, analytical, application-based, and problem-solving
        - Test both theoretical understanding and practical application
        - Include questions that require critical thinking
        - Questions should prepare students for actual university exams
        
        Format as a numbered list (1-15).
        Make questions challenging but fair for comprehensive exam preparation."""
    )
    chain = prompt | model
    response = chain.invoke({'topics': topics})
    return response.content


class AnswerEvaluation(BaseModel):
    question: str = Field(description="The question asked")
    answer: str = Field(description="The answer given by the candidate")
    topic: str = Field(description="The topic being tested")

@tool("evaluate_answer", args_schema=AnswerEvaluation)
def evaluate(question: str, answer: str, topic: str) -> str:
    """Evaluate the answer from university examination perspective. Rate from 1-10."""
    prompt = PromptTemplate(
        input_variables=['question', 'answer', 'topic'],
        template="""You are a university professor evaluating exam answers for final grading.
        
        Topic: {topic}
        Question: {question}
        Student's Answer: {answer}
        
        Evaluate this answer as if grading a university examination paper:
        1. Score (X/10) - Be strict but fair, as in actual university exams
        2. Marking breakdown - What marks were awarded and why
        3. Strong points - What the student demonstrated well
        4. Weak points - What was missing, incorrect, or could be improved
        5. Expected answer elements - Key points that should have been covered
        
        Format:
        Score: X/10
        Marking: ...
        Strong Points: ...
        Weak Points: ...
        Expected Elements: ..."""
    )
    chain = prompt | model
    response = chain.invoke({'question': question, 'answer': answer, 'topic': topic})
    return response.content


class TotalReview(BaseModel):
    conversation_history: str = Field(description="The full Q&A conversation history")
    topics: str = Field(description="The topics covered")

@tool("total_review", args_schema=TotalReview)
def total_evaluate(conversation_history: str, topics: str) -> str:
    """Evaluate overall exam performance and identify weak topics for targeted preparation."""
    prompt = PromptTemplate(
        input_variables=['conversation_history', 'topics'],
        template="""You are a university professor providing comprehensive exam performance feedback.
        
        TOPICS COVERED: {topics}
        
        STUDENT'S EXAM RESPONSES:
        {conversation_history}
        
        Provide a detailed evaluation report as you would for a university student:
        
        1. Overall Score (X/10) - Final grade based on all responses
        2. Performance Analysis - Comprehensive review of exam performance
        3. Strong Areas - Topics/concepts the student has mastered
        4. Areas Requiring Improvement - Be specific about gaps in knowledge
        5. Exam Preparation Recommendations - How to improve for future exams
        6. WEAK_TOPICS - Specific topics/concepts that need intensive study
        
        For WEAK_TOPICS, be very specific and list them clearly:
        WEAK_TOPICS:
        - Specific Topic/Concept 1
        - Specific Topic/Concept 2
        - Specific Topic/Concept 3
        
        Be encouraging but honest - this is to help the student prepare better."""
    )
    chain = prompt | model
    response = chain.invoke({'conversation_history': conversation_history, 'topics': topics})
    return response.content


class NoteGeneration(BaseModel):
    topics: str = Field(description="Topics to generate notes for")
    focus_areas: str = Field(default="", description="Specific areas to focus on")

def make_notes(topics: str, focus_areas: str = "") -> str:
    """Generate comprehensive study notes optimized for university exam preparation."""
    try:
        if focus_areas:
            prompt_text = f"""You are a university professor creating comprehensive study materials for exam preparation.
            
            Create detailed, exam-focused notes on: {topics}
            
            PRIORITY FOCUS on these weak areas: {focus_areas}
            
            For the weak areas (MOST IMPORTANT - cover extensively):
            - Clear, detailed explanations of core concepts
            - Step-by-step breakdowns of complex ideas
            - Common exam questions on these topics
            - Common mistakes students make and how to avoid them
            - Key formulas, definitions, or frameworks (if applicable)
            - Practice tips and memory aids
            - Real-world applications and examples
            
            For other topics (standard coverage):
            - Essential concepts and definitions
            - Important points to remember
            - Quick reference points
            
            Use university-level depth with clear formatting:
            - Bold for critical terms and concepts
            - Bullet points for key facts
            - Numbered steps for procedures/processes
            - Examples marked clearly
            - "EXAM TIP:" for exam-specific advice
            
            Make this comprehensive enough for thorough exam preparation."""
        else:
            prompt_text = f"""You are a university professor creating comprehensive study materials for exam preparation.
            
            Create detailed, exam-focused notes on: {topics}
            
            Include:
            - Core concepts and definitions
            - Key theories and frameworks
            - Important formulas or principles
            - Common exam questions
            - Practice tips and examples
            
            Use university-level depth with clear formatting:
            - Bold for critical terms
            - Bullet points for key facts
            - Numbered steps for procedures
            - "EXAM TIP:" for exam-specific advice"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a university professor creating comprehensive exam preparation materials. Focus on clarity, depth, and exam readiness."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", prompt_text)
        ])

        chain = prompt | model | StrOutputParser()

        response = chain.invoke({
            "chat_history": memory.load_memory_variables({})["chat_history"]
        })

        memory.save_context(
            {"user": f"Create notes for: {topics}"},
            {"assistant": response}
        )

        return response

    except Exception as e:
        return f"Error occurred: {e}"


def extract_weak_topics(evaluation_text: str) -> str:
    """Extract weak topics from the evaluation text."""
    lines = evaluation_text.split('\n')
    weak_topics = []
    capture = False
    
    for line in lines:
        if 'WEAK_TOPICS' in line.upper():
            capture = True
            continue
        if capture and line.strip().startswith('-'):
            weak_topics.append(line.strip('- ').strip())
        elif capture and line.strip() and not line.strip().startswith('-'):
            break
    
    return ', '.join(weak_topics) if weak_topics else "general concepts"


def run_qa_session():
    print("    UNIVERSITY EXAM PREPARATION & EVALUATION SYSTEM")
    print("=" * 70)
    print("\n📚 This system will:")
    print("   • Generate 15 university-level exam questions on your topics")
    print("   • Evaluate your answers as a professor would")
    print("   • Identify your weak areas")
    print("   • Create targeted study notes for better preparation")
    print("   • Write skip to skip the question")

    print("=" * 70)
    
    # Step 1: Get topics from user
    print("\n📝 STEP 1: Topic Selection")
    print("-" * 70)
    topics = input("Enter the topics you want to prepare for (comma-separated):\n> ")
    
    print(f"\n🎯 Generating 15 university exam questions on: {topics}")
    print("⏳ Please wait...")
    
    # Step 2: Generate questions
    questions_text = generate_questions.invoke({'topics': topics})
    questions = [q.strip() for q in questions_text.split('\n') if q.strip() and any(c.isdigit() for c in q[:3])]
    
    print(f"\n✅ Generated {len(questions)} exam questions")
    print("\n" + "=" * 70)
    print("📝 STEP 2: Answer the Questions")
    print("=" * 70)
    print("💡 TIP: Answer as you would in an actual exam. Be detailed and precise.")
    print("💡 Type 'skip' to skip a question, 'quit' to end the session early.")
    print("-" * 70)
    
    # Step 3: Ask questions and collect answers
    conversation_history = []
    
    for i, question in enumerate(questions, 1):
        question_clean = question.split('.', 1)[-1].strip() if '.' in question else question
        print(f"\n{'='*70}")
        print(f"📌 QUESTION {i}/{len(questions)}")
        print('='*70)
        print(f"{question_clean}")
        print('-'*70)
        
        user_answer = input("✍️  Your answer:\n> ")
        
        if user_answer.strip().lower() in ['quit', 'exit']:
            print("\n⚠️  Ending exam session early...")
            break
        
        if user_answer.strip().lower() == 'skip':
            print("⏭️  Question skipped")
            conversation_history.append(f"Q{i}: {question_clean}")
            conversation_history.append(f"A{i}: [SKIPPED]")
            conversation_history.append(f"Eval{i}: Not attempted")
            conversation_history.append("")
            continue
        
        # Evaluate the answer
        print("\n⏳ Professor is evaluating your answer...")
        evaluation = evaluate.invoke({
            'question': question_clean,
            'answer': user_answer,
            'topic': topics
        })
        
        print(f"\n{'='*70}")
        print("📊 EVALUATION FEEDBACK:")
        print('='*70)
        print(evaluation)
        print('='*70)
        
        # Store in conversation history
        conversation_history.append(f"Q{i}: {question_clean}")
        conversation_history.append(f"A{i}: {user_answer}")
        conversation_history.append(f"Eval{i}: {evaluation}")
        conversation_history.append("")
    
    # Step 4: Generate total evaluation
    print("STEP 3: Generating Comprehensive Performance Report")
    
    full_history = '\n'.join(conversation_history)
    total_eval = total_evaluate.invoke({
        'conversation_history': full_history,
        'topics': topics
    })
    
    print("📋 FINAL EXAM PERFORMANCE REPORT")
    print(total_eval)
    
    # Step 5: Extract weak topics
    weak_topics = extract_weak_topics(total_eval)
    print(f"\n🎯 Weak areas identified: {weak_topics}")
    print("⏳ Creating comprehensive notes with focus on your weak areas...")
    
    focused_notes = make_notes(topics, weak_topics)
    
    print("\n" + "="*70)
    print("📖 YOUR PERSONALIZED EXAM PREPARATION NOTES")
    print("="*70)
    print(focused_notes)
    print('='*70)
    
    # Option to save notes
    print("\n💾 SAVE YOUR MATERIALS")
    print("-"*70)
    save = input("Would you like to save the evaluation and notes to a file? (yes/no): ").strip().lower()
    if save in ['yes', 'y']:
        filename = input("Enter filename (e.g., exam_prep.txt): ").strip()
        if not filename:
            filename = "exam_preparation.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("UNIVERSITY EXAM PERFORMANCE REPORT\n")
            f.write("="*70 + "\n")
            f.write(f"Topics: {topics}\n")
            f.write("="*70 + "\n\n")
            f.write(total_eval)
            f.write("\n\n" + "="*70 + "\n")
            f.write("PERSONALIZED STUDY NOTES\n")
            f.write("="*70 + "\n\n")
            f.write(focused_notes)
        
        print(f"✅ Materials saved to '{filename}'")
    
    print("\n" + "="*70)
    print("✅ EXAM PREPARATION SESSION COMPLETE!")
    print("="*70)
    print("💪 Study the notes focusing on weak areas.")
    print("📚 Practice more questions on difficult topics.")
    print("🎯 Good luck with your university exams!")
    print("="*70)


def main():
    """Entry point of the program."""
    while True:
        run_qa_session()
        
        print("\n🔄 CONTINUE STUDYING?")
        print("-"*70)
        again = input("Would you like to prepare for another topic? (yes/no): ").strip().lower()
        if again not in ['yes', 'y']:
            print("\n" + "="*70)
            print("👋 Thank you for using the Exam Preparation System!")
            print("📚 Keep studying and best of luck with your exams!")
            print("="*70)
            break
        print("\n")  

if __name__ == "__main__":
    main()