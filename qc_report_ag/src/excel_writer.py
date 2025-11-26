import pandas as pd
import os
import io

def generate_excel_report(features, output_path):
    """
    Generates a professional Excel inspection report from extracted features.
    Groups features by type with smart column structures per table.
    Includes Critical Dimension detection and Pass/Fail formulas.
    
    Args:
        features: List of Feature objects
        output_path: Can be a file path (str) or BytesIO buffer
    """
    
    # 1. Categorize Features with smarter logic
    categories = {
        "Critical Dimensions": [],
        "Linear Dimensions": [],
        "Holes / Diameters": [],
        "Threads": [],
        "GD&T": [],
        "Other": []  # Surface finish, chamfer, notes, etc.
    }
    
    metadata = {}
    
    for f in features:
        if f.type == "Metadata":
            metadata[f.sub_type] = f.value
            continue
            
        if f.id is None:
            continue
            
        # Determine Category
        cat = "Other"
        
        # Check for Critical Dimension (< 0.05mm tolerance range)
        is_critical = False
        if f.min_val is not None and f.max_val is not None:
            try:
                tol_range = float(f.max_val) - float(f.min_val)
                if tol_range < 0.0500001 and tol_range > 0:
                    is_critical = True
            except:
                pass
        
        # Categorize based on type and criticality
        if is_critical and f.sub_type == "Linear":
            cat = "Critical Dimensions"
        elif f.sub_type == "Linear":
            cat = "Linear Dimensions"
        elif f.sub_type in ["Diameter", "Radius"]:
            cat = "Holes / Diameters"
        elif f.sub_type == "Thread":
            cat = "Threads"
        elif f.type == "GD&T":
            cat = "GD&T"
        # Everything else (Surface Finish, Chamfer, Notes, etc.) goes to "Other"
            
        # Prepare Row Data
        row = {
            "Balloon #": f.id,
            "Type": f.sub_type,
            "Description": f.description if f.description else "",
            "Nominal": f.value,
            "Min": f.min_val,
            "Max": f.max_val,
        }
        categories[cat].append(row)

    # 2. Create Excel Writer
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Inspection Report")
        writer.sheets["Inspection Report"] = worksheet
        
        # 3. Define Styles
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#D9E1F2', 'border': 1
        })
        header_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'align': 'center'
        })
        cell_format = workbook.add_format({
            'border': 1, 'align': 'center'
        })
        text_format = workbook.add_format({
            'border': 1, 'align': 'left'
        })
        pass_format = workbook.add_format({
            'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1, 'align': 'center'
        })
        fail_format = workbook.add_format({
            'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1, 'align': 'center'
        })
        
        # 4. Write Metadata Section
        worksheet.write(0, 0, "PART METADATA", title_format)
        row_idx = 1
        for key, val in metadata.items():
            worksheet.write(row_idx, 0, key, header_format)
            worksheet.write(row_idx, 1, val, text_format)
            row_idx += 1
            
        row_idx += 2 # Spacer
        
        # 5. Define Table-Specific Column Structures
        table_configs = {
            "Critical Dimensions": {
                "columns": ["Balloon #", "Nominal", "Min", "Max", "Actual", "Pass/Fail"],
                "widths": [10, 20, 12, 12, 15, 12],
                "has_formula": True
            },
            "Linear Dimensions": {
                "columns": ["Balloon #", "Nominal", "Min", "Max", "Actual", "Pass/Fail"],
                "widths": [10, 20, 12, 12, 15, 12],
                "has_formula": True
            },
            "Holes / Diameters": {
                "columns": ["Balloon #", "Type", "Nominal", "Min", "Max", "Actual", "Pass/Fail"],
                "widths": [10, 15, 20, 12, 12, 15, 12],
                "has_formula": True
            },
            "Threads": {
                "columns": ["Balloon #", "Specification", "Actual", "Pass/Fail"],
                "widths": [10, 30, 15, 12],
                "has_formula": False  # Manual pass/fail for threads
            },
            "GD&T": {
                "columns": ["Balloon #", "Type", "Tolerance", "Actual", "Pass/Fail"],
                "widths": [10, 20, 20, 15, 12],
                "has_formula": False  # Manual pass/fail for GD&T
            },
            "Other": {
                "columns": ["Balloon #", "Type", "Specification", "Notes"],
                "widths": [10, 20, 30, 40],
                "has_formula": False
            }
        }
        
        # 6. Write Feature Tables
        cat_order = ["Critical Dimensions", "Linear Dimensions", "Holes / Diameters", "Threads", "GD&T", "Other"]
        
        for cat_name in cat_order:
            rows = categories.get(cat_name, [])
            if not rows:
                continue
            
            config = table_configs[cat_name]
            columns = config["columns"]
            col_widths = config["widths"]
            
            # Set column widths
            for i, width in enumerate(col_widths):
                worksheet.set_column(i, i, width)
            
            # Write Category Title
            worksheet.merge_range(row_idx, 0, row_idx, len(columns)-1, cat_name.upper(), title_format)
            row_idx += 1
            
            # Write Table Header
            for col_idx, col_name in enumerate(columns):
                worksheet.write(row_idx, col_idx, col_name, header_format)
            row_idx += 1
            
            # Write Rows
            for row_data in rows:
                xl_row = row_idx + 1
                col_idx = 0
                
                # Write data based on column structure
                for col_name in columns:
                    if col_name == "Balloon #":
                        worksheet.write(row_idx, col_idx, row_data["Balloon #"], cell_format)
                    elif col_name == "Type":
                        worksheet.write(row_idx, col_idx, row_data["Type"], text_format)
                    elif col_name == "Nominal":
                        worksheet.write(row_idx, col_idx, row_data["Nominal"], cell_format)
                    elif col_name == "Specification":
                        worksheet.write(row_idx, col_idx, row_data["Nominal"], cell_format)
                    elif col_name == "Tolerance":
                        tol_str = f"{row_data['Min']} / {row_data['Max']}" if row_data['Min'] is not None else ""
                        worksheet.write(row_idx, col_idx, tol_str, cell_format)
                    elif col_name == "Min":
                        worksheet.write(row_idx, col_idx, row_data["Min"], cell_format)
                    elif col_name == "Max":
                        worksheet.write(row_idx, col_idx, row_data["Max"], cell_format)
                    elif col_name == "Actual":
                        worksheet.write(row_idx, col_idx, "", cell_format)
                    elif col_name == "Notes":
                        worksheet.write(row_idx, col_idx, "", text_format)
                    elif col_name == "Pass/Fail":
                        # Write formula if applicable
                        if config["has_formula"] and row_data["Min"] is not None and row_data["Max"] is not None:
                            # Find the column indices for Min, Max, Actual
                            min_col_idx = columns.index("Min")
                            max_col_idx = columns.index("Max")
                            actual_col_idx = columns.index("Actual")
                            
                            min_col = chr(65 + min_col_idx)  # Convert to Excel column letter
                            max_col = chr(65 + max_col_idx)
                            actual_col = chr(65 + actual_col_idx)
                            
                            formula = f'=IF(ISBLANK({actual_col}{xl_row}), "", IF(AND({actual_col}{xl_row}>={min_col}{xl_row}, {actual_col}{xl_row}<={max_col}{xl_row}), "PASS", "FAIL"))'
                            worksheet.write_formula(row_idx, col_idx, formula, cell_format)
                        else:
                            worksheet.write(row_idx, col_idx, "", cell_format)
                    
                    col_idx += 1
                
                row_idx += 1
            
            # Apply Conditional Formatting to Pass/Fail Column
            if "Pass/Fail" in columns and config["has_formula"]:
                pf_col_idx = columns.index("Pass/Fail")
                start_row = row_idx - len(rows)
                end_row = row_idx - 1
                
                worksheet.conditional_format(start_row, pf_col_idx, end_row, pf_col_idx, {
                    'type': 'cell',
                    'criteria': 'equal to',
                    'value': '"PASS"',
                    'format': pass_format
                })
                worksheet.conditional_format(start_row, pf_col_idx, end_row, pf_col_idx, {
                    'type': 'cell',
                    'criteria': 'equal to',
                    'value': '"FAIL"',
                    'format': fail_format
                })

            row_idx += 2 # Spacer between tables
            
    # Print only if output_path is a string (file path)
    if isinstance(output_path, str):
        print(f"Report generated: {output_path}")
