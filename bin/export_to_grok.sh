#!/bin/bash

# Usage: ./import_to_grok.sh /path/to/your/package_folder > output.txt
# Then, upload or paste the contents of output.txt into your Grok chat for analysis.

if [ $# -ne 1 ]; then
    echo "Usage: $0 /path/to/package_folder"
    exit 1
fi

PACKAGE_DIR="$1"

if [ ! -d "$PACKAGE_DIR" ]; then
    echo "Error: Directory $PACKAGE_DIR does not exist."
    exit 1
fi

# Function to print file contents with delimiters
print_file() {
    local file="$1"
    echo "=== FILE: $file ==="
    cat "$file"
    echo ""
    echo "=== END OF FILE: $file ==="
    echo ""
}

# Export the function for use in find
export -f print_file

# Print directory structure
echo "=== DIRECTORY STRUCTURE ==="
tree "$PACKAGE_DIR" || find "$PACKAGE_DIR" -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
echo "=== END OF DIRECTORY STRUCTURE ==="
echo ""

# Find and print all Python files (and other relevant files like setup.py, README, etc.)
find "$PACKAGE_DIR" -type f \( -name "*.py" -o -name "setup.*" -o -name "README*" -o -name "LICENSE*" -o -name "*.toml" -o -name "*.cfg" -o -name "*.ini" \) -exec bash -c 'print_file "$0"' {} \;

echo "=== END OF PACKAGE IMPORT ==="