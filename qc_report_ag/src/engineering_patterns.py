import re

# GD&T Symbol Map (Unicode to Name)
GDT_SYMBOLS = {
    "⏥": "Flatness",
    "⏊": "Perpendicularity",
    "⌭": "Cylindricity",
    "◎": "Concentricity/Position", # Sometimes used for Position in older fonts, or Concentricity
    "⌖": "Position",
    "⏇": "Profile of Surface",
    "⏆": "Profile of Line",
    "⏃": "Runout",
    "⏄": "Total Runout",
    "⫽": "Parallelism",
    "∠": "Angularity",
    "⏤": "Straightness",
    "Ⓗ": "Maximum Material Condition (MMC)", # Enclosed H
    "Ⓛ": "Least Material Condition (LMC)", # Enclosed L
    "Ⓟ": "Projected Tolerance Zone", # Enclosed P
    "⌀": "Diameter", # Unicode Diameter
    "Ø": "Diameter", # Latin O with stroke
    "⌯": "Symmetry", # Symmetry
}

# Regex Patterns

# Threads: M5x0.8, M24x2, 1/4-20 UNC, etc.
# Matches: "M5", "M5x0.8", "M5 x 0.8", "1/4-20 UNC"
THREAD_PATTERN = re.compile(r'\b(M\d+(\.\d+)?(\s*[xX]\s*\d+(\.\d+)?)?|(\d+(/\d+)?\s*[-]\s*\d+\s*(UNC|UNF|UNEF|NPT)))\b', re.IGNORECASE)

# Surface Finish: 3.2 Ra, 6.3 RMS, N7, etc.
# Also matches standalone standard Ra values: 0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.3, 12.5, 25, 50
# Matches: "3.2 Ra", "3.2Ra", "Ra 3.2", "N7", "6.3 RMS"
# For implicit values (0.8, 1.6, etc.), we require them to be the ONLY text on the line to avoid matching tolerances like +0.8
SURFACE_FINISH_PATTERN = re.compile(r'\b((Ra|Rz|RMS)\s*\d+(\.\d+)?|\d+(\.\d+)?\s*(Ra|Rz|RMS)|N[1-9][0-2]?)\b|^\s*(0\.025|0\.05|0\.1|0\.2|0\.4|0\.8|1\.6|3\.2|6\.3|12\.5|25|50)\s*$', re.IGNORECASE)

# Hardness: 50 HRC, 200 HB, etc.
HARDNESS_PATTERN = re.compile(r'\b(\d+(\.\d+)?\s*(HRC|HRB|HB|HV|HRA))\b', re.IGNORECASE)

# Welding: WELD, FILLET, SEAM, etc.
WELDING_PATTERN = re.compile(r'\b(WELD|FILLET|SEAM|SPOT WELD|ARC WELD)\b', re.IGNORECASE)

# Chamfers: C5, 2x45°, 0.5 x 45
# Matches: "C5", "C 0.5", "2x45", "0.5 x 45"
CHAMFER_PATTERN = re.compile(r'\b(C\s*\d+(\.\d+)?|\d+(\.\d+)?\s*[xX]\s*45[°]?)\b', re.IGNORECASE)

# Hole Modifiers / Notes
HOLE_MODIFIERS = [
    "THRU", "DP", "DEPTH", "CBORE", "CSINK", "SPOTFACE", 
    "EQ SP", "EQUI SP", "TYP", "PLACES", "PLCS", 
    "H7", "g6", "H11", "h11", # Fits
    "DRILL", "REAM", "TAP", "BORE", "GRIND", "PITCH" # Operations
]

# GD&T Frame Text Pattern (Heuristic)
# Looks for symbol followed by number, optionally datum
# e.g. "⏊ 0.01 A", "◎ 0.05 M A B"
# We construct this dynamically from GDT_SYMBOLS keys
gdt_chars = "".join(GDT_SYMBOLS.keys())
# Regex: [Symbol] [Spaces] [Value] [Spaces] [Datum?]
GDT_TEXT_PATTERN = re.compile(r'([' + gdt_chars + r'])\s*(\d+(\.\d+)?)\s*([A-Z\s]*)')

# Dimension & Tolerance Pattern
# Matches: "10.00", "10", "10.00 ± 0.05", "Ø 10", "31 +0.2 / +0.1", "25 0 / -0.2"
# Base: ([ØR\u2300]?\s*\d+(\.\d+)?)
# Tolerance:
#   ± 0.1: \s*[±]\s*\d+(\.\d+)?
#   +0.2 / +0.1 (or mixed signs/zeros): \s*([+-]?\d+(\.\d+)?|[+-]?0(\.0+)?)\s*[/]?\s*([+-]?\d+(\.\d+)?|[+-]?0(\.0+)?)
DIMENSION_PATTERN = re.compile(r'([ØR\u2300]?\s*\d+(\.\d+)?)(\s*[±]\s*\d+(\.\d+)?|\s*([+-]?\d+(\.\d+)?|[+-]?0(\.0+)?)\s*[/]?\s*([+-]?\d+(\.\d+)?|[+-]?0(\.0+)?))?')

# Metadata Patterns
METADATA_PATTERNS = {
    "PART_NUMBER": re.compile(r'(P/N|PART NO|PART NUMBER)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "TITLE": re.compile(r'(TITLE|DWG TITLE)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "MATERIAL": re.compile(r'(MATERIAL|MATL)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "REVISION": re.compile(r'(REV|REVISION)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "SCALE": re.compile(r'(SCALE)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "SHEET": re.compile(r'(SHEET|SHT)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "DATE": re.compile(r'(DATE)\s*[:.-]?\s*(.*)', re.IGNORECASE),
    "WEIGHT": re.compile(r'(WEIGHT|MASS)\s*[:.-]?\s*(.*)', re.IGNORECASE)
}

# Table Headers (for heuristic detection)
TABLE_HEADERS = [
    "ITEM", "QTY", "DESCRIPTION", "PART NO", "MATERIAL", 
    "ZONE", "REV", "DATE", "APPROVED", "CHECKED", "DRAWN",
    "ABOVE", "UPTO", "TOLERANCE", "LINEAR DIMENSIONS", "ANGULAR DIMENSIONS",
    "FINISHED SIZE", "HEAT TREATMENT", "SURFACE COATING",
    "TAG", "X LOC", "Y LOC", "HOLE TABLE", "SIZE"
]

# Modifier Pattern (for vertical merging)
# Matches: "3x", "3X", "4 PLACES", "@'a'", "TYP"
MODIFIER_PATTERN = re.compile(r'^(\d+\s*[xX]|@|TYP|PLACES|PLCS)', re.IGNORECASE)

# Alphanumeric Label Pattern (Hole identifiers like A1, B2)
# Matches: Single Letter followed by 1-2 digits (e.g., A1, B12)
# Note: "M5" matches this, so ensure Thread detection runs FIRST.
ALPHANUMERIC_LABEL_PATTERN = re.compile(r'^[A-Z][0-9]{1,2}$', re.IGNORECASE)
