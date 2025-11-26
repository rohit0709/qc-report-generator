import pytesseract

class Feature:
    def __init__(self, id, type, value, location, page_num, sub_type=None, description=None):
        self.id = id
        self.type = type
        self.value = value
        self.location = location # (x, y, w, h)
        self.page_num = page_num
        self.sub_type = sub_type # e.g., "Thread", "Chamfer", "Perpendicularity"
        self.description = description # e.g., "M5x0.8", "0.01 wrt A"
        self.tolerance = None
        self.min_val = None
        self.max_val = None

import re

import cv2
import numpy as np
from . import engineering_patterns

def parse_tolerance(dim_string):
    """
    Parse a dimension string to extract nominal, min, and max values.
    Handles formats like:
    - "13 ± 0.1" -> nominal=13, min=12.9, max=13.1
    - "12.1 +0.1 0" -> nominal=12.1, min=12.1, max=12.2
    - "10 +0.2/-0.1" -> nominal=10, min=9.9, max=10.2
    - "67 -0.1 -0.2" -> nominal=67, min=66.8, max=66.9
    - "⌀ 12.1 +0.1 0" -> nominal=12.1, min=12.1, max=12.2
    Returns: (nominal, min_val, max_val) or (None, None, None) if parsing fails
    """
    import re
    
    # Remove symbols like ⌀, R, etc. for parsing
    clean_str = dim_string.replace("⌀", "").replace("Ø", "").replace("R", "").strip()
    
    # Pattern 1: ± format (e.g., "13 ± 0.1")
    match = re.search(r'([\d.]+)\s*[±]\s*([\d.]+)', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            tol = float(match.group(2))
            return nominal, nominal - tol, nominal + tol
        except:
            pass
    
    # Pattern 2: +X -Y format (e.g., "10 +0.2/-0.1" or "10 +0.2 -0.1")
    match = re.search(r'([\d.]+)\s*\+\s*([\d.]+)\s*[/-]\s*([\d.]+)', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            upper_tol = float(match.group(2))
            lower_tol = float(match.group(3))
            return nominal, nominal - lower_tol, nominal + upper_tol
        except:
            pass
    
    # Pattern 2b: +X +Y format (e.g., "45 +0.015 +0.005")
    # This means upper tolerance is +0.015 (max = nominal + 0.015) and lower is +0.005 (min = nominal + 0.005)
    match = re.search(r'([\d.]+)\s*\+\s*([\d.]+)\s+\+\s*([\d.]+)', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            upper_tol = float(match.group(2))  # Larger positive (further from nominal)
            lower_tol = float(match.group(3))  # Smaller positive (closer to nominal)
            return nominal, nominal + lower_tol, nominal + upper_tol
        except:
            pass
    
    # Pattern 3: -X -Y format (e.g., "67 -0.1 -0.2")
    # This means upper tolerance is -0.1 (max = nominal - 0.1) and lower is -0.2 (min = nominal - 0.2)
    match = re.search(r'([\d.]+)\s+-\s*([\d.]+)\s+-\s*([\d.]+)', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            upper_tol = float(match.group(2))  # Less negative (closer to nominal)
            lower_tol = float(match.group(3))  # More negative (further from nominal)
            return nominal, nominal - lower_tol, nominal - upper_tol
        except:
            pass
    
    # Pattern 4: +X 0 format (e.g., "12.1 +0.1 0")
    match = re.search(r'([\d.]+)\s*\+\s*([\d.]+)\s+0', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            upper_tol = float(match.group(2))
            return nominal, nominal, nominal + upper_tol
        except:
            pass
    
    # Pattern 5: 0 -X format (e.g., "12.1 0 -0.1")
    match = re.search(r'([\d.]+)\s+0\s*-\s*([\d.]+)', clean_str)
    if match:
        try:
            nominal = float(match.group(1))
            lower_tol = float(match.group(2))
            return nominal, nominal - lower_tol, nominal
        except:
            pass
    
    # Pattern 6: Just a number (no tolerance)
    match = re.search(r'^([\d.]+)$', clean_str.strip())
    if match:
        try:
            nominal = float(match.group(1))
            return nominal, nominal, nominal
        except:
            pass
    
    return None, None, None


def extract_features(pdf_page, image, page_num):
    """Extracts dimensions, GD&T, and other features from a page."""
    features = []
    feature_id = 1 # Should probably be global or passed in to maintain continuity across pages
    
    # 1. Text Extraction with Merging
    # PyMuPDF returns blocks. Sometimes a dimension "10.00 ± 0.05" is split into "10.00" and "± 0.05".
    # We need to merge text that is spatially close.
    
    raw_blocks = pdf_page.get_text("dict")["blocks"]
    
    # RE-IMPLEMENTATION:
    # Instead of complex merging, let's just concatenate all text in a LINE.
    # Often "10.00" and "± 0.05" are in the same line object.
    
    # Pre-process lines to handle vertical splits (e.g. +0.2 over +0.1)
    processed_lines = []
    
    # Extract all lines first with their bboxes
    all_lines = []
    for block in raw_blocks:
        if "lines" in block:
            for line in block["lines"]:
                text = " ".join([s["text"] for s in line["spans"]]).strip()
                if text:
                    all_lines.append({"text": text, "bbox": line["bbox"]})
    
    # Simple Vertical Merge
    i = 0
    while i < len(all_lines):
        current_line = all_lines[i]
        text = current_line["text"]
        bbox = current_line["bbox"]
        
        # Look ahead
        if i + 1 < len(all_lines):
            next_line = all_lines[i+1]
            next_text = next_line["text"]
            
            # Heuristic: Merge if next line is a Tolerance, Modifier, or Continuation
            
            # Check vertical distance
            v_dist = next_line["bbox"][1] - bbox[3] # y0_next - y1_current
            
            should_merge = False
            
            if v_dist < 15: # Slightly increased threshold
                # 1. Tolerance (+/-)
                if next_text.startswith("+") or next_text.startswith("-"):
                    should_merge = True
                
                # 2. Zero Tolerance ("0")
                # Often appears as "0" over "-0.1" or "+0.1" over "0"
                elif next_text.strip() == "0":
                    should_merge = True
                    
                # 3. Modifiers (3x, @'a')
                elif engineering_patterns.MODIFIER_PATTERN.match(next_text):
                    should_merge = True
                    
            if should_merge:
                # Merge
                text += " " + next_text
                # Expand bbox to include next line
                bbox = (
                    min(bbox[0], next_line["bbox"][0]),
                    min(bbox[1], next_line["bbox"][1]),
                    max(bbox[2], next_line["bbox"][2]),
                    max(bbox[3], next_line["bbox"][3])
                )
                i += 1 # Skip next line
                
                # Check for a THIRD line (e.g. +0.1 over 0)
                if i + 1 < len(all_lines):
                    next_next_line = all_lines[i+1]
                    next_next_text = next_next_line["text"]
                    v_dist_2 = next_next_line["bbox"][1] - bbox[3]
                    
                    should_merge_2 = False
                    if v_dist_2 < 15:
                        if next_next_text.startswith("+") or next_next_text.startswith("-") or next_next_text.strip() == "0":
                            should_merge_2 = True
                            
                    if should_merge_2:
                        text += " " + next_next_text
                        bbox = (
                            min(bbox[0], next_next_line["bbox"][0]),
                            min(bbox[1], next_next_line["bbox"][1]),
                            max(bbox[2], next_next_line["bbox"][2]),
                            max(bbox[3], next_next_line["bbox"][3])
                        )
                        i += 1
        
        processed_lines.append({"text": text, "bbox": bbox})
        i += 1

    for line_data in processed_lines:
        line_text = line_data["text"]
        line_bbox = line_data["bbox"]
        
        # --- PRIORITY 0: Metadata ---
        is_metadata = False
        for meta_type, pattern in engineering_patterns.METADATA_PATTERNS.items():
            meta_match = pattern.search(line_text)
            if meta_match:
                val = meta_match.group(2).strip()
                if val: # Only if there is a value
                    f = Feature(
                        id=None, # No ID for Metadata
                        type="Metadata",
                        value=val,
                        location=line_bbox,
                        page_num=page_num,
                        sub_type=meta_type,
                        description=f"{meta_type}: {val}"
                    )
                    features.append(f)
                    # Do NOT increment feature_id
                    is_metadata = True
                    break
        if is_metadata:
            continue

        # --- PRIORITY 0.5: Table Headers / Text ---
        # Check if line contains table headers
        if any(header in line_text.upper() for header in engineering_patterns.TABLE_HEADERS):
            f = Feature(
                id=None, # No ID for Notes/Headers
                type="Note",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Table/Header",
                description="Document Text"
            )
            features.append(f)
            # Do NOT increment feature_id
            continue

        # --- PRIORITY 1: GD&T (Text-based) ---
        # Check for GD&T symbols in text
        gdt_match = engineering_patterns.GDT_TEXT_PATTERN.search(line_text)
        if gdt_match:
            symbol = gdt_match.group(1)
            value = gdt_match.group(2)
            datum = gdt_match.group(4).strip()
            
            symbol_name = engineering_patterns.GDT_SYMBOLS.get(symbol, "Unknown Symbol")
            
            # Fix: Diameter symbol (⌀) is often caught here but should be treated as a Dimension
            if symbol_name == "Diameter":
                # Skip this block and let it fall through to Dimension logic
                pass
            else:
                f = Feature(
                    id=feature_id,
                    type="GD&T",
                    value=line_text, # Full text
                    location=line_bbox,
                    page_num=page_num,
                    sub_type=symbol_name,
                    description=f"Tol: {value} | Datum: {datum}" if datum else f"Tol: {value}"
                )
                features.append(f)
                feature_id += 1
                continue # Skip other checks
        
        # --- PRIORITY 2: Threads ---
        thread_match = engineering_patterns.THREAD_PATTERN.search(line_text)
        if thread_match:
            f = Feature(
                id=feature_id,
                type="Thread",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Thread",
                description="Thread Callout"
            )
            features.append(f)
            feature_id += 1
            continue
        
        # --- PRIORITY 3: Chamfers ---
        chamfer_match = engineering_patterns.CHAMFER_PATTERN.search(line_text)
        if chamfer_match:
            f = Feature(
                id=feature_id,
                type="Chamfer",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Chamfer",
                description="Chamfer Dimension"
            )
            features.append(f)
            feature_id += 1
            continue

        # --- PRIORITY 3.1: Surface Finish ---
        sf_match = engineering_patterns.SURFACE_FINISH_PATTERN.search(line_text)
        if sf_match:
            f = Feature(
                id=feature_id,
                type="Surface Finish",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Roughness",
                description="Surface Finish Spec"
            )
            features.append(f)
            feature_id += 1
            continue

        # --- PRIORITY 3.2: Hardness/Material ---
        hard_match = engineering_patterns.HARDNESS_PATTERN.search(line_text)
        if hard_match:
            f = Feature(
                id=feature_id,
                type="Material/Hardness",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Hardness",
                description="Material Property"
            )
            features.append(f)
            feature_id += 1
            continue

        # --- PRIORITY 3.3: Welding ---
        weld_match = engineering_patterns.WELDING_PATTERN.search(line_text)
        if weld_match:
            f = Feature(
                id=feature_id,
                type="Welding",
                value=line_text,
                location=line_bbox,
                page_num=page_num,
                sub_type="Weld Note",
                description="Welding Instruction"
            )
            features.append(f)
            feature_id += 1
            continue
        
        # --- PRIORITY 4: Dimensions (Linear & Holes) ---
        # Uses improved regex from engineering_patterns to capture tolerances like +0.2 / +0.1
        match = engineering_patterns.DIMENSION_PATTERN.search(line_text)
        if match:
            val = match.group(0)
            
            # Filter Alphanumeric Hole Labels (e.g., A1, B2)
            # These are often hole identifiers, not dimensions.
            # Note: Threads (M5) are already caught by Priority 2.
            # EXCEPTION: "R" prefix is Radius (e.g., R5), so keep it.
            if engineering_patterns.ALPHANUMERIC_LABEL_PATTERN.match(val):
                if not val.upper().startswith("R"):
                    continue

            if len(val) < 30: # Filter noise
                # Determine Type
                if "Ø" in val or "R" in val or "\u2300" in val:
                    feat_type = "Hole/Radius"
                    sub_type = "Diameter" if ("Ø" in val or "\u2300" in val) else "Radius"
                    # Assign ID for Holes
                    f_id = feature_id
                    feature_id += 1
                else:
                    # Treat as Linear Dimension (User Feedback: "10" is a valid dimension)
                    feat_type = "Linear Dimension"
                    sub_type = "Linear"
                    # Assign ID
                    f_id = feature_id
                    feature_id += 1
                    
                # Check for Hole Modifiers
                desc = []
                for mod in engineering_patterns.HOLE_MODIFIERS:
                    if mod in line_text:
                        desc.append(mod)
                
                # Capture any other remaining text (like "4X", "@'a'", etc.)
                # Remove the extracted value from the full line text
                remainder = line_text.replace(val, "").strip()
                if remainder:
                    # Avoid duplicating modifiers if they were already found
                    if remainder not in desc:
                         desc.append(remainder)

                description = ", ".join(desc) if desc else None

                # Parse tolerance to get min/max values
                nominal, min_val, max_val = parse_tolerance(val)

                f = Feature(
                    id=f_id,
                    type=feat_type,
                    value=val,
                    location=line_bbox, # Use line bbox to encompass full dimension
                    page_num=page_num,
                    sub_type=sub_type,
                    description=description
                )
                
                # Set tolerance values
                f.min_val = min_val
                f.max_val = max_val
                
                features.append(f)

    # 2. GD&T Frame Detection (OpenCV)
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Threshold
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Filter for rectangular frames typical of GD&T
        # Aspect ratio > 1, reasonable size
        if w > 20 and h > 10 and w < 500 and h < 100:
            # Check if it's a rectangle (approximate)
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                
                scale_x = pdf_page.rect.width / image.shape[1]
                scale_y = pdf_page.rect.height / image.shape[0]
                
                pdf_bbox = (x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
                
                f = Feature(
                    id=feature_id,
                    type="GD&T",
                    value="Frame", # Placeholder
                    location=pdf_bbox,
                    page_num=page_num
                )
                features.append(f)
                feature_id += 1

    # 3. Spatial Filtering (Title Block & Tables)
    # Pass the PDF page object to access vector drawings
    features = filter_spatial_noise(features, pdf_page)
    
    # 4. Zone Filtering (Border Noise)
    features = filter_zone_noise(features, pdf_page)

    return features

def filter_zone_noise(features, pdf_page):
    """
    Filters out Zone Indexing numbers/letters found on the borders of the page.
    """
    page_w = pdf_page.rect.width
    page_h = pdf_page.rect.height
    
    # Define Margins (e.g. 30 units from edge)
    margin = 30
    
    for f in features:
        if f.id is None:
            continue
            
        x0, y0, x1, y1 = f.location
        
        # Check if inside margins
        in_left_margin = x1 < margin
        in_right_margin = x0 > (page_w - margin)
        in_top_margin = y1 < margin
        in_bottom_margin = y0 > (page_h - margin)
        
        if in_left_margin or in_right_margin or in_top_margin or in_bottom_margin:
            # Only filter if it looks like a zone index (short text)
            if len(f.value) <= 2:
                f.id = None
                f.type = "Note"
                f.sub_type = "Zone Index"
                
    return features

def filter_spatial_noise(features, pdf_page):
    """
    Identifies Title Block and Table regions using VECTOR GRAPHICS (Rectangles)
    and removes IDs from features inside them.
    Uses CLUSTERING to distinguish tables (grids) from isolated geometry.
    """
    # 1. Extract Vector Rectangles
    drawings = pdf_page.get_drawings()
    rects = []
    
    for path in drawings:
        r = path["rect"]
        w = r.width
        h = r.height
        
        # Filter for potential cell sizes
        # Generous limits to catch title blocks
        if w > 10 and h > 5 and w < 400 and h < 200:
            rects.append(r)
            
    # 2. Cluster Rectangles (Find Grids)
    # Two rects are connected if they touch or overlap (share an edge)
    # We'll use a simple adjacency list
    adj = {i: [] for i in range(len(rects))}
    
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            r1 = rects[i]
            r2 = rects[j]
            
            # Check for intersection or touching
            # Expand r1 slightly to catch touching edges
            r1_expanded = (r1.x0 - 1, r1.y0 - 1, r1.x1 + 1, r1.y1 + 1)
            
            # Check overlap
            if not (r2.x0 > r1_expanded[2] or r2.x1 < r1_expanded[0] or
                    r2.y0 > r1_expanded[3] or r2.y1 < r1_expanded[1]):
                adj[i].append(j)
                adj[j].append(i)
                
    # Find Connected Components
    visited = set()
    table_rects = []
    
    page_h = pdf_page.rect.height
    bottom_threshold = page_h * 0.70 # Bottom 30%
    
    for i in range(len(rects)):
        if i not in visited:
            component = []
            stack = [i]
            visited.add(i)
            while stack:
                curr = stack.pop()
                component.append(rects[curr])
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            
            # Heuristic: 
            # 1. Standard Table: Grid of cells (>= 3 connected).
            # 2. Split Title Block: Even single/double rectangles in the bottom-right are likely title blocks.
            
            # Check location of component (use center of first rect)
            comp_y = component[0].y0
            
            min_cluster_size = 3
            if comp_y > bottom_threshold:
                min_cluster_size = 1 # Relax for title block area
                
            if len(component) >= min_cluster_size:
                table_rects.extend(component)

    # 3. Identify Title Block Zone (Fallback)
    # Only consider metadata in the bottom 30% of the page
    metadata_features = [
        f for f in features 
        if f.type == "Metadata" and f.location[1] > bottom_threshold
    ]
    
    title_block_zone = None
    if metadata_features:
        min_x = min(f.location[0] for f in metadata_features)
        min_y = min(f.location[1] for f in metadata_features)
        max_x = max(f.location[2] for f in metadata_features)
        max_y = max(f.location[3] for f in metadata_features)
        title_block_zone = (min_x - 20, min_y - 20, max_x + 500, max_y + 500)

    # 4. Identify Explicit Table Zones (Hole Tables, BOMs)
    # Look for Table Headers ANYWHERE on the page
    table_header_features = [f for f in features if f.sub_type == "Table/Header"]
    explicit_table_zones = []
    
    for hf in table_header_features:
        # Define a zone extending from the header downwards
        # Assuming table is below the header
        # Width: Extend to page width (aggressive but safer for now)
        # Height: Extend to bottom of page
        
        # Heuristic: If header is "TAG" or "X LOC", it's likely a Hole Table.
        # These tables can be wide.
        
        zone = (hf.location[0] - 20, hf.location[1] - 10, pdf_page.rect.width, pdf_page.rect.height)
        explicit_table_zones.append(zone)

    # 5. Filter Features
    for f in features:
        if f.id is None:
            continue
            
        cx = (f.location[0] + f.location[2]) / 2
        cy = (f.location[1] + f.location[3]) / 2
        
        # Check Vector Table Rects
        in_table = False
        for r in table_rects:
            if cx >= r.x0 and cx <= r.x1 and cy >= r.y0 and cy <= r.y1: # Corrected: cy >= r.y0 and cy <= r.y1
                in_table = True
                break
        
        if in_table:
            f.id = None
            f.type = "Note"
            f.sub_type = "Table/Content"
            continue
            
        # Check Title Block Zone (Backup)
        if title_block_zone:
            if (cx >= title_block_zone[0] and cx <= title_block_zone[2] and 
                cy >= title_block_zone[1] and cy <= title_block_zone[3]):
                f.id = None
                f.type = "Note"
                f.sub_type = "TitleBlock/Context"
                continue
                
        # Check Explicit Table Zones
        for zone in explicit_table_zones:
             if (cx >= zone[0] and cx <= zone[2] and cy >= zone[1] and cy <= zone[3]):
                f.id = None
                f.type = "Note"
                f.sub_type = "Table/Content"
                break
                
    return features
