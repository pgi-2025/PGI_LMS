from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, Response, stream_with_context)
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from functools import wraps
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash as wp_check
from supabase import create_client, Client
from dotenv import load_dotenv
import os, random, string, mimetypes

load_dotenv()

# ════════════════════════════════════════════════════════
# APP & CONFIG
# ════════════════════════════════════════════════════════
app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY']          = os.environ.get('SECRET_KEY', 'pgi-lms-secret-2024')
app.config['UPLOAD_FOLDER']       = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH']  = 500 * 1024 * 1024  # 500 MB

ALLOWED_VIDEO = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
ALLOWED_IMG   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

bcrypt = Bcrypt(app)

# ════════════════════════════════════════════════════════
# SUPABASE CLIENT
# Use the SERVICE ROLE key here — this runs only on the
# server, never in the browser, so it's safe to bypass RLS.
# Set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env
# ════════════════════════════════════════════════════════
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL / SUPABASE_SERVICE_KEY environment variables. "
        "Set them in your .env file (see .env.example)."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create upload directories on startup
for _sub in ('videos', 'thumbnails', 'avatars'):
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], _sub), exist_ok=True)

# Confirm Supabase connection on startup
try:
    supabase.table('users').select('id').limit(1).execute()
    print("✅  Connected to Supabase")
except Exception as _e:
    print("❌  Supabase connection failed:", _e)


# ════════════════════════════════════════════════════════
# SMALL HELPERS
# ════════════════════════════════════════════════════════
def one(resp):
    """Return the first row of a supabase response, or None."""
    data = resp.data
    return data[0] if data else None


def rows(resp):
    """Return the row list of a supabase response (never None)."""
    return resp.data or []


def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def today_iso():
    return date.today().isoformat()


def now_iso():
    return datetime.utcnow().isoformat()


def is_duplicate_error(e):
    msg = str(e).lower()
    return 'duplicate key' in msg or '23505' in msg or 'already exists' in msg


# ════════════════════════════════════════════════════════
# AUTH DECORATORS
# ════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        u = one(supabase.table('users').select('is_admin')
                .eq('id', session['user_id']).execute())
        if not u or not u.get('is_admin'):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


# ════════════════════════════════════════════════════════
# PAGE ROUTES
# ════════════════════════════════════════════════════════
@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

@app.route('/login')
def login_page():           return render_template('login.html')

@app.route('/register')
def register_page():        return render_template('register.html')

@app.route('/edit-profile')
@login_required
def edit_profile_page():    return render_template('edit_profile.html')

@app.route('/dashboard')
@login_required
def dashboard_page():       return render_template('dashboard.html')

@app.route('/schedule')
@login_required
def schedule_page():        return render_template('schedule.html')

@app.route('/my-courses')
@login_required
def courses_page():         return render_template('my_courses.html')

@app.route('/assignments')
@login_required
def assignments_page():     return render_template('assignments.html')

@app.route('/quiz')
@login_required
def quiz_page():            return render_template('quiz.html')

@app.route('/leaderboard')
@login_required
def leaderboard_page():     return render_template('leaderboard.html')

@app.route('/profile')
@login_required
def profile_page():         return render_template('profile.html')

@app.route('/settings')
@login_required
def settings_page():        return render_template('settings.html')

@app.route('/notifications')
@login_required
def notifications_page():   return render_template('notifications.html')


# ════════════════════════════════════════════════════════
# AUTH API
# ════════════════════════════════════════════════════════
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    d = request.get_json()
    if not d:
        return jsonify({'error': 'No data sent'}), 400

    email    = d.get('email', '').strip()
    password = d.get('password', '')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = one(supabase.table('users').select('*').eq('email', email).execute())
    if not user:
        user = one(supabase.table('users').select('*').eq('username', email).execute())
    if not user:
        return jsonify({'error': 'No account found with that email or username'}), 401

    valid   = False
    pw_hash = user.get('password_hash', '') or ''

    if not valid and pw_hash.startswith('pbkdf2:'):
        try:   valid = wp_check(pw_hash, password)
        except Exception: pass

    if not valid and pw_hash.startswith('$2b$'):
        try:   valid = bcrypt.check_password_hash(pw_hash, password)
        except Exception: pass

    # Demo shortcut — only if hash is a placeholder
    if not valid:
        hash_real = pw_hash.startswith('pbkdf2:') or pw_hash.startswith('$2b$')
        if not hash_real and password == 'demo123':
            valid = True

    if not valid:
        return jsonify({'error': 'Incorrect password'}), 401

    _update_streak(user['id'])
    session.clear()
    session['user_id']   = user['id']
    session['username']  = user['username']
    session['full_name'] = user['full_name']
    return jsonify({'success': True, 'redirect': '/dashboard'})


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    d         = request.get_json()
    username  = d.get('username', '').strip()
    email     = d.get('email', '').strip()
    full_name = d.get('full_name', '').strip()
    password  = d.get('password', '')
    if not all([username, email, full_name, password]):
        return jsonify({'error': 'All fields required'}), 400

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    try:
        res = supabase.table('users').insert({
            'username': username, 'email': email,
            'full_name': full_name, 'password_hash': pw_hash
        }).execute()
        uid = res.data[0]['id']
        session.update({'user_id': uid, 'username': username, 'full_name': full_name})
        return jsonify({'success': True, 'redirect': '/dashboard'})
    except Exception as e:
        if is_duplicate_error(e):
            return jsonify({'error': 'Username or email already exists'}), 400
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect('/login')


