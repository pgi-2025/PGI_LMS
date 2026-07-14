// ── State ─────────────────────────────────────────────────────────────────
let allCourses    = [];
let viewerCourse  = null;
let viewerLessons = [];
let currentIdx    = 0;

// Quiz state
let quizQuestions = [];
let quizAnswers   = {};
let quizCurrentQ  = 0;
let quizAssignId  = null;

// ══════════════════════════════════════════════════════════════════════════
// URL NORMALISATION
// ══════════════════════════════════════════════════════════════════════════
function normaliseVideoUrl(raw) {
  if (!raw || !raw.trim()) return '';
  let url = raw.trim().replace(/\\/g, '/');
  if (url.startsWith('http://') || url.startsWith('https://')) return url;

  // Strip Windows-style absolute paths (e.g. C:/Users/.../static/uploads/videos/DM1.mp4)
  // by extracting everything from 'static/uploads/' onward
  const staticIdx = url.indexOf('static/uploads/');
  if (staticIdx !== -1) {
    url = url.slice(staticIdx + 'static/uploads/'.length);
  } else {
    url = url.replace(/^\/+/, '');
  }

  // Also handle paths that already start with videos/ or video/
  if (url.startsWith('video/')) return '/' + url;
  if (!url.startsWith('videos/')) url = 'videos/' + url;
  return '/video/' + url;
}

function normaliseYouTubeUrl(raw) {
  if (!raw || !raw.trim()) return '';
  let url = raw.trim();
  if (url.includes('youtube.com/embed/')) return url;
  if (url.includes('watch?v=')) {
    try {
      const v = new URL(url).searchParams.get('v');
      if (v) return `https://www.youtube.com/embed/${v}`;
    } catch {}
  }
  if (url.includes('youtu.be/')) {
    const v = url.split('youtu.be/')[1].split('?')[0];
    return `https://www.youtube.com/embed/${v}`;
  }
  return url;
}

// ══════════════════════════════════════════════════════════════════════════
// COURSE CARDS
// ══════════════════════════════════════════════════════════════════════════
async function loadCourses() {
  allCourses = await api.get('/api/courses') || [];
  renderCourses(allCourses);
}

const DIFF_CLASS = { Beginner:'tag-b', Intermediate:'tag-i', Advanced:'tag-a' };

function renderCourses(list) {
  const grid = document.getElementById('courses-grid');
  if (!list.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">📚</div><p>No courses found.</p></div>`;
    return;
  }
  grid.innerHTML = list.map(c => {
    const enrolled = !!c.enroll_status;
    const pct      = c.progress_percent || 0;
    const allDone  = enrolled && pct === 100;

    return `
    <div class="course-card ${allDone ? 'completed-card' : ''}"
         onclick="${enrolled ? `openViewer(${c.id})` : `enrollCourse(${c.id},event)`}">
      <div class="course-card-banner"></div>
      <div class="course-card-body">
        <div class="cc-top">
          <div class="cc-icon">${getCourseIcon(c.title)}</div>
          <div>
            <div class="cc-title">${c.title}</div>
            <div class="cc-instructor">👨‍🏫 ${c.instructor || '—'}</div>
            <div class="cc-tags">
              <span class="tag tag-cat">${c.category || 'General'}</span>
              <span class="tag ${DIFF_CLASS[c.difficulty] || 'tag-b'}">${c.difficulty}</span>
              <span class="tag tag-h">⏱ ${c.total_hours}h</span>
            </div>
          </div>
        </div>
        <div class="cc-desc">${c.description || ''}</div>
        ${enrolled ? `
          <div class="cc-progress-row"><span>Progress</span><span>${pct}%</span></div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${pct}%"></div>
          </div>
          <div class="cc-actions">
            <button class="btn btn-primary btn-sm" style="flex:1;justify-content:center">
              ${allDone ? '🔁 Review Lessons' : '▶ Continue Learning'}
            </button>
          </div>
          ${allDone ? `
            <div style="margin-top:10px">
              <div class="card-completed-badge">🏆 All lessons complete</div>
              <div style="margin-top:8px">
                <button class="btn-test-ready"
                        onclick="event.stopPropagation();openCourseTestFromCard(${c.id})">
                  📝 Take Course Test
                </button>
              </div>
            </div>` : ''}
        ` : `
          <div class="cc-actions">
            <button class="btn btn-outline btn-sm" style="flex:1;justify-content:center">
              Enroll Free →
            </button>
          </div>`}
      </div>
    </div>`;
  }).join('');
}

