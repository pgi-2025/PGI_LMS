-- ============================================================================
-- ADD "DIGITAL MARKETING" COURSE  (run in Supabase -> SQL Editor)
-- ============================================================================
-- HOW TO USE
--   1. Replace every  PASTE_VIDEO_ID_HERE  below with your YouTube video link.
--      Any of these formats work:
--         https://www.youtube.com/watch?v=abc123XYZ
--         https://youtu.be/abc123XYZ
--         https://www.youtube.com/embed/abc123XYZ
--      (Playlist links and Shorts links will NOT play.)
--   2. Edit the title / instructor / description / hours if you want.
--   3. Click RUN once. Running it twice creates the course twice.
--
-- THE VIDEO LINK GOES IN:   lessons.video_url   (one link per lesson)
-- ============================================================================

WITH new_course AS (
  INSERT INTO courses
    (title, description, instructor, total_modules, total_hours,
     difficulty, category, xp_reward)
  VALUES
    ('Digital Marketing',
     'Learn SEO, Google Ads, social media, content and email marketing, and analytics to grow a brand online.',
     'PGI Faculty',          -- <- change to your instructor name
     8,                      -- total_modules (must match number of lessons below)
     4,                      -- total_hours   (8 lessons x 30 min)
     'Beginner',
     'Marketing',
     400)
  RETURNING id
)
INSERT INTO lessons
  (course_id, module_number, title, content, video_url, duration_minutes, xp_reward)
SELECT
  new_course.id, v.module_number, v.title, v.content, v.video_url, v.duration_minutes, v.xp_reward
FROM new_course,
(VALUES
  (1, 'Introduction to Digital Marketing',
      'What digital marketing is, the main channels, and how a marketing funnel works.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (2, 'Search Engine Optimization (SEO)',
      'Keywords, on-page SEO, off-page SEO, and how search engines rank pages.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (3, 'Google Ads & Search Engine Marketing',
      'Setting up campaigns, choosing keywords, writing ads, and controlling budget.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (4, 'Social Media Marketing',
      'Building a presence on Instagram, Facebook, LinkedIn and YouTube, plus paid social ads.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (5, 'Content Marketing',
      'Planning content, storytelling, blogs, video, and a content calendar.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (6, 'Email Marketing',
      'Building an email list, writing campaigns, automation, and measuring open and click rates.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (7, 'Web Analytics & Reporting',
      'Google Analytics basics, tracking conversions, and reading campaign reports.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10),

  (8, 'Affiliate Marketing & Final Project',
      'Affiliate and influencer marketing, plus a wrap-up project tying every channel together.',
      'https://www.youtube.com/watch?v=PASTE_VIDEO_ID_HERE', 30, 10)
) AS v(module_number, title, content, video_url, duration_minutes, xp_reward);


-- ----------------------------------------------------------------------------
-- LATER: to change a video link after the course already exists
-- ----------------------------------------------------------------------------
-- UPDATE lessons
--    SET video_url = 'https://www.youtube.com/watch?v=YOUR_REAL_ID'
--  WHERE module_number = 1
--    AND course_id = (SELECT id FROM courses WHERE title = 'Digital Marketing');
--
-- Or simply: Supabase -> Table Editor -> lessons -> edit the video_url cell.
