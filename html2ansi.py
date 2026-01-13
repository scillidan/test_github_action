# Usage: python file.py <input_file> <output_file>

import sys

def convert(input_file, output_file):
    convert_dict = {
        '<font color="gray">': "\033[38;5;245m",
        '<font class="grammar" color="green">': "\033[32m",
        "</font>": "\033[0m",
        "<br>": r"\n",
    }

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            modified_line = line
            for html_tag, ansi_code in convert_dict.items():
                modified_line = modified_line.replace(html_tag, ansi_code)
            outfile.write(modified_line)

def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Call the convert function with the file names
    convert(input_file, output_file)

    print(f"Conversion completed: {input_file} to {output_file}")

if __name__ == '__main__':
    main()
