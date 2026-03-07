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


class ColorDiffImageLZWCoding(LZWCoding):
    # Level 5 - Color Image Compression using pixel differences per channel
    # Combines Level 3 (differences) and Level 4 (RGB channels) approaches

    def __init__(self, filename):
        super().__init__(filename, 'image')
        self.num_rows = 0
        self.num_cols = 0
        self.channels = ['R', 'G', 'B']

    def get_difference_image(self, img_array):
        # Calculate differences between neighboring pixels for one channel
        arr = img_array.astype(np.int32)
        diff_arr = np.zeros_like(arr)

        # Row-wise differences (left neighbor)
        diff_arr[:, 1:] = arr[:, 1:] - arr[:, :-1]
        # Keep first column values as-is
        diff_arr[:, 0] = arr[:, 0]
        # Column-wise differences for first column (top neighbor)
        diff_arr[1:, 0] = arr[1:, 0] - arr[:-1, 0]

        return (diff_arr % 256).astype(np.uint8)

    def restore_from_difference_image(self, diff_arr):
        # Reconstruct original pixel values from the difference array
        diff_arr = diff_arr.astype(np.int32)
        restored = np.zeros_like(diff_arr)

        # Restore first column from top to bottom
        restored[0, 0] = diff_arr[0, 0]
        for i in range(1, self.num_rows):
            restored[i, 0] = (restored[i-1, 0] + diff_arr[i, 0]) % 256

        # Restore remaining columns left to right
        for j in range(1, self.num_cols):
            restored[:, j] = (restored[:, j-1] + diff_arr[:, j]) % 256

        return restored.astype(np.uint8)

    def compress_color_diff_image(self, image_path):
        print("\n--- LEVEL 5: COLOR IMAGE DIFFERENCE COMPRESSION ---")

        img = Image.open(image_path).convert('RGB')
        img_array = np.array(img)
        self.num_rows, self.num_cols, _ = img_array.shape
        print(f"Image Dimensions: {self.num_rows}x{self.num_cols}  (3 channels)")

        total_uncomp = 0
        total_comp = 0

        # Process each color channel separately
        for idx, color in enumerate(self.channels):
            print(f"\nChannel: {color}")
            channel_array = img_array[:, :, idx]

            # Print entropy before and after taking differences
            orig_entropy = calculate_entropy(channel_array)
            print(f"  Original Entropy:    {orig_entropy:.4f} bits/pixel")

            diff_array = self.get_difference_image(channel_array)
            diff_entropy = calculate_entropy(diff_array)
            print(f"  Difference Entropy:  {diff_entropy:.4f} bits/pixel")

            # Compress the difference array
            flat_diff = diff_array.flatten()
            text = ""
            for p in flat_diff:
                text = text + chr(p)

            encoded_ints = self.encode(text)
            bitstring = self.int_list_to_binary_string(encoded_ints)
            bitstring = self.add_code_length_info(bitstring)
            padded = self.pad_encoded_data(bitstring)
            byte_array = self.get_byte_array(padded)

            output_path = self.filename + '_' + color + '_diff_compressed.bin'
            header = struct.pack('>HH', self.num_rows, self.num_cols)

            with open(output_path, 'wb') as f:
                f.write(header)
                f.write(bytes(byte_array))

            uncomp = len(flat_diff)
            comp = os.path.getsize(output_path)
            total_uncomp = total_uncomp + uncomp
            total_comp = total_comp + comp

            CR = comp / uncomp
            avg = (comp * 8) / uncomp
            print(f"  Saved -> '{os.path.basename(output_path)}'")
            print(f"  Code Length:         {self.codelength} bits")
            print(f"  Avg Code Length:     {avg:.4f} bits/pixel")
            print(f"  Channel CR:          {CR:.4f}")

        # Overall statistics for all 3 channels
        overall_CR = total_comp / total_uncomp
        overall_CF = total_uncomp / total_comp
        overall_SS = (total_uncomp - total_comp) / total_uncomp
        overall_avg = (total_comp * 8) / (self.num_rows * self.num_cols * 3)

        print("\n--- LEVEL 5 SUMMARY ---")
        print(f"Total Original Size:     {total_uncomp:,d} bytes")
        print(f"Total Compressed Size:   {total_comp:,d} bytes")
        print(f"Overall Avg Code Length: {overall_avg:.4f} bits/pixel")
        print(f"Compression Ratio  (CR): {overall_CR:.4f}")
        print(f"Compression Factor (CF): {overall_CF:.4f}")
        print(f"Space Saving       (SS): {overall_SS*100:.2f}%")

    def decompress_color_diff_image(self):
        print("\n--- LEVEL 5: COLOR IMAGE DIFFERENCE DECOMPRESSION ---")

        restored_channels = []

        for color in self.channels:
            input_path = self.filename + '_' + color + '_diff_compressed.bin'
            print(f"Decompressing channel {color}  <- '{os.path.basename(input_path)}'")

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

            # Rebuild the difference array and restore original pixels
            restored_flat = np.array([ord(c) for c in decomp_text], dtype=np.uint8)
            restored_diff_array = restored_flat.reshape((self.num_rows, self.num_cols))
            restored_channel = self.restore_from_difference_image(restored_diff_array)
            restored_channels.append(restored_channel)

        # Combine all 3 channels into the final color image
        restored_img_array = np.dstack(restored_channels)
        output_path = self.filename + '_color_diff_decompressed.bmp'

        Image.fromarray(restored_img_array, 'RGB').save(output_path)
        print(f"\nColor diff image reconstructed -> '{os.path.basename(output_path)}'")

        return restored_img_array


# -----------------------------------------------------------------------
if __name__ == "__main__":
    image_name = "thumbs_up"
    image_file_path = image_name + ".bmp"

    if not os.path.exists(image_file_path):
        print(f"ERROR: '{image_file_path}' not found.")
    else:
        lzw = ColorDiffImageLZWCoding(image_name)

        lzw.compress_color_diff_image(image_file_path)
        restored = lzw.decompress_color_diff_image()

        print("\n--- LEVEL 5: VERIFICATION ---")
        original = np.array(Image.open(image_file_path).convert('RGB'))
        if np.array_equal(original, restored):
            print("SUCCESS: Original and reconstructed images are IDENTICAL.")
        else:
            print("ERROR: Mismatch detected.")