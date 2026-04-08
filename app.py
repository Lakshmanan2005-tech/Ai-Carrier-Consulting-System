import os
import requests
import sys
import json
from dotenv import load_dotenv

# MUST happen before importing any local modules that use env vars
load_dotenv(override=True)

from firebase_helper import db
from firebase_admin import firestore
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import google.generativeai as genai
import PyPDF2
import docx
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
# Trigger reload...
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, send_file, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import urllib.parse
import re
from roadmap_data import ROADMAPS,SKILL_ALIASES, RESOURCES_MAP, JOBS_MAP, INTERVIEW_MAP

# Force override to prevent old keys getting stuck in memory caching
# load_dotenv(override=True)

app = Flask(__name__, 
            template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static'))
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        print("Warning: GEMINI_API_KEY missing from .env file")
except Exception as e:
    print(f"GenAI Config Error: {str(e)}")

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_KEY_2 = os.getenv('GROQ_API_KEY_2.0')
GROQ_CHAT_API_KEY = os.getenv('GROQ_CHAT_API_KEY')

def get_groq_market_demand():
    """Fetches real-time IT market demand data using Groq Llama-3."""
    if not GROQ_CHAT_API_KEY:
        # High-quality Mock Data if API key is missing
        return {
            "skills": [
                {"name": "AI & Machine Learning", "demand": 94, "growth": 15, "color": "#6366f1"},
                {"name": "Cloud Computing", "demand": 89, "growth": 10, "color": "#0ea5e9"},
                {"name": "Full Stack Dev", "demand": 86, "growth": 8, "color": "#10b981"},
                {"name": "Cyber Security", "demand": 82, "growth": 12, "color": "#f43f5e"},
                {"name": "Data Engineering", "demand": 78, "growth": 14, "color": "#f59e0b"},
                {"name": "DevOps & SRE", "demand": 75, "growth": 9, "color": "#8b5cf6"}
            ]
        }
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_CHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = """
    Analyze the current (2024-2025) global IT job market. 
    Return exactly 6 of the most in-demand skills and their current market demand percentage (0-100).
    Provide an estimated year-over-year growth percentage for each.
    
    Strict Output Format (JSON only):
    {
        "skills": [
            {"name": "Skill Name", "demand": 95, "growth": 12, "color": "#HEX_CODE"},
            ...
        ]
    }
    Use vibrant, modern colors (Indigo, Emerald, Sky Blue, Rose, Amber, Violet).
    """

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

@app.route('/api/market-demand')
def api_market_demand():
    data = get_groq_market_demand()
    if data is None:
        return jsonify({"skills": []}), 500
    if isinstance(data, str):
        # AI returns a JSON string, try to parse it safely
        try:
            parsed = json.loads(data)
            return jsonify(parsed)
        except Exception as e:
            print(f"Failed to parse Market Demand JSON: {e}")
            return jsonify({"skills": []}), 500
    # Mock data case (it returns a dict)
    return jsonify(data)


def generate_nvidia_roadmap(skill):
    """Generates an in-depth, expert-level 12-point roadmap using NVIDIA AI."""
    if not NVIDIA_API_KEY:
        return None
        
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Generate a COMPLETE, IN-DEPTH, and PROFESSIONAL career roadmap for the skill: {skill}.

    STRICT REQUIREMENTS:

    1. STRUCTURE (VERY IMPORTANT):
    - Sections:
      1. Beginner Level
      2. Intermediate Level
      3. Advanced Level
      4. Tools & Technologies
      5. Projects (Beginner -> Advanced)
      6. Interview Preparation
      7. Industrial Workflow (Intern -> Manager)
      8. Resources (IMPORTANT SECTION)

    2. CONTENT RULES:
    - Each section must contain detailed bullet points (use • character)
    - Cover ALL topics (A to Z) without missing anything
    - Include theory + practical + real-world concepts
    - Add MORE depth (not basic — advanced explanation topics)
    - IMPORTANT: DO NOT use markdown asterisks (**) anywhere! Use HTML <b> tags for bolding key terms.

    3. RESOURCE HANDLING (VERY IMPORTANT CHANGE):
    - DO NOT add "Resource" links next to each topic
    - DO NOT repeat links
    - Instead create ONE SEPARATE SECTION titled "Resources"
    - Inside Resources section, add categorized links (Official Docs, Learning Platforms, Practice, Projects). Format them directly as Markdown: [Site Name](URL)
    - All links must be HIGH QUALITY (e.g. GeeksforGeeks, MDN, LeetCode, HackerRank, Official Docs)

    4. INDUSTRIAL WORKFLOW:
    - Include roles: Intern -> Junior -> Developer -> Senior -> Lead -> Architect -> Manager
    - For EACH role include: Responsibilities, Skills required, Goal
    - STRICT FORMATTING: You MUST format each role name using HTML bold tags (e.g. <b>Intern:</b>). DO NOT use markdown asterisks (**) anywhere!

    5. OUTPUT FORMAT (CRITICAL):
    - You must return ONLY a valid JSON object.
    - DO NOT return plaintext or markdown outside of the JSON.
    - The JSON MUST have a single root key 'sections' which is a list of objects.
    - Each object must have a 'title' (string) and 'content' (list of strings, representing the bullet points).
    """

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 4096,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        res_json = response.json()
        content = res_json['choices'][0]['message']['content']
        # Extract JSON from markdown if needed
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        return json.loads(content)
    except Exception as e:
        print(f"NVIDIA API Error: {e}")
        return None

def get_nvidia_interview_questions(skill):
    """Generates the top 5 interview questions for a given skill using Groq AI with robust fallback."""
    api_key = os.getenv('GROQ_CHAT_API_KEY') or os.getenv('GROQ_API_KEY')
    if not api_key:
        return None
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Generate exactly 5 highly relevant technical interview questions for the skill: {skill}.
    Return ONLY a JSON object:
    {{
        "items": [
            {{ "q": "Sophisticated Question", "a": "Expert-level Answer" }}
        ]
    }}
    Rules:
    - Include 1-3 keywords wrapped in <span class="iq-keyword">...</span> in both 'q' and 'a'.
    - Use JSON format ONLY.
    """

    # Try models in order of reliability
    models = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]
    
    for model_name in models:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"}
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            res_json = response.json()
            content = res_json['choices'][0]['message']['content'].strip()
            
            # Robust JSON extraction
            if '```' in content:
                content = re.sub(r'```(?:json)?|```', '', content).strip()
            
            data = json.loads(content)
            if data and (data.get('items') or data.get('questions')):
                # Normalize key names
                if 'questions' in data and 'items' not in data:
                    data['items'] = data['questions']
                return data
        except Exception as e:
            print(f"Groq API Attempt ({model_name}) failed: {e}")
            continue # Try next model
            
    return None

@app.route('/api/interview-questions')
def api_interview_questions():
    skill = request.args.get('skill', 'Software Engineering')
    questions = get_nvidia_interview_questions(skill)
    if questions:
        return jsonify(questions)
    return jsonify({"questions": []}), 500

def get_canonical_skill(skill_query):
    """Normalizes a skill name based on aliases and existing roadmaps."""
    if not skill_query:
        return ""
    
    skill_clean = skill_query.lower().strip()
    
    # 1. Check direct aliases
    if skill_clean in SKILL_ALIASES:
        return SKILL_ALIASES[skill_clean]
    
    # 2. Check if it's already a direct key in ROADMAPS
    if skill_clean in ROADMAPS:
        return skill_clean
        
    # 3. Fuzzy match: check if clean name is INSIDE a key or vice versa
    for key in ROADMAPS.keys():
        if skill_clean in key or key in skill_clean:
            return key
            
    return skill_clean

# Official Career Portals Mapping (Strict)
OFFICIAL_CAREERS = {
    "google": "https://www.google.com/about/careers/applications/jobs/results/",
    "microsoft": "https://careers.microsoft.com/us/en/search-results",
    "amazon": "https://amazon.jobs/en/search?offset=0&result_limit=10&sort=recent",
    "apple": "https://www.apple.com/jobs/in/",
    "meta": "https://www.metacareers.com/jobs/",
    "tcs": "https://www.tcs.com/careers/india",
    "infosys": "https://www.infosys.com/careers/",
    "wipro": "https://careers.wipro.com/global-india/",
    "hcl": "https://www.hcltech.com/careers",
    "accenture": "https://www.accenture.com/in-en/careers",
    "adobe": "https://www.adobe.com/careers.html",
    "netflix": "https://jobs.netflix.com/search",
    "uber": "https://www.uber.com/about/careers/",
    "zomato": "https://www.zomato.com/careers",
    "swiggy": "https://www.swiggy.com/careers/",
    "ola": "https://ola.recruitee.com/",
    "flipkart": "https://www.flipkartcareers.com/",
    "paytm": "https://paytm.com/careers/",
    "atlassian": "https://www.atlassian.com/company/careers",
    "ibm": "https://www.ibm.com/careers/in-en/search",
    "oracle": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions"
}


