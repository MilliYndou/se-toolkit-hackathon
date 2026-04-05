# Product name - StudyBuddy

A theme-based quiz manager where teachers curate questions and students generate instant practice quizzes with scoring and explanations.

---

## Demo

### Student View - Quiz Generation

### Student View - Quiz History

### Teacher View - Add Question

### Teacher View - Student History

---

## Product Context

### End Users

- **Students**: University students preparing for exams who need targeted practice quizzes
- **Teachers**: Instructors who create and manage quiz content for their courses

### Problem That Your Product Solves for End Users

- **Students**: Struggle to find organized, topic-specific practice quizzes. Existing tools are either generic, require unreliable AI, or lack progress tracking.
- **Teachers**: Spend excessive time manually creating quiz questions. No centralized system to monitor student progress across quizzes.

### Your Solution

StudyBuddy is a web-based quiz platform with role-based access control:

- **Teachers** create and organize questions by theme (Chemistry, Biology, CS, etc.)
- **Students** select a theme → generate 5 random questions → answer → get instant score + explanations
- **All quiz attempts** are saved to SQLite database for progress tracking
- **Validation system** ensures themes have 5+ questions before quiz generation
- **100% local deployment** - no external API dependencies

---

## Features

### Implemented Features

- User Authentication: Login system with role-based access (Teacher/Student)
- Theme Management: Teachers can create, view, and organize quiz themes
- Question Bank: Teachers can add/edit/delete questions with 4 options + explanations
- Quiz Generation: Students generate 5 random questions from selected theme
- Quiz Validation: System prevents quiz generation if theme has less than 5 questions
- Instant Scoring: Automatic grading with correct/incorrect feedback
- Explanations: Each question shows explanation after submission
- Student History: Students view their own quiz attempts with sequential numbering
- Teacher Dashboard: Teachers view all student quiz attempts across the platform
- Responsive Web UI: Clean, modern interface that works on any browser
- SQLite Database: Normalized schema with 4 tables (users, themes, questions, attempts)
- Docker Deployment: Dockerfile + docker-compose.yml for containerized deployment
- Session Management: Proper logout state reset (no leftover data between users)

### Not Yet Implemented Features

- Password Hashing: Currently uses plaintext passwords (demo only)
- JWT Token Authentication: Session-based auth (demo); JWT needed for production
- Email Notifications: Send quiz results via email
- Question Import/Export: Bulk upload questions via CSV
- Advanced Analytics: Teacher dashboard with charts and statistics
- Multi-language Support: Internationalization for non-English users
- Mobile App: Native iOS/Android application

---

## Usage

### Step 1: Access the Application

Open your browser and navigate to: http://localhost:8000

### Step 2: Login

| Role | Username | Password |
|------|----------|----------|
| Teacher | `teacher1` | `demo123` |
| Student | `student1` | `demo123` |
| Student | `student2` | `demo123` |

### Step 3: Student Flow

1. Login as `student1` / `demo123`
2. Click **"📝 Take Quiz"** tab
3. Select a theme (e.g., "Chemistry Basics")
4. Answer 5 questions
5. Click **"✅ Submit Answers"**
6. View score + explanations
7. Click **"📊 History"** to see past attempts

### Step 4: Teacher Flow

1. Login as `teacher1` / `demo123`
2. Click **"👨‍🏫 Manage"** tab
3. Add new theme or select existing theme
4. Add new question with 4 options + correct answer + explanation
5. View all student quiz attempts in **"Student Quiz History"** section
6. Delete questions as needed

### Demo Testing Scenario

To demonstrate the 5-question validation:

1. Login as student → Click "Biology 101" (has only 4 questions)
2. **Expected:** Error message "Theme has only 4 questions (need at least 5)"
3. Logout → Login as teacher → Add 5th question to Biology
4. Logout → Login as student → Click "Biology 101"
5. **Expected:** Quiz generates successfully with 5 questions

---

## Deployment

### Which OS the VM Should Run On

**Ubuntu 24.04 LTS** (same as university VMs)

### What Should Be Installed on the VM

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Docker (if using Docker deployment)
sudo apt install docker.io docker-compose-plugin -y

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional - avoids sudo)
sudo usermod -aG docker $USER

### Step-by-Step Deployment Instructions

## Option A: Local Python Deployment

# Step 1: Clone repository
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/studybuddy.git
cd studybuddy

# Step 2: Create virtual environment
cd backend
python3 -m venv venv

# Step 3: Activate virtual environment
source venv/bin/activate

# Step 4: Install dependencies
pip install -r requirements.txt

# Step 5: Initialize database (automatic on first run)
# The database (studybuddy.db) will be created automatically

# Step 6: Run the application
python main.py

# Step 7: Access the application
# Open browser: http://<VM_IP_ADDRESS>:8000
# Or if on localhost: http://localhost:8000

## Option B: Docker Deployment

# Step 1: Clone repository
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/studybuddy.git
cd studybuddy

# Step 2: Build and run with Docker Compose
docker compose up --build -d

# Step 3: Check deployment status
docker compose ps

# Step 4: View logs (optional)
docker compose logs -f

# Step 5: Access the application
# Open browser: http://<VM_IP_ADDRESS>:8000

# Step 6: Stop deployment (when done)
docker compose down