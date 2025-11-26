import argparse
import os
from src import pdf_processor, extractor, ballooner, excel_writer

import shutil
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="QC Report Generator")
    parser.add_argument("input_pdf", help="Path to the input PDF drawing")
    parser.add_argument("--output_dir", help="Directory to save output files", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.input_pdf):
        print(f"Error: File {args.input_pdf} not found.")
        return

    # Determine Output Directory
    base_output_dir = "QC_Output"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    if args.output_dir:
        # User specified directory, use it but maybe append timestamp? 
        # No, if user specifies, respect it.
        final_output_dir = args.output_dir
    else:
        # Default behavior: QC_Output/<timestamp>
        final_output_dir = os.path.join(base_output_dir, timestamp)
    
    if not os.path.exists(final_output_dir):
        os.makedirs(final_output_dir)

    print(f"Processing {args.input_pdf}...")
    print(f"Output directory: {final_output_dir}")
    
    # 1. Load PDF
    doc = pdf_processor.load_pdf(args.input_pdf)
    if not doc:
        return

    all_features = []
    
    # 2. Process each page
    for page_num, page in enumerate(doc):
        print(f"Processing page {page_num + 1}...")
        img = pdf_processor.get_page_image(page)
        features = extractor.extract_features(page, img, page_num)
        all_features.extend(features)

    # 3. Generate Excel Report
    excel_path = os.path.join(final_output_dir, "qc_report.xlsx")
    print(f"Generating report: {excel_path}")
    excel_writer.generate_excel_report(all_features, excel_path)
    print(f"Generated report: {excel_path}")

    # 4. Generate Ballooned PDF
    pdf_out_path = os.path.join(final_output_dir, "ballooned_drawing.pdf")
    ballooner.add_balloons(args.input_pdf, all_features, pdf_out_path)
    print(f"Generated ballooned PDF: {pdf_out_path}")
    
    # 5. Update 'latest' folder
    if not args.output_dir: # Only if using default structure
        latest_dir = os.path.join(base_output_dir, "latest")
        if os.path.exists(latest_dir):
            shutil.rmtree(latest_dir)
        shutil.copytree(final_output_dir, latest_dir)
        print(f"Updated latest output: {latest_dir}")


if __name__ == "__main__":
    main()