@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    d      = request.get_json()
    email  = d.get('email', '').strip().lower()
    new_pw = d.get('new_password', '')
    if not email:         return jsonify({'error': 'Email is required.'}), 400
    if not new_pw:        return jsonify({'error': 'New password is required.'}), 400
    if len(new_pw) < 8:   return jsonify({'error': 'Password must be at least 8 characters.'}), 400

    user = one(supabase.table('users').select('id,email').eq('email', email).execute())
    if not user:
        return jsonify({'error': 'No account found with that email address.'}), 404

    new_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    supabase.table('users').update({'password_hash': new_hash}).eq('id', user['id']).execute()
    return jsonify({'success': True, 'message': f"Password updated for {user['email']}"})


# ════════════════════════════════════════════════════════
# USER API
# ════════════════════════════════════════════════════════
# @app.route('/api/user/me')
# @login_required
# def api_me():
#     u = one(supabase.table('users').select(
#         'id,username,full_name,email,level,xp,xp_max,streak_days,'
#         'bio,phone,avatar_url,dark_mode,notifications_email,'
#         'notifications_push,timezone,date_of_birth,gender'
#     ).eq('id', session['user_id']).execute())
#     if u:
#         u['date_of_birth'] = u.get('date_of_birth') or ''
#         u['gender']        = u.get('gender') or ''
#     return jsonify(u)

@app.route('/api/user/me')
@login_required
def api_me():
    u = one(
        supabase.table("users").select(
            "id,username,full_name,email,level,xp,xp_max,streak_days,"
            "bio,phone,avatar_url,dark_mode,notifications_email,"
            "notifications_push,timezone"
        ).eq("id", session["user_id"]).execute()
    )
    return jsonify(u)


@app.route('/api/user/update', methods=['POST'])
@login_required
def api_update_user():
    d = request.get_json()
    if not d:
        return jsonify({'error': 'No data received'}), 400

    ALLOWED = {'full_name', 'bio', 'phone', 'timezone',
               'notifications_email', 'notifications_push', 'dark_mode'}
    updates = {k: v for k, v in d.items() if k in ALLOWED}
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    supabase.table('users').update(updates).eq('id', session['user_id']).execute()
    return jsonify({'success': True})


