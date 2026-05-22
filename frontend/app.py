import json
import re
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Resume Intelligence", page_icon="🔍", layout="wide")

st.title("🔍 AI Resume Intelligence & Candidate Matching")
st.markdown("Enter a job requirement in natural language to find matching candidates.")

for key in ["results", "requirements", "last_query"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "email_popup" not in st.session_state:
    st.session_state.email_popup = None
if "bg_verification" not in st.session_state:
    st.session_state.bg_verification = {}

query = st.text_area(
    "Job Requirement",
    placeholder="e.g. Looking for a senior software engineer with Python, React and AWS experience",
    height=100,
    key="query_input",
)
if st.button("Search", type="primary", use_container_width=True):
    if not query.strip():
        st.error("Please enter a job requirement.")
    else:
        with st.status("Searching candidates...", expanded=True) as status:
            try:
                resp = requests.post(
                    f"{API_URL}/search/stream",
                    json={"query": query, "top_k": 3, "expand_queries": True},
                    stream=True,
                    timeout=120,
                )
                resp.raise_for_status()

                data = None
                for line in resp.iter_lines():
                    if not line:
                        continue
                    raw = line.decode("utf-8")
                    if not raw.startswith("data: "):
                        continue
                    event = json.loads(raw[6:])

                    if event.get("type") == "step":
                        step = event["step"]
                        evt_status = event["status"]
                        detail = event.get("detail", "")
                        t = event.get("time")
                        if evt_status == "running":
                            status.write(f"⏳ **{step}**...")
                        elif evt_status == "done":
                            label = f"✅ **{step}**"
                            if t is not None:
                                label += f" — {t:.1f}s"
                            if detail:
                                label += f"  \n_{detail}_"
                            status.write(label)
                        elif evt_status == "skipped":
                            status.write(f"⏭️ **{step}** — skipped")

                    elif event.get("type") == "result":
                        data = event
                        status.update(
                            label=f"✅ Found {len(data['results'])} candidates in {data['elapsed']:.1f}s",
                            state="complete",
                        )
                    elif event.get("type") == "error":
                        status.update(label="❌ Search failed", state="error")
                        st.error(event["message"])
                        data = None

                if data:
                    st.session_state.results = data["results"]
                    st.session_state.requirements = data["requirements"]
                    st.session_state.last_query = query
                    st.session_state.email_popup = None
                    st.session_state.bg_verification = {}
                    st.rerun()

            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to API at {API_URL}")
            except Exception as e:
                st.error(f"Error: {e}")

if st.session_state.results:
    reqs = st.session_state.requirements
    results = st.session_state.results

    with st.expander("📋 Extracted Requirements", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Skills:** {', '.join(reqs['skills']) if reqs['skills'] else 'None detected'}")
            st.markdown(f"**Seniority:** {reqs['seniority']}")
        with col2:
            st.markdown(f"**Category:** {reqs['category']}")
            st.markdown(f"**Must Have:** {', '.join(reqs['must_have']) if reqs['must_have'] else 'None'}")
        with col3:
            st.markdown(f"**Nice to Have:** {', '.join(reqs['nice_to_have']) if reqs['nice_to_have'] else 'None'}")
            st.markdown(f"**Min Experience:** {reqs['years_experience'] if reqs['years_experience'] else 'Not specified'}")

    st.success(f"Found {len(results)} matching candidates")
    st.divider()

    for i, r in enumerate(results):
        score_color = "🟢" if r["overall_score"] >= 70 else "🟡" if r["overall_score"] >= 40 else "🔴"
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                st.markdown(f"### {score_color} #{i+1} — {r['id']}")
                st.markdown(f"**Overall Score:** {r['overall_score']}/100")
            with col2:
                st.markdown(f"**Skills:** {', '.join(r['skills'][:10])}")
                st.markdown(f"**Role:** {r['role_category']}")
            with col3:
                st.markdown(f"**Skill Score:** {r['skill_score']}/100")
                st.markdown(f"**Experience Score:** {r['experience_score']}/100")
                exp = r["years_experience"]
                st.markdown(f"**Years Exp:** {exp if exp is not None and exp >= 0 else 'Unknown'}")

            just_col, bg_col, email_col = st.columns([1, 1, 1])
            with just_col:
                with st.expander("💬 Justification"):
                    st.markdown(r["justification"])
            with bg_col:
                if st.button("🔍 Run BG Verification", key=f"bg_{r['id']}", use_container_width=True):
                    with st.spinner("Logging into LinkedIn and fetching profile..."):
                        try:
                            detail_resp = requests.get(f"{API_URL}/candidates/{r['id']}", timeout=10)
                            linkedin_url = None
                            if detail_resp.ok:
                                detail = detail_resp.json()
                                text = detail.get("clean_text", "") or ""
                                sections = detail.get("sections", {})
                                all_text = text + " " + " ".join(sections.values())
                                match = re.search(r'(https?://)?(www\.)?linkedin\.com/in/[\w\-%]+', all_text, re.IGNORECASE)
                                if match:
                                    linkedin_url = match.group(0)

                            if linkedin_url:
                                bg_resp = requests.post(
                                    f"{API_URL}/bg-verification",
                                    json={"linkedin_url": linkedin_url},
                                    timeout=120,
                                )
                                if bg_resp.ok:
                                    bg_data = bg_resp.json()
                                    st.session_state.bg_verification[r["id"]] = bg_data
                                else:
                                    st.session_state.bg_verification[r["id"]] = {
                                        "status": "error",
                                        "message": "BG verification API failed",
                                    }
                            else:
                                st.session_state.bg_verification[r["id"]] = {
                                    "status": "error",
                                    "message": "No LinkedIn URL found in resume",
                                }
                        except Exception as e:
                            st.session_state.bg_verification[r["id"]] = {
                                "status": "error",
                                "message": f"Error: {str(e)}",
                            }
                    st.rerun()

            if r["id"] in st.session_state.bg_verification:
                bg = st.session_state.bg_verification[r["id"]]
                if bg.get("status") == "success":
                    with st.expander("✅ BG Verification — LinkedIn Profile"):
                        about = bg.get("about", "")
                        if about:
                            st.markdown("### 📋 About")
                            st.markdown(about)
                        experience = bg.get("experience", [])
                        if experience:
                            st.markdown("### 💼 Experience")
                            for i, exp in enumerate(experience, 1):
                                with st.container(border=True):
                                    st.markdown(f"**{exp.get('title', '')}**")
                                    if exp.get('company'):
                                        st.markdown(f"🏢 {exp['company']}")
                                    info_parts = []
                                    if exp.get('dates'):
                                        info_parts.append(f"📅 {exp['dates']} ({exp.get('duration', '')})")
                                    if exp.get('location'):
                                        info_parts.append(f"📍 {exp['location']}")
                                    if exp.get('mode'):
                                        info_parts.append(f"🏠 {exp['mode']}")
                                    if exp.get('employment_type'):
                                        info_parts.append(f"💼 {exp['employment_type']}")
                                    if info_parts:
                                        st.markdown(" · ".join(info_parts))
                                    if exp.get('skills'):
                                        st.markdown(f"**Skills:** {', '.join(exp['skills'])}")
                                    if exp.get('description'):
                                        st.markdown(f"_{exp['description'][:300]}_")
                elif bg.get("status") == "error":
                    st.error(f"❌ {bg.get('message', 'BG verification failed')}")
            with email_col:
                if st.button("📧 Send Email", key=f"eb_{r['id']}", use_container_width=True):
                    st.session_state.email_popup = r["id"]
                    st.rerun()

            if st.session_state.email_popup == r["id"]:
                st.divider()
                with st.container(border=True):
                    col_title, col_close = st.columns([5, 1])
                    with col_title:
                        st.markdown("### ✉️ Interview Invitation")
                    with col_close:
                        if st.button("❌ Close", key=f"cl_{r['id']}"):
                            st.session_state.email_popup = None
                            st.rerun()

                    default_subject = r.get("email_subject", "") or "Interview Invitation – Let's Schedule a Time"
                    default_body = r.get("email_body", "") or (
                        f"Dear {r['id']},\n\n"
                        f"Congratulations! Your profile stood out for this role and we'd love to invite you for an interview. "
                        f"Your skills and experience are a great match for what we're looking for.\n\n"
                        f"Could you please suggest a few convenient times next week so we can schedule a call?\n\n"
                        f"Looking forward to speaking with you.\n\nBest regards,\nNaga Rithesh"
                    )
                    to_email = st.text_input("Recipient Email", value=r.get("email", ""), key=f"to_{r['id']}", placeholder="candidate@email.com")
                    edit_subject = st.text_input("Subject", value=default_subject, key=f"sub_{r['id']}")
                    edit_body = st.text_area("Body", value=default_body, height=200, key=f"bod_{r['id']}")

                    if st.button("✅ Send Email", key=f"send_{r['id']}", type="primary"):
                        if to_email:
                            st.success(f"📧 Email ready to send to **{to_email}**\n\n"
                                       f"**Subject:** {edit_subject}\n\n"
                                       f"**Body:**\n{edit_body}")
                        else:
                            st.error("Please enter a recipient email address")

            with st.expander("📄 Full Resume"):
                try:
                    detail_resp = requests.get(f"{API_URL}/candidates/{r['id']}", timeout=10)
                    if detail_resp.ok:
                        detail = detail_resp.json()
                        sections = detail.get("sections", {})
                        st.markdown(f"## {sections.get('header', r['id'])}")
                        st.markdown(f"**Role:** {detail.get('role_category', 'N/A')}  |  **Experience:** {detail.get('years_experience', 'N/A')} yrs")
                        st.markdown(f"**Skills:** {', '.join(detail['skills'])}")
                        st.divider()
                        for sec_name in ["summary", "experience", "education", "skills", "projects", "certifications"]:
                            content = sections.get(sec_name, "")
                            if content:
                                st.markdown(f"### {sec_name.title()}")
                                st.markdown(content)
                    else:
                        st.info("Full details not available")
                except Exception:
                    st.info("Could not fetch full details")
