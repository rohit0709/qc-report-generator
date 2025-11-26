import streamlit as st
import os
import tempfile
import pandas as pd
import fitz
from src import pdf_processor, extractor, ballooner, excel_writer
import io
import zipfile

# Page config
st.set_page_config(
    page_title="QC Report Generator",
    page_icon="📋",
    layout="wide"
)

# Simple, professional styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("QC Report Generator")
st.markdown("Generate inspection reports from engineering drawings")
st.divider()

# Initialize session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# File upload
uploaded_files = st.file_uploader(
    "Upload PDF Drawing(s)",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"**{len(uploaded_files)} file(s) uploaded**")
    
    # Process button (always processes all files)
    if st.button("Process All Files", type="primary"):
        progress_bar = st.progress(0)
        status = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            status.text(f"Processing {file.name}...")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                doc = pdf_processor.load_pdf(tmp_path)
                
                if doc:
                    all_features = []
                    for page_num, page in enumerate(doc):
                        img = pdf_processor.get_page_image(page)
                        features = extractor.extract_features(page, img, page_num)
                        all_features.extend(features)
                    
                    # Generate outputs in memory with proper naming
                    base_name = file.name.replace('.pdf', '')
                    
                    excel_buffer = io.BytesIO()
                    excel_writer.generate_excel_report(all_features, excel_buffer)
                    excel_buffer.seek(0)
                    
                    pdf_buffer = io.BytesIO()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
                        tmp_out_path = tmp_out.name
                    ballooner.add_balloons(tmp_path, all_features, tmp_out_path)
                    with open(tmp_out_path, 'rb') as f:
                        pdf_buffer.write(f.read())
                    pdf_buffer.seek(0)
                    os.unlink(tmp_out_path)
                    
                    st.session_state.processed_files[file.name] = {
                        'features': all_features,
                        'excel': excel_buffer,
                        'pdf': pdf_buffer,
                        'page_count': len(doc),
                        'base_name': base_name
                    }
                
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status.text("✓ Processing complete")
    
    # Show results if any files are processed
    if st.session_state.processed_files:
        st.divider()
        st.subheader("Results")
        
        # Download all button
        if len(st.session_state.processed_files) > 1:
            # Create zip file with all results
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, results in st.session_state.processed_files.items():
                    base_name = results['base_name']
                    
                    # Add Excel
                    results['excel'].seek(0)
                    zip_file.writestr(f"{base_name}_QC_Report.xlsx", results['excel'].read())
                    
                    # Add PDF
                    results['pdf'].seek(0)
                    zip_file.writestr(f"{base_name}_Ballooned.pdf", results['pdf'].read())
            
            zip_buffer.seek(0)
            st.download_button(
                label="📦 Download All Files (ZIP)",
                data=zip_buffer,
                file_name="QC_Reports.zip",
                mime="application/zip",
                use_container_width=True
            )
            st.write("")
        
        # File selector for preview
        file_names = list(st.session_state.processed_files.keys())
        selected_file_name = st.selectbox("Select file to preview:", file_names)
        results = st.session_state.processed_files[selected_file_name]
        base_name = results['base_name']
        
        # Individual download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📊 Download Excel Report",
                data=results['excel'],
                file_name=f"{base_name}_QC_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📄 Download Ballooned PDF",
                data=results['pdf'],
                file_name=f"{base_name}_Ballooned.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        st.divider()
        
        # Preview section
        st.subheader("Preview")
        
        # Page navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Previous", disabled=st.session_state.current_page == 0):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center'>Page {st.session_state.current_page + 1} of {results['page_count']}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("Next →", disabled=st.session_state.current_page >= results['page_count'] - 1):
                st.session_state.current_page += 1
                st.rerun()
        
        # Display page
        try:
            results['pdf'].seek(0)
            doc_preview = fitz.open(stream=results['pdf'].read(), filetype="pdf")
            if st.session_state.current_page < len(doc_preview):
                page = doc_preview[st.session_state.current_page]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                st.image(img_bytes, use_container_width=True)
        except Exception as e:
            st.error(f"Could not load preview: {e}")
        
        # Data table (collapsed by default)
        with st.expander("View Extracted Data"):
            data = []
            for f in results['features']:
                if f.id is not None:
                    data.append({
                        "Balloon #": f.id,
                        "Type": f.sub_type,
                        "Value": f.value,
                        "Page": f.page_num + 1
                    })
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                st.write(f"Total features: {len(data)}")
            else:
                st.info("No features extracted")

else:
    st.info("👆 Upload one or more PDF files to get started")
