import os
from LZW import LZWCoding

# This script decompresses sample_compressed.bin and produces sample_decompressed.txt
# Before running this, you must first run text_file_compression_example.py

# Get the directory where this script is located
current_dir = os.path.dirname(os.path.realpath(__file__))

# Build the full path to the compressed file
compressed_path = os.path.join(current_dir, 'sample_compressed.bin')

# Check if the compressed file exists
if not os.path.exists(compressed_path):
    print(f"ERROR: 'sample_compressed.bin' not found!")
    print("Please run text_file_compression_example.py first.")
else:
    # Pass the full path without extension
    filename = os.path.join(current_dir, 'sample')
    lzw = LZWCoding(filename, 'text')
    output_path = lzw.decompress_text_file()
    print(f"\nDecompression complete: {output_path}")

    # Compare the decompressed file with the original
    original_path = os.path.join(current_dir, 'sample.txt')
    decompressed_path = os.path.join(current_dir, 'sample_decompressed.txt')

    with open(original_path, 'r') as f1, open(decompressed_path, 'r') as f2:
        original_text = f1.read()
        decompressed_text = f2.read()

    if original_text == decompressed_text:
        print("sample.txt and sample_decompressed.txt are identical.")
    else:
        print("MISMATCH: The files are not the same!")