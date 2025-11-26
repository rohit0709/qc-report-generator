import fitz

def add_balloons(pdf_path, features, output_path):
    """Adds balloons to the PDF based on extracted features."""
    doc = fitz.open(pdf_path)
    
    # Group features by page
    features_by_page = {}
    for f in features:
        # Default to page 0 if page_num is missing
        p_num = getattr(f, 'page_num', 0)
        if p_num not in features_by_page:
            features_by_page[p_num] = []
        features_by_page[p_num].append(f)
        
    for page_num, page_features in features_by_page.items():
        # Ensure page exists
        if page_num - 1 >= len(doc):
            continue
            
        page = doc[page_num - 1]
        shape = page.new_shape()
        
        # 1. Initialize Occupied Zones with existing feature bounding boxes
        occupied_zones = []
        for f in page_features:
            if f.id is None:
                continue
            occupied_zones.append(fitz.Rect(f.location))
            
        for f in page_features:
            if f.id is None:
                continue
            
            # Feature BBox
            x0, y0, x1, y1 = f.location
            rect = fitz.Rect(f.location)
            
            # Draw box around the feature (thin red line)
            shape.draw_rect(rect)
            shape.finish(color=(1, 0, 0), width=0.5)
            
            # Balloon settings
            balloon_radius = 8
            
            # Dynamic Placement Strategy
            # Try directions: Right, Left, Top, Bottom
            # Try increasing offsets: 10, 25, 40, 55, ...
            
            directions = [
                ("Right",  (1, 0)),
                ("Left",   (-1, 0)),
                ("Top",    (0, -1)),
                ("Bottom", (0, 1))
            ]
            
            chosen_pos = None
            chosen_leader_start = None
            
            # Search for valid position
            for offset in range(15, 100, 15):
                for dir_name, (dx, dy) in directions:
                    # Calculate Balloon Center
                    # Center of rect
                    rc_x = (x0 + x1) / 2
                    rc_y = (y0 + y1) / 2
                    
                    if dir_name == "Right":
                        cx = x1 + offset + balloon_radius
                        cy = rc_y
                        leader_start = fitz.Point(x1, rc_y)
                    elif dir_name == "Left":
                        cx = x0 - offset - balloon_radius
                        cy = rc_y
                        leader_start = fitz.Point(x0, rc_y)
                    elif dir_name == "Top":
                        cx = rc_x
                        cy = y0 - offset - balloon_radius
                        leader_start = fitz.Point(rc_x, y0)
                    elif dir_name == "Bottom":
                        cx = rc_x
                        cy = y1 + offset + balloon_radius
                        leader_start = fitz.Point(rc_x, y1)
                        
                    balloon_rect = fitz.Rect(
                        cx - balloon_radius, cy - balloon_radius,
                        cx + balloon_radius, cy + balloon_radius
                    )
                    
                    # Check collision
                    collision = False
                    for zone in occupied_zones:
                        if zone == rect: continue
                        if balloon_rect.intersects(zone):
                            collision = True
                            break
                    
                    if not collision:
                        chosen_pos = fitz.Point(cx, cy)
                        chosen_leader_start = leader_start
                        occupied_zones.append(balloon_rect)
                        break
                
                if chosen_pos:
                    break
            
            # Fallback if no space found: Default to Right with small offset
            if not chosen_pos:
                offset = 15
                cx = x1 + offset + balloon_radius
                cy = (y0 + y1) / 2
                chosen_pos = fitz.Point(cx, cy)
                chosen_leader_start = fitz.Point(x1, cy)
                balloon_rect = fitz.Rect(
                        cx - balloon_radius, cy - balloon_radius,
                        cx + balloon_radius, cy + balloon_radius
                )
                occupied_zones.append(balloon_rect)

            # Draw Balloon
            center = chosen_pos
            
            # Draw Leader Line
            # Connect edge of rect to balloon center
            shape.draw_line(chosen_leader_start, center)
            shape.finish(color=(1, 0, 0), width=0.5)
            
            # Draw Circle (Red outline, White fill)
            shape.draw_circle(center, balloon_radius)
            shape.finish(color=(1, 0, 0), fill=(1, 1, 1), width=1)
            
            # Draw Text (ID)
            text = str(f.id)
            fontsize = 8
            
            # Calculate text width to center it (approximate)
            text_len = len(text)
            text_x = center.x - (text_len * 2) 
            text_y = center.y + 3
            
            shape.insert_text(fitz.Point(text_x, text_y), text, color=(1, 0, 0), fontsize=fontsize)
            
        shape.commit()
                
    doc.save(output_path)
