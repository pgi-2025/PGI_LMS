-- Run once in Supabase -> SQL Editor
CREATE TABLE IF NOT EXISTS course_payments (
  id BIGSERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  razorpay_order_id TEXT UNIQUE NOT NULL,
  razorpay_payment_id TEXT,
  amount INT NOT NULL DEFAULT 49,
  status TEXT NOT NULL DEFAULT 'created',  -- created | paid
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cp_user_course ON course_payments(user_id, course_id, status);
