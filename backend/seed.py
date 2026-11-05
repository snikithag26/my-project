"""Create demo accounts + one sample profile.  Run: python -m backend.seed"""
import json
from backend.app import auth, db

db.init_db()
SAMPLE = {"name": "Aarav Sharma", "age": "9", "gender": "Male", "city": "Hyderabad",
          "tags": ["Autism Spectrum Disorder", "Support level 2", "Verbal, limited"],
          "details": [["Date of birth", "14 Mar 2017"], ["Parent / guardian", "Neha Sharma"], ["Contact", "+91 90000 00000"], ["School", "Inclusive Primary School, Grade 4"], ["Language", "English, Telugu"], ["Blood group", "B+"]],
          "care": [["Diagnosed", "Jun 2020 (age 3)"], ["Diagnosed by", "Dr. R. Menon, Developmental Pediatrician"], ["Therapist", "Speech & OT, 3 sessions / week"], ["Co-conditions", "Sleep difficulty, mild ADHD traits"], ["Allergies", "Peanuts"]],
          "meds": ["Melatonin 1 mg - 30 min before bed", "Vitamin D3 - weekly"],
          "sensory": ["Sensitive to loud sounds and hand dryers", "Seeks deep pressure (weighted blanket)", "Avoids certain food textures", "Dislikes bright flickering lights"],
          "triggers": ["Sudden changes in routine", "Crowded, noisy places", "Transitions between activities"],
          "helps": ["Visual schedule and 5-minute warnings", "Noise-cancelling headphones", "Quiet corner with fidget toys", "Interests: trains, puzzles, music"],
          "faces": [], "sessions": [], "mood": [], "assessments": []}
with db.get_conn() as c:
    for email, name, role in (("parent@demo.com", "Neha Sharma", "parent"), ("therapist@demo.com", "Dr. R. Menon", "therapist"), ("teacher@demo.com", "Ms. Rao", "teacher")):
        if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            continue
        salt = auth.new_salt()
        cur = c.execute("INSERT INTO users(email,name,role,salt,pw_hash) VALUES(?,?,?,?,?)", (email, name, role, salt, auth.hash_pw("demo1234", salt)))
        if role == "parent":
            c.execute("INSERT OR IGNORE INTO people(id, owner_id, data) VALUES(?,?,?)", ("demo-aarav", cur.lastrowid, json.dumps({**SAMPLE, "id": "demo-aarav"})))
print("Demo users ready: parent@demo.com / therapist@demo.com / teacher@demo.com  (password: demo1234)")