def get_live_jobs():
    """Fetches trending IT jobs with DIRECT DEEP LINKS to official career portals using Groq AI."""
    fallback_jobs = [
        {"company": "Zoho", "role": "Software Developer", "location": "Chennai", "salary": "₹7 - ₹12 LPA", "type": "Full-Time", "logo": "fa-solid fa-z", "logo_url": "https://www.google.com/s2/favicons?domain=zoho.com&sz=128", "url": "https://www.zoho.com/careers/search.html"}, 
        {"company": "Freshworks", "role": "Product Engineer", "location": "Chennai", "salary": "₹8 - ₹10 LPA", "type": "Full-Time", "logo": "fa-solid fa-leaf", "logo_url": "https://www.google.com/s2/favicons?domain=www.freshworks.com&sz=128", "url": "https://www.freshworks.com/company/careers/"},
        {"company": "TCS", "role": "Ninja Developer", "location": "Chennai", "salary": "₹3.5 - ₹7 LPA", "type": "Full-Time", "logo": "fa-solid fa-building-columns", "logo_url": "https://www.google.com/s2/favicons?domain=www.tcs.com&sz=128", "url": "https://www.tcs.com/careers/india"},
        {"company": "Accenture", "role": "Associate Software Engineer", "location": "Chennai", "salary": "₹4.5 - ₹6.5 LPA", "type": "Full-Time", "logo": "fa-solid fa-a", "logo_url": "https://www.google.com/s2/favicons?domain=www.accenture.com&sz=128", "url": "https://www.accenture.com/in-en/careers/jobsearch?jk=&location=India"},
        {"company": "Amazon", "role": "Software Dev Engineer I", "location": "Chennai", "salary": "₹18 - ₹24 LPA", "type": "Full-Time", "logo": "fa-brands fa-amazon", "logo_url": "https://www.google.com/s2/favicons?domain=www.amazon.com&sz=128", "url": "https://amazon.jobs/en/search?loc_query=India"},
        {"company": "HCLTech", "role": "Graduate Engineer Trainee", "location": "Chennai", "salary": "₹3.5 - ₹5 LPA", "type": "Full-Time", "logo": "fa-solid fa-h", "logo_url": "https://www.google.com/s2/favicons?domain=www.hcltech.com&sz=128", "url": "https://www.hcltech.com/careers/careers-in-india"}
    ]

    import random
    random.shuffle(fallback_jobs)

    if not GROQ_API_KEY:
        return fallback_jobs
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Identify exactly 6 IT jobs (SDE, DevOps, Interns) CURRENTLY LIVE (2024-2025) strictly within TAMIL NADU, India (Chennai, Coimbatore, Madurai, Trichy, etc.).
    Do NOT include jobs outside of Tamil Nadu.
    Provide a RANDOM selection of 6 DIFFERENT companies from a pool of top tech giants and high-growth startups (TCS, Zoho, Freshworks, Google, Microsoft, Amazon, Zomato, Swiggy, Paytm, Ola, etc.).
    VARY the roles and companies on each request.
    
    Return EXACTLY a JSON array:
    - company: (e.g. 'Zoho')
    - role: (e.g. 'Software Developer')
    - location: (e.g. 'Chennai, TN' or 'Coimbatore, TN')
    - salary: (e.g. '₹6 - ₹10 LPA')
    - type: (e.g. 'Full-Time')
    - logo: (FontAwesome icon class)
    
    Return ONLY JSON.
    """

    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        content = res_data['choices'][0]['message']['content']
        
        # Parse the JSON from the model content
        jobs_data = json.loads(content)
        if isinstance(jobs_data, dict):
            for key in jobs_data:
                if isinstance(jobs_data[key], list):
                    jobs = jobs_data[key]
                    break
        else:
            jobs = jobs_data

        # Inject PRECISION OFFICIAL SEARCH LINKS
        for job in jobs:
            comp_name = job['company'].lower()
            comp_slug = comp_name.replace(' ', '-')
            role_param = job['role'] .replace(' ', '+')
            
            # Map common companies to domains for Logos
            domain_map = {
                "zoho": "zoho.com", "freshworks": "www.freshworks.com", "tcs": "www.tcs.com",
                "infosys": "www.infosys.com", "wipro": "www.wipro.com", "hcl": "www.hcltech.com",
                "accenture": "www.accenture.com", "google": "www.google.com", "microsoft": "www.microsoft.com",
                "amazon": "www.amazon.com", "adobe": "www.adobe.com", "cognizant": "www.cognizant.com",
                "zomato": "www.zomato.com", "swiggy": "www.swiggy.com", "flipkart": "www.flipkart.com",
                "ola": "www.olacabs.com", "paytm": "www.paytm.com", "uber": "www.uber.com"
            }
            
            matched_domain = None
            comp_name_clean = comp_name.strip()
            for key in domain_map:
                if key in comp_name_clean:
                    matched_domain = domain_map[key]
                    break
            
            job['logo_url'] = f"https://www.google.com/s2/favicons?domain={matched_domain}&sz=128" if matched_domain else None
            
            # Precision Official Site Search URLs
            if "accenture" in comp_name:
                job['url'] = "https://www.accenture.com/in-en/careers/jobsearch?jk=&location=India"
            elif "zoho" in comp_name:
                job['url'] = f"https://www.zoho.com/careers/search.html?q={role_param}"
            elif "freshworks" in comp_name:
                job['url'] = f"https://www.freshworks.com/company/careers/?q={role_param}"
            elif "tcs" in comp_name:
                job['url'] = "https://www.tcs.com/careers/india/entry-level-hiring-2024"
            elif "infosys" in comp_name:
                job['url'] = f"https://www.infosys.com/careers/apply/?q={role_param}"
            elif "hcl" in comp_name:
                job['url'] = f"https://www.hcltech.com/careers/careers-in-india?q={role_param}"
            elif "google" in comp_name:
                job['url'] = f"https://www.google.com/about/careers/applications/jobs/results/?q={role_param}&location=India"
            elif "microsoft" in comp_name:
                job['url'] = f"https://careers.microsoft.com/us/en/search-results?q={role_param}&location=India"
            elif "amazon" in comp_name:
                job['url'] = f"https://amazon.jobs/en/search?base_query={role_param}&loc_query=India"
            elif "cognizant" in comp_name:
                job['url'] = f"https://careers.cognizant.com/global/en/search-results?q={role_param}"
            else:
                job['url'] = f"https://www.google.com/search?q=site:careers.{comp_slug}.com+{role_param}&btnI=1"
        
        return jobs[:6]
    except Exception as e:
        print(f"Groq API Error (Live Jobs): {e}")
        return fallback_jobs

@app.route('/api/live-jobs')
def api_live_jobs():
    jobs = get_live_jobs()
    return jsonify(jobs)

@app.route('/api/topic-explanation')
def api_topic_explanation():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400
        
    # Robust retry logic for Topic Explanation
    api_key = os.getenv('GROQ_CHAT_API_KEY') or os.getenv('GROQ_API_KEY')
    if not api_key:
        return jsonify({"error": "Groq API Key missing"}), 500
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"""Explain '{topic}'. Return ONLY a JSON object:
    {{
        "title": "{topic}",
        "explanation": "3-5 lines...",
        "resources": [{{"type": "Docs/Video", "title": "...", "link": "..."}}],
        "ai_tutor_article": "Detailed guide..."
    }}"""

    for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            res_data = response.json()
            content = res_data['choices'][0]['message']['content'].strip()
            
            # Verify basic structure
            test_json = json.loads(content)
            if test_json.get('explanation'):
                return content
        except Exception as e:
            print(f"Topic Explanation Attempt ({model_name}) failed: {e}")
            continue
            
    return jsonify({"error": "Failed to fetch explanation"}), 500

@app.route('/api/explain_skill')
def api_explain_skill():
    skill = request.args.get('skill')
    if not skill:
        return jsonify({"error": "No skill provided"}), 400
        
    # Robust implementation for Skill Explanation
    api_key = os.getenv('GROQ_CHAT_API_KEY') or os.getenv('GROQ_API_KEY')
    if not api_key:
        return jsonify({"error": "Groq API Key missing"}), 500
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"Explain the technical skill '{skill}' to a university student in 2-3 engaging sentences. Focus on WHY companies value it and what it solves. No markdown."

    # Sequential fallback for reliability
    for model_name in ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            response.raise_for_status()
            res_data = response.json()
            explanation = res_data['choices'][0]['message']['content'].strip()
            if explanation:
                return jsonify({"explanation": explanation})
        except Exception as e:
            print(f"Skill Explanation Attempt ({model_name}) failed: {e}")
            continue
            
    return jsonify({"error": "Failed to fetch explanation"}), 500

# Firebase is initialized via firebase_helper.db

# Centralized STRICT mapping for dynamic learning resources to trusted URLs (Order matters: specific first, general last)
TOPIC_LINKS = {
    # --- JAVA TOPICS ---
    "java syntax & features": "https://docs.oracle.com/javase/tutorial/getStarted/application/index.html",
    "java syntax": "https://docs.oracle.com/javase/tutorial/getStarted/application/index.html",
    "data types & operators": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/datatypes.html",
    "data types": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/datatypes.html",
    "operators": "https://www.w3schools.com/java/java_operators.asp",
    "control flow": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/flow.html",
    "oop": "https://www.geeksforgeeks.org/object-oriented-programming-oops-concept-in-java/",
    "classes and objects": "https://docs.oracle.com/javase/tutorial/java/javaOO/classes.html",
    "methods": "https://www.w3schools.com/java/java_methods.asp",
    "constructors": "https://www.baeldung.com/java-constructors",
    "access modifiers": "https://www.geeksforgeeks.org/access-modifiers-java/",
    "exception handling": "https://docs.oracle.com/javase/tutorial/essential/exceptions/",
    "collections framework": "https://docs.oracle.com/javase/tutorial/collections/interfaces/index.html",
    "collections": "https://docs.oracle.com/javase/tutorial/collections/",
    "generics": "https://docs.oracle.com/javase/tutorial/java/generics/",
    "multithreading": "https://www.baeldung.com/java-concurrency",
    "file i/o": "https://docs.oracle.com/javase/tutorial/essential/io/",
    "lambdas": "https://docs.oracle.com/javase/tutorial/java/javaOO/lambdaexpressions.html",
    "streams": "https://www.baeldung.com/java-8-streams",
    "jdbc": "https://docs.oracle.com/javase/tutorial/jdbc/basics/index.html",
    "jvm architecture": "https://www.geeksforgeeks.org/jvm-works-jvm-architecture/",
    "garbage collection": "https://www.baeldung.com/jvm-garbage-collectors",
    "design patterns": "https://www.geeksforgeeks.org/design-patterns-in-java/",
    "spring boot": "https://www.baeldung.com/spring-boot",
    "microservices": "https://www.baeldung.com/spring-microservices-guide",
    "hibernate": "https://www.baeldung.com/hibernate-5-spring",
    "rest api": "https://www.baeldung.com/rest-with-spring-series",
    "spring security": "https://www.baeldung.com/spring-security",
    
    # --- PYTHON TOPICS ---
    "python syntax": "https://www.w3schools.com/python/python_syntax.asp",
    "lists dictionaries": "https://docs.python.org/3/tutorial/datastructures.html",
    "python lists": "https://www.w3schools.com/python/python_lists.asp",
    "python dictionaries": "https://www.w3schools.com/python/python_dictionaries.asp",
    "python functions": "https://www.w3schools.com/python/python_functions.asp",
    "python oop": "https://realpython.com/python3-object-oriented-programming/",
    "decorators": "https://realpython.com/primer-on-python-decorators/",
    "generators": "https://realpython.com/introduction-to-python-generators/",
    "context managers": "https://realpython.com/python-with-statement/",
    "django": "https://docs.djangoproject.com/en/stable/",
    "flask": "https://flask.palletsprojects.com/en/stable/",
    "fastapi": "https://fastapi.tiangolo.com/",
    "pandas": "https://pandas.pydata.org/docs/",
    "numpy": "https://numpy.org/doc/stable/",
    
    # --- WEB DEV (HTML/CSS/JS) ---
    "semantic html": "https://developer.mozilla.org/en-US/docs/Glossary/Semantics",
    "css flexbox": "https://css-tricks.com/snippets/css/a-guide-to-flexbox/",
    "css grid": "https://css-tricks.com/snippets/css/complete-guide-grid/",
    "responsive design": "https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design",
    "dom manipulation": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Client-side_web_APIs/Manipulating_documents",
    "promises": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises",
    "async await": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Asynchronous/Promises",
    "es6 features": "https://www.w3schools.com/js/js_es6.asp",
    
    # --- REACT TOPICS ---
    "react hooks": "https://react.dev/reference/react/hooks",
    "usestate": "https://react.dev/reference/react/useState",
    "useeffect": "https://react.dev/reference/react/useEffect",
    "jsx": "https://react.dev/learn/writing-markup-with-jsx",
    "react components": "https://react.dev/learn/your-first-component",
    "react props": "https://react.dev/learn/passing-props-to-a-component",
    "react router": "https://reactrouter.com/en/main",
    "redux": "https://redux.js.org/",
    "next js": "https://nextjs.org/docs",
    
    # --- DATABASE/SQL TOPICS ---
    "sql joins": "https://www.w3schools.com/sql/sql_join.asp",
    "group by": "https://www.w3schools.com/sql/sql_groupby.asp",
    "sql indexing": "https://www.geeksforgeeks.org/indexing-in-databases-and-search-engines/",
    "normalization": "https://www.geeksforgeeks.org/database-normalization-normal-forms/",
    "nosql": "https://www.mongodb.com/nosql-explained",
    "mongodb crud": "https://www.mongodb.com/docs/manual/crud/",
    "aggregation framework": "https://www.mongodb.com/docs/manual/aggregation/",
    "postgresql": "https://www.postgresql.org/docs/",
    
    # --- DevOps & Tools ---
    "maven": "https://www.baeldung.com/maven",
    "gradle": "https://www.baeldung.com/gradle",
    "docker containers": "https://docs.docker.com/get-started/",
    "kubernetes pods": "https://kubernetes.io/docs/concepts/workloads/pods/",
    "jenkins pipeline": "https://www.jenkins.io/doc/book/pipeline/",
    "junit": "https://www.baeldung.com/junit",
    "mockito": "https://www.baeldung.com/mockito-series",
    "github actions": "https://docs.github.com/en/actions",
    "aws basics": "https://aws.amazon.com/getting-started/",
    
    # --- C++ TOPICS ---
    "c++ syntax": "https://www.w3schools.com/cpp/cpp_syntax.asp",
    "pointers": "https://www.geeksforgeeks.org/cpp-pointers/",
    "references": "https://www.geeksforgeeks.org/references-in-cpp/",
    "strings": "https://www.w3schools.com/cpp/cpp_strings.asp",
    "arrays": "https://www.w3schools.com/cpp/cpp_arrays.asp",
    "stl": "https://www.geeksforgeeks.org/the-c-standard-template-library-stl/",
    "smart pointers": "https://www.geeksforgeeks.org/smart-pointers-cpp/",
    "mutexes": "https://en.cppreference.com/w/cpp/thread/mutex",
    "gcc": "https://gcc.gnu.org/onlinedocs/",
    "cmake": "https://cmake.org/documentation/",
    
    # --- DATA & ML/AI TOPICS ---
    "statistics": "https://www.khanacademy.org/math/statistics-probability",
    "linear algebra": "https://ocw.mit.edu/courses/linear-algebra/",
    "eda": "https://www.ibm.com/topics/exploratory-data-analysis",
    "exploratory data analysis": "https://www.ibm.com/topics/exploratory-data-analysis",
    "data wrangling": "https://www.coursera.org/articles/data-wrangling",
    "scikit-learn": "https://scikit-learn.org/stable/",
    "matplotlib": "https://matplotlib.org/stable/tutorials/index.html",
    "seaborn": "https://seaborn.pydata.org/tutorial.html",
    "linear regression": "https://www.geeksforgeeks.org/ml-linear-regression/",
    "logistic regression": "https://www.geeksforgeeks.org/understanding-logistic-regression/",
    "decision trees": "https://www.geeksforgeeks.org/decision-tree/",
    "random forests": "https://www.geeksforgeeks.org/random-forest-regression-in-machine-learning/",
    "svm": "https://www.geeksforgeeks.org/support-vector-machine-algorithm/",
    "k-means": "https://www.geeksforgeeks.org/k-means-clustering-introduction/",
    "pca": "https://www.geeksforgeeks.org/principal-component-analysis-pca/",
    "neural networks": "https://www.ibm.com/topics/neural-networks",
    "deep learning": "https://www.ibm.com/topics/deep-learning",
    "tensorflow": "https://www.tensorflow.org/tutorials",
    "pytorch": "https://pytorch.org/tutorials/",
    "keras": "https://keras.io/guides/",
    "nlp": "https://www.ibm.com/topics/natural-language-processing",
    "transformers": "https://huggingface.co/docs/transformers/index",
    "llms": "https://www.ibm.com/topics/large-language-models",
    "gans": "https://developers.google.com/machine-learning/gan",
    "opencv": "https://docs.opencv.org/4.x/d9/df8/tutorial_root.html",
    
    # --- CYBER SECURITY TOPICS ---
    "networking basics": "https://www.cisco.com/c/en/us/solutions/enterprise-networks/what-is-computer-networking.html",
    "tcp/ip": "https://www.geeksforgeeks.org/tcp-ip-model/",
    "osi model": "https://www.geeksforgeeks.org/osi-model-7-layers/",
    "linux administration": "https://linuxjourney.com/",
    "cryptography": "https://www.geeksforgeeks.org/cryptography-introduction/",
    "firewalls": "https://www.cisco.com/c/en/us/products/security/firewalls/what-is-a-firewall.html",
    "owasp": "https://owasp.org/www-project-top-ten/",
    "iam": "https://www.ibm.com/topics/identity-access-management",
    "ethical hacking": "https://www.eccouncil.org/cybersecurity/what-is-ethical-hacking/",
    "penetration testing": "https://www.ibm.com/topics/penetration-testing",
    "kali linux": "https://www.kali.org/docs/",
    "wireshark": "https://www.wireshark.org/docs/wsug_html_chunked/",
    "nmap": "https://nmap.org/book/man.html",
    "metasploit": "https://docs.rapid7.com/metasploit/",
    "burp suite": "https://portswigger.net/burp/documentation/desktop/getting-started",
    
    # --- CLOUD TOPICS ---
    "iaas": "https://www.ibm.com/topics/iaas",
    "paas": "https://www.ibm.com/topics/paas",
    "saas": "https://www.ibm.com/topics/saas",
    "ec2": "https://docs.aws.amazon.com/ec2/",
    "s3": "https://docs.aws.amazon.com/s3/",
    "aws lambda": "https://docs.aws.amazon.com/lambda/",
    "serverless": "https://www.ibm.com/topics/serverless",
    "terraform": "https://developer.hashicorp.com/terraform/intro",
    "ansible": "https://docs.ansible.com/ansible/latest/getting_started/index.html",
    
    # --- MOBILE DEV (ANDROID/IOS) ---
    "kotlin": "https://kotlinlang.org/docs/home.html",
    "android studio": "https://developer.android.com/studio/intro",
    "activity": "https://developer.android.com/guide/components/activities/intro-activities",
    "fragment": "https://developer.android.com/guide/fragments",
    "recyclerviews": "https://developer.android.com/guide/topics/ui/layout/recyclerview",
    "retrofit": "https://square.github.io/retrofit/",
    "room": "https://developer.android.com/training/data-storage/room",
    "jetpack": "https://developer.android.com/jetpack",
    "coroutines": "https://kotlinlang.org/docs/coroutines-overview.html",
    "swift": "https://docs.swift.org/swift-book/",
    "xcode": "https://developer.apple.com/xcode/",
    "viewcontrollers": "https://developer.apple.com/documentation/uikit/view_controllers",
    "storyboards": "https://developer.apple.com/library/archive/documentation/General/Conceptual/Devpedia-CocoaApp/Storyboard.html",
    "swiftui": "https://developer.apple.com/xcode/swiftui/",
    "coredata": "https://developer.apple.com/documentation/coredata",
    
    # --- UX/UI & TESTING ---
    "color theory": "https://www.interaction-design.org/literature/topics/color-theory",
    "typography": "https://www.interaction-design.org/literature/topics/typography",
    "wireframing": "https://www.interaction-design.org/literature/topics/wireframing",
    "figma": "https://help.figma.com/hc/en-us",
    "sdlc": "https://www.geeksforgeeks.org/software-development-life-cycle-sdlc/",
    "selenium": "https://www.selenium.dev/documentation/",
    "postman": "https://learning.postman.com/docs/getting-started/introduction/",
    "jmeter": "https://jmeter.apache.org/usermanual/get-started.html",
    
    # --- BLOCKCHAIN & GAMES ---
    "blockchain nodes": "https://www.ibm.com/topics/blockchain",
    "smart contracts": "https://www.ibm.com/topics/smart-contracts",
    "solidity": "https://docs.soliditylang.org/",
    "defi": "https://ethereum.org/en/defi/",
    "web3": "https://ethereum.org/en/web3/",
    "hardhat": "https://hardhat.org/getting-started/",
    "game loop": "https://gameprogrammingpatterns.com/game-loop.html",
    "3d mathematics": "https://docs.unity3d.com/Manual/VectorMath.html",
    "unity": "https://docs.unity3d.com/Manual/index.html",
    "unreal engine": "https://docs.unrealengine.com/",
    
    # --- CATCH-ALL & CORE LANGUAGES (Must be at the bottom so specific keys match first) ---
    "c++": "https://www.w3schools.com/cpp/",
    "java": "https://docs.oracle.com/en/java/",
    "python": "https://www.w3schools.com/python/",
    "html": "https://www.w3schools.com/html/",
    "css": "https://www.w3schools.com/css/",
    "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "react": "https://react.dev/learn",
    "sql": "https://www.w3schools.com/sql/",
    "mongodb": "https://www.mongodb.com/docs/manual/",
    "machine learning": "https://www.geeksforgeeks.org/machine-learning/",
    "data science": "https://www.datacamp.com/",
    "artificial intelligence": "https://www.geeksforgeeks.org/artificial-intelligence/",
    "cyber security": "https://www.ibm.com/topics/cybersecurity",
    "cloud computing": "https://aws.amazon.com/what-is-cloud-computing/",
    "devops": "https://www.atlassian.com/devops",
    "docker": "https://docs.docker.com/",
    "kubernetes": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
    "jenkins": "https://www.jenkins.io/doc/",
    "android": "https://developer.android.com/docs",
    "ios": "https://developer.apple.com/ios/",
    "ui/ux": "https://www.interaction-design.org/literature/topics/ui-design",
    "software testing": "https://www.softwaretestinghelp.com/",
    "blockchain": "https://ethereum.org/en/developers/docs/",
    "game development": "https://learn.unity.com/",
    "git": "https://git-scm.com/doc"
}

# Centralized data structures for roadmaps follow...


@app.route('/ats')
def ats_test():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    return render_template('ats.html')

@app.route('/career-test')
def career_test():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    return render_template('career_test.html')

@app.route('/api/ats_analyze', methods=['POST'])
def ats_analyze():
        
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file uploaded"}), 400
        
    file = request.files['resume']
    job_desc = request.form.get('job_description', '')
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    text = ""
    try:
        if file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif file.filename.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            return jsonify({"error": "Unsupported format. Please upload PDF or DOCX."}), 400
    except Exception as e:
        return jsonify({"error": f"Could not read file."}), 400

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer.
Evaluate the following resume against the job description (if provided). If no job description is provided, evaluate it against general software engineering best practices.
Resume Text:
{text[:4000]}

Job Description:
{job_desc[:2000]}

Return ONLY a JSON object with your analysis in this exact format:
{{
    "score": 85,
    "match_status": "Great Match!",
    "summary": "Short 1-2 sentence summary of the fit...",
    "feedback": [
        {{"icon": "check", "text": "Good use of metrics"}},
        {{"icon": "cross", "text": "Missing keyword: React"}}
    ]
}}
IMPORTANT: Return ONLY valid JSON, no markdown formatting."""

        response = model.generate_content(prompt)
        result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
        return jsonify(result)
    except Exception as e:
        print("ATS API Error:", str(e))
        return jsonify({"error": "Error during AI analysis."}), 500

