import os
import math

# LZW Compression and Decompression class
# This class can compress text files and image files using the LZW algorithm
# Level 1 uses progressive (variable) code length
# Levels 2-5 use fixed code length

class LZWCoding:

    def __init__(self, filename, data_type, progressive=True):
        # Save the parameters
        self.data_type = data_type
        self.progressive = progressive
        self.codelength = None

        # Handle file extension - remove it if it exists
        root, ext = os.path.splitext(filename)
        if ext.lower() in ('.txt', '.bin', '.bmp', '.png'):
            self.filename = root
            self._base_dir = os.path.dirname(os.path.abspath(root))
        else:
            self.filename = filename
            self._base_dir = os.path.dirname(os.path.abspath(filename))

        # If directory is empty, use the script's own directory
        if not self._base_dir:
            self._base_dir = os.path.dirname(os.path.realpath(__file__))

    # -----------------------------------------------------------------------
    # PROGRESSIVE ENCODE (Level 1 - Text)
    # Starts with 9-bit codes, increases bit width as dictionary grows
    # -----------------------------------------------------------------------

    def encode_progressive(self, uncompressed_data):
        # Initialize dictionary with all single characters (0-255)
        dict_size = 256
        dictionary = {}
        for i in range(dict_size):
            dictionary[chr(i)] = i

        # Start with 9-bit codes
        cur_bits = 9
        max_code = 2 ** cur_bits  # = 512

        w = ''
        result = []

        for c in uncompressed_data:
            wc = w + c
            if wc in dictionary:
                # Found wc in dictionary, extend current string
                w = wc
            else:
                # wc not found, output code for w and add wc to dictionary
                result.append((dictionary[w], cur_bits))
                dictionary[wc] = dict_size
                dict_size = dict_size + 1
                w = c

                # Check if we need to increase bit width
                if dict_size > max_code:
                    cur_bits = cur_bits + 1
                    max_code = 2 ** cur_bits

        # Output the last code
        if w:
            result.append((dictionary[w], cur_bits))

        self.codelength = cur_bits
        return result

    def decode_progressive(self, encoded_pairs):
        from io import StringIO

        # Initialize dictionary with all single characters (0-255)
        dict_size = 256
        dictionary = {}
        for i in range(dict_size):
            dictionary[i] = chr(i)

        result = StringIO()

        # Read first code
        first_code, _ = encoded_pairs[0]
        w = chr(first_code)
        result.write(w)

        # Process the rest of the codes
        for k, _ in encoded_pairs[1:]:
            if k in dictionary:
                entry = dictionary[k]
            elif k == dict_size:
                # Special case: code not yet in dictionary
                entry = w + w[0]
            else:
                raise ValueError('Bad compressed code: %s' % k)

            result.write(entry)
            dictionary[dict_size] = w + entry[0]
            dict_size = dict_size + 1
            w = entry

        return result.getvalue()

    # -----------------------------------------------------------------------
    # FIXED-WIDTH ENCODE / DECODE (Levels 2-5 - Image)
    # -----------------------------------------------------------------------

    def encode(self, uncompressed_data):
        # Initialize dictionary with all single characters (0-255)
        dict_size = 256
        dictionary = {}
        for i in range(dict_size):
            dictionary[chr(i)] = i

        w = ''
        result = []

        for c in uncompressed_data:
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                result.append(dictionary[w])
                dictionary[wc] = dict_size
                dict_size = dict_size + 1
                w = c

        if w:
            result.append(dictionary[w])

        # Calculate how many bits are needed to store the biggest code
        self.codelength = math.ceil(math.log2(max(len(dictionary), 2)))
        return result

    def decode(self, encoded_values):
        from io import StringIO

        # Initialize dictionary with all single characters (0-255)
        dict_size = 256
        dictionary = {}
        for i in range(dict_size):
            dictionary[i] = chr(i)

        result = StringIO()

        # Read first code
        w = chr(encoded_values.pop(0))
        result.write(w)

        # Process the rest
        for k in encoded_values:
            if k in dictionary:
                entry = dictionary[k]
            elif k == dict_size:
                entry = w + w[0]
            else:
                raise ValueError('Bad compressed k: %s' % k)

            result.write(entry)
            dictionary[dict_size] = w + entry[0]
            dict_size = dict_size + 1
            w = entry

        return result.getvalue()

    # -----------------------------------------------------------------------
    # BIT PACKING - Progressive
    # Convert list of (code, bit_width) pairs to a binary string
    # -----------------------------------------------------------------------

    def progressive_pairs_to_binary_string(self, encoded_pairs):
        bits = []
        for code, width in encoded_pairs:
            # Convert each code to binary with the given width
            for n in range(width):
                if code & (1 << (width - 1 - n)):
                    bits.append('1')
                else:
                    bits.append('0')
        return ''.join(bits)

    def binary_string_to_progressive_pairs(self, bitstring):
        # We need to simulate the same dictionary growth to know when bit width changes
        dict_size = 256
        cur_bits = 9
        max_code = 2 ** cur_bits

        pairs = []
        i = 0

        while i + cur_bits <= len(bitstring):
            code = int(bitstring[i:i + cur_bits], 2)
            pairs.append((code, cur_bits))
            i = i + cur_bits
            dict_size = dict_size + 1

            if dict_size > max_code:
                cur_bits = cur_bits + 1
                max_code = 2 ** cur_bits

        return pairs

    # -----------------------------------------------------------------------
    # BIT PACKING - Fixed width
    # -----------------------------------------------------------------------

    def int_list_to_binary_string(self, int_list):
        bits = []
        for num in int_list:
            for n in range(self.codelength):
                if num & (1 << (self.codelength - 1 - n)):
                    bits.append('1')
                else:
                    bits.append('0')
        return ''.join(bits)

    def add_code_length_info(self, bitstring):
        # Prepend the code length as an 8-bit number at the start
        code_length_bits = '{0:08b}'.format(self.codelength)
        return code_length_bits + bitstring

    def pad_encoded_data(self, encoded_data):
        # Add zeros at the end so total length is divisible by 8
        extra_bits = (8 - len(encoded_data) % 8) % 8
        encoded_data = encoded_data + '0' * extra_bits
        # Store how many padding bits we added (as 8-bit number at start)
        padding_info = '{0:08b}'.format(extra_bits)
        return padding_info + encoded_data

    def get_byte_array(self, padded_encoded_data):
        if len(padded_encoded_data) % 8 != 0:
            print('Compressed data not padded properly!')
            exit(0)
        b = bytearray()
        # Convert every 8 bits to a byte
        for i in range(0, len(padded_encoded_data), 8):
            b.append(int(padded_encoded_data[i:i+8], 2))
        return b

    def remove_padding(self, padded_encoded_data):
        # Read how many padding bits were added
        extra_padding = int(padded_encoded_data[:8], 2)
        encoded_data = padded_encoded_data[8:]
        # Remove the padding bits from the end
        if extra_padding != 0:
            encoded_data = encoded_data[:-extra_padding]
        return encoded_data

    def extract_code_length_info(self, bitstring):
        # Read the code length from the first 8 bits
        self.codelength = int(bitstring[:8], 2)
        return bitstring[8:]

    def binary_string_to_int_list(self, bitstring):
        int_codes = []
        # Read groups of bits, each group is one code
        for i in range(0, len(bitstring), self.codelength):
            int_codes.append(int(bitstring[i:i+self.codelength], 2))
        return int_codes

    # -----------------------------------------------------------------------
    # Level 1 - TEXT COMPRESSION (Progressive LZW)
    # -----------------------------------------------------------------------

    def compress_text_file(self):
        input_path = self.filename + '.txt'
        output_path = self.filename + '_compressed.bin'

        # Read the text file
        with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()

        # Encode the text with progressive LZW
        encoded_pairs = self.encode_progressive(text)
        bitstring = self.progressive_pairs_to_binary_string(encoded_pairs)

        # Add padding so length is divisible by 8
        extra_bits = (8 - len(bitstring) % 8) % 8
        bitstring = bitstring + '0' * extra_bits

        # Store padding count at the beginning
        header_bits = '{0:08b}'.format(extra_bits)
        full_bits = header_bits + bitstring

        # Convert binary string to actual bytes
        b = bytearray()
        for i in range(0, len(full_bits), 8):
            b.append(int(full_bits[i:i+8], 2))

        # Write the compressed file
        with open(output_path, 'wb') as f:
            f.write(bytes(b))

        # Calculate and print statistics
        original_size = os.path.getsize(input_path)
        compressed_size = len(b)
        CR = compressed_size / original_size
        CF = original_size / compressed_size
        SS = (original_size - compressed_size) / original_size

        print("\n--- LEVEL 1: TEXT COMPRESSION (Progressive LZW) ---")
        print(f"File compressed  -> '{os.path.basename(output_path)}'")
        print(f"Original Size:       {original_size:,d} bytes")
        print(f"Compressed Size:     {compressed_size:,d} bytes")
        print(f"Final Code Length:   {self.codelength} bits  (started at 9 bits, progressive)")
        print(f"Compression Ratio  (CR = comp/orig):  {CR:.4f}")
        print(f"Compression Factor (CF = orig/comp):  {CF:.4f}")
        print(f"Space Saving       (SS):              {SS*100:.2f}%")

        return output_path

    # -----------------------------------------------------------------------
    # Level 1 - TEXT DECOMPRESSION + VERIFICATION
    # -----------------------------------------------------------------------

    def decompress_text_file(self):
        input_path = self.filename + '_compressed.bin'
        output_path = self.filename + '_decompressed.txt'
        original_path = self.filename + '.txt'

        # Read the compressed binary file
        with open(input_path, 'rb') as f:
            compressed_data = f.read()

        # Convert bytes to binary string
        full_bits = ''
        for byte in compressed_data:
            full_bits = full_bits + bin(byte)[2:].rjust(8, '0')

        # Remove padding
        extra_padding = int(full_bits[:8], 2)
        payload_bits = full_bits[8:]
        if extra_padding:
            payload_bits = payload_bits[:-extra_padding]

        # Decode
        encoded_pairs = self.binary_string_to_progressive_pairs(payload_bits)
        decompressed_text = self.decode_progressive(encoded_pairs)

        # Write the decompressed text file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(decompressed_text)

        print("\n--- LEVEL 1: TEXT DECOMPRESSION (Progressive LZW) ---")
        print(f"Decompressed -> '{os.path.basename(output_path)}'")

        comp_size = os.path.getsize(input_path)
        restored_size = os.path.getsize(output_path)
        CR = comp_size / restored_size
        CF = restored_size / comp_size
        SS = (restored_size - comp_size) / restored_size
        print(f"Compression Ratio  (CR):  {CR:.4f}")
        print(f"Compression Factor (CF):  {CF:.4f}")
        print(f"Space Saving       (SS):  {SS*100:.2f}%")

        # Compare original vs restored
        print("\n--- LEVEL 1: VERIFICATION ---")
        if os.path.exists(original_path):
            with open(original_path, 'r', encoding='utf-8', errors='replace') as f:
                original_text = f.read()
            if original_text == decompressed_text:
                print("SUCCESS: Original and decompressed texts are IDENTICAL.")
            else:
                min_len = min(len(original_text), len(decompressed_text))
                diffs = 0
                for i in range(min_len):
                    if original_text[i] != decompressed_text[i]:
                        diffs = diffs + 1
                print(f"MISMATCH: {diffs} character(s) differ. "
                      f"Lengths: original={len(original_text)}, "
                      f"restored={len(decompressed_text)}")
        else:
            print("(Original .txt not found — skipping text comparison)")

        return output_path