@app.route('/api/user/update_profile', methods=['POST'])
@login_required
def update_profile():
    d         = request.get_json()
    uid       = session['user_id']
    full_name = d.get('full_name', '').strip()
    email     = d.get('email', '').strip()
    phone     = d.get('phone', '').strip()
    dob       = d.get('date_of_birth') or None
    gender    = d.get('gender', '').strip()
    bio       = d.get('bio', '').strip()

    if not full_name: return jsonify({'error': 'Full name is required.'}), 400
    if not email:     return jsonify({'error': 'Email is required.'}), 400

    try:
        supabase.table('users').update({
            'full_name': full_name, 'email': email, 'phone': phone,
            'date_of_birth': dob, 'gender': gender, 'bio': bio
        }).eq('id', uid).execute()
        session['full_name'] = full_name
        return jsonify({'success': True, 'message': '✓ Profile updated!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    f = request.files.get('avatar')
    if not f or not allowed_file(f.filename, ALLOWED_IMG):
        return jsonify({'error': 'Invalid file'}), 400
    fname = f"avatar_{session['user_id']}_{secure_filename(f.filename)}"
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', fname))
    url = f"/static/uploads/avatars/{fname}"
    supabase.table('users').update({'avatar_url': url}).eq('id', session['user_id']).execute()
    return jsonify({'success': True, 'url': url})


@app.route('/api/user/change-password', methods=['POST'])
@login_required
def api_change_password():
    d                = request.get_json()
    current_password = d.get('current_password', '')
    new_password     = d.get('new_password', '')
    if not current_password or not new_password:
        return jsonify({'error': 'Both current and new password are required.'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters.'}), 400

    user = one(supabase.table('users').select('password_hash')
               .eq('id', session['user_id']).execute())
    try:   valid = bcrypt.check_password_hash(user['password_hash'], current_password)
    except Exception: valid = False

    if not valid:
        return jsonify({'error': 'Current password is incorrect.'}), 401

    new_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    supabase.table('users').update({'password_hash': new_hash}).eq('id', session['user_id']).execute()
    return jsonify({'success': True, 'message': 'Password changed successfully!'})


@app.route('/api/user/storage')
@login_required
def api_user_storage():
    uid         = session['user_id']
    upload_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
    total_bytes = 0

    avatar_dir = os.path.join(upload_root, 'avatars')
    if os.path.isdir(avatar_dir):
        for f in os.listdir(avatar_dir):
            if f.startswith(f'avatar_{uid}_'):
                try: total_bytes += os.path.getsize(os.path.join(avatar_dir, f))
                except Exception: pass

    ul_rows   = rows(supabase.table('user_lessons').select('lesson_id').eq('user_id', uid).execute())
    lesson_ids = [r['lesson_id'] for r in ul_rows]
    video_urls = []
    if lesson_ids:
        l_rows = rows(supabase.table('lessons').select('video_url').in_('id', lesson_ids).execute())
        video_urls = [l['video_url'] for l in l_rows if l.get('video_url')]

    video_dir = os.path.join(upload_root, 'videos')
    for vurl in video_urls:
        fpath = os.path.join(video_dir, os.path.basename(vurl))
        if os.path.isfile(fpath):
            try: total_bytes += os.path.getsize(fpath)
            except Exception: pass

    used_gb = round(total_bytes / (1024 ** 3), 2)
    max_gb  = 5.0
    return jsonify({
        'used_gb':  used_gb,
        'max_gb':   max_gb,
        'used_pct': round((used_gb / max_gb) * 100, 1),
        'used_mb':  round(total_bytes / (1024 ** 2), 1),
    })


# ════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    uid = session['user_id']

    user = one(supabase.table('users').select(
        'level,xp,xp_max,streak_days,full_name').eq('id', uid).execute())

    ucs = rows(supabase.table('user_courses').select('*')
               .eq('user_id', uid).eq('status', 'active').execute())
    active_courses = len(ucs)

    logs = rows(supabase.table('streak_logs').select('minutes_studied').eq('user_id', uid).execute())
    total_hours = round(sum((l.get('minutes_studied') or 0) for l in logs) / 60, 1)

    lessons_done = len(rows(supabase.table('user_lessons').select('id').eq('user_id', uid).execute()))

    course_ids = [uc['course_id'] for uc in ucs]
    courses_map = {}
    if course_ids:
        crs = rows(supabase.table('courses').select('id,title,category,total_modules')
                   .in_('id', course_ids).execute())
        courses_map = {c['id']: c for c in crs}

    ucs_sorted = sorted(ucs, key=lambda x: x.get('enrolled_at') or '', reverse=True)
    courses = []
    for uc in ucs_sorted:
        c = courses_map.get(uc['course_id'])
        if not c:
            continue
        courses.append({
            'title': c['title'], 'category': c['category'],
            'current_module': uc['current_module'], 'progress_percent': uc['progress_percent'],
            'mode': uc['mode'], 'total_modules': c['total_modules'], 'course_id': c['id'],
        })

    uas = rows(supabase.table('user_assignments').select('*')
               .eq('user_id', uid).neq('status', 'graded').execute())
    assignment_ids = [ua['assignment_id'] for ua in uas]
    ftasks = []
    if assignment_ids:
        assigns = rows(supabase.table('assignments').select('id,title,type,due_date')
                       .in_('id', assignment_ids).execute())
        assigns_map = {a['id']: a for a in assigns}
        for ua in uas:
            a = assigns_map.get(ua['assignment_id'])
            if not a:
                continue
            ftasks.append({'title': a['title'], 'type': a['type'],
                            'due_date': str(a['due_date']), 'status': ua['status']})
        ftasks.sort(key=lambda t: t['due_date'])
        ftasks = ftasks[:5]

    cutoff = (date.today() - timedelta(days=21)).isoformat()
    streak_rows = rows(supabase.table('streak_logs').select('log_date')
                        .eq('user_id', uid).gte('log_date', cutoff).execute())
    streak_dates = [str(r['log_date']) for r in streak_rows]

    uach = rows(supabase.table('user_achievements').select('*')
                .eq('user_id', uid).order('earned_at', desc=True).limit(8).execute())
    ach_ids = [a['achievement_id'] for a in uach]
    achievements = []
    if ach_ids:
        achs = rows(supabase.table('achievements').select('id,title,icon').in_('id', ach_ids).execute())
        achs_map = {a['id']: a for a in achs}
        for ua in uach:
            a = achs_map.get(ua['achievement_id'])
            if a:
                achievements.append({'title': a['title'], 'icon': a['icon']})

    return jsonify({
        'user': user,
        'stats': {
            'active_courses': active_courses,
            'total_hours':    total_hours,
            'total_xp':       user['xp'],
            'lessons_done':   lessons_done,
            'lessons_today':  0,
            'streak_days':    user['streak_days'],
            'best_streak':    user['streak_days'],
            'level':          user['level'],
        },
        'courses':      courses,
        'tasks':        ftasks,
        'streak_dates': streak_dates,
        'achievements': achievements,
    })


# ════════════════════════════════════════════════════════
# COURSES
# ════════════════════════════════════════════════════════
@app.route('/api/courses')
@login_required
def api_courses():
    uid = session['user_id']
    courses = rows(supabase.table('courses').select('*').order('id').execute())
    ucs = rows(supabase.table('user_courses').select('*').eq('user_id', uid).execute())
    uc_map = {uc['course_id']: uc for uc in ucs}

    result = []
    for c in courses:
        uc = uc_map.get(c['id'])
        result.append({
            'id': c['id'], 'title': c['title'], 'description': c['description'],
            'instructor': c['instructor'], 'total_modules': c['total_modules'],
            'total_hours': c['total_hours'], 'difficulty': c['difficulty'],
            'category': c['category'], 'xp_reward': c['xp_reward'],
            'google_form_url': c.get('google_form_url') or '',
            'progress_percent': uc['progress_percent'] if uc else None,
            'current_module': uc['current_module'] if uc else None,
            'enroll_status': uc['status'] if uc else None,
            'mode': uc['mode'] if uc else None,
            'uc_id': uc['id'] if uc else None,
            '_enrolled_at': uc['enrolled_at'] if uc else None,
        })

    enrolled     = sorted([r for r in result if r['uc_id']],
                           key=lambda r: r['_enrolled_at'] or '', reverse=True)
    not_enrolled = [r for r in result if not r['uc_id']]
    for r in enrolled + not_enrolled:
        r.pop('_enrolled_at', None)
    return jsonify(enrolled + not_enrolled)


@app.route('/api/courses/<int:course_id>')
@login_required
def api_course_detail(course_id):
    uid = session['user_id']
    course = one(supabase.table('courses').select('*').eq('id', course_id).execute())
    if not course:
        return jsonify({'error': 'Not found'}), 404
    course['google_form_url'] = course.get('google_form_url') or ''

    uc = one(supabase.table('user_courses').select('*')
             .eq('user_id', uid).eq('course_id', course_id).execute())
    course['progress_percent'] = uc['progress_percent'] if uc else None
    course['current_module']   = uc['current_module'] if uc else None
    course['enroll_status']    = uc['status'] if uc else None
    course['mode']             = uc['mode'] if uc else None

    lessons = rows(supabase.table('lessons').select('*').eq('course_id', course_id)
                   .order('module_number').order('id').execute())

    ul = rows(supabase.table('user_lessons').select('lesson_id').eq('user_id', uid).execute())
    completed_ids = {r['lesson_id'] for r in ul}

    for l in lessons:
        l['duration_minutes'] = int(l.get('duration_minutes') or 0)
        l['completed']        = l['id'] in completed_ids
        raw_video = l.get('video_url') or ''
        if 'youtube.com' in raw_video or 'youtu.be' in raw_video:
            l['youtube_url'] = raw_video
            l['video_url']   = ''
        else:
            l['video_url']   = raw_video
            l['youtube_url'] = l.get('youtube_url') or ''

    total_lessons   = len(lessons)
    completed_count = sum(1 for l in lessons if l['completed'])
    all_done        = total_lessons > 0 and completed_count == total_lessons

    return jsonify({
        'course':          course,
        'lessons':         lessons,
        'total_lessons':   total_lessons,
        'completed_count': completed_count,
        'all_done':        all_done,
    })


@app.route('/api/courses/enroll', methods=['POST'])
@login_required
def api_enroll():
    d = request.get_json()
    try:
        supabase.table('user_courses').insert(
            {'user_id': session['user_id'], 'course_id': d['course_id']}
        ).execute()
        _add_notification(session['user_id'], 'Enrolled! 🎉',
                          'You enrolled in a new course. Start learning!', 'success')
        return jsonify({'success': True})
    except Exception:
        return jsonify({'error': 'Already enrolled'}), 400


@app.route('/api/courses/complete-lesson', methods=['POST'])
@login_required
def api_complete_lesson():
    d   = request.get_json()
    uid = session['user_id']
    lid = d['lesson_id']

    try:
       supabase.table('user_lessons').insert({'user_id': uid, 'lesson_id': lid}).execute()
    except Exception as e:
       print("USER_LESSONS INSERT FAILED:", e)
       return jsonify({'success': True, 'already_done': True})

    lesson = one(supabase.table('lessons').select('course_id,xp_reward,duration_minutes')
                 .eq('id', lid).execute())
    xp_gain, cert_issued, pct = 10, False, 0

    if lesson:
        cid     = lesson['course_id']
        xp_gain = lesson.get('xp_reward') or 10

        course_lessons = rows(supabase.table('lessons').select('id').eq('course_id', cid).execute())
        course_lesson_ids = {l['id'] for l in course_lessons}
        total = len(course_lesson_ids)

        done_ul = rows(supabase.table('user_lessons').select('lesson_id').eq('user_id', uid).execute())
        done = sum(1 for r in done_ul if r['lesson_id'] in course_lesson_ids)

        pct = int((done / total) * 100) if total else 0

        supabase.table('user_courses').update({
            'progress_percent': pct, 'current_module': d.get('module_number', 1)
        }).eq('user_id', uid).eq('course_id', cid).execute()

        u = one(supabase.table('users').select('xp').eq('id', uid).execute())
        supabase.table('users').update({'xp': (u['xp'] or 0) + xp_gain}).eq('id', uid).execute()

        dur   = d.get('duration', lesson.get('duration_minutes') or 10)
        today = today_iso()
        try:
            existing = one(supabase.table('streak_logs').select('*')
                           .eq('user_id', uid).eq('log_date', today).execute())
            if existing:
                supabase.table('streak_logs').update({
                    'xp_earned':         existing['xp_earned'] + xp_gain,
                    'lessons_completed': existing['lessons_completed'] + 1,
                    'minutes_studied':   existing['minutes_studied'] + dur,
                }).eq('id', existing['id']).execute()
            else:
                supabase.table('streak_logs').insert({
                    'user_id': uid, 'log_date': today, 'xp_earned': xp_gain,
                    'lessons_completed': 1, 'minutes_studied': dur,
                }).execute()
        except Exception:
            pass

        if pct == 100:
            cert_issued = True
            try:
                supabase.table('certificates').insert({
                    'user_id': uid, 'course_id': cid,
                    'issued_at': now_iso(),
                }).execute()
            except Exception:
                pass

    return jsonify({'success': True, 'xp_gained': xp_gain,
                    'progress': pct, 'cert_issued': cert_issued})


# ════════════════════════════════════════════════════════
# ASSIGNMENTS
# ════════════════════════════════════════════════════════
@app.route('/api/assignments')
@login_required
def api_assignments():
    uid = session['user_id']
    ucs = rows(supabase.table('user_courses').select('course_id').eq('user_id', uid).execute())
    course_ids = [uc['course_id'] for uc in ucs]
    if not course_ids:
        return jsonify([])

    assigns = rows(supabase.table('assignments').select('*')
                   .in_('course_id', course_ids).order('due_date').execute())
    crs = rows(supabase.table('courses').select('id,title').in_('id', course_ids).execute())
    courses_map = {c['id']: c['title'] for c in crs}

    aids = [a['id'] for a in assigns]
    uas = rows(supabase.table('user_assignments').select('*')
               .eq('user_id', uid).in_('assignment_id', aids).execute()) if aids else []
    ua_map = {ua['assignment_id']: ua for ua in uas}

    result = []
    for a in assigns:
        ua = ua_map.get(a['id'])
        result.append({
            **a,
            'course_title':      courses_map.get(a['course_id']),
            'submission_status': ua['status'] if ua else None,
            'score':             ua['score'] if ua else None,
            'feedback':          ua['feedback'] if ua else None,
            'submitted_at':      str(ua['submitted_at']) if ua and ua.get('submitted_at') else None,
            'due_date':          str(a['due_date']),
        })
    return jsonify(result)


@app.route('/api/assignments/add', methods=['POST'])
@login_required
def api_add_assignment():
    d = request.get_json()
    res = supabase.table('assignments').insert({
        'course_id': d['course_id'], 'title': d['title'],
        'description': d.get('description', ''), 'due_date': d['due_date'],
        'max_score': d.get('max_score', 100), 'xp_reward': d.get('xp_reward', 50),
        'type': d.get('type', 'Assignment'),
    }).execute()
    aid = res.data[0]['id']

    active_users = rows(supabase.table('user_courses').select('user_id')
                         .eq('course_id', d['course_id']).eq('status', 'active').execute())
    for u in active_users:
        try:
            supabase.table('user_assignments').insert(
                {'user_id': u['user_id'], 'assignment_id': aid}
            ).execute()
        except Exception:
            pass

    return jsonify({'success': True, 'id': aid})


@app.route('/api/assignments/submit', methods=['POST'])
@login_required
def api_submit_assignment():
    d   = request.get_json()
    uid = session['user_id']
    supabase.table('user_assignments').upsert({
        'user_id': uid, 'assignment_id': d['assignment_id'],
        'status': 'submitted', 'submitted_at': now_iso(),
    }, on_conflict='user_id,assignment_id').execute()
    return jsonify({'success': True})


# ════════════════════════════════════════════════════════
# SCHEDULE
# ════════════════════════════════════════════════════════
@app.route('/api/schedule')
@login_required
def api_schedule():
    uid   = session['user_id']
    month = int(request.args.get('month', datetime.now().month))
    year  = int(request.args.get('year', datetime.now().year))

    start = date(year, month, 1)
    end   = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)

    events = rows(supabase.table('schedule_events').select('*')
                  .eq('user_id', uid)
                  .gte('event_date', start.isoformat())
                  .lte('event_date', end.isoformat())
                  .order('event_date').order('start_time').execute())

    course_ids = list({e['course_id'] for e in events if e.get('course_id')})
    courses_map = {}
    if course_ids:
        crs = rows(supabase.table('courses').select('id,title').in_('id', course_ids).execute())
        courses_map = {c['id']: c['title'] for c in crs}

    for e in events:
        e['course_title'] = courses_map.get(e.get('course_id'))
        e['event_date']   = str(e['event_date'])
        e['start_time']   = str(e['start_time'])
        e['end_time']     = str(e['end_time']) if e.get('end_time') else None

    return jsonify(events)


@app.route('/api/schedule/add', methods=['POST'])
@login_required
def api_add_event():
    d   = request.get_json()
    uid = session['user_id']
    res = supabase.table('schedule_events').insert({
        'user_id': uid, 'title': d['title'], 'description': d.get('description'),
        'event_type': d.get('event_type', 'study'), 'event_date': d['event_date'],
        'start_time': d['start_time'], 'end_time': d.get('end_time'),
        'course_id': d.get('course_id'),
    }).execute()
    return jsonify({'success': True, 'id': res.data[0]['id']})


@app.route('/api/schedule/delete/<int:event_id>', methods=['DELETE'])
@login_required
def api_delete_event(event_id):
    supabase.table('schedule_events').delete().eq('id', event_id) \
        .eq('user_id', session['user_id']).execute()
    return jsonify({'success': True})


# ════════════════════════════════════════════════════════
# NOTIFICATIONS
# ════════════════════════════════════════════════════════
@app.route('/api/notifications')
@login_required
def api_notifications():
    notifs = rows(supabase.table('notifications').select('*')
                  .eq('user_id', session['user_id'])
                  .order('created_at', desc=True).limit(30).execute())
    for n in notifs:
        n['created_at'] = str(n['created_at'])
    return jsonify(notifs)


@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def api_mark_read():
    d   = request.get_json() or {}
    nid = d.get('id')
    q = supabase.table('notifications').update({'is_read': True}).eq('user_id', session['user_id'])
    if nid:
        q = q.eq('id', nid)
    q.execute()
    return jsonify({'success': True})


@app.route('/api/notifications/delete/<int:nid>', methods=['DELETE'])
@login_required
def api_delete_notification(nid):
    supabase.table('notifications').delete().eq('id', nid) \
        .eq('user_id', session['user_id']).execute()
    return jsonify({'success': True})


# ════════════════════════════════════════════════════════
# NAV BADGE COUNTS
# ════════════════════════════════════════════════════════
@app.route('/api/nav-counts')
@login_required
def api_nav_counts():
    uid = session['user_id']

    completed_ucs = rows(supabase.table('user_courses').select('course_id')
                         .eq('user_id', uid).eq('progress_percent', 100).execute())
    completed_ids = {r['course_id'] for r in completed_ucs}
    certs = rows(supabase.table('certificates').select('course_id').eq('user_id', uid).execute())
    cert_ids = {c['course_id'] for c in certs}
    pending_tests = len(completed_ids - cert_ids)

    pending_uas = rows(supabase.table('user_assignments').select('assignment_id')
                       .eq('user_id', uid).eq('status', 'pending').execute())
    pending_aids = [ua['assignment_id'] for ua in pending_uas]
    pending_assignments = pending_quizzes = 0
    if pending_aids:
        assigns = rows(supabase.table('assignments').select('id,type')
                       .in_('id', pending_aids).execute())
        type_map = {a['id']: a['type'] for a in assigns}
        for aid in pending_aids:
            if type_map.get(aid) == 'Quiz':
                pending_quizzes += 1
            else:
                pending_assignments += 1

    unread_notifications = len(rows(supabase.table('notifications').select('id')
                                    .eq('user_id', uid).eq('is_read', False).execute()))

    today_events = len(rows(supabase.table('schedule_events').select('id')
                            .eq('user_id', uid).eq('event_date', today_iso()).execute()))

    return jsonify({
        'courses':       pending_tests,
        'assignments':   pending_assignments,
        'quiz':          pending_quizzes,
        'notifications': unread_notifications,
        'schedule':      today_events,
    })


# ════════════════════════════════════════════════════════
# LEADERBOARD
# ════════════════════════════════════════════════════════
@app.route('/api/leaderboard')
@login_required
def api_leaderboard():
    period = request.args.get('period', 'all')
    users = rows(supabase.table('users').select(
        'id,full_name,username,level,avatar_url,streak_days,xp').execute())

    if period in ('weekly', 'monthly'):
        days   = 7 if period == 'weekly' else 30
        cutoff_date = date.today() - timedelta(days=days)
        cutoff      = cutoff_date.isoformat()
        cutoff_ts   = datetime.combine(cutoff_date, datetime.min.time()).isoformat()

        logs = rows(supabase.table('streak_logs').select('user_id,xp_earned')
                    .gte('log_date', cutoff).execute())
        xp_by_user = {}
        for l in logs:
            xp_by_user[l['user_id']] = xp_by_user.get(l['user_id'], 0) + (l['xp_earned'] or 0)

        uls = rows(supabase.table('user_lessons').select('user_id,completed_at')
                   .gte('completed_at', cutoff_ts).execute())
        lessons_by_user = {}
        for r in uls:
            lessons_by_user[r['user_id']] = lessons_by_user.get(r['user_id'], 0) + 1

        board = [{
            'id': u['id'], 'full_name': u['full_name'], 'username': u['username'],
            'level': u['level'], 'avatar_url': u.get('avatar_url'),
            'score': xp_by_user.get(u['id'], 0), 'streak_days': u['streak_days'],
            'lessons_done': lessons_by_user.get(u['id'], 0),
        } for u in users]
    else:
        uls = rows(supabase.table('user_lessons').select('user_id').execute())
        lessons_by_user = {}
        for r in uls:
            lessons_by_user[r['user_id']] = lessons_by_user.get(r['user_id'], 0) + 1

        board = [{
            'id': u['id'], 'full_name': u['full_name'], 'username': u['username'],
            'level': u['level'], 'score': u['xp'], 'avatar_url': u.get('avatar_url'),
            'streak_days': u['streak_days'], 'lessons_done': lessons_by_user.get(u['id'], 0),
        } for u in users]

    board.sort(key=lambda r: r['score'], reverse=True)
    board = board[:20]
    for i, u in enumerate(board):
        u['rank']       = i + 1
        u['is_current'] = u['id'] == session['user_id']
    return jsonify(board)




# ════════════════════════════════════════════════════════
# QUIZ
# ════════════════════════════════════════════════════════
@app.route('/api/quiz/<int:aid>')
@login_required
def api_get_quiz(aid):
    a = one(supabase.table('assignments').select('*').eq('id', aid).execute())
    if a:
        co = one(supabase.table('courses').select('title').eq('id', a['course_id']).execute())
        a['course_title'] = co['title'] if co else None
    questions = rows(supabase.table('quiz_questions').select(
        'id,question,option_a,option_b,option_c,option_d,explanation'
    ).eq('assignment_id', aid).execute())
    return jsonify({'assignment': a, 'questions': questions})


@app.route('/api/quiz/add-question', methods=['POST'])
@login_required
def api_add_question():
    d = request.get_json()
    res = supabase.table('quiz_questions').insert({
        'assignment_id': d['assignment_id'], 'question': d['question'],
        'option_a': d['option_a'], 'option_b': d['option_b'],
        'option_c': d.get('option_c'), 'option_d': d.get('option_d'),
        'correct_option': d['correct_option'], 'explanation': d.get('explanation', ''),
    }).execute()
    return jsonify({'success': True, 'id': res.data[0]['id']})


@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def api_submit_quiz():
    d       = request.get_json()
    uid     = session['user_id']
    aid     = d['assignment_id']
    answers = d.get('answers', {})

    questions = rows(supabase.table('quiz_questions').select('*').eq('assignment_id', aid).execute())
    correct   = sum(1 for q in questions if answers.get(str(q['id'])) == q['correct_option'])
    total     = len(questions)
    score     = int((correct / total) * 100) if total else 0

    supabase.table('user_assignments').upsert({
        'user_id': uid, 'assignment_id': aid, 'status': 'graded',
        'score': score, 'submitted_at': now_iso(),
    }, on_conflict='user_id,assignment_id').execute()

    if score >= 60:
        xp_row = one(supabase.table('assignments').select('xp_reward').eq('id', aid).execute())
        if xp_row:
            u = one(supabase.table('users').select('xp').eq('id', uid).execute())
            gained = int(xp_row['xp_reward'] * score / 100)
            supabase.table('users').update({'xp': (u['xp'] or 0) + gained}).eq('id', uid).execute()

    results = [
        {'id': q['id'], 'question': q['question'],
         'your_answer':    answers.get(str(q['id'])),
         'correct_option': q['correct_option'],
         'explanation':    q.get('explanation', ''),
         'options': {'a': q['option_a'], 'b': q['option_b'],
                     'c': q.get('option_c'), 'd': q.get('option_d')}}
        for q in questions
    ]
    return jsonify({'score': score, 'correct': correct,
                    'total': total, 'results': results})


# ════════════════════════════════════════════════════════
# PROFILE
# ════════════════════════════════════════════════════════
@app.route('/api/profile/<int:uid>')
@login_required
def api_profile(uid):
    u = one(supabase.table('users').select(
        'id,full_name,username,level,xp,streak_days,bio,avatar_url').eq('id', uid).execute())

    uach = rows(supabase.table('user_achievements').select('achievement_id,earned_at')
                .eq('user_id', uid).execute())
    ach_ids = [a['achievement_id'] for a in uach]
    badges = []
    if ach_ids:
        achs = rows(supabase.table('achievements').select('id,title,icon').in_('id', ach_ids).execute())
        achs_map = {a['id']: a for a in achs}
        for ua in uach:
            a = achs_map.get(ua['achievement_id'])
            if a:
                badges.append({'title': a['title'], 'icon': a['icon'],
                                'earned_at': str(ua['earned_at'])})

    ucs = rows(supabase.table('user_courses').select('course_id,progress_percent')
               .eq('user_id', uid).execute())
    cids = [uc['course_id'] for uc in ucs]
    courses = []
    if cids:
        crs = rows(supabase.table('courses').select('id,title,category').in_('id', cids).execute())
        crs_map = {c['id']: c for c in crs}
        for uc in ucs:
            c = crs_map.get(uc['course_id'])
            if c:
                courses.append({'title': c['title'], 'category': c['category'],
                                 'progress_percent': uc['progress_percent']})

    return jsonify({'user': u, 'badges': badges, 'courses': courses})


# ════════════════════════════════════════════════════════
# ADMIN
# ════════════════════════════════════════════════════════
@app.route('/api/admin/lessons/<int:lesson_id>/upload-video', methods=['POST'])
@admin_required
def api_admin_upload_video(lesson_id):
    f = request.files.get('video')
    if not f:
        return jsonify({'error': 'No file provided'}), 400
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_VIDEO:
        return jsonify({'error': f'Invalid type. Allowed: {", ".join(ALLOWED_VIDEO)}'}), 400
    fname    = f"lesson_{lesson_id}_{int(datetime.now().timestamp())}.{ext}"
    save_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
    os.makedirs(save_dir, exist_ok=True)
    f.save(os.path.join(save_dir, fname))
    url = f"/video/videos/{fname}"
    supabase.table('lessons').update({'video_url': url}).eq('id', lesson_id).execute()
    return jsonify({'success': True, 'url': url})


@app.route('/api/admin/courses/<int:course_id>/form-url', methods=['POST'])
@admin_required
def api_admin_set_form_url(course_id):
    d   = request.get_json()
    url = d.get('google_form_url', '').strip()
    supabase.table('courses').update({'google_form_url': url}).eq('id', course_id).execute()
    return jsonify({'success': True})


@app.route('/api/admin/courses/add', methods=['POST'])
@admin_required
def api_admin_add_course():
    d = request.get_json()
    if not d.get('title', '').strip():
        return jsonify({'error': 'Title is required'}), 400
    res = supabase.table('courses').insert({
        'title': d['title'].strip(), 'description': d.get('description', ''),
        'instructor': d.get('instructor', ''), 'total_modules': int(d.get('total_modules', 0)),
        'total_hours': float(d.get('total_hours', 0)), 'difficulty': d.get('difficulty', 'Beginner'),
        'category': d.get('category', 'General'), 'xp_reward': int(d.get('xp_reward', 100)),
    }).execute()
    return jsonify({'success': True, 'id': res.data[0]['id']})


@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    students = len(rows(supabase.table('users').select('id').eq('is_admin', False).execute()))
    courses  = len(rows(supabase.table('courses').select('id').execute()))

    lesson_rows = rows(supabase.table('lessons').select('id,youtube_url,video_url').execute())
    lessons    = len(lesson_rows)
    with_video = sum(1 for l in lesson_rows if (l.get('youtube_url') or l.get('video_url')))
    no_video   = lessons - with_video

    completions = len(rows(supabase.table('user_lessons').select('id').execute()))

    return jsonify({'students': students, 'courses': courses,
                    'lessons': lessons, 'with_video': with_video,
                    'no_video': no_video, 'completions': completions})


# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════
def _update_streak(uid):
    u     = one(supabase.table('users').select('last_login,streak_days').eq('id', uid).execute())
    today = date.today()
    last  = u.get('last_login') if u else None
    if isinstance(last, str) and last:
        last = datetime.strptime(last[:10], '%Y-%m-%d').date()

    if last == today:
        pass
    elif last == today - timedelta(days=1):
        supabase.table('users').update({
            'streak_days': (u['streak_days'] or 0) + 1, 'last_login': today.isoformat()
        }).eq('id', uid).execute()
    else:
        supabase.table('users').update({
            'streak_days': 1, 'last_login': today.isoformat()
        }).eq('id', uid).execute()

    try:
        supabase.table('streak_logs').insert({
            'user_id': uid, 'log_date': today.isoformat(),
            'xp_earned': 0, 'lessons_completed': 0, 'minutes_studied': 0,
        }).execute()
    except Exception:
        pass


def _add_notification(uid, title, message, ntype='info'):
    supabase.table('notifications').insert({
        'user_id': uid, 'title': title, 'message': message, 'type': ntype
    }).execute()


# ════════════════════════════════════════════════════════
# VIDEO STREAMING  (HTTP Range requests for seek / scrub)
# ════════════════════════════════════════════════════════
@app.route('/video/<path:filename>')
@login_required
def stream_video(filename):
    upload_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
    file_path   = os.path.abspath(os.path.join(upload_root, filename))

    if not file_path.startswith(upload_root):
        return jsonify({'error': 'Forbidden'}), 403
    if not os.path.isfile(file_path):
        return jsonify({'error': 'File not found'}), 404

    file_size        = os.path.getsize(file_path)
    mime_type, _     = mimetypes.guess_type(file_path)
    mime_type        = mime_type or 'application/octet-stream'
    range_header     = request.headers.get('Range')

    if range_header:
        parts  = range_header.replace('bytes=', '').split('-')
        start  = int(parts[0]) if parts[0] else 0
        end    = int(parts[1]) if parts[1] else file_size - 1
        end    = min(end, file_size - 1)
        length = end - start + 1

        def gen_chunk():
            with open(file_path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return Response(stream_with_context(gen_chunk()), status=206, headers={
            'Content-Range':  f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges':  'bytes',
            'Content-Length': str(length),
            'Content-Type':   mime_type,
            'Cache-Control':  'no-cache',
        })

    def gen_full():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    return Response(stream_with_context(gen_full()), status=200, headers={
        'Content-Length': str(file_size),
        'Content-Type':   mime_type,
        'Accept-Ranges':  'bytes',
        'Cache-Control':  'no-cache',
    })


@app.route('/static/uploads/<path:filename>')
def serve_upload_static(filename):
    return redirect(f'/video/{filename}')


# ════════════════════════════════════════════════════════
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
