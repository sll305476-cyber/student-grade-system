"""
学生成绩管理系统 v3.0
支持：多角色登录、主题切换、中英双语、顶部导航
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pathlib import Path
import io
import json
import hashlib
from datetime import datetime

st.set_page_config(page_title="Student Grade Management", page_icon="🎓", layout="wide")

DB_PATH = Path(__file__).parent / "data" / "student_management.db"
LOG_PATH = Path(__file__).parent / "data" / "logs"
LOG_FILE = LOG_PATH / "app.log"

DEFAULT_COURSES = [
    ("C语言程序设计", 2.0),
    ("C语言程序设计实验", 1.0),
    ("现代测量学", 2.0),
    ("现代测量学实验", 1.0),
    ("地理信息系统概论", 2.5),
    ("地图学", 2.0),
    ("遥感概论", 2.5),
    ("数字测图实习", 1.5),
]

DEFAULT_MAJORS = [
    ("地理信息科学", "张老师", "李主任"),
    ("遥感科学与技术", "王老师", "刘主任"),
    ("测绘工程", "赵老师", "陈主任"),
]

DEFAULT_CLASSES = [
    ("地信2401", "地理信息科学"),
    ("地信2402", "地理信息科学"),
    ("遥感2401", "遥感科学与技术"),
    ("测绘2401", "测绘工程"),
]

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            head_teacher TEXT,
            department_head TEXT
        );
        
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            major_id INTEGER,
            FOREIGN KEY (major_id) REFERENCES majors(id)
        );
        
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            class_id INTEGER,
            gender TEXT,
            birth_date TEXT,
            enrollment_date TEXT,
            hometown TEXT,
            phone TEXT,
            email TEXT,
            photo BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        );
        
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            student_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        );
        
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT UNIQUE NOT NULL,
            credit REAL NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS teacher_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            course_id INTEGER,
            class_id INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        );
        
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            score REAL NOT NULL,
            semester TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            UNIQUE(student_id, course_id, semester)
        );
        
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    try:
        cursor.execute("SELECT class_name FROM students LIMIT 1")
        has_class_name = True
    except:
        has_class_name = False
    
    if has_class_name:
        cursor.execute("SELECT DISTINCT class_name FROM students WHERE class_name IS NOT NULL AND class_name != ''")
        existing_classes = [row[0] for row in cursor.fetchall()]
        
        for cls_name in existing_classes:
            major_name = "地理信息科学"
            cursor.execute("SELECT id FROM majors WHERE name = ?", (major_name,))
            major = cursor.fetchone()
            if major:
                cursor.execute("INSERT OR IGNORE INTO classes (name, major_id) VALUES (?, ?)", (cls_name, major[0]))
        
        cursor.execute("SELECT id, class_name FROM students WHERE class_name IS NOT NULL AND class_name != ''")
        for student_id, class_name in cursor.fetchall():
            cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
            cls = cursor.fetchone()
            if cls:
                cursor.execute("UPDATE students SET class_id = ? WHERE class_name = ?", (cls[0], class_name))
        
        try:
            cursor.execute("ALTER TABLE students DROP COLUMN class_name")
        except:
            pass
    
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN enrollment_date TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN hometown TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN phone TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN email TEXT")
    except:
        pass
    
    for name, credit in DEFAULT_COURSES:
        cursor.execute("INSERT OR IGNORE INTO courses (course_name, credit) VALUES (?, ?)", (name, credit))
    
    for name, head, dept in DEFAULT_MAJORS:
        cursor.execute("INSERT OR IGNORE INTO majors (name, head_teacher, department_head) VALUES (?, ?, ?)", (name, head, dept))
    
    for cls_name, major_name in DEFAULT_CLASSES:
        cursor.execute("SELECT id FROM majors WHERE name = ?", (major_name,))
        major = cursor.fetchone()
        if major:
            cursor.execute("INSERT OR IGNORE INTO classes (name, major_id) VALUES (?, ?)", (cls_name, major[0]))
    
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
            ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "admin"))
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def log_action(username, action, detail=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (username, action, detail) VALUES (?, ?, ?)", 
            (username, action, detail))
        conn.commit()
        conn.close()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {username}: {action} - {detail}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except:
        pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute("SELECT id, username, role, student_id FROM users WHERE username = ? AND password = ?", 
        (username, password_hash))
    user = cursor.fetchone()
    conn.close()
    return user

def get_student_info(student_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, c.name as class_name, m.name as major_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN majors m ON c.major_id = m.id
            WHERE s.student_id = ?
        """, (student_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        return None

def get_user_students(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()
    
    if role == "admin":
        df = pd.read_sql("""
            SELECT s.student_id, s.name, c.name as class_name, m.name as major_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN majors m ON c.major_id = m.id
            ORDER BY c.name, s.student_id
        """, conn)
    elif role == "teacher":
        cursor.execute("""
            SELECT DISTINCT s.student_id, s.name, c.name as class_name, m.name as major_name
            FROM students s
            JOIN classes c ON s.class_id = c.id
            JOIN teacher_courses tc ON tc.class_id = c.id
            LEFT JOIN majors m ON c.major_id = m.id
            WHERE tc.teacher_id = ?
        """, (user_id,))
        df = pd.DataFrame(cursor.fetchall(), columns=['student_id', 'name', 'class_name', 'major_name'])
    else:
        df = pd.DataFrame(columns=['student_id', 'name', 'class_name', 'major_name'])
    
    conn.close()
    return df

def get_translations():
    return {
        "zh": {
            "title": "学生成绩管理系统",
            "dashboard": "数据概览",
            "students": "学生管理",
            "scores": "成绩管理",
            "statistics": "统计分析",
            "profile": "个人信息",
            "settings": "设置",
            "logout": "退出登录",
            "login": "登录",
            "username": "用户名",
            "password": "密码",
            "login_btn": "登录",
            "total_students": "学生总数",
            "avg_score": "平均分",
            "pass_rate": "及格率",
            "course_count": "课程数量",
            "student_list": "学生列表",
            "add_student": "添加学生",
            "search": "搜索",
            "import_export": "导入/导出",
            "score_list": "成绩列表",
            "add_score": "录入成绩",
            "ranking": "学生排名",
            "course_stats": "课程统计",
            "detailed_analysis": "详细分析",
            "name": "姓名",
            "gender": "性别",
            "major": "专业",
            "class": "班级",
            "student_id": "学号",
            "enrollment_date": "入学日期",
            "hometown": "籍贯",
            "phone": "电话号码",
            "email": "邮箱",
            "score": "成绩",
            "credit": "学分",
            "semester": "学期",
            "theme": "主题",
            "blue_white": "蓝白",
            "green_white": "绿白",
            "dark": "灰黑",
            "language": "语言",
            "chinese": "中文",
            "english": "English",
            "welcome": "欢迎",
            "student_profile": "学生简历",
            "no_data": "暂无数据",
            "admin": "管理员",
            "teacher": "教师",
            "student": "学生",
        },
        "en": {
            "title": "Student Grade Management",
            "dashboard": "Dashboard",
            "students": "Students",
            "scores": "Scores",
            "statistics": "Statistics",
            "profile": "Profile",
            "settings": "Settings",
            "logout": "Logout",
            "login": "Login",
            "username": "Username",
            "password": "Password",
            "login_btn": "Login",
            "total_students": "Total Students",
            "avg_score": "Average Score",
            "pass_rate": "Pass Rate",
            "course_count": "Courses",
            "student_list": "Student List",
            "add_student": "Add Student",
            "search": "Search",
            "import_export": "Import/Export",
            "score_list": "Score List",
            "add_score": "Add Score",
            "ranking": "Ranking",
            "course_stats": "Course Stats",
            "detailed_analysis": "Analysis",
            "name": "Name",
            "gender": "Gender",
            "major": "Major",
            "class": "Class",
            "student_id": "Student ID",
            "enrollment_date": "Enrollment Date",
            "hometown": "Hometown",
            "phone": "Phone",
            "email": "Email",
            "score": "Score",
            "credit": "Credit",
            "semester": "Semester",
            "theme": "Theme",
            "blue_white": "Blue/White",
            "green_white": "Green/White",
            "dark": "Dark",
            "language": "Language",
            "chinese": "中文",
            "english": "English",
            "welcome": "Welcome",
            "student_profile": "Student Profile",
            "no_data": "No Data",
            "admin": "Admin",
            "teacher": "Teacher",
            "student": "Student",
        }
    }

def get_theme_css(theme):
    themes = {
        "blue_white": {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "bg": "#f5f7fa",
            "card_bg": "#ffffff",
            "text": "#2c3e50",
            "text_secondary": "#7f8c8d",
        },
        "green_white": {
            "primary": "#11998e",
            "secondary": "#38ef7d",
            "bg": "#f0f9f5",
            "card_bg": "#ffffff",
            "text": "#1a3a2a",
            "text_secondary": "#5a8a70",
        },
        "dark": {
            "primary": "#4a5568",
            "secondary": "#718096",
            "bg": "#1a202c",
            "card_bg": "#2d3748",
            "text": "#e2e8f0",
            "text_secondary": "#a0aec0",
        }
    }
    t = themes.get(theme, themes["blue_white"])
    return f"""
        <style>
        .stApp {{
            background: {t['bg']};
            color: {t['text']};
        }}
        .metric-card {{
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%);
            padding: 25px;
            border-radius: 20px;
            text-align: center;
            color: white;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        .stButton > button {{
            border-radius: 12px;
        }}
        .title-text {{
            font-weight: 700;
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2rem;
        }}
        .sidebar-title {{
            font-weight: 600;
            color: {t['primary']};
            font-size: 1.3rem;
        }}
        .profile-card {{
            background: {t['card_bg']};
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        .nav-tab {{
            padding: 12px 24px;
            background: {t['card_bg']};
            border-radius: 10px;
            margin: 0 5px;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        .nav-tab:hover {{
            background: {t['primary']};
            color: white;
        }}
        .nav-tab.active {{
            background: {t['primary']};
            color: white;
        }}
        </style>
    """

def page_login(t, lang):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 class='title-text' style='text-align:center;'>{t['title']}</h1>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["Login", "Student Registration"])
        
        with tab_login:
            with st.form("login_form"):
                username = st.text_input(t["username"])
                password = st.text_input(t["password"], type="password")
                submitted = st.form_submit_button(t["login_btn"])
                
                if submitted:
                    if username and password:
                        user = check_login(username, password)
                        if user:
                            st.session_state["logged_in"] = True
                            st.session_state["user_id"] = user[0]
                            st.session_state["username"] = user[1]
                            st.session_state["role"] = user[2]
                            st.session_state["student_id"] = user[3]
                            log_action(username, "LOGIN", f"Role: {user[2]}")
                            st.rerun()
                        else:
                            st.error(t["username"] + " or " + t["password"] + " error")
                    else:
                        st.warning("Please fill in all fields")
            
            st.markdown("---")
            st.markdown("### Default Accounts")
            st.code("Admin: admin / admin123\nTeacher: teacher / teacher123")
        
        with tab_register:
            st.markdown("### Student Self-Registration")
            st.info("Students can register using their student ID that exists in the system.")
            
            with st.form("register_form"):
                reg_student_id = st.text_input("Student ID (学号)", key="reg_sid")
                reg_username = st.text_input("Username (用户名)", key="reg_user")
                reg_password = st.text_input("Password (密码)", type="password", key="reg_pass")
                reg_password2 = st.text_input("Confirm Password (确认密码)", type="password", key="reg_pass2")
                
                reg_submit = st.form_submit_button("Register (注册)")
                
                if reg_submit:
                    if not reg_student_id or not reg_username or not reg_password:
                        st.warning("Please fill in all fields")
                    elif reg_password != reg_password2:
                        st.error("Passwords do not match")
                    elif len(reg_password) < 6:
                        st.warning("Password must be at least 6 characters")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute("SELECT id, name FROM students WHERE student_id = ?", (reg_student_id,))
                        student = cursor.fetchone()
                        
                        if not student:
                            st.error("Student ID not found in system. Please contact administrator.")
                        else:
                            cursor.execute("SELECT id FROM users WHERE username = ?", (reg_username,))
                            if cursor.fetchone():
                                st.error("Username already exists")
                            else:
                                cursor.execute("SELECT id FROM users WHERE student_id = ?", (reg_student_id,))
                                if cursor.fetchone():
                                    st.error("Account already exists for this student ID")
                                else:
                                    password_hash = hash_password(reg_password)
                                    cursor.execute("""
                                        INSERT INTO users (username, password, role, student_id)
                                        VALUES (?, ?, 'student', ?)
                                    """, (reg_username, password_hash, reg_student_id))
                                    conn.commit()
                                    st.success(f"Registration successful! Welcome, {student[1]}!")
                                    log_action(reg_username, "SELF_REGISTER", f"Student ID: {reg_student_id}")
                        
                        conn.close()

def page_dashboard(t, role, student_id=None):
    st.markdown(f"<h2 class='title-text'>{t['dashboard']}</h2>", unsafe_allow_html=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if role == "student":
        cursor.execute("SELECT COUNT(*) FROM scores WHERE student_id = ?", (student_id,))
        score_count = cursor.fetchone()[0] or 0
        
        if score_count > 0:
            cursor.execute("""
                SELECT AVG(score), MAX(score),
                       COUNT(CASE WHEN score >= 60 THEN 1 END) * 100.0 / COUNT(*)
                FROM scores WHERE student_id = ?
            """, (student_id,))
            row = cursor.fetchone()
            avg_score = round(row[0], 1) if row[0] else 0
            max_score = row[1] or 0
            pass_rate = round(row[2], 1) if row[2] else 0
        else:
            avg_score = max_score = pass_rate = 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t["avg_score"], avg_score)
        with col2:
            st.metric("Max Score", max_score)
        with col3:
            st.metric(t["pass_rate"], f"{pass_rate}%")
        
        if score_count > 0:
            df_scores = pd.read_sql("""
                SELECT c.course_name as Course, s.score as Score, c.credit as Credit
                FROM scores s JOIN courses c ON s.course_id = c.id
                WHERE s.student_id = ?
            """, conn, params=(student_id,))
            
            fig = px.bar(df_scores, x='Course', y='Score', 
                        title="My Scores", color='Score',
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
        return
    
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT AVG(score), MAX(score),
               COUNT(CASE WHEN score >= 60 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)
        FROM scores
    """)
    row = cursor.fetchone()
    avg_score = round(row[0], 1) if row[0] else 0
    max_score = row[1] or 0
    pass_rate = round(row[2], 1) if row[2] else 0
    
    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0] or 0
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t["total_students"], total_students)
    with col2:
        st.metric(t["avg_score"], avg_score)
    with col3:
        st.metric(t["pass_rate"], f"{pass_rate}%")
    with col4:
        st.metric(t["course_count"], course_count)
    
    st.markdown("### Score Distribution")
    
    conn = get_connection()
    df_scores = pd.read_sql("SELECT score FROM scores", conn)
    conn.close()
    
    if not df_scores.empty:
        bins = [0, 60, 70, 80, 90, 100]
        labels = ['Fail', 'Pass', 'Medium', 'Good', 'Excellent']
        df_scores['Grade'] = pd.cut(df_scores['score'], bins=bins, labels=labels, right=False)
        dist = df_scores['Grade'].value_counts().reindex(labels, fill_value=0)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_bar = px.bar(x=labels, y=dist.values, labels={'x': 'Grade', 'y': 'Count'},
                           title="Grade Distribution", color=dist.values)
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(values=dist.values, names=labels, title="Grade Ratio")
            st.plotly_chart(fig_pie, use_container_width=True)

def page_profile(t, role, student_id=None):
    st.markdown(f"<h2 class='title-text'>{t['profile']}</h2>", unsafe_allow_html=True)
    
    if role == "student" and student_id:
        info = get_student_info(student_id)
        if info:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown("### Photo")
                if info[9]:
                    st.image(info[9], width=200)
                else:
                    st.info("No photo")
            
            with col2:
                st.markdown(f"""
                <div class="profile-card">
                    <h3>{info[2]}</h3>
                    <p><strong>{t['student_id']}:</strong> {info[1]}</p>
                    <p><strong>{t['gender']}:</strong> {info[4] or '-'}</p>
                    <p><strong>{t['major']}:</strong> {info[12] or '-'}</p>
                    <p><strong>{t['class']}:</strong> {info[11] or '-'}</p>
                    <p><strong>{t['enrollment_date']}:</strong> {info[6] or '-'}</p>
                    <p><strong>{t['hometown']}:</strong> {info[7] or '-'}</p>
                    <p><strong>{t['phone']}:</strong> {info[8] or '-'}</p>
                    <p><strong>{t['email']}:</strong> {info[10] or '-'}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No profile data. Please contact administrator.")
    else:
        st.info(t["no_data"])

def page_students(t, role, user_id):
    st.markdown(f"<h2 class='title-text'>{t['students']}</h2>", unsafe_allow_html=True)
    
    if role == "student":
        st.warning("Access denied")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    col1, col2 = st.columns([4, 1])
    with col1:
        search = st.text_input("Search student by name or ID", placeholder="Enter name or student ID")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        import_btn = st.button("Import Students", use_container_width=True)
    
    if import_btn:
        st.session_state["show_import"] = True
    
    if st.session_state.get("show_import", False):
        with st.expander("Import Students from Excel", expanded=True):
            uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], key="student_import")
            
            if uploaded_file:
                if st.button("Start Import"):
                    try:
                        df = pd.read_excel(uploaded_file)
                        imported = 0
                        for _, row in df.iterrows():
                            try:
                                student_id = str(row.get('学号', '')).strip()
                                name = str(row.get('姓名', '')).strip()
                                class_name = str(row.get('班级', '')).strip()
                                gender = str(row.get('性别', '')).strip()
                                
                                if student_id and student_id != 'nan':
                                    cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
                                    cls = cursor.fetchone()
                                    class_id = cls[0] if cls else None
                                    
                                    cursor.execute("""
                                        INSERT OR IGNORE INTO students (student_id, name, class_id, gender)
                                        VALUES (?, ?, ?, ?)
                                    """, (student_id, name, class_id, gender))
                                    if cursor.rowcount > 0:
                                        imported += 1
                            except:
                                pass
                        
                        conn.commit()
                        st.success(f"Successfully imported {imported} students!")
                        log_action(st.session_state.get("username", "system"), "IMPORT", f"Count: {imported}")
                        st.session_state["show_import"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Import failed: {str(e)}")
    
    if role == "admin":
        query = """
            SELECT s.student_id, s.name, c.name as class_name, m.name as major_name, s.gender
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN majors m ON c.major_id = m.id
        """
        if search:
            query += f" WHERE s.name LIKE '%{search}%' OR s.student_id LIKE '%{search}%'"
        query += " ORDER BY c.name, s.student_id"
        
        df = pd.read_sql(query, conn)
    else:
        df = get_user_students(user_id, role)
        if search:
            df = df[df['name'].str.contains(search, na=False) | df['student_id'].str.contains(search, na=False)]
    
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    
    st.markdown("### Student Details")
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            selected = st.selectbox("Select student to view details", df['name'].tolist())
        with col2:
            if st.button("View Analysis"):
                st.session_state["view_student"] = selected
                st.session_state["show_analysis"] = True
        
        if st.session_state.get("show_analysis") and st.session_state.get("view_student"):
            student_name = st.session_state["view_student"]
            student_row = df[df['name'] == student_name].iloc[0]
            show_student_analysis(t, conn, student_row['student_id'], student_name)
    
    conn.close()

def show_student_analysis(t, conn, student_id, student_name):
    st.markdown(f"### {student_name} Score Analysis")
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.course_name, s.score, c.credit, s.semester
        FROM scores s
        JOIN courses c ON s.course_id = c.id
        WHERE s.student_id = ?
        ORDER BY s.semester, c.course_name
    """, (student_id,))
    
    scores = cursor.fetchall()
    
    if not scores:
        st.info("No score data available")
        return
    
    df_scores = pd.DataFrame(scores, columns=['Course', 'Score', 'Credit', 'Semester'])
    
    col1, col2, col3, col4 = st.columns(4)
    avg_score = df_scores['Score'].mean()
    max_score = df_scores['Score'].max()
    min_score = df_scores['Score'].min()
    pass_rate = (df_scores['Score'] >= 60).sum() / len(df_scores) * 100
    
    col1.metric("Average", f"{avg_score:.1f}")
    col2.metric("Highest", f"{max_score:.1f}")
    col3.metric("Lowest", f"{min_score:.1f}")
    col4.metric("Pass Rate", f"{pass_rate:.1f}%")
    
    tab1, tab2, tab3 = st.tabs(["Score Chart", "Course Analysis", "Trend"])
    
    with tab1:
        fig = px.bar(df_scores, x='Course', y='Score', title="Score by Course",
                    color='Score', color_continuous_scale='RdYlGn')
        fig.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        df_scores['Status'] = df_scores['Score'].apply(
            lambda x: 'Excellent' if x >= 90 else 'Good' if x >= 80 else 'Pass' if x >= 60 else 'Fail'
        )
        status_counts = df_scores['Status'].value_counts()
        
        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(values=status_counts.values, names=status_counts.index, 
                           title="Grade Distribution", color=status_counts.index,
                           color_discrete_map={'Excellent': '#2ecc71', 'Good': '#3498db', 
                                             'Pass': '#f1c40f', 'Fail': '#e74c3c'})
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            df_scores['Weighted'] = df_scores['Score'] * df_scores['Credit']
            total_weighted = df_scores['Weighted'].sum()
            total_credit = df_scores['Credit'].sum()
            weighted_avg = total_weighted / total_credit if total_credit > 0 else 0
            st.metric("Weighted Average", f"{weighted_avg:.1f}")
            
            st.markdown("#### Course Details")
            st.dataframe(df_scores[['Course', 'Score', 'Credit', 'Status']], hide_index=True)
    
    with tab3:
        semesters = df_scores['Semester'].unique()
        if len(semesters) > 1:
            semester_scores = df_scores.groupby('Semester')['Score'].mean()
            fig_trend = px.line(x=semester_scores.index, y=semester_scores.values, 
                               title="Score Trend by Semester", markers=True)
            fig_trend.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Need multiple semesters for trend analysis")

def page_scores(t, role, user_id, student_id=None):
    st.markdown(f"<h2 class='title-text'>{t['scores']}</h2>", unsafe_allow_html=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if role == "student" and student_id:
        df_scores = pd.read_sql("""
            SELECT c.course_name as Course, s.score as Score, c.credit as Credit, s.semester as Semester
            FROM scores s JOIN courses c ON s.course_id = c.id
            WHERE s.student_id = ?
            ORDER BY s.semester, c.course_name
        """, conn, params=(student_id,))
        
        if not df_scores.empty:
            st.dataframe(df_scores, use_container_width=True, hide_index=True)
            
            avg = df_scores['Score'].mean()
            total_credit = df_scores['Credit'].sum()
            weighted = sum(df_scores['Score'] * df_scores['Credit']) / total_credit if total_credit > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Average", f"{avg:.1f}")
            c2.metric("Total Credits", f"{total_credit:.1f}")
            c3.metric("Weighted Avg", f"{weighted:.1f}")
        else:
            st.info(t["no_data"])
    else:
        df_students = pd.read_sql("SELECT student_id, name FROM students ORDER BY name", conn)
        if not df_students.empty:
            selected = st.selectbox("Select Student", df_students['name'].tolist())
            student_id = df_students[df_students['name'] == selected]['student_id'].iloc[0]
            
            df_scores = pd.read_sql("""
                SELECT c.course_name as Course, s.score as Score, c.credit as Credit, s.semester as Semester
                FROM scores s JOIN courses c ON s.course_id = c.id
                WHERE s.student_id = ?
                ORDER BY c.course_name
            """, conn, params=(student_id,))
            
            st.dataframe(df_scores, use_container_width=True, hide_index=True)
            
            if role == "admin":
                st.markdown("### Add Score")
                with st.form("add_score_form"):
                    cursor.execute("SELECT id, course_name FROM courses")
                    courses = cursor.fetchall()
                    course = st.selectbox("Course", [c[1] for c in courses])
                    score = st.number_input("Score", 0, 100, 0)
                    semester = st.text_input("Semester", "2025-1")
                    
                    if st.form_submit_button("Add"):
                        course_id = next(c[0] for c in courses if c[1] == course)
                        try:
                            cursor.execute("INSERT INTO scores (student_id, course_id, score, semester) VALUES (?, ?, ?, ?)",
                                (student_id, course_id, score, semester))
                            conn.commit()
                            st.success("Score added!")
                            log_action(st.session_state.get("username", "system"), "ADD_SCORE", f"Student: {student_id}, Course: {course}")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Score already exists")
    
    conn.close()

def page_statistics(t, role, user_id):
    st.markdown(f"<h2 class='title-text'>{t['statistics']}</h2>", unsafe_allow_html=True)
    
    if role == "student":
        st.warning("Access denied")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    tab1, tab2, tab3, tab4 = st.tabs([t["ranking"], t["course_stats"], "Class Comparison", "Advanced Analysis"])
    
    with tab1:
        sort_option = st.radio("Sort by", ["Total Score", "Average Score", "Weighted Average"], horizontal=True)
        
        if sort_option == "Total Score":
            order = "TotalScore DESC"
        elif sort_option == "Average Score":
            order = "AvgScore DESC"
        else:
            order = "WeightedAvg DESC"
        
        df = pd.read_sql(f"""
            SELECT s.student_id, s.name, c.name as class_name,
                   SUM(sc.score) as TotalScore, ROUND(AVG(sc.score), 1) as AvgScore,
                   ROUND(SUM(sc.score * c2.credit) / SUM(c2.credit), 1) as WeightedAvg
            FROM students s
            LEFT JOIN scores sc ON s.student_id = sc.student_id
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN courses c2 ON sc.course_id = c2.id
            GROUP BY s.student_id
            HAVING TotalScore IS NOT NULL
            ORDER BY {order}
            LIMIT 50
        """, conn)
        
        if not df.empty:
            df.insert(0, 'Rank', range(1, len(df) + 1))
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df.head(10), x='name', y='TotalScore', title="Top 10 by Total Score",
                            color='TotalScore', color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = px.bar(df.head(10), x='name', y='AvgScore', title="Top 10 by Average",
                            color='AvgScore', color_continuous_scale='RdYlGn')
                st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        df_course = pd.read_sql("""
            SELECT c.course_name as Course, c.credit as Credit,
                   COUNT(sc.id) as Count, ROUND(AVG(sc.score), 1) as AvgScore,
                   ROUND(MAX(sc.score), 1) as MaxScore,
                   ROUND(MIN(sc.score), 1) as MinScore,
                   ROUND(SUM(CASE WHEN sc.score >= 60 THEN 1 END) * 100.0 / COUNT(sc.score), 1) as PassRate
            FROM courses c
            LEFT JOIN scores sc ON c.id = sc.course_id
            GROUP BY c.id
            ORDER BY Count DESC
        """, conn)
        
        if not df_course.empty:
            st.dataframe(df_course, use_container_width=True, hide_index=True)
            
            fig = px.bar(df_course, x='Course', y='AvgScore', title="Average Score by Course",
                        color='AvgScore', color_continuous_scale='RdYlGn', range_y=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Class Comparison")
        
        df_classes = pd.read_sql("""
            SELECT c.name as Class,
                   COUNT(DISTINCT s.id) as Students,
                   ROUND(AVG(sc.score), 1) as AvgScore,
                   ROUND(SUM(CASE WHEN sc.score >= 60 THEN 1 END) * 100.0 / COUNT(sc.score), 1) as PassRate
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id
            LEFT JOIN scores sc ON s.student_id = sc.student_id
            GROUP BY c.id
            HAVING Students > 0
            ORDER BY AvgScore DESC
        """, conn)
        
        if not df_classes.empty:
            st.dataframe(df_classes, use_container_width=True, hide_index=True)
            
            fig = px.bar(df_classes, x='Class', y='AvgScore', title="Class Average Comparison",
                        color='AvgScore', color_continuous_scale='RdYlGn', range_y=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Student Comparison")
        
        col1, col2 = st.columns(2)
        with col1:
            df_all_students = pd.read_sql("""
                SELECT s.name FROM students s ORDER BY s.name
            """, conn)
            student1 = st.selectbox("Select Student 1", df_all_students['name'].tolist())
        with col2:
            df_all_students2 = pd.read_sql("""
                SELECT s.name FROM students s ORDER BY s.name
            """, conn)
            student2 = st.selectbox("Select Student 2", df_all_students2['name'].tolist())
        
        if student1 and student2:
            df_compare = pd.read_sql(f"""
                SELECT s.name, c.course_name, sc.score
                FROM scores sc
                JOIN students s ON sc.student_id = s.student_id
                JOIN courses c ON sc.course_id = c.id
                WHERE s.name IN ('{student1}', '{student2}')
                ORDER BY c.course_name
            """, conn)
            
            if not df_compare.empty:
                pivot = df_compare.pivot(index='course_name', columns='name', values='score').reset_index()
                pivot.columns.name = None
                st.dataframe(pivot, use_container_width=True, hide_index=True)
                
                fig = px.bar(pivot, x='course_name', y=[student1, student2], 
                           title=f"{student1} vs {student2}", barmode='group')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.markdown("### Advanced Analysis")
        
        st.markdown("#### Score Distribution")
        df_all_scores = pd.read_sql("SELECT score FROM scores", conn)
        
        if not df_all_scores.empty:
            fig = px.histogram(df_all_scores, x="score", nbins=10, title="Score Distribution",
                             color_discrete_sequence=['#667eea'])
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Performance Warning")
        df_warning = pd.read_sql("""
            SELECT s.name, c.name as class_name, ROUND(AVG(sc.score), 1) as AvgScore
            FROM students s
            LEFT JOIN scores sc ON s.student_id = sc.student_id
            LEFT JOIN classes c ON s.class_id = c.id
            GROUP BY s.student_id
            HAVING AvgScore IS NOT NULL AND AvgScore < 60
        """, conn)
        
        if not df_warning.empty:
            st.error(f"Found {len(df_warning)} students with failing average!")
            st.dataframe(df_warning, use_container_width=True, hide_index=True)
        else:
            st.success("No students with failing average!")
        
        st.markdown("#### Top Performers")
        df_top = pd.read_sql("""
            SELECT s.name, c.name as class_name, ROUND(AVG(sc.score), 1) as AvgScore
            FROM students s
            LEFT JOIN scores sc ON s.student_id = sc.student_id
            LEFT JOIN classes c ON s.class_id = c.id
            GROUP BY s.student_id
            HAVING AvgScore >= 90
            ORDER BY AvgScore DESC
            LIMIT 10
        """, conn)
        
        if not df_top.empty:
            st.success(f"Found {len(df_top)} top performers (avg >= 90)!")
            st.dataframe(df_top, use_container_width=True, hide_index=True)
    
    conn.close()

def page_settings(t, role):
    st.markdown(f"<h2 class='title-text'>{t['settings']}</h2>", unsafe_allow_html=True)
    
    if role != "admin":
        st.warning("Access denied. Admin only.")
        return
    
    tab1, tab2, tab3 = st.tabs(["Create Student Account", "User Management", "System Info"])
    
    with tab1:
        st.markdown("### Create Student Account (Admin)")
        st.info("Manually create a student account for a student in the system.")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        df_students = pd.read_sql("""
            SELECT s.student_id, s.name, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            ORDER BY s.student_id
        """, conn)
        
        with st.form("admin_create_account"):
            selected_student = st.selectbox(
                "Select Student",
                df_students['name'].tolist() if not df_students.empty else []
            )
            
            new_username = st.text_input("Username (用户名)")
            new_password = st.text_input("Password (密码)", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Create Account"):
                if not selected_student or not new_username or not new_password:
                    st.warning("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.warning("Password must be at least 6 characters")
                else:
                    student_id = df_students[df_students['name'] == selected_student]['student_id'].iloc[0]
                    
                    cursor.execute("SELECT id FROM users WHERE username = ?", (new_username,))
                    if cursor.fetchone():
                        st.error("Username already exists")
                    else:
                        cursor.execute("SELECT id FROM users WHERE student_id = ?", (student_id,))
                        if cursor.fetchone():
                            st.error("Account already exists for this student")
                        else:
                            password_hash = hash_password(new_password)
                            cursor.execute("""
                                INSERT INTO users (username, password, role, student_id)
                                VALUES (?, ?, 'student', ?)
                            """, (new_username, password_hash, student_id))
                            conn.commit()
                            st.success(f"Account created for {selected_student}!")
                            log_action(st.session_state["username"], "CREATE_ACCOUNT", f"Student: {selected_student}, Username: {new_username}")
        
        conn.close()
    
    with tab2:
        st.markdown("### User Management")
        
        conn = get_connection()
        df_users = pd.read_sql("""
            SELECT u.id, u.username, u.role, u.student_id, s.name as student_name, u.created_at
            FROM users u
            LEFT JOIN students s ON u.student_id = s.student_id
            ORDER BY u.id
        """, conn)
        
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("#### Delete User")
        user_options = [f"{row['username']} ({row['role']})" for _, row in df_users.iterrows()]
        user_to_delete = st.selectbox("Select user to delete", user_options)
        
        if st.button("Delete User"):
            username = user_to_delete.split(" (")[0]
            if username == "admin":
                st.error("Cannot delete admin account")
            else:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                st.success(f"User {username} deleted!")
                log_action(st.session_state["username"], "DELETE_USER", username)
                st.rerun()
        
        conn.close()
    
    with tab3:
        st.markdown("### System Information")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scores")
        score_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]
        
        st.metric("Total Students", student_count)
        st.metric("Total Users", user_count)
        st.metric("Total Scores", score_count)
        st.metric("Total Courses", course_count)
        
        st.markdown("---")
        st.markdown("### Import Data")
        st.info("Upload Excel file to import student data")
        
        uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'])
        
        if uploaded_file:
            if st.button("Import Students"):
                try:
                    df = pd.read_excel(uploaded_file)
                    imported = 0
                    for _, row in df.iterrows():
                        try:
                            student_id = str(row.get('学号', '')).strip()
                            name = str(row.get('姓名', '')).strip()
                            class_name = str(row.get('班级', '')).strip()
                            gender = str(row.get('性别', '')).strip()
                            
                            if student_id and student_id != 'nan':
                                cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
                                cls = cursor.fetchone()
                                class_id = cls[0] if cls else None
                                
                                cursor.execute("""
                                    INSERT OR IGNORE INTO students (student_id, name, class_id, gender)
                                    VALUES (?, ?, ?, ?)
                                """, (student_id, name, class_id, gender))
                                if cursor.rowcount > 0:
                                    imported += 1
                        except:
                            pass
                    
                    conn.commit()
                    st.success(f"Successfully imported {imported} students!")
                    log_action(st.session_state["username"], "IMPORT_STUDENTS", f"Count: {imported}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {str(e)}")
        
        st.markdown("#### Database Logs")
        try:
            df_logs = pd.read_sql("""
                SELECT username, action, detail, created_at
                FROM logs
                ORDER BY created_at DESC
                LIMIT 20
            """, conn)
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        except:
            st.info("No logs available")
        
        conn.close()

def main():
    init_db()
    
    if "theme" not in st.session_state:
        st.session_state["theme"] = "blue_white"
    if "lang" not in st.session_state:
        st.session_state["lang"] = "zh"
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    t = get_translations()[st.session_state["lang"]]
    theme = st.session_state["theme"]
    
    st.markdown(get_theme_css(theme), unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"<p class='sidebar-title'>🎓 {t['title']}</p>", unsafe_allow_html=True)
        
        if st.session_state["logged_in"]:
            st.markdown(f"### {t['welcome']}, {st.session_state['username']}")
            st.markdown(f"Role: {st.session_state['role']}")
            
            col1, col2 = st.columns(2)
            with col1:
                theme_btn = st.button(f"🎨 {t['theme']}")
            with col2:
                lang_btn = st.button(f"🌐 {t['language']}")
            
            if theme_btn:
                themes = ["blue_white", "green_white", "dark"]
                current = themes.index(theme)
                st.session_state["theme"] = themes[(current + 1) % 3]
                st.rerun()
            
            if lang_btn:
                st.session_state["lang"] = "en" if st.session_state["lang"] == "zh" else "zh"
                st.rerun()
            
            if st.button(f"🚪 {t['logout']}"):
                log_action(st.session_state["username"], "LOGOUT", "")
                st.session_state["logged_in"] = False
                st.rerun()
    
    if not st.session_state["logged_in"]:
        page_login(t, st.session_state["lang"])
        return
    
    role = st.session_state["role"]
    user_id = st.session_state["user_id"]
    student_id = st.session_state.get("student_id")
    
    menu_items = [t["dashboard"], t["profile"], t["students"], t["scores"], t["statistics"]]
    if role == "admin":
        menu_items.append(t["settings"])
    
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
            border-radius: 10px 10px 0 0;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(menu_items)
    
    with tabs[0]:
        page_dashboard(t, role, student_id)
    with tabs[1]:
        page_profile(t, role, student_id)
    with tabs[2]:
        if role != "student":
            page_students(t, role, user_id)
        else:
            st.warning("Access denied")
    with tabs[3]:
        page_scores(t, role, user_id, student_id)
    with tabs[4]:
        if role != "student":
            page_statistics(t, role, user_id)
        else:
            st.warning("Access denied")
    
    if role == "admin" and len(tabs) > 5:
        with tabs[5]:
            page_settings(t, role)

if __name__ == "__main__":
    main()
