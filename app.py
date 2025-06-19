import streamlit as st
import requests
from urllib.parse import urlparse, urljoin
import re

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

def clean_url(url: str) -> str:
    """Clean and validate URL"""
    url = url.strip().strip('\'"')
    # Remove any extra http:// or https:// in the middle of the URL
    url = re.sub(r'https?://(?=.*https?://)', '', url)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

# Clean and validate the URL
if url:
    original_url = url
    url = clean_url(url)
    if url != original_url:
        st.info(f"🔄 Cleaned URL: {url}")

# URL type selection
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
                progress_placeholder.info("🔄 Preparing to scrape...")
                
                # Validate URL format
                parsed_url = urlparse(url)
                if not all([parsed_url.scheme, parsed_url.netloc]):
                    st.error("❌ Invalid URL format. Please enter a valid URL.")
                else:
                    # Make request to FastAPI backend
                    api_url = "http://localhost:8000/scrape/url"
                    
                    try:
                        response = requests.post(
                            api_url,
                            json={
                                "url": url,
                                "team_id": team_id
                            },
                            timeout=60  # 60 second timeout
                        )
                        
                        # Handle response
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("items"):
                                st.success("✅ Successfully scraped content!")
                                # Display results
                                for item in result["items"]:
                                    with st.expander(f"📄 {item['title']}", expanded=True):
                                        st.markdown("### Content")
                                        st.markdown(item["content"])
                                        st.markdown("### Metadata")
                                        st.json({
                                            "source_url": item["source_url"],
                                            "author": item["author"],
                                            "content_type": item["content_type"]
                                        })
                            else:
                                st.warning("⚠️ No content found in the response")
                        else:
                            error_msg = response.json().get("detail", "Unknown error")
                            st.error(f"❌ Error: {error_msg}")
                            
                    except requests.exceptions.Timeout:
                        st.error("❌ Request timed out. The server took too long to respond. Try using 'Single Page' mode for large blogs.")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Could not connect to the server. Make sure you've started the API server with 'python main.py'")
                    except Exception as e:
                        st.error(f"❌ An unexpected error occurred: {str(e)}")
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
    else:
        st.warning("⚠️ Please enter a URL to scrape")

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