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

query = st.text_area(
    "Job Requirement",
    placeholder="e.g. Looking for a senior software engineer with Python, React and AWS experience",
    height=100,
    key="query_input",
)
top_k = st.selectbox("Results", [3, 5, 10], index=1, key="top_k_select")

if st.button("Search", type="primary", use_container_width=True):
    if not query.strip():
        st.error("Please enter a job requirement.")
    else:
        with st.spinner("Running pipeline..."):
            try:
                resp = requests.post(
                    f"{API_URL}/search",
                    json={"query": query, "top_k": top_k, "expand_queries": True},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state.results = data["results"]
                st.session_state.requirements = data["requirements"]
                st.session_state.last_query = query
                st.session_state.email_popup = None
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
                st.markdown(f"**Years Exp:** {exp if exp >= 0 else 'Unknown'}")

            just_col, email_col = st.columns([1, 1])
            with just_col:
                with st.expander("💬 Justification"):
                    st.markdown(r["justification"])
            with email_col:
                if st.button("📧 Send Email", key=f"eb_{r['id']}", use_container_width=True):
                    st.session_state.email_popup = r["id"]
                    st.rerun()

            if st.session_state.email_popup == r["id"]:
                st.markdown("---")
                st.markdown("### ✉️ Shortlist Email")
                col_left, col_right = st.columns([3, 1])
                with col_left:
                    to_email = st.text_input("Recipient Email", key=f"to_{r['id']}", placeholder="candidate@email.com")
                with col_right:
                    st.markdown("")
                    st.markdown("")
                    if st.button("❌ Close", key=f"cl_{r['id']}"):
                        st.session_state.email_popup = None
                        st.rerun()

                edit_subject = st.text_input("Subject", value=r.get("email_subject", ""), key=f"sub_{r['id']}")
                edit_body = st.text_area("Body", value=r.get("email_body", ""), height=200, key=f"bod_{r['id']}")

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
