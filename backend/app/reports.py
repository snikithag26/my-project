"""PDF report for parents, teachers and therapists."""
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAL = colors.HexColor("#2f7f79")


def build_report(p: dict, author: dict) -> bytes:
    ss = getSampleStyleSheet()
    h1, h2, body = ss["Title"], ss["Heading2"], ss["BodyText"]
    h2.textColor = TEAL
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title=f"AutiSphere report - {p.get('name','')}")
    para = lambda t, st=body: Paragraph(escape(str(t)), st)
    s = [para(f"AutiSphere report: {p.get('name', '')}", h1),
         para(f"Age {p.get('age') or '-'} · {p.get('gender') or '-'} · {p.get('city') or '-'}"),
         para(f"Prepared {datetime.now():%d %b %Y} for {author['name']} ({author['role']})"), Spacer(1, 10)]

    def table(rows):
        t = Table([[Paragraph(f"<b>{escape(a)}</b>", body), para(b or "-")] for a, b in rows], colWidths=[4.5 * cm, 12 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey)]))
        return t

    s += [para("Details", h2), table(p.get("details", []) + p.get("care", []))]
    for key, title in (("sensory", "Sensory profile"), ("triggers", "Known triggers"), ("helps", "What helps"), ("meds", "Medication")):
        if p.get(key):
            s += [para(title, h2)] + [para("• " + x) for x in p[key]]

    ass = p.get("assessments", [])
    if ass:
        s.append(para("Recent assessments", h2))
        for a in ass[-5:][::-1]:
            if a["type"] == "screening":
                s.append(para(f"{a['at'][:10]} · Screening: {a['level']} (AQ-10 {a['score']}/10, model probability {round(a['probability'] * 100)}%)"))
            else:
                s.append(para(f"{a['at'][:10]} · Stress forecast: {a['level']} ({a['risk']}%)"))

    mood = p.get("mood", [])
    if mood:
        vals = [m["v"] for m in mood[-14:]]
        s += [para("Mood", h2), para(f"Average of last {len(vals)} entries: {sum(vals) / len(vals):.1f} / 5 (lowest {min(vals)}, highest {max(vals)})")]

    sess = p.get("sessions", [])
    if sess:
        s.append(para("Expression sessions", h2))
        s += [para(f"{x['at'][:16].replace('T', ' ')} · {x['secs']} s · {x['parts']}") for x in sess[:6]]

    s += [Spacer(1, 14), para("This report is a support summary, not a medical diagnosis. Screening and expression results can be wrong; please discuss concerns with a qualified professional.", ss["Italic"])]
    doc.build(s)
    return buf.getvalue()
