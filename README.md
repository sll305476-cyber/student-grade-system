# Student Grade Management System

A Streamlit-based student grade management system with multi-role authentication.

## Features
- Multi-role login (Admin/Teacher/Student)
- Theme switching (Blue/White, Green/White, Dark)
- Bilingual support (Chinese/English)
- Student self-registration
- Grade management
- Statistics and analytics

## Deployment to Streamlit Cloud

### 1. Create GitHub Repository
1. Go to https://github.com/new
2. Repository name: `student-grade-system`
3. Make it **Public**
4. Click "Create repository"

### 2. Upload Files
Upload these files to the repository:
- `app.py`
- `requirements.txt`
- `.streamlit/config.toml`

### 3. Deploy
1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Select your repository
4. Branch: `main`
   Main file path: `app.py`
5. Click "Deploy"

### Default Accounts
- Admin: `admin` / `admin123`
- Teacher: `teacher` / `teacher123`

## Note
This system uses SQLite database. On Streamlit Cloud, the database resets on each deployment.
