# LZW Compression for Text and Images

Lossless compression of text files and grayscale/color images using the **Lempel–Ziv–Welch (LZW)** algorithm, implemented from scratch in Python. The project is built in six levels, from plain text compression up to a desktop GUI, and shows how **difference images** lower entropy and improve LZW compression.

**Highlights**
- 📄 Text: **88.1% space saving** (715 KB → 85 KB) with progressive code length (9 → 16 bits)
- 🖼️ Images: difference coding improves space saving from **17% to 30%** on the same image
- ✅ Every level is verified to be **lossless** (decompressed output is identical to the input)

## Results

Measured with `sample.txt` (715,332 bytes) and `big_image.bmp` (900×698, RGB) from this repository.

| Level | Method | Entropy (bits/pixel) | Original | Compressed | Avg. code length | Space saving |
|---|---|---|---|---|---|---|
| 1 | Text, progressive LZW | – | 715,332 B | 84,809 B | – | **88.14%** |
| 2 | Grayscale image | 7.38 | 628,200 B | 518,838 B | 6.61 bits/px | 17.41% |
| 3 | Grayscale + difference image | 7.38 → 4.77 | 628,200 B | 436,662 B | 5.56 bits/px | **30.49%** |
| 4 | Color image (R, G, B separately) | ~7.2 per channel | 1,884,600 B | 1,563,958 B | 6.64 bits/px | 17.01% |
| 5 | Color + difference image | ~4.8 per channel | 1,884,600 B | 1,326,449 B | 5.63 bits/px | **29.62%** |

**Key observation:** neighbouring pixels are highly correlated. Storing each pixel as the difference from its left neighbour drops the entropy from about 7.4 to 4.8 bits/pixel, which creates more repeated patterns for LZW and nearly doubles the space saving.

## How it works

| Level | File | What it does |
|---|---|---|
| 1 | `LZW.py` | Core `LZWCoding` class. Text compression with **progressive (variable-width) codes** that start at 9 bits and grow with the dictionary. |
| 2 | `level_2.py` | Grayscale image compression with fixed-width codes; the header stores image size and code length. |
| 3 | `level_3.py` | Grayscale **difference image** (each pixel minus its left neighbour, first column uses the pixel above) before LZW. |
| 4 | `level_4.py` | Color image: R, G and B channels compressed separately, each with its own dictionary. |
| 5 | `level_5.py` | Color image with per-channel difference images. |
| 6 | `level_6.py` | **Tkinter GUI**: pick a file and a level, compress/decompress, see the original and restored image side by side with entropy, code length, CR, CF and space saving. |

Metrics reported: entropy, code length, average code length, compression ratio (CR = compressed/original), compression factor (CF = original/compressed) and space saving (SS = 1 − CR).

## Getting started

```bash
pip install numpy pillow
python level_6.py          # GUI (needs tkinter)
```

Command-line examples:

```bash
python text_file_compression_example.py      # compresses sample.txt
python text_file_decompression_example.py    # restores and verifies it
python level_3.py                            # runs a level on the test image in the current folder
```

## Tech
Python · NumPy · Pillow · Tkinter
