import os
import re
import uuid
from dotenv import load_dotenv
import docker
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import TypedDict, Annotated, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

# 1. Define the Pipeline State
class PipelineState(TypedDict):
    messages: Annotated[list, add_messages] 

# 2. Initialize Gemini and Docker
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.0
)
docker_client = docker.from_env()

def extract_code(text):
    match = re.search(r"```(?:python)?\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else text.strip()

# 3. The Developer Agent Node (Now with Rate Limit Retries!)
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=5, min=5, max=30), 
    retry=retry_if_exception_type(ResourceExhausted) 
)
def write_patch_node(state: PipelineState):
    print("🤖 Agent is writing a patch...")
    try:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("⚠️ Rate limit hit! Waiting a few seconds before retrying...")
            raise ResourceExhausted(str(e)) 
        raise e 


# 4. The QA Sandbox Node
def test_code_node(state: PipelineState):
    print("🐳 Sending code to Sandbox...")
    
    agent_message = state["messages"][-1].content
    code = extract_code(agent_message)
    
    test_script = f"""
{code}

assert add_numbers(2, 3) == 5, "Failed on basic numbers"
assert add_numbers("2", "3") == 5, "Failed on string inputs"
print('SUCCESS')
"""
    
    try:
        docker_client.containers.run(
            "python:3.11-slim",
            command=["python", "-c", test_script],
            remove=True
        )
        print("✅ Tests Passed!")
        return {"messages": [HumanMessage(content="Test passed!")]}
        
    except docker.errors.ContainerError as e:
        print("❌ Tests Failed! Sending error back to Agent...")
        error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
        feedback = f"The code failed in testing with this error:\n{error_msg}\nPlease fix the code so it handles both numbers and string inputs, and return ONLY the corrected Python code."
        return {"messages": [HumanMessage(content=feedback)]}

# 5. The Routing Logic
def route_next(state: PipelineState):
    last_message = state["messages"][-1].content
    if "Test passed!" in last_message:
        return END
    if len(state["messages"]) > 6:
        print("🛑 Max retries reached.")
        return END
    return "developer_agent"

# 6. Wire the Graph Together
workflow = StateGraph(PipelineState)
workflow.add_node("developer_agent", write_patch_node)
workflow.add_node("qa_sandbox", test_code_node)
workflow.add_edge(START, "developer_agent")
workflow.add_edge("developer_agent", "qa_sandbox")
workflow.add_conditional_edges("qa_sandbox", route_next)

# 7. NEW: FastAPI Server Setup
app = FastAPI(title="Self-Healing CI/CD Agent")

# Define the expected JSON payload format
class WebhookPayload(BaseModel):
    error_log: Optional[str] = None
    repository: Optional[dict] = None  # Changed from str to dict to accept GitHub's format
    zen: Optional[str] = None # GitHub uses this for ping events

@app.post("/webhook/trigger")
async def trigger_pipeline(payload: WebhookPayload):
    # Check if this is just a GitHub ping event
    if payload.zen:
        print(f"👋 GitHub Ping Received: {payload.zen}")
        return {"status": "success", "message": "Ping acknowledged"}
        
    # Guardrail: Ensure we actually have an error log before running LangGraph
    if not payload.error_log:
        return {"status": "ignored", "message": "No error log provided."}

    print(f"\n🔔 Webhook received for repo: {payload.repository}")
    
    # Generate a unique Job ID for this execution
    run_id = f"job_{uuid.uuid4().hex[:8]}"
    print(f"📂 Starting execution track: {run_id}")
    
    with SqliteSaver.from_conn_string("pipeline_state.db") as memory:
        agent_app = workflow.compile(checkpointer=memory)
        
        initial_state = {"messages": [HumanMessage(content=payload.error_log)]}
        config = {"configurable": {"thread_id": run_id}}
        
        # Trigger the LangGraph execution
        result = agent_app.invoke(initial_state, config=config)
        
        # Extract the final, tested code
        final_message = result["messages"][-2].content if "Test passed!" in result["messages"][-1].content else "Failed to fix code."
        
        return {
            "status": "success",
            "run_id": run_id,
            "patched_code": final_message
        }

# Start the server on port 8000
if __name__ == "__main__":
    print("🚀 Starting FastAPI Server on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)