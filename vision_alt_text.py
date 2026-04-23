#!/usr/bin/env python3
"""
Vision-based Alt Text Generator for PDF Images

Uses OCR or Vision Language Models (VLMs) to generate alternative text
for images found in PDFs. Supports multiple backends:
- Local: ollama (llava, bakllava)
- Cloud: Azure Computer Vision, AWS Rekognition, Google Vision
- OCR: pytesseract (for text-heavy images)

This is for HUMAN_REVIEW issues - generates suggestions that need human verification.
"""

import base64
import io
import json
from pathlib import Path
from typing import Optional

from PIL import Image


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "vision_results"


def extract_images_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract images from PDF using PyPDF.
    Returns list of image data with metadata.
    """
from pypdf import PdfReader as PdfDoc
    
    images = []
    
    with PdfDoc.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            resources = page.get("/Resources", {})
            xobjects = resources.get("/XObject", {})
            
            if not xobjects:
                continue
            
            for obj_name, xobj in xobjects.items():
                if xobj.get("/Subtype") == "/Image":
                    try:
                        # Extract image data
                        width = xobj.get("/Width", 0)
                        height = xobj.get("/Height", 0)
                        color_space = xobj.get("/ColorSpace", "/DeviceRGB")
                        bits_per_component = xobj.get("/BitsPerComponent", 8)
                        
                        # Get image stream
                        img_data = xobj.read_bytes()
                        
                        # Try to decode as PIL Image
                        try:
                            pil_image = Image.open(io.BytesIO(img_data))
                            images.append({
                                "pdf_path": str(pdf_path),
                                "page": page_num,
                                "object_name": str(obj_name),
                                "width": width,
                                "height": height,
                                "color_space": str(color_space),
                                "image": pil_image,
                                "image_bytes": img_data
                            })
                        except Exception:
                            # May be raw image data needing conversion
                            images.append({
                                "pdf_path": str(pdf_path),
                                "page": page_num,
                                "object_name": str(obj_name),
                                "width": width,
                                "height": height,
                                "color_space": str(color_space),
                                "image": None,
                                "image_bytes": img_data,
                                "error": "Could not decode as PIL Image"
                            })
                    except Exception as e:
                        images.append({
                            "pdf_path": str(pdf_path),
                            "page": page_num,
                            "object_name": str(obj_name),
                            "error": str(e)
                        })
    
    return images


def generate_alt_text_ollama(image: Image.Image, prompt: str = None, model: str = "llava") -> str:
    """
    Generate alt text using local ollama VLM.
    
    Requires ollama running with a vision model:
      ollama pull llava
      ollama serve
    
    Args:
        image: PIL Image object
        prompt: Custom prompt (default: accessibility-focused)
        model: ollama model name
    
    Returns:
        Generated alt text
    """
    import requests
    
    if prompt is None:
        prompt = """Describe this image concisely for accessibility purposes. 
