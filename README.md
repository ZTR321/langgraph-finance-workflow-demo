# LangGraph Finance Workflow Demo

A minimal finance Q&A and compliance-review workflow built with LangGraph.

## What This Project Does

This demo organizes the following flow:

`Researcher -> Tools -> Researcher -> Reviewer`

It can:

- answer general workflow questions
- call a stock price query tool when needed
- draft a response after tool usage
- pass the draft through a conservative reviewer node
- expose the workflow through a simple Gradio chat interface

## Why I Built It

I wanted to separate:

- response generation
- tool usage
- output review

instead of putting everything into one large prompt.

The project is intentionally scoped as a **workflow demo**, not a production investment research platform.

## Tech Stack

- Python
- LangGraph
- LangChain
- Tool Calling
- Requests
- Gradio

## Repository Structure

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── project_notes.md
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Environment Variables

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
PROJECT_2_MODEL_NAME=gpt-4o-mini
```

## Key Points I Can Explain

- Why LangGraph is useful for explicit node and edge design
- What `bind_tools`, `ToolNode`, and `tools_condition` do in a minimal tool-calling loop
- Why the `Researcher` and `Reviewer` are better described as two roles using one model instance
- Why prompt-based output review is still not the same as a full rule engine

## Current Boundaries

- Only one tool is implemented
- The workflow is still a demo-level system
- Review logic is prompt-based rather than policy-engine based
- History support is basic message passing, not a long-term memory system

## Notes

This repository is meant to demonstrate explainable workflow orchestration and tool integration, with honest project boundaries kept explicit.
