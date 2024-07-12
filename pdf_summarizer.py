import fitz  # PyMuPDF
import pytesseract
from transformers import BartForConditionalGeneration, BartTokenizer
import torch
import re
import json
import logging
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, scrolledtext

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Ensure that Tesseract OCR path is set from config
pytesseract.pytesseract.tesseract_cmd = config["tesseract_cmd"]

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if CUDA is available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logging.info(f"Using device: {device}")

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF and Tesseract OCR for images."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()

            # Handle images in the PDF
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes))
                text += pytesseract.image_to_string(image)
                
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def preprocess_text(text):
    """Preprocess text by removing unwanted characters and whitespace."""
    try:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        return text.strip()
    except Exception as e:
        logging.error(f"Error preprocessing text: {e}")
        return text

def summarize_text(text):
    """Summarize text using the BART model."""
    try:
        tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
        model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn').to(device)

        inputs = tokenizer.batch_encode_plus([text], max_length=1024, return_tensors='pt', truncation=True).to(device)
        summary_ids = model.generate(inputs['input_ids'], num_beams=4, max_length=150, early_stopping=True)

        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        return ""

def process_pdf(pdf_path, output_widget, summary_widget):
    """Process the PDF and display the result in the output widget."""
    output_widget.delete(1.0, tk.END)
    summary_widget.delete(1.0, tk.END)
    
    # Extract text from PDF
    logging.info(f"Extracting text from PDF: {pdf_path}")
    output_widget.insert(tk.END, f"Extracting text from PDF: {pdf_path}\n")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        logging.error("No text extracted from PDF.")
        output_widget.insert(tk.END, "No text extracted from PDF.\n")
        return

    logging.info("Text extracted successfully.")
    output_widget.insert(tk.END, "Text extracted successfully.\n")
    output_widget.insert(tk.END, text + "\n\n")

    # Preprocess text
    logging.info("Preprocessing text.")
    output_widget.insert(tk.END, "Preprocessing text.\n")
    preprocessed_text = preprocess_text(text)

    # Summarize text
    logging.info("Summarizing text.")
    output_widget.insert(tk.END, "Summarizing text.\n")
    summary = summarize_text(preprocessed_text)
    if not summary:
        logging.error("Failed to summarize text.")
        output_widget.insert(tk.END, "Failed to summarize text.\n")
        return

    logging.info("Text summarized successfully.")
    output_widget.insert(tk.END, "Text summarized successfully.\n\n")
    summary_widget.insert(tk.END, summary + "\n")

def select_file(output_widget, summary_widget):
    """Open a file dialog to select a PDF and process it."""
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        process_pdf(file_path, output_widget, summary_widget)

def save_summary(summary_widget):
    """Save the summary text to a file."""
    summary_text = summary_widget.get(1.0, tk.END).strip()
    if summary_text:
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, "w") as file:
                file.write(summary_text)

def clear_text(output_widget, summary_widget):
    """Clear the text in the output and summary widgets."""
    output_widget.delete(1.0, tk.END)
    summary_widget.delete(1.0, tk.END)

def create_gui():
    """Create the GUI for the PDF summarizer."""
    root = tk.Tk()
    root.title("LZAKE's TEXT SUMMARIZER")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(padx=10, pady=10)

    select_button = tk.Button(frame, text="Select PDF", command=lambda: select_file(output_text, summary_text))
    select_button.pack(pady=10)

    clear_button = tk.Button(frame, text="CLEAR", command=lambda: clear_text(output_text, summary_text))
    clear_button.pack(pady=10)

    save_button = tk.Button(frame, text="SAVE", command=lambda: save_summary(summary_text))
    save_button.pack(pady=10)

    output_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=10)
    output_text.pack(padx=10, pady=10)

    summary_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=10)
    summary_text.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
