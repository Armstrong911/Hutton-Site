import os
import anthropic
import resend
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
resend.api_key = os.environ.get("RESEND_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "admin@huttonstrata.com")
PORTAL_URL = os.environ.get("PORTAL_URL", "")

DESTINATIONS = [
    {"name": "Services",            "url": "/services",           "keywords": ["services","manage","management","strata","condo","building","property"]},
    {"name": "FAQ",                 "url": "/faq",                "keywords": ["faq","question","questions","help","how","what","when","why"]},
    {"name": "Contact",             "url": "/contact",            "keywords": ["contact","call","phone","email","reach","talk","speak"]},
    {"name": "Maintenance Request", "url": "/forms/maintenance",  "keywords": ["maintenance","repair","fix","broken","leak","heat","plumbing","electrical"]},
    {"name": "Complaint",           "url": "/forms/complaint",    "keywords": ["complaint","noise","neighbor","neighbour","dispute","issue","problem"]},
    {"name": "Owner Registration",  "url": "/forms/registration", "keywords": ["register","registration","owner","new owner","move in","moved"]},
    {"name": "Realtor Request",     "url": "/forms/realtor",      "keywords": ["realtor","real estate","agent","listing","sell","sale","mls"]},
    {"name": "Lender Request",      "url": "/forms/lender",       "keywords": ["lender","mortgage","bank","financing","loan"]},
    {"name": "Legal Request",       "url": "/forms/legal",        "keywords": ["legal","lawyer","litigation","bylaw","rule","enforcement","court"]},
    {"name": "Strata Documents",    "url": "/forms/strata-docs",  "keywords": ["documents","docs","minutes","bylaws","financials","budget","records"]},
    {"name": "Pre-Authorized Debit","url": "/forms/debit",        "keywords": ["debit","pad","payment","fees","strata fees","pre-authorized"]},
    {"name": "Form K",              "url": "/forms/form-k",       "keywords": ["form k","formk","tenant","rental","renting","landlord","lease"]},
    {"name": "Client Portal",       "url": "__portal__",          "keywords": ["login","portal","sign in","client portal","document","my documents","owner login"]},
]

def keyword_route(query):
    q = query.lower()
    for d in DESTINATIONS:
        for kw in d["keywords"]:
            if kw in q:
                return d
    return None

def ai_route(query):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        dest_list = "\n".join([f"- {d['name']}: {d['url']}" for d in DESTINATIONS])
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role":"user","content":f"A visitor to Hutton Property Management asked: '{query}'\n\nAvailable pages:\n{dest_list}\n\nReply with ONLY the URL that best matches their question, nothing else."}]
        )
        url = msg.content[0].text.strip()
        for d in DESTINATIONS:
            if d["url"] == url:
                return d
    except:
        pass
    return None

def send_email(subject, body):
    try:
        resend.Emails.send({"from":"noreply@huttonstrata.com","to":NOTIFY_EMAIL,"subject":subject,"text":body})
    except:
        pass

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        fields = request.form.to_dict()
        body = "\n".join([f"{k}: {v}" for k,v in fields.items()])
        send_email("Contact Form - Hutton", body)
        return redirect(url_for("success"))
    return render_template("contact.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    query = (data or {}).get("query","").strip()
    if not query:
        return jsonify({"message":"Please type a question."})
    dest = keyword_route(query) or ai_route(query)
    if dest:
        url = PORTAL_URL if dest["url"] == "__portal__" and PORTAL_URL else (dest["url"] if dest["url"] != "__portal__" else "/contact")
        return jsonify({"message":"I can help with that.", "url":url, "destination_name":dest["name"]})
    return jsonify({"message":"I'm not sure about that — try browsing our services or contact us directly.", "url":"/contact", "destination_name":"Contact Us"})

def form_route(template, subject_prefix):
    if request.method == "POST":
        fields = request.form.to_dict()
        body = "\n".join([f"{k}: {v}" for k,v in fields.items()])
        send_email(f"{subject_prefix} - Hutton", body)
        return redirect(url_for("success"))
    return render_template(template)

@app.route("/forms/maintenance", methods=["GET","POST"])
def form_maintenance(): return form_route("form_maintenance.html","Maintenance Request")

@app.route("/forms/complaint", methods=["GET","POST"])
def form_complaint(): return form_route("form_complaint.html","Complaint")

@app.route("/forms/registration", methods=["GET","POST"])
def form_registration(): return form_route("form_registration.html","Owner Registration")

@app.route("/forms/realtor", methods=["GET","POST"])
def form_realtor(): return form_route("form_realtor.html","Realtor Request")

@app.route("/forms/lender", methods=["GET","POST"])
def form_lender(): return form_route("form_lender.html","Lender Request")

@app.route("/forms/legal", methods=["GET","POST"])
def form_legal(): return form_route("form_legal.html","Legal Request")

@app.route("/forms/strata-docs", methods=["GET","POST"])
def form_strata_docs(): return form_route("form_strata_docs.html","Strata Documents Request")

@app.route("/forms/debit", methods=["GET","POST"])
def form_debit(): return form_route("form_debit.html","Pre-Authorized Debit")

@app.route("/forms/form-k", methods=["GET","POST"])
def form_k(): return form_route("form_k.html","Form K")

@app.route("/success")
def success(): return render_template("success.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
