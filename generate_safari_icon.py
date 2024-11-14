from generate_favicon import create_favicon

def generate_safari_icon():
    """Create SVG version of the cricket logo for Safari pinned tabs"""
    svg_content = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <path fill="#000000" d="M256 0c141.4 0 256 114.6 256 256S397.4 512 256 512 0 397.4 0 256 114.6 0 256 0zm0 96c-88.4 0-160 71.6-160 160s71.6 160 160 160 160-71.6 160-160S344.4 96 256 96zm64 120c0-35.3-28.7-64-64-64s-64 28.7-64 64 28.7 64 64 64 64-28.7 64-64z"/>
</svg>'''

    # Create favicon directory if it doesn't exist
    import os
    os.makedirs('favicon', exist_ok=True)

    # Save the SVG file
    with open('favicon/safari-pinned-tab.svg', 'w') as f:
        f.write(svg_content)

if __name__ == "__main__":
    # First generate PNG and ICO files
    create_favicon()
    # Then generate Safari icon
    generate_safari_icon() 