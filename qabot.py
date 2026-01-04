from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from yttranscriber import model

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

def ask_questions(user_topics):
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert university-level exam tutor. "
             "Always follow the formatting style requested by the user."),
            
            MessagesPlaceholder(variable_name="chat_history"),
            
            ("human",
             "Create exam-oriented notes.\n\n"
             "Topic:\n{user_topics}\n\n"
             "Answer Style: it should follow this answer style"
             "Rules:\n"
             "- bullet → bullet points\n"
             "- steps → numbered steps\n"
             "- table → markdown table\n"
             "- short → concise points\n"
             "- detailed → in-depth explanation\n"
             "the answer style should be like this unless the user asks for something else")
        ])

        chain = prompt | model | StrOutputParser()

        response = chain.invoke({
            "user_topics": user_topics,
            "answer_style": answer_style,
            "chat_history": memory.load_memory_variables({})["chat_history"]
        })

        # Save to memory
        memory.save_context(
            {"user": user_topics},
            {"assistant": response}
        )

        return response

    except Exception as e:
        return f"Error occurred: {e}"


def main():
    while True:
        user_input = input("Enter your topic (or 'exit'): ")
        if user_input == "exit":
            break

        notes = make_notes(user_input)
        print("\n", notes, "\n")


if __name__ == "__main__":
    main()
