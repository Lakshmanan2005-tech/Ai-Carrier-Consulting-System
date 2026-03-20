
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY':
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass

DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Users Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            theme TEXT DEFAULT 'light'
        )
    ''')
    try:
        conn.execute('ALTER TABLE users ADD COLUMN theme TEXT DEFAULT "light"')
    except sqlite3.OperationalError:
        pass
    
    # History Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            skill TEXT NOT NULL,
            viewed_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


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
    if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return jsonify({"error": "Gemini API key not configured."}), 400
        
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'guest':
            session['guest'] = True
            session['name'] = 'Guest'
            return redirect(url_for('dashboard'))
            
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('username')
        auth_mode = request.form.get('auth_mode', 'login')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if auth_mode == 'signup':
            if user:
                conn.close()
                return render_template('login.html', error="Account already registered! Please login.")
            else:
                if not name:
                    name = email.split('@')[0]
                hashed_pw = generate_password_hash(password)
                cur = conn.cursor()
                cur.execute('INSERT INTO users (name, email, password, theme) VALUES (?, ?, ?, ?)', (name, email, hashed_pw, 'light'))
                conn.commit()
                conn.close()
                return render_template('login.html', success="Account successfully created! Please log in.")
                
        else: # login mode
            if user:
                if check_password_hash(user['password'], password):
                    session['guest'] = False
                    session['user_id'] = user['id']
                    session['name'] = user['name']
                    session['email'] = user['email']
                    session['theme'] = user['theme'] if user['theme'] else 'light'
                    conn.close()
                    return redirect(url_for('dashboard'))
                else:
                    conn.close()
                    return render_template('login.html', error="Invalid email or password.")
            else:
                conn.close()
                return render_template('login.html', error="Account does not exist! Please sign up.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if session.get('guest') or 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        current_password = request.form.get('current_password')
        
        if not check_password_hash(user['password'], current_password):
            conn.close()
            return render_template('profile.html', user=user, error="Incorrect current password. Profile not updated.")
            
        try:
            if new_password:
                hashed_pw = generate_password_hash(new_password)
                conn.execute('UPDATE users SET name = ?, email = ?, password = ? WHERE id = ?', (name, email, hashed_pw, session['user_id']))
            else:
                conn.execute('UPDATE users SET name = ?, email = ? WHERE id = ?', (name, email, session['user_id']))
                
            conn.commit()
            session['name'] = name
            session['email'] = email
            
            updated_user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
            
            return render_template('profile.html', user=updated_user, success="Profile updated successfully!")
            
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('profile.html', user=user, error="Email already exists.")
            
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/api/forgot-password/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email', '')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user:
        otp = "944588"
        session['reset_email'] = email
        session['reset_otp'] = otp
        
        sender_email = Config.MAIL_USERNAME
        sender_password = Config.MAIL_PASSWORD
        
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
        conn = get_db_connection()
        conn.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_pw, email))
        conn.commit()
        conn.close()
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        return jsonify({"status": "success", "message": "Password successfully replaced!"})
    return jsonify({"status": "error", "message": "Security session expired."}), 400


@app.route('/roadmap')
def roadmap():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
        
    skill_query = request.args.get('skill', '').strip().lower()
    
    if not skill_query:
        return render_template('roadmap.html', skill_query='', data=None)
    
    matched_key = None
    for key in ROADMAPS.keys():
        if key in skill_query or skill_query in key:
            matched_key = key
            break
            
    if not matched_key:
        for alias, actual in SKILL_ALIASES.items():
            if alias in skill_query or skill_query in alias:
                matched_key = actual
                break
                
    if matched_key:
        roadmap_data = ROADMAPS.get(matched_key).copy()
        roadmap_data['resources'] = RESOURCES_MAP.get(matched_key, [])
        roadmap_data['jobs'] = JOBS_MAP.get(matched_key, [])
        roadmap_data['interview_qs'] = INTERVIEW_MAP.get(matched_key, [])
    else:
        roadmap_data = None
    
    if not roadmap_data:
        if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
            response_text = ""
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""You are an expert career advisor.
Generate a clear and structured learning roadmap for becoming a {skill_query.title()}.

Follow this format strictly:

1. Beginner Level:
- List fundamental skills to start with
2. Intermediate Level:
- List important concepts and tools
3. Advanced Level:
- List advanced topics and specialization areas
4. Tools & Technologies:
- Mention commonly used tools
5. Projects:
- Suggest 2-3 real-world projects
6. Career Opportunities:
- Mention possible job roles

Return the response strictly as a parseable JSON object following this exact schema:
{{
  "sections": [
     {{"title": "Beginner Level", "content": "• Skill 1<br>• Skill 2"}}
  ],
  "resources": [
      {{"name": "Resource Name", "desc": "One line short description", "url": "https://..."}}
  ],
  "jobs": [
      {{"role": "Job Role 1", "desc": "One line short role description."}}
  ],
  "interview_qs": [
      "What is <b>Concept A</b>?"
  ]
}}
Ensure NO literal newlines exist inside strings. Use <br> tags instead. Return ONLY the JSON object, do NOT use markdown ticks."""
                
                response = model.generate_content(prompt)
                ai_text = response.text.replace('```json', '').replace('```', '').strip()
                response_text = ai_text
                ai_data = json.loads(ai_text)
                
                roadmap_data = {
                    "title": skill_query.title(),
                    "is_ai_generated": True,
                    "sections": ai_data.get("sections", []),
                    "resources": ai_data.get("resources", []),
                    "jobs": ai_data.get("jobs", []),
                    "interview_qs": ai_data.get("interview_qs", []),
                    "job_url": f"https://www.naukri.com/{skill_query.replace(' ', '-')}-jobs"
                }
            except Exception as e:
                print(f"Error generating AI roadmap: {str(e)}")
                roadmap_data = {
                    "title": skill_query.title() + " (AI Error)",
                    "is_ai_generated": True,
                    "sections": [{"title": "API Exception", "content": f"Failed to connect or parse: {str(e)}<br><div style='padding: 1rem; background: #eee; color: #333; font-family: monospace; font-size: 0.9em; overflow-x: auto; border-radius: 5px; margin-top: 1rem;'>Raw Text: {response_text.replace('<', '&lt;')}</div>"}],
                    "job_url": "#"
                }

    if roadmap_data and 'user_id' in session and not session.get('guest'):
        conn = get_db_connection()
        conn.execute('INSERT INTO history (username, skill) VALUES (?, ?)', (session['name'], roadmap_data['title']))
        conn.commit()
        conn.close()

    return render_template('roadmap.html', skill_query=request.args.get('skill', ''), data=roadmap_data)

@app.route('/api/suggest', methods=['GET'])
def suggest():
    query = request.args.get('q', '').lower()
    suggestions = []
    if query:
        for sk in ROADMAPS.keys():
            if query in sk:
                suggestions.append(ROADMAPS[sk]['title'])
        for alias, actual in SKILL_ALIASES.items():
            if query in alias and ROADMAPS[actual]['title'] not in suggestions:
                suggestions.append(ROADMAPS[actual]['title'])
    return jsonify(suggestions)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return jsonify({"reply": "Gemini API key not configured."})
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(message)
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return jsonify({"reply": f"Error connecting to AI: {str(e)}"})


@app.route('/interview')
def interview_home():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    return render_template('interview_home.html')

@app.route('/interview_practice')
def interview_practice():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
        
    skill_query = request.args.get('skill', '').strip().lower()
    
    matched_key = None
    for key in ROADMAPS.keys():
        if key in skill_query or skill_query in key:
            matched_key = key
            break
            
    if not matched_key:
        for alias, actual in SKILL_ALIASES.items():
            if alias in skill_query or skill_query in alias:
                matched_key = actual
                break
                
    questions = []
    skill_title = skill_query.title()
    
    if matched_key:
        questions = INTERVIEW_MAP.get(matched_key, [])
        skill_title = ROADMAPS[matched_key]['title']
        
    if not questions and Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"Generate exactly 5 core interview questions for a {skill_title} interview. Return ONLY a JSON array of 5 plain string questions. Example: [\"question 1\", \"question 2\"]"
            response = model.generate_content(prompt)
            questions = json.loads(response.text.replace('```json', '').replace('```', '').strip())
        except Exception:
            pass
            
    return render_template('interview_practice.html', skill_title=skill_title, questions=questions, skill_query=skill_query)

@app.route('/api/evaluate_answer', methods=['POST'])
def evaluate_answer():
    data = request.json
    question = data.get('question', '')
    answer = data.get('answer', '')
    skill = data.get('skill', '')
    
    if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return jsonify({
            "feedback": "Gemini API key not configured. Cannot evaluate mathematically.",
            "correct_answer": "API Key Required",
            "difficulty": "Unknown"
        })
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
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
        
        response = model.generate_content(prompt)
        result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "feedback": f"Error connecting to AI for evaluation.",
            "correct_answer": "Evaluation failed.",
            "difficulty": "Unknown"
        }), 500

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session and not session.get('guest'):
        return redirect(url_for('login'))
    
    name = session.get('name', 'Guest')
    return render_template('index.html', name=name)

@app.route('/update_theme', methods=['POST'])
def update_theme():
    data = request.json
    theme = data.get('theme')
    if theme in ['light', 'dark']:
        session['theme'] = theme
        if 'user_id' in session and not session.get('guest'):
            conn = get_db_connection()
            conn.execute('UPDATE users SET theme = ? WHERE id = ?', (theme, session['user_id']))
            conn.commit()
            conn.close()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/history')
def history():
    is_guest = session.get('guest', False)
    
    if is_guest:
        return render_template('history.html', is_guest=True, history=[])
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    history_db = conn.execute('SELECT skill FROM history WHERE username = ? ORDER BY viewed_time DESC', (session['name'],)).fetchall()
    conn.close()
    
    unique_history = []
    for row in history_db:
        if row['skill'] not in unique_history:
            unique_history.append(row['skill'])
        if len(unique_history) == 5:
            break
            
    return render_template('history.html', is_guest=False, history=unique_history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
