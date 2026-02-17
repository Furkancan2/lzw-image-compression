from LZW import LZWCoding

filename = 'sample'
text_to_compress = "^WED^WE^WEE^WEB^WET"


with open(filename + '.txt', 'w', encoding='utf-8') as f:
    f.write(text_to_compress)

print(f"'{filename}.txt' file created: {text_to_compress}")

lzw = LZWCoding(filename, 'text')
output_path = lzw.compress_text_file()