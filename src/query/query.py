# /src/query/query.py
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage  # Import HumanMessage

def generate_response(prompt, work_type=None, top_k=5):
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    
    messages = []
    
    if work_type == "chunking":
        system_instruction = """
- **You are a prefect document splitter**.
- When you split the document, you shouldn't alter the original content
- Please respond exclusively in Korean.
- Reference the target_data to ensure the task is performed accurately as requested.
- Ensure the response strictly follows the JSON format.
        """
        
        messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))
        
    try:
        # LLM 응답 생성
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"An error occurred while generating a response: {e}"