@app.route('/api/company-mode', methods=['POST'])
def company_mode():
    if 'user_id' not in session and not session.get('guest'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    company = data.get('company', '')
    experience_level = data.get('experience_level', 'fresher')
    
    if not company:
        return jsonify({"error": "No company selected"}), 400
        
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return jsonify({"error": "Groq API key missing from .env"}), 500
        
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""You are a top FAANG career mentor and interview expert.
User goal: Get selected in {company} as a Software Engineer.
Candidate Status: {experience_level.capitalize()}

STRICT FORMATTING RULES (MANDATORY):
1. NO MARKDOWN: Do NOT use symbols like -, *, **, ###, ##, #, or any bullet characters.
2. NO BULLETS: Use clean plain text with proper spacing. Do not use lists.
3. INTEGRATED RESOURCES: 
   - Under EACH main section, provide a sub-section called "Resources:".
   - Each resource MUST be an HTML anchor tag: <a href="URL" target="_blank">Name</a>
   - Place each resource link on its own new line.
   - Include 2-3 specific, high-quality links per major section.
4. NO GLOBAL RESOURCES: Do NOT include a "Free Resources" section at the end.
5. CLEAN HEADINGS: Use emojis as section prefixes (🎯, 📌, 💻, 🧠, 🛠, 📊, 🗺, 🚀, 🔥, 🏁).
6. NO META-TEXT: Do not use labels like "[Optional Section]". Omit sections completely if they don't apply.
7. DEPTH & LENGTH: 
   - Total length MUST be between 800-1000 words.
   - Each section must be deeply detailed, providing step-by-step guidance.
   - Provide SPECIFIC context for {company} (e.g., its core values, typical OA pattern, or recent interview trends).

Aptitude Logic: 
- Include "🧠 Aptitude Round Preparation (For Freshers)" ONLY if {company} is a service-based company (TCS, Wipro, Infosys, etc.) AND candidate is a 'Fresher'.
- Omit it completely otherwise.

SECTIONS TO INCLUDE:
🎯 {company} Overview (+ Resources)
📌 Role Expectations (+ Resources)
🧠 Required Skills (+ Resources)
💻 DSA & Coding Level (+ Resources)
🛠 Tools & Technologies (+ Resources)
🧠 Aptitude Round Preparation (For Freshers) (+ Resources)
(Provide a complete breakdown: Explain the 'Elimination Factor', list topics like Percentages, Puzzles, and Grammar, and suggest specific mock test frequencies. Mention that this is often the most critical gatekeeper.)
📊 Interview Process (+ Resources)
🗺 Preparation Roadmap (+ Resources)
🔥 Tips & Final Conclusion"""

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": f"You are a specialized career mentor for {company}. You provide deep, bullet-free, HTML-ready roadmaps for {experience_level} candidates. Follow the strict logic: only include the Aptitude section for Freshers in service-based companies. NEVER use markdown symbols like -, *, or **."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "max_tokens": 2000
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        res_data = response.json()
        strategy = res_data["choices"][0]["message"]["content"]
        
        return jsonify({"strategy": strategy})
    except Exception as e:
        print("Company Mode API Error:", str(e))
        return jsonify({"error": "Error during AI generation with Groq API."}), 500

 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'guest':
            session['guest'] = True
            session['name'] = 'Guest'
            return redirect(url_for('dashboard'))
            
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        name = request.form.get('username')
        auth_mode = request.form.get('auth_mode', 'login')
        
        try:
            user_doc = db.collection('users').document(email).get()
            user = user_doc.to_dict() if user_doc.exists else None
            
            if auth_mode == 'signup':
                if user:
                    return render_template('login.html', error="Account already registered! Please login.")
                else:
                    if not name:
                        name = email.split('@')[0]
                    hashed_pw = generate_password_hash(password)
                    db.collection('users').document(email).set({
                        'name': name,
                        'email': email,
                        'password': hashed_pw,
                        'theme': 'light'
                    })
                    return render_template('login.html', success="Account successfully created! Please log in.")
                    
            else: # login mode
                if user:
                    if check_password_hash(user['password'], password):
                        session['guest'] = False
                        session['user_id'] = email
                        session['name'] = user['name']
                        session['email'] = user['email']
                        session['theme'] = user.get('theme', 'light')
                        return redirect(url_for('dashboard'))
                    else:
                        return render_template('login.html', error="Invalid email or password.")
                else:
                    return render_template('login.html', error="Account does not exist! Please sign up.")
        except Exception as e:
            print(f"Auth Error: {e}")
            return render_template('login.html', error="An error occurred during authentication.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if session.get('guest') or 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        user_doc_ref = db.collection('users').document(session['user_id'])
        user_doc = user_doc_ref.get()
        if not user_doc.exists:
            return redirect(url_for('logout'))
        user = user_doc.to_dict()
        
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email', '').strip().lower()
            new_password = request.form.get('new_password')
            current_password = request.form.get('current_password')
            
            if not check_password_hash(user['password'], current_password):
                return render_template('profile.html', user=user, error="Incorrect current password. Profile not updated.")
                
            update_data = {'name': name, 'email': email}
            if new_password:
                update_data['password'] = generate_password_hash(new_password)
            
            # If email changes, we should ideally migrate the document ID.
            # But for now, we update the fields. If identity is tied to the old email doc ID,
            # we keep it consistent for this session.
            user_doc_ref.update(update_data)
            
            session['name'] = name
            session['email'] = email
            
            updated_user = user_doc_ref.get().to_dict()
            return render_template('profile.html', user=updated_user, success="Profile updated successfully!")
                
        return render_template('profile.html', user=user)
    except Exception as e:
        print(f"Profile Error: {e}")
        return render_template('profile.html', error="An error occurred while accessing the profile.")

@app.route('/api/forgot-password/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email', '')
    
    try:
        user_doc = db.collection('users').document(email).get()
        user = user_doc.to_dict() if user_doc.exists else None
    except Exception as e:
        print(f"OTP User Lookup Error: {e}")
        return jsonify({"status": "error", "message": "Database error."}), 500
    
    if user:
        otp = "944588"
        session['reset_email'] = email
        session['reset_otp'] = otp
        
        sender_email = os.getenv('MAIL_USERNAME', '')
        sender_password = os.getenv('MAIL_PASSWORD', '')
        
        if not sender_email or not sender_password or sender_email == "your_email@gmail.com":
            print(f"\n====================================\n🛑 [SMTP NOT CONFIGURED] 🛑\nOTP FOR {email} IS: {otp}\nConfigure '.env' with MAIL_USERNAME / MAIL_PASSWORD!\n====================================\n")
            return jsonify({"status": "demo", "message": f"SMTP not configured.", "otp": otp, "email": email})
            
        try:
            msg = MIMEText(f"Hello,\n\nYour password reset OTP is: {otp}\n\nThis code will expire shortly. Do not share this with anyone.\n\n- AI Career Consulting Team")
            msg['Subject'] = 'Password Reset OTP - AI Career Consulting'
            msg['From'] = f"AI Career Consulting <{sender_email}>"
            msg['To'] = email
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            return jsonify({"status": "success", "message": f"OTP email successfully sent to {email}"})
            
        except Exception as e:
            print("❌ SMTP Error:", str(e))
            print(f"FALLBACK OTP IS: {otp}")
            return jsonify({"status": "error", "message": "Failed to send email. Check your SMTP settings and Application Password in .env!"}), 500

    return jsonify({"status": "error", "message": "Email address not found in our system."}), 404

@app.route('/api/forgot-password/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    otp = data.get('otp', '')
    if 'reset_otp' in session and session['reset_otp'] == str(otp):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid or expired 6-digit OTP."}), 400

@app.route('/api/forgot-password/reset', methods=['POST'])
def reset_password():
    data = request.json
    new_password = data.get('new_password', '')
    email = session.get('reset_email')
    
    if email and new_password:
        hashed_pw = generate_password_hash(new_password)
        try:
            db.collection('users').document(email).update({'password': hashed_pw})
        except Exception as e:
            print(f"Reset Password Error: {e}")
            return jsonify({"status": "error", "message": "Failed to update password."}), 500
            
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        return jsonify({"status": "success", "message": "Password successfully replaced!"})
    return jsonify({"status": "error", "message": "Security session expired."}), 400
import re
import urllib.request

@app.route('/topic/<path:topic_name>')
def topic_redirect(topic_name):
    clean_topic = urllib.parse.unquote(topic_name).lower().strip()
    
    # 1. Exact Match
    if clean_topic in TOPIC_LINKS:
        return redirect(TOPIC_LINKS[clean_topic])
        
    # 2. Substring Match (Strict word boundaries to prevent 'javascript' falling into 'java')
    for key, url in TOPIC_LINKS.items():
        if re.search(rf'\b{re.escape(key)}\b', clean_topic) or re.search(rf'\b{re.escape(clean_topic)}\b', key):
            return redirect(url)
            
    # 3. Ultimate Fallback: Redirect to YouTube Search for the specific topic
    search_query = urllib.parse.quote(f"{clean_topic} tutorial")
    return redirect(f"https://www.youtube.com/results?search_query={search_query}")

@app.route('/api/save-progress', methods=['POST'])
def save_progress():
    # Only for temporary logging or future features—checklists are no longer stored in cloud by request.
    # We maintain this route for backwards compatibility but it doesn't affect dashboard progress now.
    return jsonify({"success": True, "message": "Checklist state is local-only by user preference."})

def get_canonical_skill(skill):
    sk = skill.lower().strip()
    if sk in SKILL_ALIASES: return SKILL_ALIASES[sk]
    
    # Try removing common suffixes to find base roadmap
    for suffix in [" developer", " engineer", " development", " designer", " design"]:
        if sk.endswith(suffix):
            base = sk.replace(suffix, "").strip()
            if base in ROADMAPS: return base
            if base in SKILL_ALIASES: return SKILL_ALIASES[base]
    return sk

@app.route('/api/submit-section-test', methods=['POST'])
def submit_section_test():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 401
    
    data = request.json
    skill = get_canonical_skill(data.get('skill', ''))
    section_name = data.get('section', '')
    total_sections = data.get('total_sections', 1)
    
    if not skill or not section_name:
        return jsonify({"success": False, "error": "Missing skill or section"}), 400

    try:
        # Use composite ID for easy lookup: email_skill
        progress_id = f"{session['user_id']}_{skill}"
        progress_ref = db.collection('roadmap_progress').document(progress_id)
        existing_doc = progress_ref.get()
        
        passed_list = []
        if existing_doc.exists:
            passed_list = existing_doc.to_dict().get('passed_sections', [])
            
        if section_name not in passed_list:
            passed_list.append(section_name)
        
        testable_total = int(total_sections) if total_sections else 1
        if testable_total == 0: testable_total = 1
         
        percentage = int((len(passed_list) / testable_total) * 100)
        if percentage > 100: percentage = 100

        data_to_set = {
            'user_id': session['user_id'],
            'skill': skill,
            'passed_sections': passed_list,
            'percentage': percentage,
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        progress_ref.set(data_to_set, merge=True)
        
        return jsonify({"success": True, "percentage": percentage, "total_passed": len(passed_list)})
    except Exception as e:
        print(f"Submit Section Test Error: {e}")
        return jsonify({"success": False, "error": "Database error"}), 500
    
@app.route('/api/sync-roadmap-total', methods=['POST'])
def sync_roadmap_total():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 401
        
    data = request.json
    skill = get_canonical_skill(data.get('skill', ''))
    total_sections = data.get('total_sections', 1)
    
    if not skill:
        return jsonify({"success": False, "error": "Missing skill"}), 400

    try:
        progress_id = f"{session['user_id']}_{skill}"
        progress_ref = db.collection('roadmap_progress').document(progress_id)
        doc = progress_ref.get()
        
        if doc.exists:
            passed_list = doc.to_dict().get('passed_sections', [])
            
            testable_total = int(total_sections) if total_sections else 1
            if testable_total == 0: testable_total = 1
            
            percentage = int((len(passed_list) / testable_total) * 100)
            if percentage > 100: percentage = 100
            
            progress_ref.update({
                'percentage': percentage,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            return jsonify({"success": True, "percentage": percentage})
        return jsonify({"success": True, "message": "No existing progress to sync"})
    except Exception as e:
        print(f"Sync Roadmap Error: {e}")
        return jsonify({"success": False, "error": "Database error"}), 500

@app.route('/api/delete-progress', methods=['POST'])
def delete_progress():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 401
    
    data = request.json
    skill = get_canonical_skill(data.get('skill', ''))
    
    if not skill:
        return jsonify({"success": False, "error": "Skill name missing"}), 400

    try:
        progress_id = f"{session['user_id']}_{skill}"
        db.collection('roadmap_progress').document(progress_id).delete()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Delete Progress Error: {e}")
        return jsonify({"success": False, "error": "Database error"}), 500

@app.route('/api/user-progress')
def get_user_progress():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 401
    
    print(f"DEBUG: Fetching progress for session user_id: '{session.get('user_id')}'")
        
    try:
        try:
            docs = db.collection('roadmap_progress')\
                     .where('user_id', '==', session['user_id'])\
                     .where('percentage', '>', 0)\
                     .order_by('last_updated', direction=firestore.Query.DESCENDING)\
                     .get()
        except Exception as e:
            print(f"Index check triggered for progress: {e}")
            # ULTIMATE FALLBACK: Get all records for user and filter in memory
            # This bypasses the need for ANY composite index on (user_id + percentage + last_updated)
            docs = db.collection('roadmap_progress')\
                     .where('user_id', '==', session['user_id'])\
                     .get()
            
            # Filter and sort in Python
            docs = [d for d in docs if d.to_dict().get('percentage', 0) > 0]
            def sort_key(doc):
                val = doc.to_dict().get('last_updated')
                if val is None: return datetime.min
                if isinstance(val, str):
                    try: return datetime.fromisoformat(val)
                    except: return datetime.min
                return val
                
            docs = sorted(docs, key=sort_key, reverse=True)
        
        result = []
        for doc in docs:
            data = doc.to_dict()
            # Handle Potential missing timestamp
            last_updated = data.get('last_updated')
            if last_updated:
                if hasattr(last_updated, 'isoformat'):
                    last_updated = last_updated.isoformat()
                else:
                    last_updated = str(last_updated) # Fallback for strings
            
            result.append({
                "skill": data['skill'].title(),
                "percentage": data['percentage'],
                "last_updated": last_updated
            })
        return jsonify({"success": True, "progress": result})
    except Exception as e:
        print(f"Get User Progress Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-progress/<skill>')
def get_skill_progress(skill):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Login required"}), 401
        
    skill = get_canonical_skill(skill)
        
    try:
        progress_id = f"{session['user_id']}_{skill}"
        doc = db.collection('roadmap_progress').document(progress_id).get()
        
        if doc.exists:
            passed = doc.to_dict().get('passed_sections', [])
            return jsonify({"success": True, "passed_sections": passed})
        return jsonify({"success": True, "passed_sections": []})
    except Exception as e:
        print(f"Get Skill Progress Error: {e}")
        return jsonify({"success": False, "error": "Database error"}), 500

@app.route('/my-learning', endpoint='resume_learning')
def resume_learning():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    return render_template('my_learning.html')

@app.route('/answer/<path:question>')
def answer_redirect(question):
    clean_question = urllib.parse.unquote(question).strip()
    
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"Find the most authoritative OFFICIAL DOCUMENTATION page (e.g., Oracle, MDN, Python.org) that answers the interview question: '{clean_question}'. DO NOT guess or hallucinate GeekforGeeks URLs. If official docs don't exist, return ONLY 2-3 concise search keywords (e.g. 'java abstract interface'). DO NOT provide YouTube or StackOverflow. Return ONLY the raw valid URL or the keywords."
            response = model.generate_content(prompt)
            
            # Robust Regex URL Extraction and Validation
            match = re.search(r'(https?://[^\s"\'<>]+)', response.text)
            valid_url = False
            if match:
                url = match.group(1)
                if "youtube.com" not in url and "stackoverflow.com" not in url:
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=2) as r:
                            valid_url = (r.getcode() == 200)
                    except:
                        pass
                        
                    if valid_url:
                        return redirect(url)
                        
            # If URL hallucinated or not found, generate YouTube search keywords
            keywords = response.text.replace('"', '').replace("'", '').strip()
            # If response was a dead URL, strip it to extract native concepts
            if "http" in keywords or not keywords:
                fallback_clean = clean_question.lower()
                for word in ["what is ", "explain ", "the difference between ", "how to ", "describe "]:
                    fallback_clean = fallback_clean.replace(word, "")
                keywords = fallback_clean.strip()[:60]
                
            search_query = urllib.parse.quote(keywords)
            return redirect(f"https://www.youtube.com/results?search_query={search_query}")

        except Exception as e:
            print(f"Answer fetch error: {str(e)}")
            
    # Ultimate Fallback for Interview Questions: YouTube Search
    fallback_clean = clean_question.lower()
    for word in ["what is ", "explain ", "the difference between ", "how to ", "describe "]:
        fallback_clean = fallback_clean.replace(word, "")
        
    search_query = urllib.parse.quote(fallback_clean.strip()[:60])
    return redirect(f"https://www.youtube.com/results?search_query={search_query}")

@app.route('/api/check-skill')
def check_skill():
    skill = request.args.get('skill', '').strip().lower()
    if not skill:
        return jsonify({"exists": False})
    
    # Strict Exact Matching
    matched_key = None
    if skill in ROADMAPS:
        matched_key = skill
    elif skill in SKILL_ALIASES:
        matched_key = SKILL_ALIASES[skill]
    
    return jsonify({"exists": matched_key is not None})

@app.route('/roadmap')
def roadmap():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
        
    skill_query = request.args.get('skill', '').strip().lower()
    
    if not skill_query:
        return render_template('roadmap.html', skill_query='', data=None)
    
    # Strict Exact Matching
    matched_key = None
    if skill_query in ROADMAPS:
        matched_key = skill_query
    elif skill_query in SKILL_ALIASES:
        matched_key = SKILL_ALIASES[skill_query]
                
    if matched_key:
        roadmap_data = ROADMAPS.get(matched_key).copy()
        roadmap_data['resources'] = RESOURCES_MAP.get(matched_key, [])
        roadmap_data['jobs'] = JOBS_MAP.get(matched_key, [])
        roadmap_data['interview_qs'] = INTERVIEW_MAP.get(matched_key, [])
    else:
        roadmap_data = None
    
    if not roadmap_data:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            response_text = ""
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
                prompt = f"""You are an expert software architect and educator.

Generate a COMPLETE A-Z learning roadmap for the skill: {skill_query.title()}.

REQUIREMENTS:
1. Include ALL sections:
- Beginner topics
- Intermediate topics
- Advanced topics
- Real-world tools & frameworks
- Projects (Exactly 8 projects as short 1-line bullet points)
- Interview questions
- Industrial workflow (Intern → Manager)

2. IMPORTANT:
- Do NOT miss any important topic
- Cover theory + practical + real-world
- Keep topics structured
- Each section must have multiple bullet points
- Ensure the 'projects' section has EXACTLY 8 items.

3. OUTPUT FORMAT (STRICT JSON):
{{
  "beginner": ["topic 1", "topic 2"],
  "intermediate": ["topic 1", "topic 2"],
  "advanced": ["topic 1", "topic 2"],
  "tools": ["tool 1", "tool 2"],
  "projects": ["project 1", "project 2", "project 3", "project 4", "project 5", "project 6", "project 7", "project 8"],
  "interview_questions": ["question 1", "question 2"],
  "workflow": {{
    "intern": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "junior": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "developer": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "senior": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "lead": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "architect": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}},
    "manager": {{"focus": "...", "responsibilities": ["...", "..."], "goals": ["...", "..."]}}
  }}
}}
Return ONLY JSON."""

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": "You are a professional educational consultant."}, {"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"}
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                res_data = response.json()
                ai_text = res_data["choices"][0]["message"]["content"].strip()
                response_text = ai_text
                ai_data = json.loads(ai_text)
                
                sections = []
                if "beginner" in ai_data: sections.append({"title": "Beginner Level", "content": "• " + "<br>• ".join(ai_data["beginner"])})
                if "intermediate" in ai_data: sections.append({"title": "Intermediate Level", "content": "• " + "<br>• ".join(ai_data["intermediate"])})
                if "advanced" in ai_data: sections.append({"title": "Advanced Level", "content": "• " + "<br>• ".join(ai_data["advanced"])})
                if "tools" in ai_data: sections.append({"title": "Tools & Technologies", "content": "• " + "<br>• ".join(ai_data["tools"])})
                if "projects" in ai_data: sections.append({"title": "Projects", "content": "• " + "<br>• ".join(ai_data["projects"])})
                
                workflow_list = []
                role_mapping = {
                    "intern": "Intern / Trainee",
                    "junior": "Junior Developer",
                    "developer": "Software Developer (Mid-Level)",
                    "senior": "Senior Developer",
                    "lead": "Tech Lead",
                    "architect": "Solution Architect",
                    "manager": "Engineering Manager"
                }
                wf_data = ai_data.get("workflow", {})
                if isinstance(wf_data, dict):
                    for k in ["intern", "junior", "developer", "senior", "lead", "architect", "manager"]:
                        if k in wf_data:
                            v = wf_data[k]
                            workflow_list.append({
                                "role": role_mapping.get(k, k.title()),
                                "skills": v.get("responsibilities", v.get("skills", [])),
                                "goal": v.get("focus", v.get("goal", ""))
                            })
                elif isinstance(wf_data, list):
                    workflow_list = wf_data
                
                roadmap_data = {
                    "title": skill_query.title(),
                    "is_ai_generated": True,
                    "sections": sections,
                    "interview_qs": ai_data.get("interview_questions", ai_data.get("interview_qs", [])) or [],
                    "resources": ai_data.get("resources", []) or [],
                    "career_paths": ai_data.get("career_paths", []) or [],
                    "job_url": f"https://www.naukri.com/{skill_query.replace(' ', '-')}-jobs",
                    "prefetched_workflow": workflow_list
                }
            except Exception as e:
                print(f"Error generating AI roadmap with Groq: {str(e)}")
                roadmap_data = {
                    "title": skill_query.title() + " (AI Error)",
                    "is_ai_generated": True,
                    "sections": [{"title": "API Exception", "content": f"Failed to generate with Groq: {str(e)}<br><div style='padding: 1rem; background: #eee; color: #333; font-family: monospace; font-size: 0.9em; overflow-x: auto; border-radius: 5px; margin-top: 1rem;'>Raw Text: {response_text.replace('<', '&lt;')}</div>"}],
                    "interview_qs": [
                        "What are the core concepts of " + skill_query.title() + "?",
                        "Can you explain the basic architecture of " + skill_query.title() + "?",
                        "What are the best practices when working with " + skill_query.title() + "?"
                    ],
                    "resources": [],
                    "job_url": "#"
                }

    if isinstance(roadmap_data, dict):
        # 1. Inject Mandatory DSA Section (First Card)
        dsa_section = {
            "title": "Data Structures & Algorithms (Core Requirement 🔥)",
            "content": ["Arrays, Strings", "Linked List", "Stack & Queue", "Trees & Graphs", "Sorting & Searching", "Recursion", "Problem Solving (LeetCode / HackerRank)"],
            "note": "👉 <b>DSA is mandatory for cracking IT interviews</b>"
        }
        
        # Ensure sections list exists and is a list
        if 'sections' not in roadmap_data or not isinstance(roadmap_data['sections'], list):
            roadmap_data['sections'] = []
            
        # --- 12-POINT STRICT REORDERING LOGIC ---
        order_map = {
            "beginner": 1, "intermediate": 2, "advanced": 3,
            "tools & technologies": 4, "tool": 4,
            "web & api": 5, "web": 5, "api": 5,
            "database": 6, "sql": 6,
            "frameworks": 7, "framework": 7,
            "projects": 8, "project": 8,
            "data structures": 9, "dsa": 9, "algorithm": 9
        }

        # Inject DSA if missing
        has_dsa = any("data structures" in str(s.get('title', '')).lower() for s in roadmap_data['sections'])
        if not has_dsa:
            roadmap_data['sections'].append({
                "title": "Data Structures & Algorithms (Core Requirement 🔥)",
                "content": ["Arrays, Strings", "Linked List", "Stack & Queue", "Trees & Graphs", "Sorting & Searching", "Recursion", "Problem Solving (LeetCode / HackerRank)"],
                "note": "👉 <b>DSA is mandatory for cracking IT interviews</b>"
            })

        def get_order(title):
            title_lower = str(title).lower()
            for key, val in order_map.items():
                if key in title_lower:
                    return val
            return 99 # Push unknown to bottom

        # Perform the sort
        roadmap_data['sections'].sort(key=lambda x: get_order(x.get('title', '')))

        # 2. Inject Final Advice (Context data for template)
        roadmap_data['final_advice'] = [
            "Practice coding daily (1-2 hrs)",
            "Focus on DSA + core concepts",
            "Build real-world projects",
            "Learn frameworks relevant to " + str(roadmap_data.get('title', 'this role')),
            "Stay consistent for 3-6 months",
            "Don't just watch tutorials, implement everything"
        ]

    if roadmap_data:
        try:
            db.collection('history').add({
                'user_id': session['user_id'],
                'username': session.get('name', 'User'),
                'skill': roadmap_data['title'],
                'viewed_time': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Save History Error: {e}")

    resp = make_response(render_template('roadmap.html', skill_query=request.args.get('skill', ''), data=roadmap_data, nvidia_api_key=os.getenv('NVIDIA_API_KEY'), groq_key=os.getenv('GROQ_API_KEY', '')))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

def get_salary_fallback(skill):
    sq = skill.lower()
    # Numeric nested structure for 15+ skill categories
    skill_configs = {
        'java': {'fresher': {'yearly': 450000, 'monthly': 35000}, 'mid': {'yearly': 950000, 'monthly': 80000}, 'senior': {'yearly': 2200000, 'monthly': 180000}, 'tip': "Focus on Spring Boot + DSA 🚀"},
        'python': {'fresher': {'yearly': 500000, 'monthly': 40000}, 'mid': {'yearly': 1100000, 'monthly': 90000}, 'senior': {'yearly': 2500000, 'monthly': 200000}, 'tip': "Focus on Django/FastAPI + DSA 🚀"},
        'ai': {'fresher': {'yearly': 800000, 'monthly': 60000}, 'mid': {'yearly': 1800000, 'monthly': 140000}, 'senior': {'yearly': 3500000, 'monthly': 280000}, 'tip': "Focus on PyTorch/Math + DSA 🚀"},
        'ml': {'fresher': {'yearly': 700000, 'monthly': 55000}, 'mid': {'yearly': 1600000, 'monthly': 120000}, 'senior': {'yearly': 3200000, 'monthly': 260000}, 'tip': "Focus on Scikit-Learn + Mathematics 🚀"},
        'datascience': {'fresher': {'yearly': 900000, 'monthly': 70000}, 'mid': {'yearly': 2000000, 'monthly': 160000}, 'senior': {'yearly': 4000000, 'monthly': 320000}, 'tip': "Focus on SQL + Statistical Modeling 🚀"},
        'deeplearning': {'fresher': {'yearly': 1000000, 'monthly': 80000}, 'mid': {'yearly': 2200000, 'monthly': 170000}, 'senior': {'yearly': 4500000, 'monthly': 350000}, 'tip': "Focus on CNNs/RNNs + Research Papers 🚀"},
        'nlp': {'fresher': {'yearly': 900000, 'monthly': 70000}, 'mid': {'yearly': 2000000, 'monthly': 160000}, 'senior': {'yearly': 4000000, 'monthly': 320000}, 'tip': "Focus on Transformers + LLM Fine-tuning 🚀"},
        'computervision': {'fresher': {'yearly': 900000, 'monthly': 70000}, 'mid': {'yearly': 2100000, 'monthly': 170000}, 'senior': {'yearly': 4200000, 'monthly': 330000}, 'tip': "Focus on OpenCV + Edge AI Deployment 🚀"},
        'aimlengineer': {'fresher': {'yearly': 1000000, 'monthly': 80000}, 'mid': {'yearly': 2200000, 'monthly': 170000}, 'senior': {'yearly': 4500000, 'monthly': 350000}, 'tip': "Focus on MLOps + High Performance Computing 🚀"},
        'bigdata': {'fresher': {'yearly': 700000, 'monthly': 55000}, 'mid': {'yearly': 1500000, 'monthly': 110000}, 'senior': {'yearly': 3000000, 'monthly': 250000}, 'tip': "Focus on Spark/Hadoop + Cloud Data Lakes 🚀"},
        'cyber': {'fresher': {'yearly': 450000, 'monthly': 35000}, 'mid': {'yearly': 1200000, 'monthly': 100000}, 'senior': {'yearly': 2500000, 'monthly': 200000}, 'tip': "Focus on Certs (CEH, OSCP) + Networking 🚀"},
        'devops': {'fresher': {'yearly': 550000, 'monthly': 45000}, 'mid': {'yearly': 1300000, 'monthly': 110000}, 'senior': {'yearly': 2800000, 'monthly': 230000}, 'tip': "Focus on K8s + CI/CD Pipelines 🚀"},
        'fullstack': {'fresher': {'yearly': 500000, 'monthly': 40000}, 'mid': {'yearly': 1200000, 'monthly': 100000}, 'senior': {'yearly': 2800000, 'monthly': 230000}, 'tip': "Focus on MERN/Java Stack + DSA 🚀"},
        'frontend': {'fresher': {'yearly': 400000, 'monthly': 32000}, 'mid': {'yearly': 1000000, 'monthly': 85000}, 'senior': {'yearly': 2000000, 'monthly': 160000}, 'tip': "Focus on React/NextJS + UI/UX 🚀"},
        'backend': {'fresher': {'yearly': 480000, 'monthly': 38000}, 'mid': {'yearly': 1150000, 'monthly': 95000}, 'senior': {'yearly': 2400000, 'monthly': 190000}, 'tip': "Focus on Microservices + Backend Mastery 🚀"},
        'dataanalyst': {'fresher': {'yearly': 500000, 'monthly': 40000}, 'mid': {'yearly': 1200000, 'monthly': 90000}, 'senior': {'yearly': 2200000, 'monthly': 180000}, 'tip': "Focus on SQL Mastery + Tableau/PowerBI 🚀"}
    }
    
    # Matching User's requested tier logic
    conf = skill_configs.get('default', {
        'fresher': {'yearly': 400000, 'monthly': 32000},
        'mid': {'yearly': 900000, 'monthly': 75000},
        'senior': {'yearly': 1800000, 'monthly': 150000},
        'tip': "Focus on Core Concepts + Deep Projects 🚀"
    })
    
    for key in skill_configs:
        if key in sq:
            conf = skill_configs[key]
            break
            
    return conf

@app.route('/api/salary', methods=['GET'])
def get_salary_api():
    skill = request.args.get('skill', 'Generic IT')
    api_key = os.getenv('NVIDIA_API_KEY')
    
    if not api_key:
        # Fallback if key is missing
        fallback = get_salary_fallback(skill)
        return jsonify({"choices": [{"message": {"content": json.dumps(fallback)}}]})
        
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta/llama3-70b-instruct",
        "messages": [{
            "role": "user",
            "content": f"Provide average salary in India for {skill} developer in strictly JSON format with keys: fresher (object with yearly, monthly), mid (object with yearly, monthly), senior (object with yearly, monthly). Values MUST be numbers (e.g. 400000). Return ONLY JSON."
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        print(f"Salary API Error ({skill}): {e}. Using fallback.")
        fallback = get_salary_fallback(skill)
        return jsonify({"choices": [{"message": {"content": json.dumps(fallback)}}]})

@app.route('/api/suggest', methods=['GET'])
def suggest():
    query = request.args.get('q', '').lower()
    suggestions = []
    if query:
        for sk in ROADMAPS.keys():
            if query in sk.lower():
                suggestions.append(sk)
    return jsonify(suggestions)

@app.route('/api/ai_suggest', methods=['GET'])
def ai_suggest():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])

    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return jsonify([])

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"Suggest exactly 3 unique IT career roles related to: '{query}'. Return ONLY the names, one per line. No numbers, no bullets, no markdown."
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a concise IT career assistant. Provide ONLY role titles, one per line."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        response.raise_for_status()
        res_data = response.json()
        raw_text = res_data["choices"][0]["message"]["content"].strip()
        
        lines = raw_text.split('\n')
        suggestions = []
        for line in lines:
            clean = line.replace('-', '').replace('*', '').replace('•', '').replace('1.', '').replace('2.', '').replace('3.', '').strip()
            if clean and len(clean) > 2:
                suggestions.append(clean)
        
        return jsonify(suggestions[:3])
    except Exception as e:
        print(f"AI Suggestion Error: {e}")
        return jsonify([])

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    # Fallback to general Groq key if chat-specific key is missing
    api_key = os.getenv('GROQ_CHAT_API_KEY') or os.getenv('GROQ_API_KEY')
    
    if not api_key:
        return jsonify({"reply": "AI Assistant is currently offline. Please set your GROQ API key in .env"})

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are an AI Career Assistant. PRIMARY KEY RULES:\n"
        "1. If the question is related to Education, Career, Skills, Programming, Jobs, or Learning: Give a normal, clear, and direct helpful answer. Do NOT add any extra motivational line.\n"
        "2. If the user's question is NOT related to education/career (e.g., movies, celebrities, random topics, personal chat): Give a SHORT answer (1-3 lines max) AND ALWAYS ADD THIS EXACT HTML TAG AT THE VERY END: '<span class=\"dark-study-badge\">👉 focus on studies bro 🚀</span>'\n"
        "3. STYLE: Friendly and simple English, no long paragraphs, always answer the question.\n"
        "IMPORTANT: NEVER add the 'dark-study-badge' to study/career questions. ONLY add it for OUT-OF-SCOPE questions."
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "temperature": 0.5,
        "top_p": 1,
        "max_tokens": 300
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        res_data = response.json()
        reply = res_data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"Groq Chat API Error: {str(e)}")
        return jsonify({"reply": "Sorry, I couldn't connect right now. Please ask your question again in a few seconds!"})


@app.route('/interview')
def interview_home():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    return render_template('interview_home.html')

@app.route('/interview_practice')
def interview_practice():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
        
    skill_query = request.args.get('skill', '').strip()
    skill_title = skill_query.title()
    questions = []
    
    api_key = os.getenv('NVIDIA_API_KEY')
    if api_key and skill_title:
        try:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            prompt = f"Generate exactly 5 core interview questions for a {skill_title} interview. Return ONLY a JSON array of 5 plain string questions. Example: [\"question 1\", \"question 2\"]"
            
            payload = {
                "model": "meta/llama-3.1-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            res_data = response.json()
            ai_text = res_data["choices"][0]["message"]["content"]
            
            ai_text = ai_text.replace('```json', '').replace('```', '').strip()
            questions = json.loads(ai_text)
        except Exception as e:
            print(f"Interview Practice Generation Error: {str(e)}")
            
    if not questions:
        questions = [
            f"What is {skill_title} and why is it used?",
            "Can you explain the core concepts of this technology?",
            "What are the best practices when working with this?",
            "How do you handle errors and debugging in this skill?",
            "Can you describe a challenging project where you used this?"
        ]
            
    return render_template('interview_practice.html', skill_title=skill_title, questions=questions, skill_query=skill_query)

@app.route('/api/evaluate_answer', methods=['POST'])
def evaluate_answer():
    if 'user_id' not in session and not session.get('guest'):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    question = data.get('question', '')
    answer = data.get('answer', '')
    skill = data.get('skill', '')
    
    api_key = os.getenv('NVIDIA_API_KEY')
    if not api_key:
        return jsonify({
            "feedback": "API key not configured. Cannot evaluate answer.",
            "correct_answer": "API Key Required",
            "difficulty": "Unknown"
        })
        
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        prompt = f"""You are an expert technical interviewer for {skill}.
Evaluate the candidate's answer to the following question. Provide constructive feedback, the ideal correct answer, and an estimated difficulty level (Easy/Medium/Hard).