async function enrollCourse(id, e) {
  e.stopPropagation();
  const data = await api.post('/api/courses/enroll', { course_id: id });
  if (data.success) {
    toast.show('Enrolled! 🎉', 'You are enrolled. Start learning!', 'success');
    loadCourses();
  } else {
    toast.show('Error', data.error || 'Could not enroll', 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// VIEWER
// ══════════════════════════════════════════════════════════════════════════
async function openViewer(courseId) {
  const data = await api.get(`/api/courses/${courseId}`);
  if (!data || data.error) { toast.show('Error', 'Could not load course', 'error'); return; }

  viewerCourse  = data.course;
  viewerLessons = data.lessons;

  // Start at first uncompleted; if all done, start at last
  currentIdx = viewerLessons.findIndex(l => !l.completed);
  if (currentIdx === -1) currentIdx = Math.max(0, viewerLessons.length - 1);

  document.getElementById('vt-course-title').textContent = viewerCourse.title;

  // Show/hide test banner based on real completion state
  _updateTestBanner(data.all_done);

  renderLessonsPanel();
  loadLesson(currentIdx);

  document.getElementById('viewer').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeViewer() {
  document.getElementById('viewer').classList.remove('open');
  document.body.style.overflow = '';
  _stopMedia();
  loadCourses();   // refresh cards to show updated progress
}

// ══════════════════════════════════════════════════════════════════════════
// LESSON PLAYER
// ══════════════════════════════════════════════════════════════════════════
function loadLesson(idx) {
  if (idx < 0 || idx >= viewerLessons.length) return;
  currentIdx = idx;
  const l = viewerLessons[idx];

  document.getElementById('lib-title').textContent    = l.title;
  document.getElementById('lib-module').textContent   = `Module ${l.module_number}`;
  document.getElementById('lib-duration').textContent = `⏱ ${l.duration_minutes} min`;
  document.getElementById('lib-xp').textContent       = `⚡ ${l.xp_reward} XP`;
  document.getElementById('lib-content').textContent  = l.content || 'No description for this lesson.';

  const btnC = document.getElementById('btn-complete');
  btnC.innerHTML = l.completed ? '✅ Completed' : '✓ Mark as Complete';
  btnC.disabled  = l.completed;
  btnC.classList.toggle('done', l.completed);

  const isLast = idx === viewerLessons.length - 1;
  const btnN   = document.getElementById('btn-next');
  btnN.textContent = isLast ? '← Back to courses' : 'Next Lesson →';
  btnN.onclick     = isLast ? closeViewer : goNextLesson;

  _renderVideo(l);
  renderLessonsPanel();

  const active = document.querySelector('.lesson-row.active');
  if (active) active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  _updateTopCounter();
}

function _renderVideo(l) {
  const va = document.getElementById('video-area');
  const ph = document.getElementById('video-placeholder');
  _stopMedia();

  const ytUrl   = normaliseYouTubeUrl(l.youtube_url || '');
  const fileUrl = normaliseVideoUrl(l.video_url || '');

  if (ytUrl) {
    ph.style.display = 'none';
    const iframe          = document.createElement('iframe');
    iframe.id             = 'lesson-iframe';
    iframe.src            = ytUrl + '?rel=0&modestbranding=1';
    iframe.allow          = 'accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;fullscreen';
    iframe.allowFullscreen = true;
    iframe.style.cssText  = 'width:100%;height:100%;border:none;display:block;';
    va.insertBefore(iframe, ph);
    return;
  }

  if (fileUrl) {
    ph.style.display = 'none';
    const video          = document.createElement('video');
    video.id             = 'lesson-video';
    video.controls       = true;
    video.preload        = 'metadata';
    video.style.cssText  = 'width:100%;height:100%;object-fit:contain;display:block;background:#000;';

    const ext    = fileUrl.split('.').pop().toLowerCase();
    const mimes  = { mp4:'video/mp4', webm:'video/webm', mov:'video/mp4',
                     avi:'video/x-msvideo', mkv:'video/x-matroska' };
    const source = document.createElement('source');
    source.src   = fileUrl;
    source.type  = mimes[ext] || 'video/mp4';
    video.appendChild(source);

    video.addEventListener('error', () => {
      const code = video.error?.code;
      const msg  = code === 4 ? 'Format not supported — try Chrome/Firefox'
                 : code === 2 ? 'Network error — check file exists on server'
                 : 'Could not load video';
      toast.show('Video error', msg, 'error');
      ph.style.display = 'flex';
      video.remove();
    });

    va.insertBefore(video, ph);
    return;
  }

  ph.style.display = 'flex';
  ph.innerHTML = `
    <div class="vp-icon">📄</div>
    <p>No video for this lesson</p>
    <p class="vp-sub">Read the lesson notes below</p>`;
}

function _stopMedia() {
  const va = document.getElementById('video-area');
  va.querySelectorAll('video').forEach(v => { v.pause(); v.src = ''; v.remove(); });
  va.querySelectorAll('iframe').forEach(f => { f.src = ''; f.remove(); });
}

function _updateTopCounter() {
  const done  = viewerLessons.filter(l => l.completed).length;
  const total = viewerLessons.length;
  document.getElementById('vt-progress').textContent = `${done} / ${total} lessons done`;
}

// ══════════════════════════════════════════════════════════════════════════
// LESSONS SIDEBAR
// ══════════════════════════════════════════════════════════════════════════
function renderLessonsPanel() {
  const list  = document.getElementById('lp-list');
  const done  = viewerLessons.filter(l => l.completed).length;
  const total = viewerLessons.length;
  const pct   = total ? Math.round(done / total * 100) : 0;

  document.getElementById('lp-stats').textContent = `${done} / ${total} done`;
  document.getElementById('lp-fill').style.width  = pct + '%';
  document.getElementById('lp-pct').textContent   = pct + '% complete';

  if (!total) {
    list.innerHTML = '<div style="padding:20px;text-align:center;color:rgba(255,255,255,.3);font-size:13px">No lessons in this course yet.</div>';
    return;
  }

  let html = '', lastMod = null;
  viewerLessons.forEach((l, i) => {
    if (l.module_number !== lastMod) {
      html += `<div class="module-label">Module ${l.module_number}</div>`;
      lastMod = l.module_number;
    }
    const hasYT   = !!(l.youtube_url && l.youtube_url.trim());
    const hasFile = !!(l.video_url   && l.video_url.trim());
    html += `
    <div class="lesson-row ${i === currentIdx ? 'active' : ''} ${l.completed ? 'completed' : ''}"
         onclick="loadLesson(${i})">
      <div class="lr-num">${l.completed ? '✓' : i + 1}</div>
      <div class="lr-info">
        <div class="lr-title">${l.title}</div>
        <div class="lr-meta">${l.duration_minutes}min · ⚡${l.xp_reward}XP
          ${hasYT   ? ' · <span style="color:#f87171;font-size:9px">▶YT</span>'  : ''}
          ${hasFile ? ' · <span style="color:#86efac;font-size:9px">📁Vid</span>': ''}
        </div>
      </div>
      ${l.completed           ? '<span class="lr-check">✓</span>'
        : (hasYT || hasFile)  ? '<span class="lr-icon">▶</span>'
                              : ''}
    </div>`;
  });
  list.innerHTML = html;
}

// ══════════════════════════════════════════════════════════════════════════
// MARK COMPLETE
// ══════════════════════════════════════════════════════════════════════════
async function markComplete() {
  const l = viewerLessons[currentIdx];
  if (!l || l.completed) return;

  const btnC    = document.getElementById('btn-complete');
  btnC.textContent = 'Saving…';
  btnC.disabled = true;

  const res = await api.post('/api/courses/complete-lesson', {
    lesson_id:     l.id,
    module_number: l.module_number,
    duration:      l.duration_minutes,
  });

  if (res && (res.success || res.already_done)) {
    l.completed = true;
    btnC.innerHTML = '✅ Completed';
    btnC.classList.add('done');

    if (!res.already_done) {
      toast.show(`+${res.xp_gained} XP 🎉`, `"${l.title}" completed!`, 'success');
      if (res.cert_issued) {
        setTimeout(() => toast.show('🎓 Certificate!',
          'Course complete! Check Certifications page.', 'success'), 1200);
      }
    }

    // Check if ALL lessons are now done
    const allDone = viewerLessons.every(x => x.completed);
    _updateTestBanner(allDone);
    renderLessonsPanel();
    _updateTopCounter();

  } else {
    toast.show('Error', 'Could not save progress', 'error');
    btnC.innerHTML = '✓ Mark as Complete';
    btnC.disabled  = false;
  }
}

function goNextLesson() {
  if (currentIdx < viewerLessons.length - 1) loadLesson(currentIdx + 1);
}

// ══════════════════════════════════════════════════════════════════════════
// TEST BANNER  — auto-managed, no admin needed
// ══════════════════════════════════════════════════════════════════════════
function _updateTestBanner(allDone) {
  const banner = document.getElementById('test-banner');
  if (!banner) return;
  banner.style.display = allDone ? 'flex' : 'none';
}

// Called from "Take Test" button INSIDE the viewer (when all_done is true)
function openCourseTest() {
  if (!viewerCourse) return;
  _launchCourseTest(viewerCourse.id, viewerCourse.title);
}

// Called from "Take Course Test" button on the CARD (100% complete card)
async function openCourseTestFromCard(courseId) {
  // Load course to get title
  const data = await api.get(`/api/courses/${courseId}`);
  if (!data || data.error) { toast.show('Error', 'Could not load course test', 'error'); return; }
  if (!data.all_done) {
    toast.show('Not yet!', 'Complete all lessons first to unlock the test.', 'info');
    return;
  }
  _launchCourseTest(courseId, data.course.title);
}

async function _launchCourseTest(courseId, courseTitle) {
  // Look for a Quiz-type assignment linked to this course
  const assignments = await api.get('/api/assignments') || [];
  const quiz = assignments.find(a =>
    a.course_id === courseId &&
    a.type === 'Quiz' &&
    a.submission_status !== 'graded'
  );

  if (quiz) {
    // Has a real quiz with questions in the DB
    await _openQuizModal(quiz.id, quiz.title, courseTitle);
  } else {
    // No quiz set up → show a simple self-assessment
    _openSelfAssessment(courseTitle);
  }
}

// ══════════════════════════════════════════════════════════════════════════
// IN-APP QUIZ MODAL
// ══════════════════════════════════════════════════════════════════════════
async function _openQuizModal(assignmentId, quizTitle, courseTitle) {
  const data = await api.get(`/api/quiz/${assignmentId}`);
  if (!data || !data.questions || !data.questions.length) {
    toast.show('No questions', 'This quiz has no questions yet.', 'info');
    return;
  }

  quizQuestions = data.questions;
  quizAnswers   = {};
  quizCurrentQ  = 0;
  quizAssignId  = assignmentId;

  document.getElementById('qt-title').textContent    = quizTitle || 'Course Test';
  document.getElementById('qt-subtitle').textContent = courseTitle;
  document.getElementById('quiz-screen').style.display  = 'block';
  document.getElementById('result-screen').style.display = 'none';

  renderQuizQuestion();
  document.getElementById('quiz-overlay').classList.add('open');
}

function renderQuizQuestion() {
  const q     = quizQuestions[quizCurrentQ];
  const total = quizQuestions.length;
  const pct   = Math.round((quizCurrentQ / total) * 100);

  document.getElementById('q-fill').style.width  = pct + '%';
  document.getElementById('q-number').textContent = `Question ${quizCurrentQ + 1} of ${total}`;
  document.getElementById('q-text').textContent   = q.question;
  document.getElementById('q-answered').textContent =
    `${Object.keys(quizAnswers).length} / ${total} answered`;

  const isLast = quizCurrentQ === total - 1;
  document.getElementById('q-next-btn').textContent = isLast ? '🏁 Submit' : 'Next →';

  const opts = [
    { key: 'a', text: q.option_a },
    { key: 'b', text: q.option_b },
    { key: 'c', text: q.option_c },
    { key: 'd', text: q.option_d },
  ].filter(o => o.text);

  const selected = quizAnswers[q.id];
  document.getElementById('q-options').innerHTML = opts.map(o => `
    <button class="q-option ${selected === o.key ? 'selected' : ''}"
            onclick="selectAnswer('${o.key}')">
      <strong>${o.key.toUpperCase()}.</strong> ${o.text}
    </button>`).join('');
}

function selectAnswer(key) {
  quizAnswers[quizQuestions[quizCurrentQ].id] = key;
  renderQuizQuestion();
}

async function nextQuestion() {
  if (quizCurrentQ < quizQuestions.length - 1) {
    quizCurrentQ++;
    renderQuizQuestion();
  } else {
    await submitQuiz();
  }
}

async function submitQuiz() {
  const res = await api.post('/api/quiz/submit', {
    assignment_id: quizAssignId,
    answers:       quizAnswers,
  });
  if (!res) return;

  // Show results
  document.getElementById('quiz-screen').style.display   = 'none';
  document.getElementById('result-screen').style.display = 'block';

  const score = res.score;
  let emoji, msg;
  if (score >= 90) { emoji = '🏆'; msg = 'Outstanding! Excellent work!'; }
  else if (score >= 75) { emoji = '🎉'; msg = 'Great job! Well done!'; }
  else if (score >= 60) { emoji = '👍'; msg = 'Good effort! Keep practising.'; }
  else { emoji = '📖'; msg = 'Keep studying and try again!'; }

  document.getElementById('r-emoji').textContent = emoji;
  document.getElementById('r-score').textContent = score + '%';
  document.getElementById('r-msg').textContent   = `${msg} (${res.correct}/${res.total} correct)`;

  // Detail breakdown
  if (res.results && res.results.length) {
    document.getElementById('r-detail').innerHTML = res.results.map(r => {
      const correct  = r.your_answer === r.correct_option;
      const icon     = correct ? '✅' : '❌';
      return `<div class="result-detail-row">
        <span style="flex:1;font-size:12px">${icon} ${r.question.slice(0,60)}…</span>
        <span style="font-size:11px;color:var(--text-muted)">${r.your_answer?.toUpperCase() || '—'} → ${r.correct_option.toUpperCase()}</span>
      </div>`;
    }).join('');
  }

  if (score >= 60) {
    setTimeout(() => toast.show('Test passed! 🎉', `Score: ${score}%`, 'success'), 300);
  }
}

// ── Self-assessment fallback (no quiz questions in DB) ──────────────────
function _openSelfAssessment(courseTitle) {
  // Generate 5 simple self-rating questions automatically
  const selfQs = [
    `How well do you understand the core concepts of "${courseTitle}"?`,
    'Can you explain the main topics covered to someone else?',
    'Do you feel confident applying what you learned in a real project?',
    'Have you completed all the lesson notes and exercises?',
    'Are you ready to earn your certificate for this course?',
  ];
  const options = [
    { key:'a', text:'Strongly agree — fully confident' },
    { key:'b', text:'Agree — mostly understand' },
    { key:'c', text:'Neutral — need more practice' },
    { key:'d', text:'Disagree — need to review' },
  ];

  quizQuestions = selfQs.map((q, i) => ({
    id: `self_${i}`,
    question: q,
    option_a: options[0].text,
    option_b: options[1].text,
    option_c: options[2].text,
    option_d: options[3].text,
  }));
  quizAnswers  = {};
  quizCurrentQ = 0;
  quizAssignId = null;   // no DB assignment

  document.getElementById('qt-title').textContent    = 'Course Self-Assessment';
  document.getElementById('qt-subtitle').textContent = courseTitle;
  document.getElementById('quiz-screen').style.display   = 'block';
  document.getElementById('result-screen').style.display = 'none';

  // Override nextQuestion for self-assessment
  document.getElementById('q-next-btn').onclick = nextSelfQ;

  renderQuizQuestion();
  document.getElementById('quiz-overlay').classList.add('open');
}

async function nextSelfQ() {
  if (quizCurrentQ < quizQuestions.length - 1) {
    quizCurrentQ++;
    renderQuizQuestion();
    document.getElementById('q-next-btn').onclick = nextSelfQ;
  } else {
    // Self-assessment — count a/b as positive
    const total   = quizQuestions.length;
    const positive = Object.values(quizAnswers).filter(v => v === 'a' || v === 'b').length;
    const score   = Math.round((positive / total) * 100);

    document.getElementById('quiz-screen').style.display   = 'none';
    document.getElementById('result-screen').style.display = 'block';

    let emoji, msg;
    if (score >= 80) { emoji = '🏆'; msg = 'You\'re ready! Great confidence level.'; }
    else if (score >= 60) { emoji = '👍'; msg = 'Good progress. Review weak areas.'; }
    else { emoji = '📖'; msg = 'Go back and review the lessons again.'; }

    document.getElementById('r-emoji').textContent = emoji;
    document.getElementById('r-score').textContent = score + '%';
    document.getElementById('r-msg').textContent   =
      `Self-assessment complete. ${msg} (${positive}/${total} confident)`;
    document.getElementById('r-detail').innerHTML  = '';
  }
}

function closeQuiz() {
  document.getElementById('quiz-overlay').classList.remove('open');
  // Restore normal nextQuestion
  document.getElementById('q-next-btn').onclick = nextQuestion;
}

// ══════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', loadCourses);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (document.getElementById('quiz-overlay')?.classList.contains('open')) closeQuiz();
    else if (document.getElementById('viewer')?.classList.contains('open')) closeViewer();
  }
});