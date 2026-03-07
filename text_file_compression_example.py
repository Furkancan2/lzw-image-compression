import os
from LZW import LZWCoding

# This script compresses sample.txt and produces sample_compressed.bin
# Before running, make sure sample.txt is in the same folder as this script

# Get the directory where this script is located
current_dir = os.path.dirname(os.path.realpath(__file__))

# Build the full path to sample.txt
sample_path = os.path.join(current_dir, 'sample.txt')

# Check if the file exists before trying to compress
if not os.path.exists(sample_path):
    print(f"ERROR: 'sample.txt' not found!")
    print(f"Looked in: {sample_path}")
    print("Please place sample.txt in the same folder as this script.")
else:
    # Pass the full path without extension
    filename = os.path.join(current_dir, 'sample')
    lzw = LZWCoding(filename, 'text')
    output_path = lzw.compress_text_file()
    print(f"\nCompression complete: {output_path}")