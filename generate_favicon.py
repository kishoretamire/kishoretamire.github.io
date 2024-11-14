from PIL import Image
import os

def create_favicon(input_image_path="cricket_logo.png"):
    """Create favicon files from the input image"""
    try:
        # Create favicon directory if it doesn't exist
        os.makedirs('favicon', exist_ok=True)
        
        # Open the source image
        img = Image.open(input_image_path)
        
        # Generate different sizes
        sizes = {
            'favicon.ico': [16, 32, 48],  # Multiple sizes for ICO
            'favicon-16x16.png': [16],
            'favicon-32x32.png': [32],
            'apple-touch-icon.png': [180],
            'android-chrome-192x192.png': [192],
            'android-chrome-512x512.png': [512]
        }
        
        for filename, dimensions in sizes.items():
            if filename.endswith('.ico'):
                # Create ICO file with multiple sizes
                images = []
                for size in dimensions:
                    resized = img.resize((size, size), Image.Resampling.LANCZOS)
                    if resized.mode != 'RGBA':
                        resized = resized.convert('RGBA')
                    images.append(resized)
                images[0].save(f'favicon/{filename}', format='ICO', sizes=[(s, s) for s in dimensions])
            else:
                # Create PNG files
                size = dimensions[0]
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                if resized.mode != 'RGBA':
                    resized = resized.convert('RGBA')
                resized.save(f'favicon/{filename}', format='PNG')
        
        print("Favicon files generated successfully!")
        
    except Exception as e:
        print(f"Error generating favicons: {e}")

if __name__ == "__main__":
    create_favicon() 