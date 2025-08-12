import os
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from difflib import SequenceMatcher
import numpy as np

# Core libraries
import PyPDF2
import markdown
import re

# ML libraries (with error handling for optional dependencies)
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not available. Using basic text similarity.")

try:
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    pdf_path: str
    md_path: str
    structural_errors: List[str]
    semantic_similarity: float
    semantic_passed: bool
    readiness_errors: List[str]
    overall_passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pdf_path': self.pdf_path,
            'md_path': self.md_path,
            'structural_errors': self.structural_errors,
            'semantic_similarity': self.semantic_similarity,
            'semantic_passed': self.semantic_passed,
            'readiness_errors': self.readiness_errors,
            'overall_passed': self.overall_passed
        }

class DataQualityEvaluator:
    """Two-stage data quality evaluator for PDF→Markdown conversion"""
    
    def __init__(self, similarity_threshold: float = 0.7, chunk_size: int = 512):
        self.similarity_threshold = similarity_threshold
        self.chunk_size = chunk_size
        
        # Initialize embedding model if available
        self.embedding_model = None
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model for semantic similarity")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF with better error handling"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_pages = []
                
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_pages.append(page_text.strip())
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {i+1}: {e}")
                        continue
                
                full_text = "\n\n".join(text_pages)
                logger.info(f"Extracted {len(full_text)} characters from {len(text_pages)} pages")
                return full_text
                
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}")
            raise
    
    def read_markdown(self, md_path: str) -> str:
        """Read markdown file with encoding detection"""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(md_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Read markdown file with {encoding} encoding")
                return content
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode markdown file {md_path} with any supported encoding")
    
    def structural_check(self, md_text: str) -> List[str]:
        """Enhanced structural validation for markdown"""
        errors = []
        
        # Check for basic markdown structure
        if not re.search(r'^#{1,6}\s+.+', md_text, re.MULTILINE):
            errors.append("No markdown headings found")
        
        # Check for broken links
        if re.search(r'\[\]\(\)', md_text):
            errors.append("Empty links detected: []()")
        
        # Check for broken image references
        if re.search(r'!\[\]\(\)', md_text):
            errors.append("Empty image references detected: ![]()")
        
        # Check for malformed tables
        table_lines = [line for line in md_text.split('\n') if '|' in line]
        if table_lines:
            for i, line in enumerate(table_lines):
                if line.count('|') < 2:  # Should have at least | content |
                    errors.append(f"Malformed table at line with content: {line[:50]}...")
                    break
        
        # Check for incomplete code blocks
        code_block_count = md_text.count('```')
        if code_block_count % 2 != 0:
            errors.append("Unclosed code blocks detected")
        
        # Check for excessive whitespace or formatting issues
        if re.search(r'\n\s*\n\s*\n\s*\n', md_text):
            errors.append("Excessive whitespace detected (4+ consecutive newlines)")
        
        # Check for potential OCR artifacts
        if re.search(r'[^\w\s]{5,}', md_text):
            errors.append("Potential OCR artifacts detected (5+ consecutive special characters)")
        
        return errors
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for similarity comparison"""
        # Simple sentence-based chunking
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if len(chunk) > 20]  # Filter very short chunks
    
    def semantic_similarity_advanced(self, text1: str, text2: str) -> float:
        """Advanced semantic similarity using embeddings"""
        if not self.embedding_model or not HAS_SKLEARN:
            return self.semantic_similarity_basic(text1, text2)
        
        try:
            chunks1 = self.chunk_text(text1)
            chunks2 = self.chunk_text(text2)
            
            if not chunks1 or not chunks2:
                return 0.0
            
            # Get embeddings
            embeddings1 = self.embedding_model.encode(chunks1)
            embeddings2 = self.embedding_model.encode(chunks2)
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings1, embeddings2)
            
            # For each chunk in text1, find best match in text2
            similarities = []
            for i in range(len(chunks1)):
                best_match_score = np.max(similarity_matrix[i])
                similarities.append(best_match_score)
            
            return np.mean(similarities)
            
        except Exception as e:
            logger.warning(f"Advanced similarity failed, falling back to basic: {e}")
            return self.semantic_similarity_basic(text1, text2)
    
    def semantic_similarity_basic(self, text1: str, text2: str) -> float:
        """Basic semantic similarity using SequenceMatcher"""
        # Normalize texts
        text1_clean = re.sub(r'\s+', ' ', text1.lower().strip())
        text2_clean = re.sub(r'\s+', ' ', text2.lower().strip())
        
        # Use SequenceMatcher for basic similarity
        return SequenceMatcher(None, text1_clean, text2_clean).ratio()
    
    def check_markdown_readiness(self, md_text: str) -> List[str]:
        """Enhanced readiness checks for ingestion"""
        errors = []
        
        # Content length check
        if len(md_text.strip()) < 200:
            errors.append("Content too short for meaningful ingestion (<200 chars)")
        
        # Check for placeholder content
        placeholders = ['TODO', 'FIXME', 'XXX', '[PLACEHOLDER]', 'TBD']
        for placeholder in placeholders:
            if placeholder in md_text:
                errors.append(f"Contains placeholder: {placeholder}")
        
        # Check for encoding issues
        if '�' in md_text:
            errors.append("Contains replacement characters (encoding issues)")
        
        # Check for excessive special characters (potential OCR noise)
        special_char_ratio = len(re.findall(r'[^\w\s.,!?;:(){}[\]"\'-]', md_text)) / len(md_text)
        if special_char_ratio > 0.1:
            errors.append(f"High special character ratio ({special_char_ratio:.2%}) - potential OCR noise")
        
        # Check for reasonable word count
        word_count = len(re.findall(r'\b\w+\b', md_text))
        if word_count < 50:
            errors.append(f"Very low word count ({word_count}) - insufficient content")
        
        # Check for proper sentence structure
        sentences = re.split(r'[.!?]+', md_text)
        valid_sentences = [s for s in sentences if len(s.strip().split()) >= 3]
        if len(valid_sentences) < 5:
            errors.append("Insufficient sentence structure for meaningful content")
        
        return errors
    
    def evaluate(self, pdf_path: str, md_path: str) -> EvaluationResult:
        """Main evaluation pipeline"""
        logger.info(f"Starting evaluation: {pdf_path} -> {md_path}")
        
        # Stage 1: Extract and read files
        try:
            pdf_text = self.extract_text_from_pdf(pdf_path)
            md_text = self.read_markdown(md_path)
        except Exception as e:
            logger.error(f"Failed to read input files: {e}")
            raise
        
        # Stage 2: Structural validation
        logger.info("Running structural checks...")
        structural_errors = self.structural_check(md_text)
        
        # Stage 3: Semantic similarity
        logger.info("Computing semantic similarity...")
        similarity = self.semantic_similarity_advanced(pdf_text, md_text)
        semantic_passed = similarity >= self.similarity_threshold
        
        # Stage 4: Readiness checks
        logger.info("Checking markdown readiness...")
        readiness_errors = self.check_markdown_readiness(md_text)
        
        # Overall assessment
        overall_passed = (
            len(structural_errors) == 0 and 
            semantic_passed and 
            len(readiness_errors) == 0
        )
        
        result = EvaluationResult(
            pdf_path=pdf_path,
            md_path=md_path,
            structural_errors=structural_errors,
            semantic_similarity=similarity,
            semantic_passed=semantic_passed,
            readiness_errors=readiness_errors,
            overall_passed=overall_passed
        )
        
        logger.info("Evaluation complete")
        return result
    
    def print_results(self, result: EvaluationResult) -> None:
        """Print formatted results"""
        print("\n" + "="*60)
        print("DATA QUALITY EVALUATION RESULTS")
        print("="*60)
        print(f"PDF: {result.pdf_path}")
        print(f"Markdown: {result.md_path}")
        print(f"Overall Status: {'✓ PASSED' if result.overall_passed else '✗ FAILED'}")
        print("-"*60)
        
        # Structural errors
        print(f"STRUCTURAL CHECKS: {'✓ PASSED' if not result.structural_errors else '✗ FAILED'}")
        if result.structural_errors:
            for error in result.structural_errors:
                print(f"  ✗ {error}")
        
        # Semantic similarity
        print(f"SEMANTIC SIMILARITY: {'✓ PASSED' if result.semantic_passed else '✗ FAILED'}")
        print(f"  Score: {result.semantic_similarity:.3f} (threshold: {self.similarity_threshold})")
        
        # Readiness checks
        print(f"INGESTION READINESS: {'✓ PASSED' if not result.readiness_errors else '✗ FAILED'}")
        if result.readiness_errors:
            for error in result.readiness_errors:
                print(f"  ✗ {error}")
        
        print("="*60)

    def report_failures(self, result: EvaluationResult, md_text: str) -> None:
        """Print detailed reasons for failure, including error context where possible."""
        print("\nFAILURE ANALYSIS")
        print("-" * 60)
        if result.structural_errors:
            print("STRUCTURAL ERRORS:")
            for error in result.structural_errors:
                print(f"  ✗ {error}")
                # Try to show context for certain errors
                if "Malformed table" in error:
                    for i, line in enumerate(md_text.split('\n')):
                        if '|' in line and line.count('|') < 2:
                            print(f"    Line {i+1}: {line}")
                if "Empty links" in error:
                    for i, line in enumerate(md_text.split('\n')):
                        if '[]()' in line:
                            print(f"    Line {i+1}: {line}")
                if "Empty image references" in error:
                    for i, line in enumerate(md_text.split('\n')):
                        if '![]()' in line:
                            print(f"    Line {i+1}: {line}")
                if "Unclosed code blocks" in error:
                    code_block_lines = [i+1 for i, line in enumerate(md_text.split('\n')) if '```' in line]
                    print(f"    Code block markers found at lines: {code_block_lines}")
                if "Potential OCR artifacts" in error:
                    for i, line in enumerate(md_text.split('\n')):
                        if any(len(s) >= 5 for s in re.findall(r'[^\w\s]{5,}', line)):
                            print(f"    Line {i+1}: {line}")
        if not result.structural_errors:
            print("No structural errors.")
        print()
        if not result.semantic_passed:
            print(f"SEMANTIC SIMILARITY FAILED: Score {result.semantic_similarity:.3f} < threshold {self.similarity_threshold}")
        else:
            print("Semantic similarity passed.")
        print()
        if result.readiness_errors:
            print("INGESTION READINESS ERRORS:")
            for error in result.readiness_errors:
                print(f"  ✗ {error}")
                if "placeholder" in error.lower():
                    for i, line in enumerate(md_text.split('\n')):
                        if any(ph in line for ph in ['TODO', 'FIXME', 'XXX', '[PLACEHOLDER]', 'TBD']):
                            print(f"    Line {i+1}: {line}")
                if "replacement characters" in error.lower():
                    for i, line in enumerate(md_text.split('\n')):
                        if '' in line:
                            print(f"    Line {i+1}: {line}")
        else:
            print("No ingestion readiness errors.")
        print("-" * 60)

def main():
    parser = argparse.ArgumentParser(
        description="Data Quality Evaluator - Two-stage PDF→Markdown validation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf document.pdf --md document.md
  %(prog)s --pdf doc.pdf --md doc.md --threshold 0.8 --chunk-size 256
        """
    )
    
    parser.add_argument("--pdf", type=str, required=True, 
                       help="Path to the original PDF file")
    parser.add_argument("--md", type=str, required=True,
                       help="Path to the converted Markdown file")
    parser.add_argument("--threshold", type=float, default=0.7,
                       help="Semantic similarity threshold (default: 0.7)")
    parser.add_argument("--chunk-size", type=int, default=512,
                       help="Text chunk size for similarity analysis (default: 512)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input files
    if not Path(args.pdf).exists():
        print(f"Error: PDF file not found: {args.pdf}")
        return 1
    
    if not Path(args.md).exists():
        print(f"Error: Markdown file not found: {args.md}")
        return 1
    
    # Run evaluation
    try:
        evaluator = DataQualityEvaluator(
            similarity_threshold=args.threshold,
            chunk_size=args.chunk_size
        )
        
        result = evaluator.evaluate(args.pdf, args.md)
        evaluator.print_results(result)
        
        # If failed, print detailed failure analysis
        if not result.overall_passed:
            md_text = evaluator.read_markdown(args.md)
            evaluator.report_failures(result, md_text)
        
        # Return appropriate exit code
        return 0 if result.overall_passed else 1
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())