import os
import json
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google import generativeai as genai
from dotenv import load_dotenv
from storage import load_tasks, save_tasks
import re
from datetime import datetime, timedelta

# Load API Key from credentials.env
load_dotenv("credentials.env")
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY. Set it in credentials.env.")
else:
    print("API key loaded")

# Configure Gemini AI & Flask App
genai.configure(api_key=API_KEY)
app = Flask(__name__)
tasks = load_tasks()  # Load tasks from storage
limiter = Limiter(get_remote_address, app=app, default_limits=["15 per minute"])

# AI Response Handler
def ai_response(prompt, tokens=200):
    model = genai.GenerativeModel("gemini-2.0-flash")
    return model.generate_content(prompt, generation_config={"max_output_tokens": tokens}).text.strip()

# AI Task Assistance (kept for other functions)
@app.route('/task-search', methods=['POST'])
@limiter.limit("15 per minute")
def task_search():
    query = request.json.get("query", "").strip().lower()
    if not query:
        return jsonify({"error": "Search query required"}), 400

    matching_tasks = {}
    for task_id, task in tasks.items():
        # Search in title, priority, category, and due_date (case-insensitive)
        if (query in task.get("title", "").lower() or
            query in task.get("priority", "").lower() or
            query in task.get("category", "").lower() or
            query in task.get("due_date", "").lower()):
            matching_tasks[task_id] = task

    if matching_tasks:
        return jsonify({
            "matching_tasks": matching_tasks,
            "total_matches": len(matching_tasks)
        })
    else:
        return jsonify({
            "message": "No matching tasks found.",
            "matching_tasks": {}
        })


# AI-Based Task Prioritization
@app.route('/ai-prioritize', methods=['POST'])
@limiter.limit("15 per minute")
def ai_prioritize():
    task_id = request.json.get("task_id")
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    prompt = f"""
    Based on this task, assign a priority (Low, Medium, High, Urgent):
    Title: {tasks[task_id]['title']}
    Description: {tasks[task_id].get('desc', 'No description')}
    Due Date: {tasks[task_id].get('due_date', 'No Due Date')}
    Provide only the priority level as a single word.
    """
    tasks[task_id]['priority'] = ai_response(prompt)
    save_tasks(tasks)
    return jsonify({"message": "Priority updated", "task": tasks[task_id]})

# AI Task Summarization
@app.route('/ai-summarize', methods=['POST'])
@limiter.limit("15 per minute")
def ai_summarize():
    if not tasks:
        return jsonify({"summary": "No tasks available."})
    prompt = f"""
        Summarize the following tasks. Provide a concise summary that includes the total number of pending and completed tasks, the number of high-priority tasks, and any upcoming due dates. Return only the summary in plain text.

        {json.dumps(list(tasks.values()), indent=2)}
        """
    return jsonify({"summary": ai_response(prompt, tokens=250)})

# AI Task Description Enhancement
@app.route('/ai-enhance-description', methods=['POST'])
@limiter.limit("15 per minute")
def ai_enhance_description():
    task_id = request.json.get("task_id")
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    prompt = f"""
        Improve the task description below. Return a concise, enhanced description in a clean roman number list format that includes one clear objective and three key steps. Do not include any extra commentary or multiple options.

        Current description: "{tasks[task_id].get('desc', '')}"
    """
    tasks[task_id]['desc'] = ai_response(prompt)
    save_tasks(tasks)
    return jsonify({"message": "Description updated", "task": tasks[task_id]})

# AI Task Priority Suggestion
@app.route('/ai-suggest-priority', methods=['POST'])
@limiter.limit("15 per minute")
def ai_suggest_priority():
    title, desc = request.json.get("title", ""), request.json.get("desc", "")
    if not title:
        return jsonify({"error": "Title required"}), 400

    prompt = f"""
    Suggest a priority for this task: "{title}" - "{desc}"
    Choose from: Low, Medium, High, Urgent.
    """
    return jsonify({"suggested_priority": ai_response(prompt)})