Focus on:
- What is shown (main subject)
- Any text visible in the image
- The purpose/context if it appears to be a chart, graph, or diagram
Keep the description to 1-3 sentences."""
    
    # Convert image to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Call ollama API
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [img_base64],
                "stream": False
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "Error: No response from model")
    except requests.exceptions.ConnectionError:
        return "Error: ollama not running. Start with: ollama serve"
    except Exception as e:
        return f"Error: {str(e)}"


def generate_alt_text_ollama_chat(image: Image.Image, prompt: str = None, model: str = "llava") -> str:
    """
    Generate alt text using ollama chat API (better for newer models).
    """
    import requests
    
    if prompt is None:
        prompt = "Describe this image for accessibility. What does it show? Include any visible text. Be concise."
    
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [img_base64]
                    }
                ],
                "stream": False
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "Error: No response")
    except Exception as e:
        return f"Error: {str(e)}"


def generate_alt_text_azure(image: Image.Image, subscription_key: str, endpoint: str) -> str:
    """
    Generate alt text using Azure Computer Vision API.
    
    Args:
        image: PIL Image object
        subscription_key: Azure subscription key
        endpoint: Azure endpoint URL
    
    Returns:
        Generated alt text
    """
    import requests
    
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()
    
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/octet-stream"
    }
    
    # Try describe API
    try:
        response = requests.post(
            f"{endpoint}/vision/v3.2/describe",
            headers=headers,
            params={"language": "en", "maxCandidates": 1},
            data=img_bytes
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("description") and result["description"].get("captions"):
            return result["description"]["captions"][0]["text"]
        return "No description generated"
    except Exception as e:
        return f"Error: {str(e)}"


def generate_alt_text_tesseract(image: Image.Image) -> str:
    """
    Extract text from image using OCR (pytesseract).
    Good for screenshots, scanned documents, images with text.
    
    Requires: tesseract-ocr installed on system
    """
    try:
        import pytesseract
        
        # Get OCR text
        text = pytesseract.image_to_string(image)
        text = text.strip()
        
        if text:
            return f"Image contains text: {text[:200]}"  # Truncate long text
        
        # Try to get structured data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        words = [w for w in data['text'] if w.strip()]
        
        if words:
            return f"OCR detected {len(words)} words"
        
        return "No text detected in image"
    except ImportError:
        return "Error: pytesseract not installed. Run: pip install pytesseract"
    except Exception as e:
        return f"OCR Error: {str(e)}"


def process_pdf_with_vision(
    pdf_path: Path,
    backend: str = "ollama",
    model: str = "llava",
    api_config: dict = None
) -> list[dict]:
    """
    Process all images in a PDF and generate alt text suggestions.
    
    Args:
        pdf_path: Path to PDF file
        backend: "ollama", "azure", "tesseract"
        model: Model name (for ollama)
        api_config: API configuration for cloud services
    
    Returns:
        List of results with image info and generated alt text
    """
    print(f"Extracting images from {pdf_path.name}...")
    images = extract_images_from_pdf(pdf_path)
    
    if not images:
        print("  No images found in PDF")
        return []
    
    print(f"  Found {len(images)} image(s)")
    
    results = []
    
    for idx, img_data in enumerate(images, 1):
        print(f"  Processing image {idx}/{len(images)}...")
        
        result = {
            "page": img_data.get("page"),
            "object_name": img_data.get("object_name"),
            "dimensions": f"{img_data.get('width')}x{img_data.get('height')}",
            "alt_text": None,
            "error": img_data.get("error")
        }
        
        if img_data.get("error"):
            results.append(result)
            continue
        
        pil_image = img_data.get("image")
        
        if pil_image is None:
            result["alt_text"] = "Could not decode image for analysis"
            results.append(result)
            continue
        
        # Generate alt text based on backend
        if backend == "ollama":
            result["alt_text"] = generate_alt_text_ollama_chat(pil_image, model=model)
        elif backend == "azure":
            if not api_config:
                result["alt_text"] = "Error: Azure API config required"
            else:
                result["alt_text"] = generate_alt_text_azure(
                    pil_image,
                    api_config.get("subscription_key"),
                    api_config.get("endpoint")
                )
        elif backend == "tesseract":
            result["alt_text"] = generate_alt_text_tesseract(pil_image)
        else:
            result["alt_text"] = f"Error: Unknown backend '{backend}'"
        
        results.append(result)
        
        # Print preview
        alt_preview = result["alt_text"][:80] + "..." if len(result["alt_text"]) > 80 else result["alt_text"]
        print(f"    -> {alt_preview}")
    
    return results


def save_vision_results(results: list[dict], pdf_name: str, backend: str) -> Path:
    """Save vision results to JSON file."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_path = OUTPUT_DIR / f"{pdf_name}_{backend}_alt_text.json"
    
    output_data = {
        "pdf_name": pdf_name,
        "backend": backend,
        "total_images": len(results),
        "results": results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    return output_path


def main():
    """CLI entry point for vision-based alt text generation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate alt text for PDF images using AI vision models"
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to PDF file"
    )
    parser.add_argument(
        "--backend",
        choices=["ollama", "azure", "tesseract"],
        default="ollama",
        help="Vision backend to use (default: ollama)"
    )
    parser.add_argument(
        "--model",
        default="llava",
        help="Model name for ollama (default: llava)"
    )
    parser.add_argument(
        "--azure-key",
        help="Azure subscription key (required for azure backend)"
    )
    parser.add_argument(
        "--azure-endpoint",
        help="Azure endpoint URL (required for azure backend)"
    )
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        return
    
    # Build API config
    api_config = None
    if args.backend == "azure":
        if not args.azure_key or not args.azure_endpoint:
            print("Error: Azure backend requires --azure-key and --azure-endpoint")
            return
        api_config = {
            "subscription_key": args.azure_key,
            "endpoint": args.azure_endpoint
        }
    
    print("=" * 60)
    print("Vision-based Alt Text Generator")
    print("=" * 60)
    print(f"PDF: {args.pdf_path.name}")
    print(f"Backend: {args.backend}")
    if args.model:
        print(f"Model: {args.model}")
    print()
    
    # Process PDF
    results = process_pdf_with_vision(
        args.pdf_path,
        backend=args.backend,
        model=args.model,
        api_config=api_config
    )
    
    # Save results
    if results:
        save_vision_results(results, args.pdf_path.stem, args.backend)
        
        # Summary
        success = sum(1 for r in results if r["alt_text"] and not r["alt_text"].startswith("Error"))
        print(f"\nSuccessfully generated alt text for {success}/{len(results)} images")
        print("\n⚠️  IMPORTANT: Review generated alt text before using!")
        print("   AI-generated descriptions may contain errors or miss context.")


if __name__ == "__main__":
    main()
