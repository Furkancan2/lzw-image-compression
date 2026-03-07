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


class ColorImageLZWCoding(LZWCoding):
    # Level 4 - Color (RGB) Image Compression
    # Each color channel (R, G, B) is compressed separately

    def __init__(self, filename):
        super().__init__(filename, 'image')
        self.num_rows = 0
        self.num_cols = 0
        self.channels = ['R', 'G', 'B']

    def compress_color_image(self, image_path):
        print("\n--- LEVEL 4: COLOR IMAGE COMPRESSION (RGB) ---")

        # Open image as RGB (3 channels)
        img = Image.open(image_path).convert('RGB')
        img_array = np.array(img)
        self.num_rows, self.num_cols, _ = img_array.shape
        print(f"Image Dimensions: {self.num_rows}x{self.num_cols}  (3 channels)")

        total_uncomp = 0
        total_comp = 0

        # Process each channel separately (R=0, G=1, B=2)
        for idx, color in enumerate(self.channels):
            print(f"\nChannel: {color}")

            # Get the single channel as a 2D array
            channel_array = img_array[:, :, idx]

            # Calculate entropy for this channel
            entropy = calculate_entropy(channel_array)
            print(f"  Entropy:  {entropy:.4f} bits/pixel")

            # Flatten and encode
            flat_array = channel_array.flatten()
            text = ""
            for p in flat_array:
                text = text + chr(p)

            encoded_ints = self.encode(text)
            bitstring = self.int_list_to_binary_string(encoded_ints)
            bitstring = self.add_code_length_info(bitstring)
            padded = self.pad_encoded_data(bitstring)
            byte_array = self.get_byte_array(padded)

            # Save this channel to its own file
            output_path = self.filename + '_' + color + '_compressed.bin'
            header = struct.pack('>HH', self.num_rows, self.num_cols)

            with open(output_path, 'wb') as f:
                f.write(header)
                f.write(bytes(byte_array))

            uncomp = len(flat_array)
            comp = os.path.getsize(output_path)
            total_uncomp = total_uncomp + uncomp
            total_comp = total_comp + comp

            CR = comp / uncomp
            avg = (comp * 8) / uncomp
            print(f"  Saved -> '{os.path.basename(output_path)}'")
            print(f"  Code Length:         {self.codelength} bits")
            print(f"  Avg Code Length:     {avg:.4f} bits/pixel")
            print(f"  Channel CR:          {CR:.4f}")

        # Print overall statistics for all 3 channels combined
        overall_CR = total_comp / total_uncomp
        overall_CF = total_uncomp / total_comp
        overall_SS = (total_uncomp - total_comp) / total_uncomp
        overall_avg = (total_comp * 8) / (self.num_rows * self.num_cols * 3)

        print("\n--- LEVEL 4 SUMMARY ---")
        print(f"Total Original Size:     {total_uncomp:,d} bytes")
        print(f"Total Compressed Size:   {total_comp:,d} bytes")
        print(f"Overall Avg Code Length: {overall_avg:.4f} bits/pixel")
        print(f"Compression Ratio  (CR): {overall_CR:.4f}")
        print(f"Compression Factor (CF): {overall_CF:.4f}")
        print(f"Space Saving       (SS): {overall_SS*100:.2f}%")

    def decompress_color_image(self):
        print("\n--- LEVEL 4: COLOR IMAGE DECOMPRESSION ---")

        restored_channels = []

        # Decompress each channel separately
        for color in self.channels:
            input_path = self.filename + '_' + color + '_compressed.bin'
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

            # Rebuild this channel's 2D array
            restored_flat = np.array([ord(c) for c in decomp_text], dtype=np.uint8)
            restored_channel = restored_flat.reshape((self.num_rows, self.num_cols))
            restored_channels.append(restored_channel)

        # Stack all 3 channels back together to form the color image
        restored_img_array = np.dstack(restored_channels)
        output_path = self.filename + '_color_decompressed.bmp'

        Image.fromarray(restored_img_array, 'RGB').save(output_path)
        print(f"\nColor image reconstructed -> '{os.path.basename(output_path)}'")

        return restored_img_array


# -----------------------------------------------------------------------
if __name__ == "__main__":
    image_name = "thumbs_up"
    image_file_path = image_name + ".bmp"

    if not os.path.exists(image_file_path):
        print(f"ERROR: '{image_file_path}' not found.")
    else:
        lzw = ColorImageLZWCoding(image_name)

        lzw.compress_color_image(image_file_path)
        restored = lzw.decompress_color_image()

        print("\n--- LEVEL 4: VERIFICATION ---")
        original = np.array(Image.open(image_file_path).convert('RGB'))
        if np.array_equal(original, restored):
            print("SUCCESS: Original and reconstructed images are IDENTICAL.")
        else:
            print("ERROR: Mismatch detected.")