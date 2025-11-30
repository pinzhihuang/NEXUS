# -*- coding: utf-8 -*-
"""
Direct JSON → WeChat Images converter
Bypasses Google Docs - generates images directly from JSON report
"""

from pathlib import Path
from typing import List, Dict
import json

from news_bot.processing.image_generator import (
    generate_image_from_article,
    make_reference_image_from_reports,
)

# School brand colors (same as gdoc_to_wechat_images.py)
SCHOOL_BRAND_MAP = {
    "NYU": "#57068c",
    "USC": "#990000",
    "EMORY": "#222c66",
    "UCD": "#022851",
    "UC DAVIS": "#022851",
    "UBC": "#002145",
    "EDINBURGH": "#041e42",
}

SCHOOL_FOLDERS = {
    "NYU": "NYU_Weekly",
    "USC": "USC_Weekly",
    "EMORY": "EMORY_Weekly",
    "UCD": "UCD_Weekly",
    "UC DAVIS": "UCD_Weekly",
    "UBC": "UBC_Weekly",
    "EDINBURGH": "EDIN_Weekly",
}

def detect_school_from_json(json_data: List[Dict]) -> str:
    """Detect school from JSON data based on source URLs"""
    if not json_data:
        return "NYU"  # default
    
    # Check first article's source URL
    first_url = json_data[0].get("source_url", "").lower()
    
    if "nyunews.com" in first_url or "nyu.edu" in first_url:
        return "NYU"
    elif "usc" in first_url or "uscannenberg" in first_url:
        return "USC"
    elif "emory" in first_url:
        return "EMORY"
    elif "ucdavis" in first_url or "theaggie" in first_url:
        return "UCD"
    elif "ubc.ca" in first_url or "ubyssey" in first_url:
        return "UBC"
    elif "ed.ac.uk" in first_url or "edinburgh" in first_url:
        return "EDINBURGH"
    
    return "NYU"  # default

def json_to_wechat_images(
    json_path: str,
    output_base_dir: str = "wechat_images",
    page_width: int = 540,
    device_scale: int = 4,
    title_size: float = 22.093076923,
    body_size: float = 20.0,
    top_n_sources: int = 10,
    school_override: str = None,
) -> Dict:
    """
    Convert JSON report directly to WeChat-style images.
    
    Args:
        json_path: Path to the JSON report file
        output_base_dir: Base directory for output (will create school subfolder)
        page_width: Image width in pixels
        device_scale: Device scale factor (higher = better quality)
        title_size: Title font size
        body_size: Body font size
        top_n_sources: Number of sources to include in reference page (0 to disable)
        school_override: Manually specify school (NYU, USC, etc.)
        
    Returns:
        Dict with status and output information
    """
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        reports = json.load(f)
    
    if not reports:
        return {
            'success': False,
            'error': 'No reports found in JSON file'
        }
    
    # Detect school
    school = school_override or detect_school_from_json(reports)
    brand_color = SCHOOL_BRAND_MAP.get(school, "#57068c")
    school_folder = SCHOOL_FOLDERS.get(school, "Generic_Weekly")
    
    # Create output directory
    output_dir = Path(output_base_dir) / school_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if UCD (for alternating colors)
    is_ucd = school == "UCD" or school == "UC DAVIS"
    
    generated_files = []
    
    # Generate images for each article
    for i, report in enumerate(reports, 1):
        chinese_title = report.get('chinese_title', '').strip()
        chinese_content = report.get('refined_chinese_news_report', '').strip()
        source_url = report.get('source_url', '').strip()
        
        # Skip if translation failed
        if not chinese_title or not chinese_content:
            continue
        if "失败" in chinese_title or "failed" in chinese_title.lower():
            continue
        if "失败" in chinese_content or "failed" in chinese_content.lower():
            continue
        
        # UCD special: alternate blue/yellow
        left_bar_color = None
        if is_ucd:
            left_bar_color = "#022851" if (i % 2 == 1) else "#FFBF00"
        
        # Safe filename
        safe_title = chinese_title[:40].replace('/', '_').replace('\\', '_').replace(':', '_')
        output_path = output_dir / f"{i:02d}_{safe_title}.png"
        
        try:
            generate_image_from_article(
                title=chinese_title,
                content=chinese_content,
                output_path=str(output_path),
                credits="",  # Disabled as per original script
                cover_image="",  # TODO: Could extract from source URL
                cover_caption="",
                page_width=page_width,
                device_scale=device_scale,
                title_size=title_size,
                body_size=body_size,
                brand_color=brand_color,
                left_bar_color=left_bar_color,
            )
            generated_files.append(str(output_path))
            print(f"✅ Generated: {output_path.name}")
        except Exception as e:
            print(f"❌ Failed to generate image for article {i}: {e}")
            continue
    
    # Generate sources reference page (optional)
    sources_file = None
    if top_n_sources > 0:
        try:
            sources_output = make_reference_image_from_reports(
                sorted_json_path=json_path,
                output_dir=str(output_dir),
                filename="00_资料来源.png",
                top_n=top_n_sources,
                page_width=page_width,
                device_scale=device_scale,
                brand_color=brand_color,
            )
            sources_file = sources_output
            print(f"✅ Generated sources page: {sources_output}")
        except Exception as e:
            print(f"⚠️  Failed to generate sources page: {e}")
    
    return {
        'success': True,
        'school': school,
        'brand_color': brand_color,
        'output_dir': str(output_dir),
        'generated_files': generated_files,
        'sources_file': sources_file,
        'total_images': len(generated_files),
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert JSON report to WeChat-style images')
    parser.add_argument('json_path', help='Path to JSON report file')
    parser.add_argument('--out', default='wechat_images', help='Output base directory')
    parser.add_argument('--school', help='Override school detection (NYU, USC, EMORY, UCD, UBC, EDINBURGH)')
    parser.add_argument('--page-width', type=int, default=540, help='Image width')
    parser.add_argument('--device-scale', type=int, default=4, help='Device scale factor')
    parser.add_argument('--title-size', type=float, default=22.093076923, help='Title font size')
    parser.add_argument('--body-size', type=float, default=20.0, help='Body font size')
    parser.add_argument('--top-n', type=int, default=10, help='Number of sources in reference page (0 to disable)')
    
    args = parser.parse_args()
    
    result = json_to_wechat_images(
        json_path=args.json_path,
        output_base_dir=args.out,
        page_width=args.page_width,
        device_scale=args.device_scale,
        title_size=args.title_size,
        body_size=args.body_size,
        top_n_sources=args.top_n,
        school_override=args.school,
    )
    
    if result['success']:
        print(f"\n🎉 Success! Generated {result['total_images']} images")
        print(f"📁 Output: {result['output_dir']}")
        print(f"🎨 School: {result['school']} (Brand: {result['brand_color']})")
    else:
        print(f"\n❌ Error: {result['error']}")
        exit(1)


