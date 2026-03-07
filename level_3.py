import os
import struct
import numpy as np
from PIL import Image
from LZW import LZWCoding


def calculate_entropy(image_array):
    flat_array = image_array.flatten()
    counts = np.bincount(flat_array.astype(np.uint8), minlength=256)
    total_pixels = float(len(flat_array))
    probabilities = counts[counts > 0] / total_pixels
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy


class DiffImageLZWCoding(LZWCoding):
    # Level 3 - Grayscale Image Compression using pixel differences
    # Instead of compressing pixel values directly, we compress the
    # differences between neighboring pixels (reduces entropy)

    def __init__(self, filename):
        super().__init__(filename, 'image')
        self.num_rows = 0
        self.num_cols = 0

    def get_difference_image(self, img_array):
        # Create a new array to store the differences
        arr = img_array.astype(np.int32)
        diff_arr = np.zeros_like(arr)

        # For each row: store the difference between each pixel and its left neighbor
        diff_arr[:, 1:] = arr[:, 1:] - arr[:, :-1]
        # For the first column: keep the original pixel values
        diff_arr[:, 0] = arr[:, 0]
        # For the first column (except row 0): store difference with pixel above
        diff_arr[1:, 0] = arr[1:, 0] - arr[:-1, 0]

        # Use modulo 256 to keep values in range 0-255
        return (diff_arr % 256).astype(np.uint8)

    def restore_from_difference_image(self, diff_arr):
        # Reverse the process: reconstruct original pixels from differences
        diff_arr = diff_arr.astype(np.int32)
        restored = np.zeros_like(diff_arr)

        # Restore the first column top to bottom
        restored[0, 0] = diff_arr[0, 0]
        for i in range(1, self.num_rows):
            restored[i, 0] = (restored[i-1, 0] + diff_arr[i, 0]) % 256

        # Restore remaining columns left to right
        for j in range(1, self.num_cols):
            restored[:, j] = (restored[:, j-1] + diff_arr[:, j]) % 256

        return restored.astype(np.uint8)

    def compress_difference_image(self, image_path):
        print("\n--- LEVEL 3: IMAGE COMPRESSION (DIFFERENCES) ---")

        # Open image as grayscale
        img = Image.open(image_path).convert('L')
        img_array = np.array(img)
        self.num_rows, self.num_cols = img_array.shape

        # Print entropy before and after taking differences
        orig_entropy = calculate_entropy(img_array)
        print(f"Original Image Entropy:    {orig_entropy:.4f} bits/pixel")

        diff_array = self.get_difference_image(img_array)
        diff_entropy = calculate_entropy(diff_array)
        print(f"Difference Image Entropy:  {diff_entropy:.4f} bits/pixel")

        # Compress the difference image
        flat_diff = diff_array.flatten()
        text = ""
        for p in flat_diff:
            text = text + chr(p)

        encoded_ints = self.encode(text)
        bitstring = self.int_list_to_binary_string(encoded_ints)
        bitstring = self.add_code_length_info(bitstring)
        padded = self.pad_encoded_data(bitstring)
        byte_array = self.get_byte_array(padded)

        # Write compressed file with header
        output_path = self.filename + '_diff_compressed.bin'
        header = struct.pack('>HH', self.num_rows, self.num_cols)

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(bytes(byte_array))

        # Print statistics
        uncompressed_size = len(flat_diff)
        compressed_size = os.path.getsize(output_path)
        CR = compressed_size / uncompressed_size
        CF = uncompressed_size / compressed_size
        SS = (uncompressed_size - compressed_size) / uncompressed_size
        avg = (compressed_size * 8) / uncompressed_size

        print(f"\nFile compressed  -> '{os.path.basename(output_path)}'")
        print(f"Original Size:         {uncompressed_size:,d} bytes")
        print(f"Compressed Size:       {compressed_size:,d} bytes")
        print(f"Code Length:           {self.codelength} bits")
        print(f"Average Code Length:   {avg:.4f} bits/pixel")
        print(f"Compression Ratio (CR = comp/orig):   {CR:.4f}")
        print(f"Compression Factor(CF = orig/comp):   {CF:.4f}")
        print(f"Space Saving      (SS):               {SS*100:.2f}%")

        return output_path

    def decompress_difference_image(self):
        print("\n--- LEVEL 3: DIFFERENCE IMAGE DECOMPRESSION ---")

        input_path = self.filename + '_diff_compressed.bin'
        output_path = self.filename + '_diff_decompressed.bmp'

        with open(input_path, 'rb') as f:
            header = f.read(4)
            self.num_rows, self.num_cols = struct.unpack('>HH', header)
            compressed_data = f.read()

        # Convert bytes to binary string
        from io import StringIO
        bit_string = StringIO()
        for byte in compressed_data:
            bit_string.write(bin(byte)[2:].rjust(8, '0'))
        bit_string = bit_string.getvalue()

        bit_string = self.remove_padding(bit_string)
        bit_string = self.extract_code_length_info(bit_string)
        encoded_text = self.binary_string_to_int_list(bit_string)
        decomp_text = self.decode(encoded_text)

        # Rebuild the difference array and then restore original image
        restored_flat = np.array([ord(c) for c in decomp_text], dtype=np.uint8)
        restored_diff_array = restored_flat.reshape((self.num_rows, self.num_cols))
        restored_img_array = self.restore_from_difference_image(restored_diff_array)

        Image.fromarray(restored_img_array).save(output_path)
        print(f"Image reconstructed from differences -> '{os.path.basename(output_path)}'")

        return restored_img_array


# -----------------------------------------------------------------------
if __name__ == "__main__":
    image_name = "thumbs_up"
    image_file_path = image_name + ".bmp"

    if not os.path.exists(image_file_path):
        print(f"ERROR: '{image_file_path}' not found.")
    else:
        lzw = DiffImageLZWCoding(image_name)

        lzw.compress_difference_image(image_file_path)
        restored = lzw.decompress_difference_image()

        print("\n--- LEVEL 3: VERIFICATION ---")
        original = np.array(Image.open(image_file_path).convert('L'))
        if np.array_equal(original, restored):
            print("SUCCESS: Original and reconstructed images are IDENTICAL.")
        else:
            print("ERROR: Mismatch detected.")