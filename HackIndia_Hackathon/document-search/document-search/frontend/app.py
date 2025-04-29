# frontend/app.py
import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Set page config
st.set_page_config(
    page_title="AI Document Search",
    page_icon="🔍",
    layout="wide",
)

# Add custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .result-card {
        background-color: #f9f9f9;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 5px solid #4CAF50;
    }
    .metadata {
        font-size: 0.8rem;
        color: #666;
    }
    .score {
        font-weight: bold;
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🔍 AI Document Search & Retrieval</div>', unsafe_allow_html=True)
st.markdown("Quickly find and extract insights from your document repository")

# Sidebar
st.sidebar.markdown('<div class="sub-header">📁 Document Management</div>', unsafe_allow_html=True)

# Document Upload
# Change the file uploader to allow multiple files
uploaded_files = st.sidebar.file_uploader("Upload new documents", type=["pdf", "docx", "pptx", "txt", "csv", "json"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # Display spinner for each file
        with st.spinner(f"Uploading {uploaded_file.name}..."):
            # Create a temporary file
            temp_file_path = f"temp_{uploaded_file.name}"
            
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            try:
                # Open the file in a context manager for the request
                with open(temp_file_path, "rb") as file_handle:
                    files = {"file": (uploaded_file.name, file_handle, "application/octet-stream")}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files)
                
                # Now the file handle is properly closed, try to remove the file
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                except PermissionError:
                    st.sidebar.warning(f"Could not remove temporary file for {uploaded_file.name}. It will be removed later.")
                
                if response.status_code == 200:
                    st.sidebar.success(f"Document '{uploaded_file.name}' uploaded successfully!")
                else:
                    st.sidebar.error(f"Error uploading {uploaded_file.name}: {response.text}")
            except Exception as e:
                st.sidebar.error(f"Error connecting to API for {uploaded_file.name}: {str(e)}")
                # Try to remove temporary file in case of error
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                except PermissionError:
                    pass  # Already tried to warn about this above
# Document List
st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sub-header">📚 Document Library</div>', unsafe_allow_html=True)

try:
    response = requests.get(f"{API_BASE_URL}/documents")
    if response.status_code == 200:
        documents = response.json()
        if documents:
            # Create a dataframe for better display
            docs_df = pd.DataFrame(documents)
            docs_df['modified_at'] = docs_df['modified_at'].apply(lambda x: datetime.fromtimestamp(x).strftime('%Y-%m-%d'))
            docs_df = docs_df.rename(columns={
                'title': 'Title',
                'file_type': 'Type',
                'modified_at': 'Modified',
                'chunks': 'Chunks'
            })
            st.sidebar.dataframe(docs_df[['Title', 'Type', 'Modified', 'Chunks']], use_container_width=True)
        else:
            st.sidebar.info("No documents found. Upload some documents to get started.")
    else:
        st.sidebar.warning(f"Error fetching documents: {response.text}")
except Exception as e:
    st.sidebar.error(f"Error connecting to API. Make sure the backend is running: {str(e)}")

# Main content - Search
st.markdown('<div class="sub-header">🔎 Search Documents</div>', unsafe_allow_html=True)
search_query = st.text_input("Enter your search query:", placeholder="What information are you looking for?")
col1, col2 = st.columns([4, 1])
with col1:
    search_button = st.button("Search", type="primary", use_container_width=True)
with col2:
    top_k = st.selectbox("Results:", [3, 5, 10, 20], index=1)

# Display search results
if search_button and search_query:
    with st.spinner("Searching documents..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/search", 
                json={"query": search_query, "top_k": top_k}
            )
            
            if response.status_code == 200:
                results = response.json()["results"]
                
                if results:
                    st.markdown(f"**Found {len(results)} relevant results:**")
                    
                    for i, result in enumerate(results):
                        with st.container():
                            st.markdown(f"""
                            <div class="result-card">
                                <p class="metadata">
                                    <span class="score">Score: {result['score']:.2f}</span> | 
                                    File: {result['metadata']['title']} | 
                                    Type: {result['metadata']['file_type']}
                                </p>
                                <p>{result['text'][:500]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Add a button to show full text
                            if st.button(f"Show full text", key=f"btn_{i}"):
                                st.text_area("Full text", result['text'], height=300)
                else:
                    st.info("No results found. Try a different search query.")
            else:
                st.error(f"Error searching documents: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")

# Summarize functionality
st.markdown("---")
st.markdown('<div class="sub-header">📝 Document Summarization</div>', unsafe_allow_html=True)
st.markdown("Select a document to generate a quick summary")

# Get document list for summarization
try:
    response = requests.get(f"{API_BASE_URL}/documents")
    if response.status_code == 200:
        documents = response.json()
        if documents:
            # Create a selection box with document titles
            doc_titles = {doc['title']: doc['source'] for doc in documents}
            selected_doc = st.selectbox("Select a document to summarize:", list(doc_titles.keys()))
            
            if st.button("Generate Summary", type="primary"):
                # Extract doc_id from source path
                doc_path = doc_titles[selected_doc]
                
                # Find the document with matching source
                doc_id = None
                for doc in documents:
                    if doc['source'] == doc_path:
                        # Extract doc_id from metadata
                        doc_id = os.path.basename(doc_path).split('.')[0]  # Just use filename as ID
                        break
                
                if doc_id:
                    with st.spinner("Generating summary..."):
                        try:
                            response = requests.get(f"{API_BASE_URL}/summarize?doc_id={doc_id}")
                            if response.status_code == 200:
                                summary = response.json()["summary"]
                                st.subheader(f"Summary of '{selected_doc}'")
                                st.markdown(summary)
                            else:
                                st.error(f"Error generating summary: {response.text}")
                        except Exception as e:
                            st.error(f"Error connecting to API: {str(e)}")
                else:
                    st.error("Could not find document ID for summarization")
        else:
            st.info("No documents available for summarization. Please upload some documents first.")
except Exception as e:
    st.error(f"Error fetching document list: {str(e)}")

# Footer
st.markdown("---")
st.markdown("AI Document Search & Retrieval System | Powered by Client Zero")