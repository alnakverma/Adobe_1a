import os
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from collections import Counter
import unicodedata

# Configuration
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Regex for decorative separators
SEPARATOR_RE = re.compile(r"^[\-\—\–\s]{3,}$")
# Default black color in PyMuPDF
DEFAULT_COLOR = 0
# Regex to detect address-like titles (contains digits and letters)
ADDRESS_RE = re.compile(r"\d+.*[A-Za-z]+")
# List of forbidden/generic titles
FORBIDDEN_TITLES = {"ADDRESS:", "NAME:", "DATE:", "SIGNATURE:"}
# Regex to detect numbered heading prefixes (e.g., 1., 1.1, 2.3.4) but not numbers alone
NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2})(?:\.(\d{1,2}))*\.(?=\s*\S)")
# Set of keywords that should always be added as headings (normalized)
ALWAYS_HEADING_KEYWORDS = {"tableofcontent", "tableofcontents", "summary", "acknowledgement", "acknowledgements"}

def normalize_heading(text):
    """Normalize text for comparison, supporting multilingual characters."""
    # Convert to lowercase and remove non-alphabetic characters
    normalized = re.sub(r'[^a-z\u00c0-\u017f]', '', text.lower())
    return normalized

def is_multilingual_character(char):
    """Check if character is from a multilingual script."""
    try:
        # Check if character is from non-Latin scripts
        category = unicodedata.category(char)
        # Include letters from various scripts
        if category.startswith('L'):
            # Check for non-Latin scripts
            if ord(char) > 127:  # Non-ASCII characters
                return True
        return False
    except:
        return False

def extract_text_lines(page):
    """
    Extract text spans from a page, skipping any text inside drawn rectangles (boxes).
    Decorative lines and colored text are retained unless boxed.
    Returns list of dicts with text metadata.
    """
    # Get all rectangles (any boxes) and images
    drawings = page.get_drawings()
    box_rects = [fitz.Rect(d["rect"]) for d in drawings if d["type"] == "rect"]
    # Detect table-heavy layout
    table_zone = len(box_rects) >= 5

    image_rects = [fitz.Rect(d["rect"]) for d in drawings if d["type"] == "image"]

    lines = []
    lines_in_boxes = {i: [] for i in range(len(box_rects))}
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            text = " ".join(span["text"].strip() for span in spans if span["text"].strip())
            if not text:
                continue

            bbox = fitz.Rect(line["bbox"])
            # Check if inside any box
            inside_box_idx = None
            for i, r in enumerate(box_rects):
                expanded_box = r + (-5, -5, 5, 5)
                if expanded_box.intersects(bbox):
                    inside_box_idx = i
                    break
            # Check if inside any image
            if any((r + (-5, -5, 5, 5)).intersects(bbox) for r in image_rects):
                continue

            # If this page is likely a table, skip text intersecting table cells
            if table_zone and any((r + (-2, -2, 2, 2)).intersects(bbox) for r in box_rects):
                continue

            size = max(span.get("size", 0) for span in spans)
            fonts = [span.get("font", "") for span in spans]
            flags = sum(span.get("flags", 0) for span in spans)
            y0 = min(span.get("bbox")[1] for span in spans)
            # Check color: PyMuPDF color is int, 0 is black
            colors = [span.get("color", 0) for span in spans]
            is_colored = any(c != 0 for c in colors)

            line_data = {
                "text": text,
                "size": size,
                "fonts": fonts,
                "flags": flags,
                "y0": y0,
                "is_colored": is_colored
            }
            if inside_box_idx is not None:
                lines_in_boxes[inside_box_idx].append(line_data)
            else:
                lines.append(line_data)
    
    # Add single-line-in-box as heading candidates (even if colored)
    for box_lines in lines_in_boxes.values():
        if len(box_lines) == 1:
            # Mark as from_box for clarity (optional)
            box_lines[0]["from_box"] = True
            lines.append(box_lines[0])
    
    # Add text immediately above each box as heading candidate if bold or large font
    for i, rect in enumerate(box_rects):
        # Find lines just above the top of the box (within 20 units)
        above_lines = [ln for ln in lines if ln["y0"] < rect.y0 and rect.y0 - ln["y0"] < 20]
        for ln in above_lines:
            # Only add if bold or large font (e.g., > mean size)
            if is_bold(ln["fonts"], ln["flags"]) or ln["size"] > 0:  # mean size can be calculated in process_pdf
                ln["from_above_box"] = True
                ln["above_box_idx"] = i
                lines.append(ln)
    return lines

def is_bold(fonts, flags):
    return any("Bold" in f for f in fonts) or (flags & 2 != 0)

