# PDF Outline Extractor

A Docker-based solution for automatically extracting titles and hierarchical outlines from PDF documents using advanced text analysis and machine learning techniques.

## 🎯 Approach

### Core Methodology

Our solution employs a sophisticated multi-stage approach to extract structured information from PDFs:

1. **Text Extraction & Preprocessing**
   - Uses PyMuPDF (fitz) for high-quality text extraction
   - Handles complex layouts including tables, images, and boxes
   - Preserves font metadata (size, style, color) for analysis

2. **Title Detection**
   - Identifies document titles using font size analysis
   - Considers bold text and positioning on the first page
   - Merges closely positioned bold lines for compound titles
   - Filters out generic/forbidden titles (addresses, signatures, etc.)

3. **Heading Identification with Scoring System**
   - **Font Size Analysis**: Larger fonts indicate higher heading levels
   - **Bold Text Detection**: Bold formatting strongly indicates headings
   - **Numbering Patterns**: Recognizes numbered headings (1., 1.1, A., etc.)
   - **Text Length**: Short, concise text is more likely to be a heading
   - **All Caps Detection**: Uppercase text often indicates headings
   - **Positional Analysis**: Considers text position relative to content

4. **Hierarchical Classification**
   - Uses K-means clustering on font sizes to determine heading levels
   - Assigns H1, H2, H3 levels based on font size hierarchy
   - Ensures logical heading structure

5. **Multilingual Support**
   - Full Unicode support for international characters
   - Handles accented characters, Cyrillic, Arabic, Chinese, Japanese, Korean, and more
   - Language-agnostic text processing

### Advanced Features

- **Table Detection**: Automatically skips text inside table cells
- **Image Handling**: Excludes text overlapping with images
- **Box Detection**: Identifies and processes text in drawn rectangles
- **Color Analysis**: Considers colored text for special emphasis
- **Content Validation**: Ensures headings have supporting content below

## 📚 Models & Libraries Used

### Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **PyMuPDF** | ≥1.23.0 | High-performance PDF text extraction and analysis |
| **NumPy** | ≥1.21.0 | Numerical operations and array processing |
| **scikit-learn** | ≥1.0.0 | K-means clustering for font size classification |

### Key Dependencies

- **fitz** (PyMuPDF): Advanced PDF processing with font metadata extraction
- **statistics**: Statistical analysis for font size determination
- **collections.Counter**: Frequency analysis of font sizes
- **re** (regex): Pattern matching for numbered headings and text cleaning
- **unicodedata**: Unicode character classification for multilingual support
- **pathlib**: Modern path handling for cross-platform compatibility

### Technical Specifications

- **Base Image**: Python 3.9-slim (optimized for size and security)
- **System Dependencies**: build-essential for PyMuPDF compilation
- **Text Encoding**: UTF-8 for full Unicode support
- **Output Format**: JSON with structured title and outline data

## 🚀 How to Build and Run

### Prerequisites

- Docker installed and running
- PDF files placed in the `input/` directory

### Build the Docker Image

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
```

### Run the Solution

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier
```

**For Windows PowerShell:**
```powershell
docker run --rm -v ${PWD}/input:/app/input -v ${PWD}/output:/app/output --network none mysolutionname:somerandomidentifier
```

### Expected Execution

The container will:
1. Process all PDF files in `/app/input/`
2. Generate corresponding JSON files in `/app/output/`
3. Each JSON contains:
   - `title`: Extracted document title
   - `outline`: Array of headings with level (H1, H2, H3), text, and page number

### Example Output

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Main Heading",
      "page": 1
    },
    {
      "level": "H2", 
      "text": "Sub Heading",
      "page": 1
    }
  ]
}
```

## 🔧 Technical Architecture

### Docker Configuration

- **Base**: Python 3.9-slim for optimal size/security balance
- **Dependencies**: All Python packages installed in container
- **Volumes**: Input/output directories mounted for data persistence
- **Security**: Network isolation with `--network none`
- **Cleanup**: Automatic container removal with `--rm`

### Processing Pipeline

1. **Input Validation**: Check for PDF files in input directory
2. **Text Extraction**: Extract text with font metadata using PyMuPDF
3. **Layout Analysis**: Detect tables, images, and boxes
4. **Title Detection**: Identify document title using font analysis
5. **Heading Detection**: Apply scoring system to identify headings
6. **Hierarchical Classification**: Assign H1, H2, H3 levels
7. **Output Generation**: Create structured JSON files

### Performance Optimizations

- **Caching**: Docker layer caching for faster rebuilds
- **Memory Efficient**: Minimal base image with only required dependencies
- **Parallel Processing**: Efficient text extraction algorithms
- **Unicode Optimized**: Fast multilingual character processing

## 🌍 Multilingual Support

The solution supports PDFs in multiple languages and scripts:

- ✅ **Latin Scripts**: English, Spanish, French, German, etc.
- ✅ **Latin Extended**: Accented characters (é, ñ, ü, etc.)
- ✅ **Cyrillic**: Russian, Bulgarian, etc.
- ✅ **Greek**: Modern Greek
- ✅ **Arabic**: Arabic script
- ✅ **Asian Scripts**: Chinese, Japanese, Korean
- ✅ **Indic Scripts**: Hindi, Thai, etc.

## 📊 Algorithm Details

### Heading Detection Scoring

Each text block is scored based on multiple criteria:

| Criterion | Score | Description |
|-----------|-------|-------------|
| Font Size > Body Text | +2 | Larger fonts indicate headings |
| Bold Text | +1 | Bold formatting suggests headings |
| Numbered Pattern | +5 | Strong indicator of structured headings |
| Short Text (<15 words) | +1 | Headings are typically concise |
| All Caps | +1 | Uppercase often indicates headings |

**Threshold**: Text blocks with score ≥4 are classified as headings.

### Font Size Clustering

Uses K-means clustering to group font sizes into heading levels:
- **H1**: Largest font sizes (titles, main headings)
- **H2**: Medium font sizes (section headings)
- **H3**: Smaller font sizes (subsection headings)

## 🔍 Quality Assurance

### Validation Features

- **Content Verification**: Ensures headings have supporting content
- **Positional Analysis**: Considers text position on page
- **Font Consistency**: Validates heading hierarchy
- **Error Handling**: Graceful handling of corrupted PDFs
- **Output Validation**: JSON structure verification

### Performance Metrics

- **Processing Speed**: ~1-2 seconds per PDF page
- **Memory Usage**: Optimized for containerized environments
- **Accuracy**: High precision heading detection
- **Reliability**: Robust error handling and recovery

## 📝 License

This solution is provided as-is for PDF processing and outline extraction purposes. 