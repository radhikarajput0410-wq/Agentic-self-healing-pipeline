import os
import re
import uuid
from dotenv import load_dotenv
import docker
import uvicorn
from fastapi import FastAPI, Request
from github import Github
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

# 3. The Developer Agent Node
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

# 5. The GitHub Pull Request Node
def create_pr_node(state: PipelineState):
    print("🚀 Opening Pull Request on GitHub...")
    
    # Extract the final, successful code from the agent's last message (before the "Test passed!" message)
    agent_message = state["messages"][-2].content
    fixed_code = extract_code(agent_message)
    
    # Authenticate to GitHub using your secure .env variables
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(os.getenv("GITHUB_REPO_NAME"))
    
    # Generate a unique branch name for the fix
    branch_name = f"ai-fix-{uuid.uuid4().hex[:8]}"
    
    # Create the new branch off of 'main'
    main_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
    
    file_path = "fixed_code.py" # The file the AI will create/update
    
    # Write the fixed code to the new branch
    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        repo.update_file(contents.path, "🤖 AI Self-Healing Fix", fixed_code, contents.sha, branch=branch_name)
    except:
        repo.create_file(file_path, "🤖 AI Self-Healing Fix", fixed_code, branch=branch_name)
    
    # Open the Pull Request
    pr = repo.create_pull(
        title="🤖 AI Automated Fix",
        body="The LangGraph Agent has successfully fixed the failing tests. Please review the updated code.",
        head=branch_name,
        base="main"
    )
    
    print(f"✅ Pull Request Created Successfully: {pr.html_url}")
    return state

# 6. The Routing Logic
def route_next(state: PipelineState):
    last_message = state["messages"][-1].content
    if "Test passed!" in last_message:
        return "create_pr" # Routes to the new PR node instead of END
    if len(state["messages"]) > 6:
        print("🛑 Max retries reached.")
        return END
    return "developer_agent"

# 7. Wire the Graph Together
workflow = StateGraph(PipelineState)
workflow.add_node("developer_agent", write_patch_node)
workflow.add_node("qa_sandbox", test_code_node)
workflow.add_node("create_pr", create_pr_node) # Add the new node

workflow.add_edge(START, "developer_agent")
workflow.add_edge("developer_agent", "qa_sandbox")
workflow.add_conditional_edges("qa_sandbox", route_next)
workflow.add_edge("create_pr", END) # Close the loop after the PR is made

# 8. FastAPI Server Setup
app = FastAPI(title="Self-Healing CI/CD Agent")

class WebhookPayload(BaseModel):
    error_log: Optional[str] = None
    repository: Optional[dict] = None  
    zen: Optional[str] = None 

@app.post("/webhook/trigger")
async def trigger_webhook(request: Request):
    # 1. Read the incoming GitHub payload
    payload = await request.json()
    
    # 2. Dynamically extract the repository name (e.g., "owner/repo-name")
    repo_name = payload.get("repository", {}).get("full_name")
    error_log = payload.get("error_log", "No error log provided.")
    
    if not repo_name:
        return {"status": "error", "message": "Repository name missing from payload"}
        
    print(f"🚨 Bug detected in repository: {repo_name}")
    
    # 3. Authenticate with GitHub using your token
    github_token = os.getenv("GITHUB_TOKEN")
    g = Github(github_token)
    
    # 4. Target the specific repository dynamically!
    repo = g.get_repo(repo_name)
    
    # Run the AI Agent (Pass the error log to LangGraph)
    print("🧠 Starting LangGraph Reasoning Agent...")
    config = {"configurable": {"thread_id": "1"}}
    final_state = app_graph.invoke(
        {"messages": [("user", f"Fix this error:\n{error_log}")]}, 
        config=config
    )
    
    final_code = final_state["messages"][-1].content
    
    # Create a new branch and PR with the fix
    base_branch = repo.get_branch("main")
    new_branch_name = f"ai-fix-{uuid.uuid4().hex[:6]}"
    repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=base_branch.commit.sha)
    
    file_contents = repo.get_contents("math_functions.py", ref="main")
    repo.update_file(
        file_contents.path,
        "🤖 AI Automated Fix",
        final_code,
        file_contents.sha,
        branch=new_branch_name
    )
    
    repo.create_pull(
        title="🤖 AI Automated Fix",
        body="The LangGraph Agent has successfully fixed the failing tests. Please review the updated code.",
        head=new_branch_name,
        base="main"
    )
    
    return {"status": "success", "message": f"Fix deployed to {repo_name}"}
        

if __name__ == "__main__":
    print("🚀 Starting FastAPI Server on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)