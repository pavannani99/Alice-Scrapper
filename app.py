import streamlit as st
import requests

# Set the page config
st.set_page_config(page_title="Technical Content Scraper", layout="centered")

# Page header
st.title("📚 Technical Content Scraper")
st.markdown("""
This tool allows you to extract structured knowledge (in Markdown) from:
- 🔗 Any technical blog (like `https://interviewing.io/blog`)
- 📄 PDF documents (like Aline's book)
- ✍️ Substack articles

The backend returns data in a reusable, standardized format for Aline and other customers.
""")

# Input: Team ID (defaulted to aline123)
team_id = st.text_input("Team ID", value="aline123")

# --- Section 1: Scrape from URL ---
st.subheader("🔗 Scrape Blog / Guide / Substack")

url = st.text_input("Enter URL (e.g., https://interviewing.io/blog/how-to-succeed)")

# Clean and validate the URL
if url:
    url = url.strip()
    # Remove any whitespace or quotes
    url = url.strip('\'"')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        st.info(f"🔄 Added https:// to URL: {url}")

# After the URL input field:
url_type = st.radio(
    "URL Type",
    ["Single Page", "Index Page (like interviewing.io/topics#companies)"]
)

if st.button("Scrape URL"):
    if url:
        try:
            progress_placeholder = st.empty()
            with st.spinner(""):
                # Show detailed progress
                progress_placeholder.info("🔄 Initializing scraper...")
                
                # Determine the endpoint based on URL type
                endpoint = "scrape/url"
                if url_type == "Index Page (like interviewing.io/topics#companies)":
                    endpoint = "scrape/index"
                    progress_placeholder.info("🔄 Preparing to crawl index page...")
                else:
                    progress_placeholder.info("🔄 Preparing to scrape single page...")
                
                # Make the API request with shorter timeout
                res = requests.post(
                    f"http://localhost:8000/{endpoint}",
                    json={"url": url, "team_id": team_id},
                    timeout=20
                )
                
                if res.status_code == 200:
                    progress_placeholder.success("✅ Content retrieved successfully!")
                    result = res.json()
                    if isinstance(result, dict):
                        if result.get('detail'):
                            st.warning(result['detail'])
                        elif result.get('items'):
                            st.success(f"✅ Successfully scraped {len(result['items'])} items!")
                            st.json(result)
                        else:
                            st.json(result)
                else:
                    error_msg = "Unknown error"
                    try:
                        error_data = res.json()
                        error_msg = error_data.get('detail', str(error_data))
                    except:
                        error_msg = res.text
                    st.error(f"❌ Failed to scrape URL.\n\n{error_msg}")
        
        except requests.Timeout:
            st.error("❌ Request timed out. The server took too long to respond. Please try again.")
        except requests.ConnectionError:
            st.error("❌ Connection error. Please make sure the backend server is running.")
        except requests.RequestException as e:
            st.error(f"❌ Connection error: {str(e)}")
    else:
        st.warning("⚠️ Please enter a URL to scrape.")

# --- Section 2: Scrape from PDF ---
st.subheader("📄 Scrape from PDF (e.g., Aline's book)")

pdf_file = st.file_uploader("Upload PDF", type=["pdf"])

if st.button("Scrape PDF"):
    if pdf_file:
        with st.spinner("Processing PDF..."):
            res = requests.post(
                "http://localhost:8000/scrape/pdf",
                files={"file": (pdf_file.name, pdf_file, "application/pdf")},
                data={"team_id": team_id}
            )
        if res.status_code == 200:
            st.success("✅ PDF processed successfully!")
            st.json(res.json())
        else:
            st.error(f"❌ Failed to parse PDF.\n\n{res.text}")
    else:
        st.warning("⚠️ Please upload a PDF file.")