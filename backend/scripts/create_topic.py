#!/usr/bin/env python3
"""
Create a topic with a system prompt via the API.

Usage:
    python create_topic.py --name "Software Interview" \
        --description "Practice software engineering interviews" \
        --base-url http://localhost:8000 \
        --email admin@example.com \
        --password yourpassword

    # Or pipe in a system prompt from a file:
    python create_topic.py --name "Software Interview" \
        --system-prompt-file prompts/software_interview.txt \
        --email admin@example.com --password yourpassword
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BUILTIN_PROMPTS = {
    "software-interview": {
        "name": "Software Interview",
        "description": "Practice software engineering interviews with a realistic interviewer",
        "system_prompt": (
            "You are an experienced software engineering interviewer at a top tech company. "
            "Your goal is to conduct a realistic technical interview.\n\n"
            "Guidelines:\n"
            "- Start by introducing yourself and giving the candidate a warm welcome.\n"
            "- Ask one coding, system design, or behavioral question at a time.\n"
            "- For coding questions, let the candidate think out loud and guide them with hints "
            "if they are stuck, rather than giving the answer directly.\n"
            "- Evaluate problem-solving approach, code quality, and communication skills.\n"
            "- After the candidate answers, give concise, constructive feedback.\n"
            "- Adjust difficulty based on the candidate's responses.\n"
            "- Keep answers conversational and natural since your responses will be read aloud.\n"
            "- Do not use markdown formatting, bullet points, or code blocks in your responses "
            "as they do not translate well to speech.\n"
            "- Wrap up the session with overall feedback when the candidate is done."
        ),
    },
    "english-conversation": {
        "name": "English Conversation",
        "description": "Practice everyday English conversation",
        "system_prompt": (
            "You are a friendly native English speaker helping someone practice conversational English. "
            "Speak naturally and clearly. Gently correct grammar or vocabulary mistakes by rephrasing "
            "the sentence correctly in your reply without making the user feel bad. "
            "Keep responses concise and natural since they will be spoken aloud. "
            "Do not use bullet points, markdown, or formatting — just plain conversational sentences."
        ),
    },
    "language-tutor": {
        "name": "Language Tutor",
        "description": "Practice a foreign language with a patient tutor",
        "system_prompt": (
            "You are a patient and encouraging language tutor. "
            "The user wants to practice speaking a foreign language. "
            "Respond in the target language and provide simple, clear sentences. "
            "When the user makes a mistake, gently correct it and explain why. "
            "Keep your responses short and conversational since they will be read aloud. "
            "Do not use bullet points or markdown formatting."
        ),
    },
}


def login(base_url: str, email: str, password: str) -> str:
    url = f"{base_url}/auth/login"
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            return body["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Login failed ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def create_topic(base_url: str, token: str, name: str, description: str | None, system_prompt: str | None) -> dict:
    url = f"{base_url}/topics"
    payload = {"name": name}
    if description:
        payload["description"] = description
    if system_prompt:
        payload["system_prompt"] = system_prompt
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Create topic failed ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a topic via the AI Speaker API")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")

    name_group = parser.add_mutually_exclusive_group(required=True)
    name_group.add_argument("--name", help="Topic name (custom)")
    name_group.add_argument(
        "--preset",
        choices=list(BUILTIN_PROMPTS.keys()),
        help="Use a built-in preset: " + ", ".join(BUILTIN_PROMPTS.keys()),
    )

    parser.add_argument("--description", help="Short description of the topic")
    parser.add_argument("--system-prompt", help="System prompt text")
    parser.add_argument("--system-prompt-file", type=Path, help="File containing the system prompt")

    args = parser.parse_args()

    if args.preset:
        preset = BUILTIN_PROMPTS[args.preset]
        name = args.name or preset["name"]
        description = args.description or preset["description"]
        system_prompt = args.system_prompt or preset["system_prompt"]
    else:
        name = args.name
        description = args.description
        if args.system_prompt_file:
            system_prompt = args.system_prompt_file.read_text()
        else:
            system_prompt = args.system_prompt

    print(f"Logging in as {args.email}...")
    token = login(args.base_url, args.email, args.password)
    print("Login successful.")

    print(f"Creating topic '{name}'...")
    topic = create_topic(args.base_url, token, name, description, system_prompt)

    print("Topic created successfully:")
    print(json.dumps(topic, indent=2, default=str))


if __name__ == "__main__":
    main()
