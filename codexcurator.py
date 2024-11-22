import os
import sys
import json
import requests
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Retrieve the OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in the environment. Please add it to your .env file.")

# Initialize OpenAI client with the API key
client = OpenAI(api_key=api_key)

# Ensure the required directories and files exist
DOWNLOAD_FOLDER = "./downloaded_papers"
PAPERS_FILE = "./papers.jsonl"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

if not os.path.exists(PAPERS_FILE):
    with open(PAPERS_FILE, 'w') as f:
        pass  # Create an empty file

ASSISTANT_ID = "asst_YNyW95TTHYeFgG6h41ArLGi7"  # Your assistant ID


def download_paper(url: str) -> str:
    """
    Download the paper from the given URL and save it in the DOWNLOAD_FOLDER.
    Append the file path and URL to PAPERS_FILE.
    """
    try:
        # Get the filename from the URL
        filename = os.path.basename(url.split("?")[0])  # Remove query params
        if not filename.endswith(".pdf"):  # Ensure the correct extension
            filename += ".pdf"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Append the entry to papers.jsonl
        with open(PAPERS_FILE, 'a') as f:
            json.dump({"url": url, "file_path": file_path}, f)
            f.write("\n")

        print(f"Downloaded and saved: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"Failed to download the paper: {e}")
        sys.exit(1)


def upload_to_openai(file_path: str) -> dict:
    """
    Upload the given file to OpenAI and return the file info.
    """
    try:
        with open(file_path, "rb") as file:
            response = client.files.create(file=file, purpose="assistants")
        print(f"Uploaded to OpenAI: {response}")
        return response
    except Exception as e:
        print(f"Failed to upload the file to OpenAI: {e}")
        sys.exit(1)


def analyze_with_assistant(file_id: str):
    """
    Analyze the uploaded file using the assistant and print the result.
    """
    try:
        # Retrieve the assistant
        codexcurator = client.beta.assistants.retrieve(ASSISTANT_ID)
        print("Retrieved Assistant:", codexcurator)

        # Create a thread for interaction
        message_thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": "Please summarize this document in simple terms.",
                    "attachments": [
                        {
                            "file_id": file_id,
                            "tools": [{"type": "code_interpreter"}]
                        }
                    ]
                }
            ]
        )
        print("Message Thread Created:", message_thread)

        # Run the thread
        run = client.beta.threads.runs.create(
            thread_id=message_thread.id,
            assistant_id=codexcurator.id
        )
        print("Run Started:", run)

        # Poll until the run is complete or fails
        while run.status not in ["completed", "failed"]:
            print(f"Run Status: {run.status}")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(run.id, thread_id=message_thread.id)

        # Handle failed state
        if run.status == "failed":
            print(f"Run Failed. Details: {run}")
            sys.exit(1)

        # Retrieve and print the messages from the thread
        thread_messages = client.beta.threads.messages.list(thread_id=message_thread.id)
        print("Run Completed. Messages:")
        for message in thread_messages:
            # Adjust based on the actual attributes of the `message` object
            print(f"{message.role}: {message.content}")

    except Exception as e:
        print(f"Failed to analyze file with assistant: {e}")
        sys.exit(1)




def main():
    if len(sys.argv) > 1:
        # URL passed as a command-line argument
        url = sys.argv[1]
    else:
        # Interactive mode
        url = input("> please give me the URL to a paper: ").strip()

    # Download, upload, and analyze the paper
    file_path = download_paper(url)
    uploaded_file = upload_to_openai(file_path)
    analyze_with_assistant(uploaded_file.id)  # Use dot notation to access `id`


if __name__ == "__main__":
    main()