def process_pdf(path):
    doc = fitz.open(path)
    # --- Title extraction: boldest, largest text on first page ---
    page0 = doc.load_page(0)
    lines0 = extract_text_lines(page0)
    title = ""
    title_size = 0
    colored_title_candidates = []
    
    if lines0:
        # Get page height
        page_height = page0.rect.height
        # Find all bold lines within top 50% of the page
        bold_lines = sorted([ln for ln in lines0 if is_bold(ln["fonts"], ln["flags"]) and ln["y0"] <= page_height * 0.5], key=lambda x: x["y0"])
        if len(bold_lines) >= 2:
            # If the top two bold lines are close together vertically, merge them as title
            if abs(bold_lines[1]["y0"] - bold_lines[0]["y0"]) < 100:
                candidate = f"{bold_lines[0]['text']} {bold_lines[1]['text']}"
                size_val = max(bold_lines[0]["size"], bold_lines[1]["size"])
                if candidate and candidate not in FORBIDDEN_TITLES and not ADDRESS_RE.match(candidate) and ',' not in candidate and '-' not in candidate:
                    title = candidate
                    title_size = size_val
            else:
                # Fallback to the topmost bold line
                candidate = bold_lines[0]["text"]
                size_val = bold_lines[0]["size"]
                if candidate and candidate not in FORBIDDEN_TITLES and not ADDRESS_RE.match(candidate) and ',' not in candidate and '-' not in candidate:
                    title = candidate
                    title_size = size_val
        elif bold_lines:
            candidate = bold_lines[0]["text"]
            size_val = bold_lines[0]["size"]
            if candidate and candidate not in FORBIDDEN_TITLES and not ADDRESS_RE.match(candidate) and ',' not in candidate and '-' not in candidate:
                title = candidate
                title_size = size_val
        # Fallback: previous logic for colored text at top position
        top_y = min(ln["y0"] for ln in lines0)
        tops = [ln for ln in lines0 if abs(ln["y0"] - top_y) < 1.0]
        colored = [ln for ln in tops if ln.get("is_colored", False)]
        if colored:
            colored_title_candidates = colored

    # --- Collect all text lines for heading detection ---
    all_lines = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        for ln in extract_text_lines(page):
            all_lines.append({**ln, "page": i+1})
    # Add colored title candidates as H1 heading on page 1 if not already present
    for ln in colored_title_candidates:
        all_lines.append({**ln, "page": 1})

    # Compute mean size for exclamation detection and large font
    sizes = [ln["size"] for ln in all_lines]
    mean_size = sum(sizes) / len(sizes) if sizes else 0

    texts = [ln["text"] for ln in all_lines]

    # Detect H1 size from the first detected H1 heading
    h1_size = None
    for ln in all_lines:
        if is_bold(ln["fonts"], ln["flags"]):
            if h1_size is None or ln["size"] > h1_size:
                h1_size = ln["size"]

    # Heading detection
    outline = []
    h1_sz = h2_sz = None
    for idx, ln in enumerate(all_lines):

         # Ignore lines inside boxes
        if ln.get("from_box"):
            continue

        txt = ln["text"]
        sz = ln["size"]
        fonts = ln["fonts"]
        flags = ln["flags"]
        pg = ln["page"]

        # Skip title in outline
        if pg == 1 and txt == title:
            continue

        # Exclude headings that contain a comma
        if ',' in txt:
            continue

        # Improved multilingual support: Check for alphabetic characters without language assumptions
        first_alpha = next((c for c in txt if c.isalpha()), None)
        if first_alpha:
            # For multilingual support, we need to be more flexible
            # Only exclude if it's clearly a lowercase Latin character and not part of a multilingual script
            if first_alpha.islower() and not is_multilingual_character(first_alpha):
                # Additional check: if the text is very short and starts with lowercase, it might be a heading
                if len(txt.strip()) < 3:
                    continue
                # For longer texts, be more permissive with multilingual content
                if len(txt.strip()) < 10 and not any(is_multilingual_character(c) for c in txt):
                    continue

        # Exclude headings ending with a colon if they have more than 6 words (word = length > 3)
        if txt.endswith(":"):
            word_count_colon = sum(1 for w in txt.split() if len(w) > 3)
            if word_count_colon > 6:
                continue

        # Check standalone bold: neighbors blank or nonexistent
        prev_txt = texts[idx-1] if idx > 0 else None
        next_txt = texts[idx+1] if idx < len(all_lines)-1 else None
        standalone_bold = is_bold(fonts, flags) and (not prev_txt or not prev_txt.strip()) and (not next_txt or not next_txt.strip())

        # Must have content below
        has_content_below = idx < len(all_lines)-1 and bool(all_lines[idx+1]["text"].strip())
        if not has_content_below:
            continue

        # Heading criteria: standalone bold, endswith colon, large exclamation, or numbered prefix
        numbered_match = NUMBERED_HEADING_RE.match(txt)
        is_numbered_heading = False
        if numbered_match:
            # Only allow if first number <= 10 and text after prefix is not empty and not just a number
            first_num = int(numbered_match.group(1))
            # Get the text after the prefix
            after_prefix = txt[numbered_match.end():].strip()
            if first_num <= 10 and after_prefix and not after_prefix.replace('.', '').isdigit():
                is_numbered_heading = True
        if not (standalone_bold or txt.endswith(":") or (txt.endswith("!") and sz > mean_size * 1.2) or is_numbered_heading):
            continue

        # Exclude headings with more than 7 words (word = length > 3)
        word_count = sum(1 for w in txt.split() if len(w) > 3)
        if word_count > 7:
            continue

        # Improved multilingual support for first word check
        first_word = txt.split()[0] if txt.split() else ""
        if first_word:
            # Be more permissive with multilingual content
            if (first_word[0].islower() and 
                len(first_word) < 4 and 
                not is_multilingual_character(first_word[0]) and
                not any(is_multilingual_character(c) for c in first_word)):
                continue

        # Always add certain keywords as headings (robust match)
        if any(normalize_heading(txt) == keyword for keyword in ALWAYS_HEADING_KEYWORDS):
            # Assign level by font size
            if h1_sz is None or sz == h1_sz:
                if h1_sz is None:
                    h1_sz = sz
                level = "H1"
            elif h2_sz is None or sz == h2_sz:
                if h2_sz is None and sz < h1_sz:
                    h2_sz = sz
                level = "H2"
            else:
                level = "H3"
            outline.append({"level": level, "text": txt, "page": pg, "size": sz})
            continue

        # Add: If line is from_above_box and not used as title, and is bold or large font
        if ln.get("from_above_box") and txt != title and (is_bold(fonts, flags) or sz > mean_size):
            # Assign level by font size
            if h1_sz is None or sz == h1_sz:
                if h1_sz is None:
                    h1_sz = sz
                level = "H1"
            elif h2_sz is None or sz == h2_sz:
                if h2_sz is None and sz < h1_sz:
                    h2_sz = sz
                level = "H2"
            else:
                level = "H3"
            outline.append({"level": level, "text": txt, "page": pg, "size": sz})
            continue

        # Treat as heading if same size as H1 (and not inside table/image)
        if h1_size is not None and sz == h1_size:
            level = "H1"
            outline.append({"level": level, "text": txt, "page": pg, "size": sz})
            continue

        # Assign level by font size
        if h1_sz is None or sz == h1_sz:
            if h1_sz is None:
                h1_sz = sz
            level = "H1"
        elif h2_sz is None or sz == h2_sz:
            if h2_sz is None and sz < h1_sz:
                h2_sz = sz
            level = "H2"
        else:
            level = "H3"

        outline.append({"level": level, "text": txt, "page": pg, "size": sz})

    # Remove title if title_size < max heading size
    max_heading_sz = 0
    if outline:
        # Use the first heading's size as a reference if available
        # But since we no longer store size, skip this check
        pass
    # Exclude forbidden titles from outline
    outline = [item for item in outline if item["text"] not in FORBIDDEN_TITLES]
    # Add colored title candidates as H1 if not already in outline
    for ln in colored_title_candidates:
        if not any(item["text"] == ln["text"] and item["page"] == 1 for item in outline):
            outline.insert(0, {"level": "H1", "text": ln["text"], "page": 1})
    # After all headings are detected, ensure the first heading after the title is H1
    if outline:
        outline[0]["level"] = "H1"
        h1_size = outline[0].get("size")
        for item in outline[1:]:
            if "size" in item and item["size"] == h1_size:
                item["level"] = "H1"
            else:
                item["level"] = "H2"
    # After all headings are detected, assign H1, H2, H3, H4, H6 based on size
    sizes = sorted({item["size"] for item in outline if "size" in item}, reverse=True)
    level_map = {0: "H1", 1: "H2", 2: "H3", 3: "H4", 4: "H6"}
    for item in outline:
        if "size" in item:
            idx = sizes.index(item["size"])
            item["level"] = level_map.get(idx, "H6")
    # Remove the 'size' field before returning
    for item in outline:
        item.pop("size", None)
    return {"title": title, "outline": outline}

def main():
    """Main function to process all PDFs in the input directory."""
    print("Starting PDF processing...")
    
    # Ensure input directory exists
    if not INPUT_DIR.exists():
        print(f"Input directory {INPUT_DIR} does not exist!")
        return
    
    # Find all PDF files
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in input directory.")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    # Process each PDF file
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        
        # Process the PDF
        result = process_pdf(str(pdf_file))
        
        # Create output filename
        output_file = OUTPUT_DIR / f"{pdf_file.stem}.json"
        
        # Write the result to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"  -> {output_file.name}")
    
    print("Processing complete!")

if __name__ == "__main__":
    main()