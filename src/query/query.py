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
- **You are a professional document splitter and summarizer.**
- Review the provided full document and proceed in the following order:
    1. Understand the overall meaning of the document. (You may divide it by chapters or use any method, but focus on summarizing the content as accurately as possible.)
    2. Summarize the document based on your understanding.
    3. Based on your understanding, split the original document into chunks of 300 to 500 characters. Provide a clear reason for the structure of each chunk.
    4. Ensure that all chunks collectively include the full content of the original document.

- The number of chunks does not matter as long as the splitting follows consistent criteria. (The character limit per chunk is specified in the prompt.)
- All responses must be in JSON format and written exclusively in Korean.
        """
        
        messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))
        
    try:
        # LLM 응답 생성
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"An error occurred while generating a response: {e}"