# AI Task Category Suggestion
@app.route('/ai-suggest-category', methods=['POST'])
@limiter.limit("15 per minute")
def ai_suggest_category():
    title, desc = request.json.get("title", ""), request.json.get("desc", "")
    if not title:
        return jsonify({"error": "Title required"}), 400

    prompt = f"""
    Categorize this task: "{title}" - "{desc}"
    Choose from: Work, Personal, Study, Health, Finance, Home, Shopping, Other.
    """
    return jsonify({"suggested_category": ai_response(prompt)})

# CRUD Operations

# Get tasks with pagination
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    if not tasks:
        return jsonify({"error": "No tasks available."}), 404

    task_list = list(tasks.values())
    start = (page - 1) * page_size
    end = start + page_size
    paginated_tasks = task_list[start:end]

    return jsonify({
        "tasks": paginated_tasks,
        "page": page,
        "page_size": page_size,
        "total_tasks": len(task_list)
    })

def process_title(input_title):
    """
    Processes the input title to extract time-related information.
    For example, if the title is "mother's medicine at 6oclock",
    it returns ("mother's medicine", "YYYY-MM-DD 06:00") where YYYY-MM-DD is today's date.
    If no time is found, returns the original title and "No Due Date".
    """
    # --- Time Extraction ---
    time_pattern = re.compile(r'(?:\S*at\S*\s+)?at\s*(\d{1,2}(?::\d{2})?)\s*(?:o\'?clock)?', re.IGNORECASE)
    time_match = time_pattern.search(input_title)
    if time_match:
        time_str = time_match.group(1)
        if ':' not in time_str:
            time_str += ":00"
        try:
            time_obj = datetime.strptime(time_str, "%H:%M").time()
        except Exception:
            time_obj = None
    else:
        time_obj = None

    # --- Date Extraction ---
    date_pattern = re.compile(r'\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE)
    date_match = date_pattern.search(input_title)
    if date_match:
        date_keyword = date_match.group(1).lower()
        if date_keyword == 'today':
            date_obj = datetime.today()
        elif date_keyword == 'tomorrow':
            date_obj = datetime.today() + timedelta(days=1)
        else:
            weekdays = {
                'monday': 0,
                'tuesday': 1,
                'wednesday': 2,
                'thursday': 3,
                'friday': 4,
                'saturday': 5,
                'sunday': 6
            }
            today_weekday = datetime.today().weekday()
            target_weekday = weekdays[date_keyword]
            days_ahead = (target_weekday - today_weekday + 7) % 7
            days_ahead = days_ahead if days_ahead > 0 else 7
            date_obj = datetime.today() + timedelta(days=days_ahead)
    else:
        date_obj = None

    # --- Construct Due Date ---
    if date_obj and time_obj:
        due_date = datetime.combine(date_obj.date(), time_obj).strftime("%Y-%m-%d %H:%M")
    elif date_obj:
        due_date = date_obj.strftime("%Y-%m-%d")
    elif time_obj:
        today_str = datetime.today().strftime("%Y-%m-%d")
        due_date = f"{today_str} {time_obj.strftime('%H:%M')}"
    else:
        due_date = "No Due Date"

    # --- Clean the Title ---
    cleaned_title = time_pattern.sub("", input_title)
    cleaned_title = date_pattern.sub("", cleaned_title)
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

    return {"clean_title": cleaned_title, "due_date": due_date}

def auto_set_priority(due_date_str):
    """
    Automatically sets the task priority based on the due date.
    If no due date is provided ("No Due Date"), returns "Low".
    Otherwise, checks how many hours away the due date is:
      - < 2 hours: "Urgent"
      - < 24 hours: "High"
      - < 72 hours: "Medium"
      - Otherwise: "Low"
    """
    if due_date_str == "No Due Date":
        return "Low"

    now = datetime.now()
    try:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    except Exception:
        return "Low"  # Fallback priority

    diff_hours = (due_date - now).total_seconds() / 3600.0

    if diff_hours < 2:
        return "Urgent"
    elif diff_hours < 24:
        return "High"
    elif diff_hours < 72:
        return "Medium"
    else:
        return "Low"

# The add_task endpoint now accepts only a title and generates all other task details using AI.
@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    if not data.get("title"):
        return jsonify({"error": "Title required"}), 400

    raw_title = data["title"]
    processed = process_title(raw_title)

    # Refined prompt with explicit instructions to return only valid JSON.
    prompt = f"""
    Generate task details for the following title: "{processed['clean_title']}".
    Provide a description, select a priority from Low, Medium, High, or Urgent,
    and choose a category from Work, Personal, Study, Health, Finance, Home, Shopping, or Other.
    Use the due date "{processed['due_date']}" extracted from the title if applicable, otherwise return "No Due Date".
    Return exactly one JSON object with only the following keys:
      - "desc": A task description.
      - "priority": One of Low, Medium, High, or Urgent.
      - "category": One of Work, Personal, Study, Health, Finance, Home, Shopping, or Other.
      - "due_date": A due date in the format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM", or "No Due Date" if not applicable.
    Do not include any additional text or formatting.
    """
    
    ai_generated = ai_response(prompt, tokens=150)
    print("AI generated response:", repr(ai_generated))
    
    # Remove markdown formatting if present
    if ai_generated.startswith("```"):
        parts = ai_generated.split("```")
        if len(parts) >= 3:
            ai_generated = parts[1].strip()
        else:
            ai_generated = ai_generated.replace("```", "").strip()
    
    # Remove a leading "json" if it exists
    if ai_generated.lower().startswith("json"):
        ai_generated = ai_generated[4:].strip()

    # If the response is empty, use default details
    if not ai_generated.strip():
        details = {
            "desc": "No description provided.",
            "priority": "Low",
            "category": "Personal",
            "due_date": processed['due_date']
        }
    else:
        try:
            details = json.loads(ai_generated)
        except Exception as e:
            print("Error parsing AI response:", e)
            print("Raw AI response:", repr(ai_generated))
            return jsonify({"error": "AI generation failed: " + str(e), "raw_response": ai_generated}), 500

    final_due_date = details.get("due_date", "No Due Date")
    if final_due_date == "No Due Date" and processed['due_date'] != "No Due Date":
        final_due_date = processed['due_date']

    task_id = str(len(tasks) + 1)
    tasks[task_id] = {
        "title": processed['clean_title'],
        "desc": details.get("desc", "No description provided."),
        "priority": details.get("priority", "Low"),
        "category": details.get("category", "Personal"),
        "due_date": final_due_date,
        "status": "Pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_tasks(tasks)
    return jsonify({"message": "Task added", "task": tasks[task_id]}), 201

@app.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    tasks[task_id].update(request.json)
    save_tasks(tasks)
    return jsonify({"message": "Task updated", "task": tasks[task_id]})

@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    del tasks[task_id]
    save_tasks(tasks)
    return jsonify({"message": f"Task {task_id} deleted!"})

# Modified AI Task Assistant / Search endpoint: now performs a local search over tasks.
@app.route('/ai-search', methods=['POST'])
@limiter.limit("15 per minute")
def ai_search():
    query = request.json.get("query", "").strip().lower()
    if not query:
        return jsonify({"error": "Search query required"}), 400

    matching_tasks = {}
    for task_id, task in tasks.items():
        # Check if the query exists in any of the relevant fields.
        if (query in task.get("title", "").lower() or
            query in task.get("priority", "").lower() or
            query in task.get("category", "").lower() or
            query in task.get("due_date", "").lower()):
            matching_tasks[task_id] = task

    if matching_tasks:
        return jsonify({
            "matching_tasks": matching_tasks,
            "total_matches": len(matching_tasks)
        })
    else:
        return jsonify({
            "message": "No matching tasks found.",
            "matching_tasks": {}
        })

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/info')
def info():
    return render_template('info.html')

# Rate Limit Error Handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Max 15 requests/min.", "retry_after": e.description}), 429

if __name__ == '__main__':
    app.run(debug=True)
