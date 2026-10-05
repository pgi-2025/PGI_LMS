CREATE DATABASE IF NOT EXISTS pgi_lms;
USE pgi_lms;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(255) DEFAULT NULL,
    level INT DEFAULT 1,
    xp INT DEFAULT 0,
    xp_max INT DEFAULT 1000,
    streak_days INT DEFAULT 0,
    last_login DATE DEFAULT NULL,
    bio TEXT DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    notifications_email BOOLEAN DEFAULT TRUE,
    notifications_push BOOLEAN DEFAULT TRUE,
    dark_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Courses table
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    instructor VARCHAR(100),
    thumbnail VARCHAR(255),
    total_modules INT DEFAULT 0,
    total_hours FLOAT DEFAULT 0,
    difficulty ENUM('Beginner','Intermediate','Advanced') DEFAULT 'Beginner',
    category VARCHAR(100),
    xp_reward INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User course enrollments
CREATE TABLE IF NOT EXISTS user_courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    current_module INT DEFAULT 1,
    progress_percent INT DEFAULT 0,
    status ENUM('active','completed','paused') DEFAULT 'active',
    mode ENUM('LIVE','SELF-PACED','NEW') DEFAULT 'SELF-PACED',
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE KEY unique_enrollment (user_id, course_id)
);

-- Lessons table
CREATE TABLE IF NOT EXISTS lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    module_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    video_url VARCHAR(255),
    duration_minutes INT DEFAULT 0,
    xp_reward INT DEFAULT 10,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- User lesson completions
CREATE TABLE IF NOT EXISTS user_lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    lesson_id INT NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    UNIQUE KEY unique_lesson (user_id, lesson_id)
);

-- Assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATETIME NOT NULL,
    max_score INT DEFAULT 100,
    xp_reward INT DEFAULT 50,
    type ENUM('Assignment','Quiz','Project','Live Session') DEFAULT 'Assignment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- User assignment submissions
CREATE TABLE IF NOT EXISTS user_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    assignment_id INT NOT NULL,
    status ENUM('pending','submitted','graded') DEFAULT 'pending',
    score INT DEFAULT NULL,
    feedback TEXT DEFAULT NULL,
    submitted_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    UNIQUE KEY unique_submission (user_id, assignment_id)
);

-- Quiz questions
CREATE TABLE IF NOT EXISTS quiz_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    question TEXT NOT NULL,
    option_a VARCHAR(255),
    option_b VARCHAR(255),
    option_c VARCHAR(255),
    option_d VARCHAR(255),
    correct_option ENUM('a','b','c','d') NOT NULL,
    explanation TEXT,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Schedule/Events
CREATE TABLE IF NOT EXISTS schedule_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    event_type ENUM('lesson','live_session','assignment_due','quiz','study') DEFAULT 'study',
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    course_id INT DEFAULT NULL,
    reminder_sent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- Daily streak tracking
CREATE TABLE IF NOT EXISTS streak_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    log_date DATE NOT NULL,
    xp_earned INT DEFAULT 0,
    lessons_completed INT DEFAULT 0,
    minutes_studied INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_day (user_id, log_date)
);

-- Achievements/Badges
CREATE TABLE IF NOT EXISTS achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    criteria_type ENUM('streak','xp','lessons','courses','quiz_score') NOT NULL,
    criteria_value INT NOT NULL,
    xp_reward INT DEFAULT 50
);

-- User achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    achievement_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
    UNIQUE KEY unique_achievement (user_id, achievement_id)
);

-- Certificates
CREATE TABLE IF NOT EXISTS certificates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    course_id INT NOT NULL,
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info','success','warning','error') DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ========================
-- SEED DATA
-- ========================

-- Default achievements
INSERT INTO achievements (title, description, icon, criteria_type, criteria_value, xp_reward) VALUES
('First Login', 'Welcome to the platform!', '🚀', 'lessons', 0, 10),
('7-Day Streak', 'Studied 7 days in a row', '🔥', 'streak', 7, 100),
('10 Lessons', 'Completed 10 lessons', '📚', 'lessons', 10, 50),
('500 XP Club', 'Earned 500 XP total', '⚡', 'xp', 500, 75),
('Course Master', 'Completed your first course', '🏆', 'courses', 1, 200),
('Quiz Ace', 'Scored 100% on a quiz', '🎯', 'quiz_score', 100, 150),
('30-Day Streak', 'Studied 30 days in a row', '💎', 'streak', 30, 500),
('1000 XP Legend', 'Earned 1000 XP total', '👑', 'xp', 1000, 300);