Question: {question}
Candidate's Answer: {answer}

Return the response strictly as a JSON object:
{{
  "feedback": "Short evaluation (Good answer / Improve this point)...",
  "correct_answer": "Complete, accurate answer...",
  "difficulty": "Easy"
}}
Return ONLY the JSON. No markdown ticks."""
        
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1000
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        res_data = response.json()
        ai_text = res_data["choices"][0]["message"]["content"]
        
        ai_text = ai_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(ai_text)
        return jsonify(result)
    except Exception as e:
        print(f"Evaluate API Error: {str(e)}")
        return jsonify({
            "feedback": "Error connecting to AI for evaluation.",
            "correct_answer": "Evaluation failed.",
            "difficulty": "Unknown"
        }), 500

@app.route('/')
def index():
    return render_template('index.html', groq_key=os.getenv('GROQ_API_KEY', ''))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    
    name = session.get('name', 'Guest')
    
    # Fetch recently viewed roadmaps for the user
    recent_history = []
    if not session.get('guest') and 'user_id' in session:
        docs = []
        try:
            docs = db.collection('history')\
                     .where('user_id', '==', session['user_id'])\
                     .order_by('viewed_time', direction=firestore.Query.DESCENDING)\
                     .get()
        except Exception as e:
            print(f"Index check triggered for history index: {e}")
            # Total Fallback: Fetch by user_id only
            try:
                docs = db.collection('history')\
                         .where('user_id', '==', session['user_id'])\
                         .get()
                
                # Robust Sort: Handle datetime and string (legacy)
                def sort_key(doc):
                    val = doc.to_dict().get('viewed_time')
                    if val is None: return datetime.min
                    if isinstance(val, str):
                        try:
                            return datetime.fromisoformat(val)
                        except:
                            return datetime.min
                    return val
                    
                docs = sorted(docs, key=sort_key, reverse=True)
            except Exception as e2:
                print(f"Total history fallback failed: {e2}")
                docs = []
            
        try:
            # Filter to get unique skills (last 4)
            for doc in docs:
                skill = doc.to_dict().get('skill')
                if skill and skill not in recent_history:
                    recent_history.append(skill)
                if len(recent_history) >= 4:
                    break
        except Exception as e:
            print(f"Error filtering history docs: {e}")

    return render_template('index.html', name=session.get('name', 'Guest'), recent_history=recent_history, groq_key=os.getenv('GROQ_API_KEY', ''))

@app.route('/update_theme', methods=['POST'])
def update_theme():
    data = request.json
    theme = data.get('theme')
    if theme in ['light', 'dark']:
        session['theme'] = theme
        if 'user_id' in session and not session.get('guest'):
            try:
                db.collection('users').document(session['user_id']).update({'theme': theme})
            except Exception as e:
                print(f"Update Theme Error: {e}")
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/history')
def history():
    is_guest = session.get('guest', False)
    if 'user_id' not in session and not is_guest:
        return redirect(url_for('login'))
        
    unique_history = []
    try:
        docs = []
        try:
            docs = db.collection('history')\
                     .where('user_id', '==', session['user_id'])\
                     .order_by('viewed_time', direction=firestore.Query.DESCENDING)\
                     .get()
        except Exception as e:
            print(f"Index check triggered for history page: {e}")
            # Total Fallback: Fetch by user_id only
            try:
                docs = db.collection('history')\
                         .where('user_id', '==', session['user_id'])\
                         .get()
                
                # Robust Sort
                def sort_key(doc):
                    val = doc.to_dict().get('viewed_time')
                    if val is None: return datetime.min
                    if isinstance(val, str):
                        try: return datetime.fromisoformat(val)
                        except: return datetime.min
                    return val
                
                docs = sorted(docs, key=sort_key, reverse=True)
            except Exception as e2:
                print(f"Total history page fallback failed: {e2}")
                docs = []

        for doc in docs:
            skill = doc.to_dict().get('skill')
            if skill and skill not in unique_history:
                unique_history.append(skill)
            if len(unique_history) == 5:
                break
                
        return render_template('history.html', history=unique_history, is_guest=is_guest)
    except Exception as e:
        print(f"History Page Error: {e}")
        return render_template('history.html', history=[], is_guest=is_guest)

import json

INDUSTRIAL_WORKFLOW_DATA = {
    "java": [
        {"role": "Intern / Trainee", "skills": ["Java syntax", "OOPs", "Version Control (Git)", "Basic SQL"], "goal": "Understand codebase and fix minor bugs"},
        {"role": "Junior Developer", "skills": ["Spring Boot", "REST APIs", "Hibernate/JPA", "JUnit", "Debugging"], "goal": "Build independent features and write tests"},
        {"role": "Software Developer (Mid-Level)", "skills": ["Microservices", "Design Patterns", "Performance Optimization", "CI/CD"], "goal": "Design complex modules and guide juniors"},
        {"role": "Senior Developer", "skills": ["System Architecture", "Cloud (AWS/Azure)", "Kafka", "Security", "Scalability"], "goal": "Lead technical development and code reviews"},
        {"role": "Tech Lead", "skills": ["Agile Leadership", "Cross-team communication", "Technical Strategy", "Mentoring"], "goal": "Drive project delivery and technical standards"},
        {"role": "Solution Architect", "skills": ["Enterprise Architecture", "Technology Selection", "Risk Management", "System Integration"], "goal": "Design organization-wide scalable software solutions"},
        {"role": "Engineering Manager", "skills": ["People Management", "Budgeting", "Project Planning", "Stakeholder Management"], "goal": "Manage engineering teams and strategic delivery"}
    ],
    "python": [
        {"role": "Intern / Trainee", "skills": ["Python basics", "Data structures", "Git", "Basic scripting"], "goal": "Assist team and understand codebase"},
        {"role": "Junior Developer", "skills": ["Django/Flask", "REST APIs", "SQLAlchemy", "Pytest", "Linux"], "goal": "Develop backend endpoints and write tests"},
        {"role": "Software Developer (Mid-Level)", "skills": ["FastAPI", "Asyncio", "Docker", "Database Optimization", "CI/CD"], "goal": "Build scalable services and mentor juniors"},
        {"role": "Senior Developer", "skills": ["System Design", "Kubernetes", "Redis", "Message Queues", "Cloud architecture"], "goal": "Architect high-traffic systems and optimize performance"},
        {"role": "Tech Lead", "skills": ["Technical Strategy", "Agile", "Code Review", "Cross-functional leadership"], "goal": "Lead sprints and define engineering standards"},
        {"role": "Solution Architect", "skills": ["Platform Architecture", "Evaluation of Tech Stack", "Security", "Cost Optimization"], "goal": "Design large-scale distributed systems"},
        {"role": "Engineering Manager", "skills": ["Team Building", "Delivery Management", "Resource Planning", "Mentorship"], "goal": "Ensure team health and project success"}
    ],
    "web development": [
        {"role": "Intern / Trainee", "skills": ["HTML/CSS", "JavaScript basics", "Git", "Responsive Design"], "goal": "Assist with UI components and bug fixes"},
        {"role": "Junior Developer", "skills": ["React/Vue", "Node.js", "REST APIs", "DOM manipulation", "SQL/NoSQL"], "goal": "Build full-stack features independently"},
        {"role": "Software Developer (Mid-Level)", "skills": ["State Management", "Next.js", "Performance Optimization", "Web Security", "CI/CD"], "goal": "Develop complex architectures and optimize load times"},
        {"role": "Senior Developer", "skills": ["Micro-frontends", "System Architecture", "Cloud Hosting", "WebSockets", "Serverless"], "goal": "Lead technical decisions and enforce best practices"},
        {"role": "Tech Lead", "skills": ["Sprint Planning", "Code Review", "Mentorship", "Technical Roadmaps"], "goal": "Guide development team and resolve blockers"},
        {"role": "Solution Architect", "skills": ["Enterprise Architecture", "Scalability Strategy", "DevOps integration", "System Design"], "goal": "Design high-availability enterprise web products"},
        {"role": "Engineering Manager", "skills": ["People Management", "Strategic Planning", "Stakeholder Communication", "Budgeting"], "goal": "Manage deliveries and engineer career growth"}
    ],
    "ai": [
        {"role": "Intern / Trainee", "skills": ["Python", "Pandas/NumPy", "Basic ML algorithms", "Data Cleaning"], "goal": "Assist in data preparation and EDA"},
        {"role": "Junior Developer", "skills": ["Scikit-learn", "TensorFlow/PyTorch basics", "SQL", "Model evaluation"], "goal": "Train baseline models and build data pipelines"},
        {"role": "Software Developer (Mid-Level)", "skills": ["Deep Learning", "NLP/Computer Vision", "Model Deployment", "Docker"], "goal": "Develop complex AI models and productionize them"},
        {"role": "Senior Developer", "skills": ["MLOps", "LLMs (LangChain)", "Distributed Training", "Cloud AI services", "Optimization"], "goal": "Architect end-to-end AI systems and optimize inference"},
        {"role": "Tech Lead", "skills": ["Research Direction", "Team Leadership", "Code Review", "Agile AI"], "goal": "Lead AI strategy and drive model accuracy"},
        {"role": "Solution Architect", "skills": ["AI Infrastructure", "Enterprise ML Design", "Data Security", "Cost Optimization"], "goal": "Design organization-wide scalable AI platforms"},
        {"role": "Engineering Manager", "skills": ["AI Project Management", "Resource Allocation", "Cross-team collaboration", "Mentoring"], "goal": "Deliver AI products and manage technical teams"}
    ],
    "blockchain": [
        {"role": "Intern / Trainee", "skills": ["Cryptography basics", "Blockchain concepts", "Solidity basics", "Git"], "goal": "Understand smart contracts and assist team"},
        {"role": "Junior Developer", "skills": ["Solidity", "Web3.js/ethers.js", "Truffle/Hardhat", "Smart Contract Testing"], "goal": "Develop and test basic smart contracts"},
        {"role": "Software Developer (Mid-Level)", "skills": ["DeFi protocols", "Smart Contract Security", "IPFS", "L2 Scaling (Polygon)"], "goal": "Build secure DApps and optimize gas costs"},
        {"role": "Senior Developer", "skills": ["Protocol Architecture", "Zero-Knowledge Proofs", "Cross-chain bridges", "Auditing"], "goal": "Design complex tokenomics and secure core protocols"},
        {"role": "Tech Lead", "skills": ["Technical Strategy", "Security Code Reviews", "Team Management", "Agile"], "goal": "Lead blockchain initiatives and enforce security standards"},
        {"role": "Solution Architect", "skills": ["Enterprise Blockchain Design", "Consensus Mechanisms", "System Integration", "Scalability"], "goal": "Design decentralized networks and token ecosystems"},
        {"role": "Engineering Manager", "skills": ["Delivery Management", "Strategic Roadmaps", "Stakeholder Communication", "Team Building"], "goal": "Manage blockchain teams and product launches"}
    ]
}

DEFAULT_WORKFLOW = [
     {"role": "Intern / Trainee", "skills": ["Basic Programming", "Version Control", "Debugging", "Communication"], "goal": "Learn the codebase and assist developers"},
     {"role": "Junior Developer", "skills": ["Core Frameworks", "Database basics", "Testing", "API Integration"], "goal": "Deliver independent features on time"},
     {"role": "Software Developer (Mid-Level)", "skills": ["System Design", "Performance Optimization", "CI/CD", "Security Basics"], "goal": "Architect complex components and mentor juniors"},
     {"role": "Senior Developer", "skills": ["Cloud Architecture", "Scalability", "Advanced System Design", "Code Review"], "goal": "Lead technical development and ensure code quality"},
     {"role": "Tech Lead", "skills": ["Technical Strategy", "Agile Leadership", "Cross-team coordination", "Mentoring"], "goal": "Drive project delivery and resolve technical blockers"},
     {"role": "Solution Architect", "skills": ["Enterprise Architecture", "Risk Management", "Technology Evaluation", "System Integration"], "goal": "Design organization-wide scalable software solutions"},
     {"role": "Engineering Manager", "skills": ["People Management", "Budgeting", "Project Planning", "Strategic Delivery"], "goal": "Ensure team health and manage product delivery"}
]

@app.route('/api/industrial-workflow', methods=['GET', 'POST'])
@app.route('/api/industrial_workflow', methods=['GET', 'POST'])
def get_industrial_workflow():
    if request.method == 'POST':
        data = request.json or {}
        skill = data.get('skill', '').lower().strip()
    else:
        skill = request.args.get('skill', '').lower().strip()
    
    # 1. Hardcoded Fetch (Lightning Fast)
    if skill in INDUSTRIAL_WORKFLOW_DATA:
        return jsonify({"status": "success", "data": INDUSTRIAL_WORKFLOW_DATA[skill]})
        
    for key, workflow in INDUSTRIAL_WORKFLOW_DATA.items():
        if key in skill:
            return jsonify({"status": "success", "data": workflow})

    groq_api_key = os.getenv('GROQ_CHAT_API_KEY') or os.getenv('GROQ_API_KEY_2.0') or os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        return jsonify({"status": "success", "data": DEFAULT_WORKFLOW})

    # 2. Dynamic Groq Fallback Generation
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        prompt = f"""
        You are an elite Industry Expert AI system. Your task is to generate a REALISTIC and PRACTICAL "Industrial Workflow" roadmap for the skill: '{skill}'.

        ⚠️ STRICT RULES:
        1. NO textbook or generic answers.
        2. NO definitions, theory, or academic explanations.
        3. Explain ONLY how things work in REAL leading companies.
        4. Content must feel like "Insider Industry Knowledge" (e.g., mention Sprint reviews, specific CI/CD triggers, real-world bug prioritization, etc.).
        5. Keep it structured, detailed, and truthful.

        Roles to include strictly in this order: Intern / Trainee, Junior Developer, Software Developer (Mid-Level), Senior Developer, Tech Lead, Solution Architect, Engineering Manager.
        
        For EACH role return exactly:
        - "role": string
        - "skills": list of strings (max 4 core technical skills actually used in production)
        - "goal": one line string describing their practical business goal

        Return ONLY a valid JSON object with a root key "workflow" containing the list. No markdown.
        """
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"}
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        res_data = response.json()
        raw_json = res_data["choices"][0]["message"]["content"].strip()
        workflow_data = json.loads(raw_json)
        # Handle case where AI might wrap it in a root key
        if isinstance(workflow_data, dict):
            for k in workflow_data:
                if isinstance(workflow_data[k], list):
                    workflow_data = workflow_data[k]
                    break
        return jsonify({"status": "success", "workflow": workflow_data})
    except Exception as e:
        print(f"Workflow Generation Error with Groq: {str(e)}")
        # 3. Always strictly guarantee a fallback array
        return jsonify({"status": "success", "data": DEFAULT_WORKFLOW})

def fetch_roadmap_json(skill):
    # Build prompt using string concatenation to avoid f-string brace issues
    prompt = (
        "You are a Senior Career Mentor and Industry Architect.\n"
        "Generate a PREMIUM, EXECUTIVE-LEVEL career roadmap and guidance document for: " + skill + "\n\n"
        "GOAL: Create the definitive A-Z guide for this career path, including technical mastery, aptitude, DSA, and professional mentorship.\n\n"
        "STRICT INSTRUCTIONS:\n"
        "- Act as an elite mentor who cares about the student's success\n"
        "- Provide deep, structured, step-by-step technical guidance\n"
        "- Include REAL tools and technologies used in the industry today\n"
        "- Include HIGH-QUALITY learning resources with REAL clickable links (https://...)\n"
        "- NEW: Include a dedicated Aptitude section (Logical/Quant) relevant to this role\n"
        "- NEW: Include a dedicated DSA section (Data Structures & Algorithms) with high-frequency patterns\n"
        "- NEW: Include 'Mentor Wisdom' with 3-4 powerful career secrets/preparation strategies\n"
        "- Return ONLY valid JSON, no markdown, no explanation\n\n"
        "Return this EXACT JSON structure:\n"
        '{\n'
        '  "title": "' + skill.title() + ' Elite Career Guidance",\n'
        '  "introduction": "Strategic overview of ' + skill + ', its industrial impact, and why it is a top-tier career choice - 4 detailed lines",\n'
        '  "beginner": [\n'
        '    {"topic":"Concept","description":"Reason to learn and industry use","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "intermediate": [\n'
        '    {"topic":"Topic","description":"Mastery details and practical application","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "advanced": [\n'
        '    {"topic":"Architectural Concept","description":"System design and performance details","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "aptitude": [\n'
        '    {"topic":"Aptitude Area","reason":"Why this is tested in companies like Google/TCS/Zoho","preparation_tip":"Specific shortcut or strategy","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "dsa": [\n'
        '    {"pattern":"DSA Pattern/Topic","importance":"Why it matters for ' + skill + ' interviews","practice_problem":"One classic problem name","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "tools": [\n'
        '    {"tool":"Tool","description":"Professional use case","free_resource_link":"https://..."}\n'
        '  ],\n'
        '  "projects": [\n'
        '    {"title":"Project Name","description":"What it proves to recruiters","difficulty":"Level"}\n'
        '  ],\n'
        '  "mentor_wisdom": [\n'
        '    {"strategy":"Mentor Secret","detail":"Why most candidates fail here and how to win"}\n'
        '  ],\n'
        '  "career_paths": [\n'
        '    {"role":"Job Title","salary_range":"X-Y LPA","responsibilities":"Key metrics for success"}\n'
        '  ],\n'
        '  "certifications": [\n'
        '    {"name":"Certs","organization":"Org","difficulty":"Level","url":"https://..."}\n'
        '  ],\n'
        '  "salary_insights": {"fresher":{"yearly":500000,"monthly":40000},"mid":{"yearly":1200000,"monthly":100000},"senior":{"yearly":2500000,"monthly":200000}},\n'
        '  "interview_questions": [\n'
        '    {"question":"Question?","in_depth_answer":"Expert 3-line response"}\n'
        '  ],\n'
        '  "resources": [\n'
        '    {"name":"Resource","description":"What it offers","url":"https://..."}\n'
        '  ],\n'
        '  "workflow": {\n'
        '    "intern":{"skills":["S1","S2"],"goal":"Industry Expert Tip: focus on real production workflows"},\n'
        '    "junior":{"skills":["S1","S2"],"goal":"Practical application in sprints"},\n'
        '    "developer":{"skills":["S1","S2"],"goal":"Building scalable features"},\n'
        '    "senior":{"skills":["S1","S2"],"goal":"Architectural and code complexity mastery"},\n'
        '    "lead":{"skills":["S1","S2"],"goal":"Technical leadership and project scoping"},\n'
        '    "architect":{"skills":["S1","S2"],"goal":"Design vision and cross-team strategy"},\n'
        '    "manager":{"skills":["S1","S2"],"goal":"Engineering health, budget, and delivery"}\n'
        '  }\n'
        '}\n\n'
        "ITEM COUNTS: beginner=5, intermediate=5, advanced=4, aptitude=4, dsa=4, tools=6, projects=4, mentor_wisdom=4, "
        "career_paths=6, interview_questions=5, resources=6.\n\n"
        "CRITICAL: Use REAL high-quality URLs. Every field MUST be filled with detailed data."
    )

    api_key = GROQ_API_KEY_2 or GROQ_API_KEY
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        raw_json = result["choices"][0]["message"]["content"].strip()
        res_json = json.loads(raw_json)
        
        return res_json
    except json.JSONDecodeError as e:
        print(f"JSON Parse error in fetch_roadmap_json: {str(e)}")
        try:
            import re
            fixed_json = re.sub(r',\s*([\]}])', r'\1', raw_json)
            return json.loads(fixed_json)
        except Exception as inner_e:
            print(f"Secondary JSON Parse error: {str(inner_e)}")
            with open('bad_json.txt', 'w', encoding='utf-8') as f:
                f.write(raw_json)
            error_msg = "Error: The AI generated an invalid response. Please try again."
            return {
                "title": f"{skill.title()} Complete Career Guidance",
                "beginner": [error_msg],
                "intermediate": [error_msg],
                "advanced": [error_msg],
                "tools": [error_msg],
                "projects": [error_msg],
                "interview_questions": [error_msg],
                "workflow": {}
            }
    except Exception as e:
        print(f"Error in fetch_roadmap_json: {str(e)}")
        error_msg = f"API Error ({str(e)}). Please ensure your NVIDIA AI account has available credits or quota."
        return {
            "title": f"{skill.title()} Complete Career Guidance",
            "beginner": [error_msg],
            "intermediate": ["A valid API key is required to generate this section."],
            "advanced": ["A valid API key is required to generate this section."],
            "tools": ["A valid API key is required to generate this section."],
            "projects": ["A valid API key is required to generate this section."],
            "interview_questions": ["A valid API key is required to generate this section."],
            "workflow": {}
        }

@app.route('/api/generate_complete_roadmap', methods=['POST'])
def generate_complete_roadmap():
    if 'user_id' not in session and not session.get('guest'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    skill = data.get('skill', '')
    
    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"error": "Groq API key missing"}), 500
        
    try:
        roadmap_json = fetch_roadmap_json(skill)
        return jsonify(roadmap_json)
    except Exception as e:
        print("API generation error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/download_complete_pdf', methods=['POST'])
def download_complete_pdf():
    skill = request.form.get('skill', '')
    if not skill:
        data = request.get_json(silent=True) or {}
        skill = data.get('skill', '')
            
    if not skill:
        return "Skill required", 400
        
    try:
        # ── EXACTLY ONE API CALL ─────────────────────────
        # Skip the extra heavy text processing/fallback loops
        # Directly grab the lightweight, structured JSON
        roadmap_json = fetch_roadmap_json(skill)
        is_indepth = True  # We have dynamic data from fetch_roadmap_json
        
        buffer = io.BytesIO()
        pdf_title = f"{skill.title()} Career Roadmap"
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            rightMargin=60, leftMargin=60,
            topMargin=50, bottomMargin=40,
            title=pdf_title, author="AI Career Consulting System"
        )
        
        styles = getSampleStyleSheet()
        
        # ── Premium PDF Styles (Apple-style clean layout) ──
        title_style = ParagraphStyle(
            'PdfTitle', parent=styles['Heading1'],
            fontSize=20, leading=26,
            spaceBefore=0, spaceAfter=4,
            alignment=1,
            textColor='#1a1a2e',
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'PdfSubtitle', parent=styles['Normal'],
            fontSize=10, leading=14,
            alignment=1,
            spaceAfter=14,
            textColor='#888888',
            fontName='Helvetica'
        )
        h2_style = ParagraphStyle(
            'PdfH2', parent=styles['Heading2'],
            fontSize=16, leading=20,
            spaceBefore=14, spaceAfter=8,
            textColor='#1a1a2e',
            fontName='Helvetica-Bold'
        )
        h3_style = ParagraphStyle(
            'PdfH3', parent=styles['Heading3'],
            fontSize=13, leading=17,
            spaceBefore=10, spaceAfter=5,
            textColor='#0f3460',
            fontName='Helvetica-Bold'
        )
        body_style = ParagraphStyle(
            'PdfBody', parent=styles['Normal'],
            fontSize=10.5, leading=15,
            spaceAfter=5,
            textColor='#333333',
            fontName='Helvetica'
        )
        bullet_style = ParagraphStyle(
            'PdfBullet', parent=styles['Normal'],
            fontSize=10.5, leading=15,
            spaceAfter=4,
            leftIndent=18,
            textColor='#333333',
            fontName='Helvetica'
        )
        intro_style = ParagraphStyle(
            'PdfIntro', parent=styles['Normal'],
            fontSize=10.5, leading=16,
            spaceBefore=2, spaceAfter=10,
            textColor='#444444',
            fontName='Helvetica-Oblique'
        )
        mentor_style = ParagraphStyle(
            'PdfMentor', parent=styles['Normal'],
            fontSize=10.5, leading=15,
            leftIndent=20, rightIndent=20,
            spaceBefore=10, spaceAfter=10,
            textColor='#1a1a2e',
            backColor='#f0f4f8',
            borderPadding=10,
            fontName='Helvetica-Oblique'
        )
        
        Story = []
        
        # ── Helper: apply_linkify ───────────────────────
        def apply_linkify(text):
            if not text: return ""
            safe_text = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_text = safe_text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
            safe_text = safe_text.replace('&lt;strong&gt;', '<b>').replace('&lt;/strong&gt;', '</b>')
            safe_text = safe_text.replace('&lt;br&gt;', '<br/>').replace('&lt;br/&gt;', '<br/>')
            safe_text = re.sub(r'\[([^\]]+)\]\((https?://[^\s<>]+)\)', r'<a href=' + chr(34) + r'\2' + chr(34) + r' color=' + chr(34) + r'blue' + chr(34) + r'><u>\1</u></a>', safe_text)
            safe_text = re.sub(r'(?<!href=' + chr(34) + r')(?<!' + chr(34) + r'>)(https?://[^\s<>]+)', r'<a href=' + chr(34) + r'\1' + chr(34) + r' color=' + chr(34) + r'blue' + chr(34) + r'><u>\1</u></a>', safe_text)
            return safe_text

        # ── Helper: Clean section divider ─────────────────
        def add_divider():
            Story.append(Spacer(1, 10))
            Story.append(HRFlowable(width='100%', thickness=0.3, color='#dddddd', spaceAfter=6, spaceBefore=2))
        
        # ── Helper: Section heading with divider + real emojis ──
        # Try to register Segoe UI Emoji for real emoji support (Windows/Local)
        has_emoji_font = False
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            font_path = r'C:\Windows\Fonts\seguiemj.ttf'
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('SegoeUIEmoji', font_path))
                has_emoji_font = True
        except Exception as e:
            print("Could not load emoji font:", e)

        # Real Emoji Map (keyword → emoji character)
        _section_emojis = {
            'introduction': '🚀',
            'beginner': '🌱',
            'intermediate': '⚙️',
            'advanced': '🏆',
            'tool': '🧰',
            'project': '💼',
            'career': '🎯',
            'certification': '📜',
            'salary': '💰',
            'interview': '❓',
            'resource': '📚',
            'workflow': '🏭',
            'advice': '✅',
            'industrial': '🏢',
        }
        
        def add_section(title_text, custom_emoji=''):
            add_divider()
            import re as _re
            
            # The original AI content might have its own emojis, let's keep them if present,
            # otherwise strip them from the text itself and add our standard one.
            clean_title = _re.sub(r'[^\x00-\x7F]+', '', title_text).strip()
            
            if has_emoji_font:
                # Use real emoji from mapping or fallback custom_emoji
                icon_char = '📌' # default
                for keyword, char in _section_emojis.items():
                    if keyword in clean_title.lower():
                        icon_char = char
                        break
                if custom_emoji:
                    icon_char = custom_emoji
                    
                icon_markup = f'<font name="SegoeUIEmoji" size="14">{icon_char}</font>  '
                Story.append(Paragraph(icon_markup + f'<font color="#16213e">{clean_title}</font>', h2_style))
            else:
                # Fallback to plain text if font fails
                Story.append(Paragraph(f'<font color="#16213e">{clean_title}</font>', h2_style))
        
        # ── Helper: Render items as spaced bullets ────────
        def add_bullets(items_list):
            bullet_items = []
            for item in items_list:
                if isinstance(item, dict):
                    name = item.get('topic') or item.get('tool') or item.get('title') or item.get('name') or item.get('question') or item.get('role') or ''
                    desc = item.get('description') or item.get('in_depth_answer') or item.get('responsibilities') or item.get('goal') or ''
                    link = item.get('free_resource_link') or item.get('url') or ''
                    diff = item.get('difficulty') or item.get('organization') or ''
                    
                    parts = [f"<b>{apply_linkify(str(name))}</b>"]
                    if diff:
                        parts.append(f"  <font color='#666666'>({apply_linkify(str(diff))})</font>")
                    if link:
                        parts.append(f'  <a href="{link}" color="blue"><u>Link</u></a>')
                    
                    text = ''.join(parts)
                    if desc:
                        text += f"<br/><font color='#555555'>{apply_linkify(str(desc))}</font>"
                else:
                    text = apply_linkify(str(item).lstrip('•').strip())
                
                if text.strip():
                    bullet_items.append(ListItem(Paragraph(text, bullet_style), bulletColor='#0f3460'))
            
            if bullet_items:
                Story.append(ListFlowable(
                    bullet_items,
                    bulletType='bullet',
                    bulletFontSize=5,
                    bulletOffsetY=-2,
                    start='\u2022'
                ))
                Story.append(Spacer(1, 6))
        
        # ══════════════════════════════════════════════════
        # PDF CONTENT START
        # ══════════════════════════════════════════════════
        
        title = roadmap_json.get("title", f"{skill.title()} Complete Career Guidance")
        Story.append(Paragraph(title, title_style))
        Story.append(Spacer(1, 2))
        Story.append(HRFlowable(width='40%', thickness=1.5, color='#0f3460', spaceAfter=4, spaceBefore=0))
        Story.append(Paragraph("AI-Powered Career Guidance Document", subtitle_style))
        Story.append(Spacer(1, 8))
        
        # ── Introduction ─────────────────────────────
        intro = roadmap_json.get("introduction", "")
        if intro:
            add_section("Introduction")
            safe_intro = str(intro).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            Story.append(Paragraph(safe_intro, intro_style))
            Story.append(Spacer(1, 8))



        # ── Dynamic Sections Loop ────────────────────────
        if 'sections' in roadmap_json and roadmap_json['sections']:
            for section in roadmap_json['sections']:
                sec_title = section.get('title', 'Section').replace('🔥', '').replace('🚀', '').strip()
                sec_content = section.get('content', '')
                
                if not is_indepth and ('Career' in sec_title or 'Job' in sec_title):
                    continue
                
                add_section(sec_title, '📌')
                
                items = []
                if isinstance(sec_content, list):
                    items = sec_content
                elif isinstance(sec_content, str):
                    if '<br>' in sec_content or '•' in sec_content:
                        items = sec_content.replace('<br>', '\n').replace('•', '\n').split('\n')
                        items = [i.strip() for i in items if i.strip()]
                    else:
                        items = [sec_content]

                add_bullets(items)
                Story.append(Spacer(1, 6))
        else:
            # Fallback for re-fetch without sections key
            sections_map = [
                ("📘 Beginner Level", "beginner"),
                ("📗 Intermediate Level", "intermediate"),
                ("📕 Advanced Level", "advanced"),
                ("🛠 Tools & Technologies", "tools"),
                ("🌐 Web & API", "web"),
                ("🗄 Database", "database"),
                ("⚙ Frameworks", "frameworks"),
                ("🚀 Real-world Projects", "projects")
            ]
            for ui_title, json_key in sections_map:
                if json_key in roadmap_json and roadmap_json[json_key]:
                    add_section(ui_title)
                    add_bullets(roadmap_json[json_key])
                    Story.append(Spacer(1, 6))
                
        # ── Industrial Workflow ───────────────────────────
        if "workflow" in roadmap_json:
            add_section("Industrial Workflow", "🏭")
            wf_data = roadmap_json["workflow"]
            roles = ["intern", "junior", "developer", "senior", "lead", "architect", "manager"]
            display_roles = ["Intern / Trainee", "Junior Developer", "Software Developer (Mid-Level)", "Senior Developer", "Tech Lead", "Solution Architect", "Engineering Manager"]
            
            for k, display in zip(roles, display_roles):
                if k in wf_data:
                    role_data = wf_data[k]
                    Story.append(Paragraph(f"<b>{display}</b>", h3_style))
                    goal = role_data.get("goal", "")
                    if goal:
                        Story.append(Paragraph(f"Goal: {apply_linkify(goal)}", bullet_style))
                    skills = role_data.get("skills", [])
                    if skills:
                        skill_str = ", ".join(str(s) for s in skills)
                        Story.append(Paragraph(f"Skills: {apply_linkify(skill_str)}", bullet_style))
                    Story.append(Spacer(1, 4))

        # ── Aptitude Preparation ──────────────────────────
        aptitude_data = roadmap_json.get("aptitude", [])
        if aptitude_data:
            add_section("IMPORTANT: Aptitude & Logical Mastery", "🧠")
            apt_items = []
            for item in aptitude_data:
                topic = item.get("topic", "")
                reason = item.get("reason", "")
                tip = item.get("preparation_tip", "")
                link = item.get("free_resource_link", "")
                
                text = f"<b>{apply_linkify(topic)}</b>"
                if reason:
                    text += f"<br/><font color='#555555'><i>Why:</i> {apply_linkify(reason)}</font>"
                if tip:
                    text += f"<br/><font color='#0a4d68'><i>Mentor Tip:</i> {apply_linkify(tip)}</font>"
                if link:
                    text += f"<br/><a href='{link}' color='blue'><u>Access Learning Resource</u></a>"
                
                apt_items.append(ListItem(Paragraph(text, bullet_style), bulletColor='#0f3460'))
            if apt_items:
                Story.append(ListFlowable(apt_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
            Story.append(Spacer(1, 6))

        # ── DSA Mastery ──────────────────────────────────
        dsa_data = roadmap_json.get("dsa", [])
        if dsa_data:
            add_section("IMPORTANT: High-Frequency DSA Patterns", "💻")
            dsa_items = []
            for item in dsa_data:
                pattern = item.get("pattern", "")
                imp = item.get("importance", "")
                prob = item.get("practice_problem", "")
                link = item.get("free_resource_link", "")
                
                text = f"<b>{apply_linkify(pattern)}</b>"
                if imp:
                    text += f"<br/><font color='#555555'><i>Importance:</i> {apply_linkify(imp)}</font>"
                if prob:
                    text += f"<br/><font color='#7c3aed'><i>Must-Do Problem:</i> {apply_linkify(prob)}</font>"
                if link:
                    text += f"<br/><a href='{link}' color='blue'><u>Practice on LeetCode/GFG</u></a>"
                
                dsa_items.append(ListItem(Paragraph(text, bullet_style), bulletColor='#0f3460'))
            if dsa_items:
                Story.append(ListFlowable(dsa_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
            Story.append(Spacer(1, 6))

        # ── Career Paths ─────────────────────────────────
        career_paths = roadmap_json.get("career_paths", [])
        if career_paths:
            add_section("Career Paths", "💼")
            add_bullets(career_paths)
            Story.append(Spacer(1, 6))

        # ── Certifications ───────────────────────────────
        certifications = roadmap_json.get("certifications", [])
        if certifications:
            add_section("Certifications", "🎓")
            add_bullets(certifications)
            Story.append(Spacer(1, 6))

        # ── Salary Insights ──────────────────────────────
        def format_salary_py(amount):
            if not amount: return "N/A"
            try:
                a = float(amount)
                if a >= 100000: return f"Rs. {a/100000:.1f}".replace(".0","") + "L"
                if a >= 1000: return f"Rs. {int(a/1000)}K"
                return f"Rs. {int(a)}"
            except: return str(amount)

        salary_data = roadmap_json.get("salary_insights", {})
        if salary_data and isinstance(salary_data, dict):
            add_section("Salary Insights (India)", "💰")
            salary_items = []
            for level, label in [("fresher", "Fresher (0-2 yrs)"), ("mid", "Mid-Level (2-5 yrs)"), ("senior", "Senior (5+ yrs)")]:
                level_data = salary_data.get(level, {})
                if isinstance(level_data, dict):
                    yearly = level_data.get("yearly", 0)
                    monthly = level_data.get("monthly", 0)
                    salary_items.append(ListItem(
                        Paragraph(f"<b>{label}:</b>  {format_salary_py(yearly)}/yr  ({format_salary_py(monthly)}/mo)", bullet_style),
                        bulletColor='#0f3460'
                    ))
            if salary_items:
                Story.append(ListFlowable(salary_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
            Story.append(Spacer(1, 6))

        # ── Mentor Wisdom ────────────────────────────────
        mentor_data = roadmap_json.get("mentor_wisdom", [])
        if mentor_data:
            add_section("Mentor Wisdom & Strategy", "✨")
            for item in mentor_data:
                strat = item.get("strategy", "")
                detail = item.get("detail", "")
                if strat:
                    Story.append(Paragraph(f"<b>{apply_linkify(strat)}</b>", h3_style))
                if detail:
                    Story.append(Paragraph(apply_linkify(detail), mentor_style))
            Story.append(Spacer(1, 8))

        # ── Interview Questions ──────────────────────────
        iq_data = roadmap_json.get("interview_questions", [])
        if iq_data:
            add_section("Interview Questions", "❓")
            add_bullets(iq_data)
            Story.append(Spacer(1, 6))

        # ── Best Resources ────────────────────────────────
        resources_data = roadmap_json.get("resources", [])
        if resources_data:
            add_section("Best Resources", "🌐")
            res_items = []
            for res in resources_data:
                if isinstance(res, dict):
                    name = res.get("name", "")
                    desc = res.get("description", "")
                    url = res.get("url", "")
                    parts = [f"<b>{apply_linkify(str(name))}</b>"]
                    if desc:
                        parts.append(f" — {apply_linkify(str(desc))}")
                    if url:
                        parts.append(f' <a href="{url}" color="blue"><u>Visit</u></a>')
                    text = ''.join(parts)
                else:
                    text = apply_linkify(str(res))
                if text.strip():
                    res_items.append(ListItem(Paragraph(text, bullet_style), bulletColor='#0f3460'))
            if res_items:
                Story.append(ListFlowable(res_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
            Story.append(Spacer(1, 6))

        # --- Manual Extensions (Only if NOT in-depth) ---
        if not is_indepth:
            sq = skill.lower()
            
            # Define skill-specific data including tools, fallback salary (Legacy format), and tips
            skill_configs = {
                'java': {
                    'tools': ["IntelliJ IDEA", "Eclipse", "Spring Boot", "Maven / Gradle", "Postman", "Docker"],
                    'fallback': "<b>Fresher:</b> Rs. 3-6 LPA (Rs. 25K-45K/mo)<br/><b>Mid:</b> Rs. 6-12 LPA (Rs. 50K-1L/mo)<br/><b>Senior:</b> Rs. 12-25+ LPA (Rs. 1L-2L+/mo)<br/><br/>",
                    'tip': "Focus on Spring Boot + DSA"
                },
                'python': {
                    'tools': ["VS Code", "PyCharm", "Jupyter Notebook", "Django / Flask", "Pandas / NumPy"],
                    'fallback': "<b>Fresher:</b> Rs. 3-7 LPA (Rs. 25K-55K/mo)<br/><b>Mid:</b> Rs. 7-15 LPA (Rs. 55K-1.2L/mo)<br/><b>Senior:</b> Rs. 15-30+ LPA (Rs. 1.2L-2.5L+/mo)<br/><br/>",
                    'tip': "Focus on Django/FastAPI + DSA"
                },
                'cyber': {
                    'tools': ["Kali Linux", "Wireshark", "Metasploit", "Burp Suite", "Nmap"],
                    'fallback': "<b>Fresher:</b> Rs. 4–8 LPA (Rs. 30K–60K/mo)<br/><b>Mid:</b> Rs. 8–18 LPA (Rs. 60K–1.5L/mo)<br/><b>Senior:</b> Rs. 20–40+ LPA (Rs. 1.5L–3L+/mo)<br/><br/>",
                    'tip': "Focus on Certs (CEH, OSCP) + Networking"
                },
                'ai': {
                    'tools': ["Jupyter Notebook", "TensorFlow", "Scikit-learn", "Pandas", "Google Colab"],
                    'fallback': "<b>Fresher:</b> Rs. 5–10 LPA (Rs. 40K–80K/mo)<br/><b>Mid:</b> Rs. 10–25 LPA (Rs. 80K–2L/mo)<br/><b>Senior:</b> Rs. 25–50+ LPA (Rs. 2L–4L+/mo)<br/><br/>",
                    'tip': "Focus on PyTorch/Math + DSA"
                },
                'fullstack': {
                    'tools': ["VS Code", "GitHub", "Docker", "Postman", "Chrome DevTools"],
                    'fallback': "<b>Fresher:</b> Rs. 4–8 LPA (Rs. 30K–60K/mo)<br/><b>Mid:</b> Rs. 8–18 LPA (Rs. 60K–1.5L/mo)<br/><b>Senior:</b> Rs. 18–35+ LPA (Rs. 1.5L–2.5L+/mo)<br/><br/>",
                    'tip': "Focus on React/NodeJS + DSA"
                },
                'frontend': {
                    'tools': ["VS Code", "Webpack", "Figma", "Chrome DevTools", "Git / GitHub"],
                    'fallback': "<b>Fresher:</b> Rs. 3–6 LPA (Rs. 25K–45K/mo)<br/><b>Mid:</b> Rs. 6–14 LPA (Rs. 50K–1.1L/mo)<br/><b>Senior:</b> Rs. 14–25+ LPA (Rs. 1.1L–2L+/mo)<br/><br/>",
                    'tip': "Focus on React/NextJS + UI/UX"
                },
                'backend': {
                    'tools': ["VS Code", "Postman", "Docker", "Kubernetes", "Linux Shell"],
                    'fallback': "<b>Fresher:</b> Rs. 4–7 LPA (Rs. 30K–55K/mo)<br/><b>Mid:</b> Rs. 7–16 LPA (Rs. 55K–1.3L/mo)<br/><b>Senior:</b> Rs. 16–30+ LPA (Rs. 1.3L–2.5L+/mo)<br/><br/>",
                    'tip': "Focus on Microservices + DB Scaling"
                },
                'data': {
                    'tools': ["Jupyter Notebook", "Tableau / PowerBI", "SQL Server / MySQL", "Apache Spark", "Excel"],
                    'fallback': "<b>Fresher:</b> Rs. 4–8 LPA (Rs. 30K–60K/mo)<br/><b>Mid:</b> Rs. 8–15 LPA (Rs. 60K–1.2L/mo)<br/><b>Senior:</b> Rs. 15–35+ LPA (Rs. 1.2L–2.5L+/mo)<br/><br/>",
                    'tip': "Focus on SQL Mastery + Stats"
                },
                'devops': {
                    'tools': ["Docker", "Kubernetes", "Jenkins", "Terraform", "AWS / Azure Console"],
                    'fallback': "<b>Fresher:</b> Rs. 5–9 LPA (Rs. 40K–70K/mo)<br/><b>Mid:</b> Rs. 9–18 LPA (Rs. 70K–1.5L/mo)<br/><b>Senior:</b> Rs. 18–35+ LPA (Rs. 1.5L–2.5L+/mo)<br/><br/>",
                    'tip': "Focus on K8s + CI/CD Pipelines"
                },
                'mobile': {
                    'tools': ["Android Studio", "Xcode", "Firebase", "Postman", "Figma"],
                    'fallback': "<b>Fresher:</b> Rs. 3–7 LPA (Rs. 25K–55K/mo)<br/><b>Mid:</b> Rs. 7–14 LPA (Rs. 55K–1.1L/mo)<br/><b>Senior:</b> Rs. 14–25+ LPA (Rs. 1.1L–2L+/mo)<br/><br/>",
                    'tip': "Focus on Native iOS/Android or Flutter"
                },
                'game': {
                    'tools': ["Unity / Unreal Editor", "Visual Studio", "Blender", "GitHub", "Rider"],
                    'fallback': "<b>Fresher:</b> Rs. 3–6 LPA (Rs. 25K–45K/mo)<br/><b>Mid:</b> Rs. 6–12 LPA (Rs. 50K–1L/mo)<br/><b>Senior:</b> Rs. 12–22+ LPA (Rs. 1L–1.8L+/mo)<br/><br/>",
                    'tip': "Focus on Engine Mastery + C++/C#"
                },
                'blockchain': {
                    'tools': ["Remix IDE", "Hardhat / Truffle", "Ganache", "Metamask", "VS Code"],
                    'fallback': "<b>Fresher:</b> Rs. 6–10 LPA (Rs. 50K–80K/mo)<br/><b>Mid:</b> Rs. 10–25 LPA (Rs. 80K–2L/mo)<br/><b>Senior:</b> Rs. 25–50+ LPA (Rs. 2L–4L+/mo)<br/><br/>",
                    'tip': "Focus on Smart Contracts + Rust/Solidity"
                },
                'qa': {
                    'tools': ["Selenium", "Postman", "JMeter", "Jira", "Appium"],
                    'fallback': "<b>Fresher:</b> Rs. 3-5 LPA (Rs. 25K-40K/mo)<br/><b>Mid:</b> Rs. 5-10 LPA (Rs. 40K-80K/mo)<br/><b>Senior:</b> Rs. 10-20+ LPA (Rs. 80K-1.6L+/mo)<br/><br/>",
                    'tip': "Focus on Test Automation + Edge Cases"
                },
                'uiux': {
                    'tools': ["Figma", "Adobe XD", "Sketch", "InVision", "Miro"],
                    'fallback': "<b>Fresher:</b> Rs. 3-6 LPA (Rs. 25K-45K/mo)<br/><b>Mid:</b> Rs. 6-12 LPA (Rs. 50K-1L/mo)<br/><b>Senior:</b> Rs. 12-20+ LPA (Rs. 1L-1.6L+/mo)<br/><br/>",
                    'tip': "Focus on User Research + Prototyping"
                }
            }
            
            # Identify the relevant config group
            conf = skill_configs.get('default', {
                'tools': ["VS Code", "Git / GitHub", "Docker", "Postman", "Google Chrome"],
                'fallback': "<b>Fresher:</b> Rs. 3-6 LPA (Rs. 25K-45K/mo)<br/><b>Mid:</b> Rs. 6-12 LPA (Rs. 50K-1L/mo)<br/><b>Senior:</b> Rs. 12-25+ LPA (Rs. 1L-2L+/mo)<br/><br/>",
                'tip': "Focus on Core Concepts + Deep Projects"
            })
            
            for key in skill_configs:
                if key in sq:
                    conf = skill_configs[key]
                    break

            Story.append(Paragraph("Industry Tools", h2_style))
            for t in conf['tools']:
                Story.append(Paragraph(f"• {t}", body_style))
            Story.append(Spacer(1, 0.1 * inch))

            # --- Point 11: Career Opportunities ---
            if 'career' in roadmap_json and roadmap_json['career']:
                Story.append(Paragraph("Career Opportunities", h2_style))
                for item in roadmap_json['career']:
                    if isinstance(item, dict):
                        role = item.get('role') or item.get('topic') or item.get('title') or ''
                        desc = item.get('description') or item.get('desc') or ''
                        if role:
                            safe_role = apply_linkify(role)
                            Story.append(Paragraph(f"<b>• {safe_role}</b>", body_style))
                        if desc:
                            safe_desc = apply_linkify(desc)
                            Story.append(Paragraph(safe_desc, body_style))
                    else:
                        safe_item_c = apply_linkify(item)
                        Story.append(Paragraph(f"• {safe_item_c}", body_style))
                Story.append(Spacer(1, 0.1 * inch))

        # ── Resources ────────────────────────────────────
        has_resources = False
        if 'sections' in roadmap_json and roadmap_json['sections']:
            for s in roadmap_json['sections']:
                if 'Resource' in s.get('title', ''):
                    has_resources = True
                    break
        
        if not has_resources:
            add_section("Resources & Official Docs", "📚")
            resources_html = [
                "Official Documentation: <a href='https://docs.oracle.com/' color='blue'><u>Oracle</u></a> / <a href='https://devdocs.io/' color='blue'><u>DevDocs</u></a>",
                "Core Logic & Syntax: <a href='https://www.w3schools.com/' color='blue'><u>W3Schools</u></a>",
                "Advanced Concepts: <a href='https://www.geeksforgeeks.org/' color='blue'><u>GeeksforGeeks</u></a> / <a href='https://developer.mozilla.org/' color='blue'><u>MDN</u></a>",
                "Interview Prep: <a href='https://leetcode.com/' color='blue'><u>LeetCode</u></a> / <a href='https://www.hackerrank.com/' color='blue'><u>HackerRank</u></a>"
            ]
            res_items = [ListItem(Paragraph(r, bullet_style), bulletColor='#0f3460') for r in resources_html]
            Story.append(ListFlowable(res_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
            Story.append(Spacer(1, 6))

        # ── Final Advice ─────────────────────────────────
        add_section("Final Advice", "✅")
        advice_points = [
            "Practice coding daily (1–2 hrs)",
            "Focus on DSA + core concepts",
            "Build real-world projects",
            "Stay consistent for 3–6 months",
            "Don't just watch tutorials, implement everything"
        ]
        advice_items = [ListItem(Paragraph(a, bullet_style), bulletColor='#0f3460') for a in advice_points]
        Story.append(ListFlowable(advice_items, bulletType='bullet', bulletFontSize=6, bulletOffsetY=-2, start='•'))
        Story.append(Spacer(1, 12))

        doc.build(Story)
        buffer.seek(0)
        
        # Safe filename
        safe_skill = "".join(c for c in skill if c.isalnum() or c in " _-").replace(' ', '_')
        filename = f"{safe_skill}_Career_Guidance.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
    except Exception as e:
        print("PDF Generation Error:", e)
        import traceback
        traceback.print_exc()
        return "PDF generation failed. Please try again.", 500
@app.route('/api/topic_explanation', methods=['POST'])
def topic_explanation():
    data = request.json
    topic = data.get('topic', '')
    
    # Force reload environment to catch immediate .env changes
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return jsonify({"success": False, "error": "GROQ_API_KEY not configured. Please add it to your .env file."}), 500
        
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Explain the topic: {topic}

Provide:

1. Short explanation (3–5 lines)

2. FREE RESOURCES ONLY:

- 2–3 Articles (with title + link)
- 1 Documentation link
- 1 YouTube video

Rules:
- Beginner friendly
- Short and clear
- No long paragraphs
- Real links only (https://...)"""

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful AI tutor. You provide clear, short explanations and always format resources exactly as requested: [Article] Title URL, [Docs] Title URL, [Video] Title URL."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 400
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        response.raise_for_status()
        res_data = response.json()
        ai_text = res_data["choices"][0]["message"]["content"]
        
        return jsonify({"success": True, "content": ai_text})
        
    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        return jsonify({"success": False, "error": f"Groq AI service error: {str(e)}"}), 500

