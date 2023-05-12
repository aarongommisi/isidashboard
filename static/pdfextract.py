import os
import sys
import re
import pdfplumber
import csv
import gc
import shutil
import time
import argparse
from tqdm import tqdm
from PyPDF2 import PdfMerger
import datetime

# Add this function to merge PDFs
def merge_pdfs(pdf_files, output_path):
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    with open(output_path, "wb") as merged_pdf:
        merger.write(merged_pdf)

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text(x_tolerance=2)  # Adjust the x_tolerance value as needed
    return text

def extract_information(text, business_entity):
    inspection_no = re.search(r"#InspectionID#\s*(\d+)", text)
    job_no = re.search(r"#JobID#\s*(\d+)", text)
    client_id = re.search(r"#ClientID#\s*(.+)", text)
    serial_no = re.search(r"#SerialNumber#\s*(.+)", text)
    date = re.search(r"#VisitDate#\s*(\d{2}/\d{2}/\d{4})", text)

    intolerable = re.search(r"Intolerable - Defects requiring immediate action\s*(.+)", text)
    substantial = re.search(r"Substantial - Defects requiring attention within a(?:\stime period)?\s*(.+)", text)
    moderate = re.search(r"Moderate - Other defects requiring attention\s*(.+)", text)

    priority = ""
    if intolerable and intolerable.group(1).strip().lower() not in ["", "none"]:
        priority = "Intolerable"
    elif substantial and substantial.group(1).strip().lower() not in ["", "none"]:
        priority = "Substantial"
    elif moderate and moderate.group(1).strip().lower() not in ["", "none"]:
        priority = "Moderate"

    remedial_works = []
    if intolerable and intolerable.group(1).strip().lower() != "none":
        remedial_works.append(intolerable.group(1).strip())
    if substantial and substantial.group(1).strip().lower() != "none":
        remedial_works.append(substantial.group(1).strip())
    if moderate and moderate.group(1).strip().lower() != "none":
        remedial_works.append(moderate.group(1).strip())

    remedial_works_notes = " ".join(remedial_works)

    if date:
        date_action_raised = datetime.datetime.strptime(date.group(1), "%d/%m/%Y")
        formatted_date = date_action_raised.strftime("%d%m%Y")

        if priority == "Moderate":
            target_date = date_action_raised + datetime.timedelta(days=180)
        elif priority == "Substantial":
            target_date = date_action_raised + datetime.timedelta(days=30)
        elif priority == "Intolerable":
            target_date = date_action_raised + datetime.timedelta(days=7)
        else:
            target_date = None
        
        if target_date:
            target_completion_date = target_date.strftime("%d/%m/%Y")
        else:
            target_completion_date = ""
    else:
        target_completion_date = ""

    info = {
        "Inspection Ref / Job No": f"{business_entity}-PWR-{formatted_date}-{job_no.group(1) if job_no else ''}",
        "Remedial Reference Number": f"{business_entity}-PWR-{formatted_date}-{job_no.group(1) if job_no else ''}-{inspection_no.group(1) if inspection_no else ''}",
        "Action Owner": "PiC",
        "Date Action Raised": date.group(1) if date else "",
        "Corrective Job Number": "",
        "Remedial Works Action Required/Notes": f"{remedial_works_notes} - Client-ID:{client_id.group(1)}, - Serial Number:{serial_no.group(1)}",
        "Priority": priority,
        "Target Completion Date": target_completion_date,
        "Actual Completion Date": "",
        "PiC Comments": "",
        "Property Inspection Ref. No.": "",
        "Asset No": business_entity,
        "Business Entity": business_entity,
    }

    return info


def main(input_folder, output_folder, processed_folder, business_entity):
    csv_file = os.path.join(output_folder, f"{business_entity}-PWR-ADDDATE.csv")
    with open(csv_file, "w", newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        header = ["Inspection Ref / Job No", "Remedial Reference Number", "Action Owner", "Date Action Raised", "Corrective Job Number", "Remedial Works Action Required/Notes", "Priority", "Target Completion Date", "Actual Completion Date", "PiC Comments", "Property Inspection Ref. No.", "Asset No", "Business Entity"]
        csvwriter.writerow(header)

    processed_pdfs = []
    skipped_pdfs = []

    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            print(f"Processing {filename}...")
            pdf_path = os.path.join(input_folder, filename)
            text = extract_text_from_pdf(pdf_path)

            # Add this condition to process only PDFs containing "#JobType# PUWER"
            if "#JobType# PUWER" in text:
                information = extract_information(text, business_entity)

                if information["Remedial Works Action Required/Notes"].strip().lower() == "none":
                    print(f"{filename} has no remedial actions. Skipping...\n")
                    continue

                if information["Priority"] in ["Intolerable", "Substantial", "Moderate"]:
                    with open(csv_file, "a", newline='', encoding='utf-8') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        row = [information[key] for key in header]
                        csvwriter.writerow(row)
                else:
                    print(f"{filename} has no remedial actions. Skipping...\n")

                processed_pdfs.append(pdf_path)
            else:
                print(f"{filename} does not contain #JobType# PUWER. Skipping...\n")
                skipped_pdfs.append(pdf_path)

    merged_pdf_path = os.path.join(output_folder, f"{business_entity}-PWR-ADDDATE.pdf")
    merge_pdfs(processed_pdfs, merged_pdf_path)

    skipped_pdf_path = os.path.join(output_folder, f"{business_entity}-FAULTYREPORTS-ADDDATE.pdf")
    merge_pdfs(skipped_pdfs, skipped_pdf_path)

    for pdf_path in tqdm(processed_pdfs + skipped_pdfs, desc="Moving files", unit="file"):
        shutil.copy(pdf_path, os.path.join(processed_folder, os.path.basename(pdf_path)))
        time.sleep(1)  # Add a short delay before removing the original file
        gc.collect()  # Force garbage collection to free up resources
        os.remove(pdf_path)
    return merged_pdf_path, csv_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input folder containing PDF files")
    parser.add_argument("--output", required=True, help="Output folder for generated files")
    parser.add_argument("--processed", required=True, help="Processed folder for completed files")
    parser.add_argument("--business_entity", required=True, help="Business entity for the processing")
    args = parser.parse_args()

    main(args.input, args.output, args.processed, args.business_entity)
