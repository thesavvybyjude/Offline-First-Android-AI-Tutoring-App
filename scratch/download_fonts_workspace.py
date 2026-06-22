import os
import urllib.request

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print("Success.")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    os.makedirs('assets/fonts', exist_ok=True)
    
    fonts = {
        'Manrope-Regular.ttf': 'https://github.com/google/fonts/raw/main/ofl/manrope/static/Manrope-Regular.ttf',
        'Manrope-Medium.ttf': 'https://github.com/google/fonts/raw/main/ofl/manrope/static/Manrope-Medium.ttf',
        'Manrope-Bold.ttf': 'https://github.com/google/fonts/raw/main/ofl/manrope/static/Manrope-Bold.ttf'
    }
    
    for filename, url in fonts.items():
        dest = os.path.join('assets', 'fonts', filename)
        if not os.path.exists(dest):
            download_file(url, dest)
        else:
            print(f"{filename} already exists.")

if __name__ == "__main__":
    main()
