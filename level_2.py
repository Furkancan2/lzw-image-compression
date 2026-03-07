import os
import math
import struct
import numpy as np
from PIL import Image
from LZW import LZWCoding


def calculate_entropy(image_array):
    # Flatten the 2D image array into a 1D list
    flat_array = image_array.flatten()

    # Count how many times each pixel value (0-255) appears
    counts = np.bincount(flat_array.astype(np.uint8), minlength=256)

    # Calculate probability for each pixel value that actually appears
    total_pixels = float(len(flat_array))
    probabilities = counts[counts > 0] / total_pixels

    # Entropy formula: H = -sum(p * log2(p))
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy


class ImageLZWCoding(LZWCoding):
    # Level 2 - Grayscale Image Compression
    # Stores image width and height in the first 4 bytes of the compressed file

    def __init__(self, filename):
        super().__init__(filename, 'image')
        self.num_rows = 0
        self.num_cols = 0

    def compress_image_file(self, image_path):
        print("\n--- LEVEL 2: GRAY LEVEL IMAGE COMPRESSION ---")

        # Step 1: Open image and convert to grayscale
        img = Image.open(image_path).convert('L')
        img_array = np.array(img)
        self.num_rows, self.num_cols = img_array.shape

        # Step 2: Calculate entropy
        entropy = calculate_entropy(img_array)
        print(f"Image Entropy:  {entropy:.4f} bits/pixel")

        # Step 3: Flatten image to 1D and encode
        flat_array = img_array.flatten()
        text = ""
        for p in flat_array:
            text = text + chr(p)

        encoded_ints = self.encode(text)
        bitstring = self.int_list_to_binary_string(encoded_ints)
        bitstring = self.add_code_length_info(bitstring)
        padded = self.pad_encoded_data(bitstring)
        byte_array = self.get_byte_array(padded)

        # Step 4: Write compressed file with header (rows and cols)
        output_path = self.filename + '_compressed.bin'
        # Pack rows and cols as 2-byte unsigned integers (big-endian)
        header = struct.pack('>HH', self.num_rows, self.num_cols)

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(bytes(byte_array))

        # Step 5: Print statistics
        uncompressed_size = len(flat_array)   # 1 byte per pixel
        compressed_size = os.path.getsize(output_path)
        CR = compressed_size / uncompressed_size
        CF = uncompressed_size / compressed_size
        SS = (uncompressed_size - compressed_size) / uncompressed_size
        avg = (compressed_size * 8) / uncompressed_size

        print(f"File compressed  -> '{os.path.basename(output_path)}'")
        print(f"Original Size:         {uncompressed_size:,d} bytes")
        print(f"Compressed Size:       {compressed_size:,d} bytes")
        print(f"Code Length:           {self.codelength} bits")
        print(f"Average Code Length:   {avg:.4f} bits/pixel")
        print(f"Compression Ratio (CR = comp/orig):   {CR:.4f}")
        print(f"Compression Factor(CF = orig/comp):   {CF:.4f}")
        print(f"Space Saving      (SS):               {SS*100:.2f}%")

        return output_path

    def decompress_image_file(self):
        print("\n--- LEVEL 2: GRAY LEVEL IMAGE DECOMPRESSION ---")

        input_path = self.filename + '_compressed.bin'
        output_path = self.filename + '_decompressed.bmp'

        with open(input_path, 'rb') as f:
            # Read the 4-byte header to get image dimensions
            header = f.read(4)
            self.num_rows, self.num_cols = struct.unpack('>HH', header)
            compressed_data = f.read()

        # Convert bytes to binary string
        from io import StringIO
        bit_string = StringIO()
        for byte in compressed_data:
            bit_string.write(bin(byte)[2:].rjust(8, '0'))
        bit_string = bit_string.getvalue()

        # Decode the binary string back to pixel values
        bit_string = self.remove_padding(bit_string)
        bit_string = self.extract_code_length_info(bit_string)
        encoded_text = self.binary_string_to_int_list(bit_string)
        decomp_text = self.decode(encoded_text)

        # Rebuild the 2D image array
        restored_flat = np.array([ord(c) for c in decomp_text], dtype=np.uint8)
        restored_array = restored_flat.reshape((self.num_rows, self.num_cols))

        # Save as BMP file
        Image.fromarray(restored_array).save(output_path)
        print(f"Image decompressed -> '{os.path.basename(output_path)}'")

        return restored_array


# -----------------------------------------------------------------------
if __name__ == "__main__":
    image_name = "thumbs_up"
    image_file_path = image_name + ".bmp"

    if not os.path.exists(image_file_path):
        print(f"ERROR: '{image_file_path}' not found.")
    else:
        lzw = ImageLZWCoding(image_name)

        lzw.compress_image_file(image_file_path)
        restored = lzw.decompress_image_file()

        print("\n--- LEVEL 2: VERIFICATION ---")
        original = np.array(Image.open(image_file_path).convert('L'))
        if np.array_equal(original, restored):
            print("SUCCESS: Original and decompressed images are IDENTICAL.")
        else:
            print("ERROR: Mismatch detected.")