@app.route('/api/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    section = data.get('topic', '')
    subtopics = data.get('subtopics', [])
    
    # Create topic description for AI
    target = f"{section} (focusing on: {', '.join(subtopics)})" if subtopics else section
    
    # --- Try OpenAI First ---
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and not openai_key.startswith('sk-1234'):
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            prompt = f"""Generate a technical quiz for the section '{section}'. 
            The user has specifically completed these sub-topics: {', '.join(subtopics)}.
            Create EXACTLY 5 challenging multiple-choice questions focusing ONLY on these sub-topics.
            
            Format:
            {{
                "questions": [
                    {{
                        "question": "Question text?",
                        "options": ["A", "B", "C", "D"],
                        "correctIndex": 0
                    }},
                    ...
                ]
            }}
            Return ONLY the strict JSON object."""
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                quiz_json = response.json()["choices"][0]["message"]["content"]
                return jsonify({"success": True, "quiz": json.loads(quiz_json), "provider": "openai"})
        except Exception as e:
            print(f"OpenAI Quiz Error: {str(e)}")

    # --- Fallback to Groq ---
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        return jsonify({"success": False, "error": "AI service unavailable."}), 500
        
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        prompt = f"""Generate a 5-question technical quiz for: {target}.
        Focus exclusively on assessment of knowledge for these topics: {', '.join(subtopics)}.
        Format: {{ "questions": [ {{ "question": "...", "options": ["...", "..."], "correctIndex": 0 }} ] }}
        Return ONLY valid JSON."""

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "response_format": {"type": "json_object"}
        }
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        quiz_json = response.json()["choices"][0]["message"]["content"]
        return jsonify({"success": True, "quiz": json.loads(quiz_json), "provider": "groq"})
        
    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        return jsonify({"success": False, "error": "AI provider error."}), 500

@app.route("/redirect")
def redirect_to_resource():
    """Securely redirect to external resources via backend middleman."""
    import urllib.parse
    target_url = request.args.get("url")
    if not target_url:
        return "Invalid Resource URL", 400
    
    try:
        decoded_url = urllib.parse.unquote(target_url)
        return redirect(decoded_url)
    except Exception as e:
        print(f"Redirect Error: {e}")
        return "Failed to redirect to target resource", 500
if __name__ == '__main__':
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
# Force reload for new env config



