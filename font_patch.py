# Write by GPT-4o mini👨‍💻, scillidan🤡
# Purpose: Patch fonts by copying glyphs from a patch font to a main font.
# Tools: fontTools
# Usage: python file.py <main_font> <patch_font> <Fontfamily> <Subfamily Name>

from fontTools.ttLib import TTFont
import sys
import os

def patch_fonts(main_font_path, patch_font_path, font_family, subfamily_name, output_font_name):
    main_font = TTFont(main_font_path)
    patch_font = TTFont(patch_font_path)

    if 'glyf' not in main_font or 'hmtx' not in main_font:
        print("Main font does not contain 'glyf' or 'hmtx' tables.")
        return

    if 'glyf' not in patch_font or 'hmtx' not in patch_font:
        print("Patch font does not contain 'glyf' or 'hmtx' tables.")
        return

    max_glyphs_to_copy = 65535 - len(main_font['glyf'].keys())
    copied_glyphs = 0

    for name in patch_font['glyf'].keys():
        if name not in main_font['glyf'] and copied_glyphs < max_glyphs_to_copy:
            main_font['glyf'][name] = patch_font['glyf'][name]
            copied_glyphs += 1

            if 'hmtx' in patch_font and name in patch_font['hmtx'].metrics:
                main_font['hmtx'].metrics[name] = patch_font['hmtx'].metrics[name]

    if 'name' in main_font:
        for record in main_font['name'].names:
            if record.nameID == 1:
                record.string = font_family.encode('utf-16-be')
            elif record.nameID == 4:
                record.string = output_font_name.encode('utf-16-be')
            elif record.nameID == 2:
                record.string = subfamily_name.encode('utf-16-be')

    # Create the output directory if it doesn't exist
    output_dir = font_family
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{output_font_name}.ttf")
    main_font.save(output_path)
    print(f"Patched font saved as '{output_path}'.")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python cli.py <main_font> <patch_font> <Fontfamily> <Subfamily Name>")
        sys.exit(1)

    main_font_path = sys.argv[1]
    patch_font_path = sys.argv[2]
    font_family = sys.argv[3]
    subfamily_name = sys.argv[4]

    output_font_name = f"{font_family.replace(' ', '-')}-{subfamily_name.replace(' ', '-')}"

    patch_fonts(main_font_path, patch_font_path, font_family, subfamily_name, output_font_name)

