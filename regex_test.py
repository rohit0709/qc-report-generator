import re

# Current Regex (reconstructed from extractor.py)
# dim_pattern = re.compile(r'([ØR\u2300]?\s*\d+(\.\d+)?)(\s*[±]\s*\d+(\.\d+)?|\s*[+]\d+(\.\d+)?\s*/\s*[-]\d+(\.\d+)?)?')

# Proposed Regex for Tolerances
# Needs to handle:
# +0.2 / +0.1
# -0.1 / -0.2
# +0.1 / -0.1 (Existing)
# 0 / -0.02 (Mixed zero)

# Let's construct a more flexible pattern
# Base value: ([ØR\u2300]?\s*\d+(\.\d+)?)
# Tolerance Part:
#   Option A: ± 0.1  -> \s*[±]\s*\d+(\.\d+)?
#   Option B: +0.2 / +0.1 -> \s*[+-]\d+(\.\d+)?\s*/\s*[+-]\d+(\.\d+)?
#   Option C: +0.2 0 -> \s*[+-]\d+(\.\d+)?\s*[+-]?0(\.0+)?  (Sometimes zero doesn't have sign)

# Combined Tolerance Regex
tol_pattern = r'(\s*[±]\s*\d+(\.\d+)?|\s*[+-]\d+(\.\d+)?\s*/\s*[+-]\d+(\.\d+)?|\s*[+-]\d+(\.\d+)?\s*[+-]?0(\.0+)?|\s*[+-]?0(\.0+)?\s*[+-]\d+(\.\d+)?)'

full_pattern = re.compile(r'([ØR\u2300]?\s*\d+(\.\d+)?)' + tol_pattern + r'?')

test_cases = [
    "31 +0.2 / +0.1",
    "31+0.2/+0.1",
    "45 -0.1 / -0.2",
    "10 ± 0.05",
    "50 +0.1 / -0.1",
    "25 0 / -0.2",
    "100"
]

print("--- Tolerance Tests ---")
for text in test_cases:
    match = full_pattern.search(text)
    if match:
        print(f"'{text}' -> MATCH: '{match.group(0)}'")
    else:
        print(f"'{text}' -> NO MATCH")

# Surface Finish Tests
# User says "0.8" over a symbol.
# We need to detect "0.8", "1.6", "3.2", "6.3", "12.5" as potential surface finishes if they are isolated.
# But "0.8" could be a dimension.
# Heuristic: If it matches a standard Ra series value AND is NOT a dimension (no tolerance, no lines attached?), it's a candidate.
# This is hard to distinguish from a dimension "0.8".
# However, usually dimensions have tolerance or are part of geometry.
# Let's just create a regex for the values for now.

ra_values = r'\b(0\.025|0\.05|0\.1|0\.2|0\.4|0\.8|1\.6|3\.2|6\.3|12\.5|25|50)\b'
sf_pattern = re.compile(ra_values)

print("\n--- Surface Finish Tests ---")
sf_cases = [
    "0.8",
    "1.6",
    "3.2",
    "10.5", # Not standard Ra
    "0.80" # Variation
]

for text in sf_cases:
    match = sf_pattern.search(text)
    if match:
        print(f"'{text}' -> MATCH: '{match.group(0)}'")
    else:
        print(f"'{text}' -> NO MATCH")