-- Sample courses
INSERT INTO courses (title, description, instructor, total_modules, total_hours, difficulty, category, xp_reward) VALUES
('Web Development (Full Stack)', 'Master HTML, CSS, JavaScript, React, Node.js, and databases to build complete web applications.', 'Prof. Ravi Kumar', 12, 48, 'Intermediate', 'Development', 500),
('Artificial Intelligence & ML', 'Learn Python for AI, machine learning algorithms, neural networks, and deep learning.', 'Dr. Priya Nair', 10, 40, 'Advanced', 'AI/ML', 600),
('UI/UX Design', 'Design beautiful interfaces using Figma, user research, wireframing, and prototyping.', 'Ms. Ananya Sharma', 8, 32, 'Beginner', 'Design', 400),
('Data Science with Python', 'Pandas, NumPy, Matplotlib, data wrangling, statistical analysis and visualization.', 'Dr. Arjun Mehta', 10, 35, 'Intermediate', 'Data Science', 450),
('Cloud Computing (AWS)', 'EC2, S3, Lambda, RDS — deploy and manage scalable cloud infrastructure.', 'Mr. Suresh Balan', 8, 30, 'Advanced', 'Cloud', 550),
('DevOps & CI/CD', 'Docker, Kubernetes, Jenkins, GitHub Actions — automate your dev pipeline.', 'Ms. Kavya Reddy', 9, 36, 'Advanced', 'DevOps', 500);

-- Sample demo user
INSERT INTO users (username, email, password_hash, full_name, level, xp, xp_max, streak_days, last_login) VALUES
('abi', 'abi@example.com', 'pbkdf2:sha256:260000$demo$hash', 'Abi', 4, 720, 1000, 7, CURDATE());

-- Enroll demo user
INSERT INTO user_courses (user_id, course_id, current_module, progress_percent, status, mode) VALUES
(1, 1, 6, 62, 'active', 'LIVE'),
(1, 2, 3, 31, 'active', 'NEW'),
(1, 3, 8, 88, 'active', 'SELF-PACED');

-- Sample assignments for demo user
INSERT INTO assignments (course_id, title, description, due_date, max_score, xp_reward, type) VALUES
(1, 'REST API Assignment', 'Build a complete REST API using Node.js and Express with CRUD operations.', DATE_ADD(NOW(), INTERVAL 0 DAY), 100, 80, 'Assignment'),
(2, 'Neural Networks Quiz', 'Quiz covering backpropagation, activation functions, and CNN basics.', DATE_ADD(NOW(), INTERVAL 1 DAY), 100, 60, 'Quiz'),
(3, 'Figma Wireframes', 'Design a mobile app wireframe for an e-commerce checkout flow.', DATE_SUB(NOW(), INTERVAL 1 DAY), 100, 50, 'Assignment'),
(1, 'Live Session — DevOps', 'Attend the live DevOps session covering Docker containerization.', DATE_ADD(NOW(), INTERVAL 2 DAY), 100, 40, 'Live Session');

-- Sample user_assignments
INSERT INTO user_assignments (user_id, assignment_id, status, score) VALUES
(1, 1, 'pending', NULL),
(1, 2, 'pending', NULL),
(1, 3, 'submitted', 92),
(1, 4, 'pending', NULL);

-- Sample schedule events
INSERT INTO schedule_events (user_id, title, description, event_type, event_date, start_time, end_time, course_id) VALUES
(1, 'REST API Module', 'Continue REST APIs with Node.js', 'lesson', CURDATE(), '09:00:00', '10:30:00', 1),
(1, 'Neural Networks Live', 'Live session with Dr. Priya', 'live_session', CURDATE(), '14:00:00', '15:30:00', 2),
(1, 'DevOps Live Session', 'Docker containerization deep dive', 'live_session', DATE_ADD(CURDATE(), INTERVAL 2 DAY), '16:00:00', '17:30:00', 1),
(1, 'UI/UX Final Project', 'Final project submission deadline', 'assignment_due', DATE_ADD(CURDATE(), INTERVAL 3 DAY), '23:59:00', NULL, 3),
(1, 'ML Quiz Prep', 'Study neural networks chapter', 'study', DATE_ADD(CURDATE(), INTERVAL 1 DAY), '10:00:00', '12:00:00', 2);

-- Sample streak logs
INSERT INTO streak_logs (user_id, log_date, xp_earned, lessons_completed, minutes_studied) VALUES
(1, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 45, 2, 90),
(1, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 60, 3, 120),
(1, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 30, 1, 60),
(1, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 75, 4, 150),
(1, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 50, 2, 80),
(1, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 90, 5, 180),
(1, CURDATE(), 40, 2, 70);

-- Sample notifications
INSERT INTO notifications (user_id, title, message, type) VALUES
(1, 'Assignment Due Today!', 'REST API Assignment is due tonight at 11:59 PM. Submit before deadline!', 'warning'),
(1, 'New Live Session Added', 'DevOps Docker session added for Friday 4:00 PM. Mark your calendar!', 'info'),
(1, '7-Day Streak Achievement!', 'Congratulations! You earned the 7-Day Streak badge. +100 XP awarded!', 'success'),
(1, 'Quiz Available', 'Neural Networks Quiz is now available. Complete it before tomorrow 5 PM.', 'info');

-- User achievements
INSERT INTO user_achievements (user_id, achievement_id) VALUES
(1, 1), (1, 2), (1, 3), (1, 4);

-- Sample messages
INSERT INTO messages (sender_id, receiver_id, content) VALUES
(1, 1, 'Welcome to Plant Green Inertia LMS! Start your learning journey today.');

SELECT 'Database setup complete!' AS status;