```
# 🤖 Agentic Self-Healing CI/CD Pipeline

An autonomous AI developer loop that automatically detects failing code pushed to GitHub, writes a patch, tests it in an isolated QA sandbox, and submits a Pull Request with the verified fix.

## 🚀 The Vision
Traditional CI/CD pipelines tell you *when* your code breaks. This pipeline actually **fixes it**. By combining LangGraph reasoning agents with Dockerized testing environments, this project acts as an always-on AI engineer that catches bugs and handles the tedious debugging process completely autonomously.

## ⚙️ How It Works
1. **Detection:** A GitHub Action monitors your repository for failing tests on every push.
2. **Trigger:** If a test fails, the Action securely sends the error log to a FastAPI webhook.
3. **Reasoning:** A LangGraph agent (powered by Gemini 2.5 Flash) analyzes the stack trace and writes a Python code patch.
4. **Validation:** The AI's code is injected into a transient Docker container and tested against the original assertions.
5. **Auto-PR:** If the tests pass, PyGithub creates a new branch and automatically opens a Pull Request on your repository with the fixed code.

## 🛠️ Tech Stack
* **Agent Framework:** LangGraph, LangChain
* **LLM Engine:** Google Gemini 2.5 Flash
* **Backend Server:** FastAPI, Uvicorn, Python
* **Environment Validation:** Docker
* **CI/CD Integration:** GitHub Actions, PyGithub
* **Cloud Hosting:** AWS EC2 (Ubuntu)

---

## 💻 How to Use This Agent For Your Own Project

Want this AI developer to automatically fix bugs in your repository? Follow these steps to host the engine and integrate it into your workflow.

### 1. Set Up the Engine
Clone this repository to your local machine or a cloud server (like AWS EC2):
```bash
git clone [https://github.com/radhikarajput0410-wq/Agentic-self-healing-pipeline.git](https://github.com/radhikarajput0410-wq/Agentic-self-healing-pipeline.git)
cd Agentic-self-healing-pipeline

```

Create a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```
# 🤖 Agentic Self-Healing CI/CD Pipeline

An autonomous AI developer loop that automatically detects failing code pushed to GitHub, writes a patch, tests it in an isolated QA sandbox, and submits a Pull Request with the verified fix.

## 🚀 The Vision
Traditional CI/CD pipelines tell you *when* your code breaks. This pipeline actually **fixes it**. By combining LangGraph reasoning agents with Dockerized testing environments, this project acts as an always-on AI engineer that catches bugs and handles the tedious debugging process completely autonomously.

## ⚙️ How It Works
1. **Detection:** A GitHub Action monitors your repository for failing tests on every push.
2. **Trigger:** If a test fails, the Action securely sends the error log to a FastAPI webhook.
3. **Reasoning:** A LangGraph agent (powered by Gemini 2.5 Flash) analyzes the stack trace and writes a Python code patch.
4. **Validation:** The AI's code is injected into a transient Docker container and tested against the original assertions.
5. **Auto-PR:** If the tests pass, PyGithub creates a new branch and automatically opens a Pull Request on your repository with the fixed code.

## 🛠️ Tech Stack
* **Agent Framework:** LangGraph, LangChain
* **LLM Engine:** Google Gemini 2.5 Flash
* **Backend Server:** FastAPI, Uvicorn, Python
* **Environment Validation:** Docker
* **CI/CD Integration:** GitHub Actions, PyGithub
* **Cloud Hosting:** AWS EC2 (Ubuntu)

---

## 💻 How to Use This Agent For Your Own Project

Want this AI developer to automatically fix bugs in your repository? Follow these steps to host the engine and integrate it into your workflow.

### 1. Set Up the Engine
Clone this repository to your local machine or a cloud server (like AWS EC2):
```bash
git clone [https://github.com/radhikarajput0410-wq/Agentic-self-healing-pipeline.git](https://github.com/radhikarajput0410-wq/Agentic-self-healing-pipeline.git)
cd Agentic-self-healing-pipeline
### Create a virtual environment and install the required dependencies:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### 2. Configure Your Secrets

Create a `.env` file in the root directory and add your API keys:

```env
GEMINI_API_KEY=your_google_gemini_key
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_REPO_NAME=your-username/your-target-repo

```

### 3. Start the Server

Run the FastAPI server. (If you are running this locally, you will need to expose port 8000 using a tool like Ngrok).

```bash
python pipeline.py

```

### 4. Add the GitHub Action to Your Target Repo

In the repository you want the AI to monitor, create a new GitHub secret named `WEBHOOK_URL` containing your server's endpoint (e.g., `http://your-server-ip:8000/webhook/trigger`).

Then, add the following file to `.github/workflows/ai-healer.yml` in your target repository:

```yaml
name: AI Self-Healing Pipeline

on:
  push:
    branches: [ "main" ]

jobs:
  test-and-heal:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Run Tests (Catch Failure)
        id: run_tests
        run: |
          python -m unittest discover 2> error_log.txt || echo "TESTS_FAILED=true" >> $GITHUB_ENV
          
      - name: Trigger AI Agent via Webhook
        if: env.TESTS_FAILED == 'true'
        run: |
          ERROR_CONTENT=$(cat error_log.txt | jq -R -s '.')
          curl -X POST -H "Content-Type: application/json" \
               -d "{\"repository\": {\"name\": \"YourRepoName\"}, \"error_log\": $ERROR_CONTENT}" \
               ${{ secrets.WEBHOOK_URL }}

```

## 👨‍💻 Author

**RADHIKA RAJPUT**
Built to explore the intersection of artificial intelligence, automated testing, and product engineering.

