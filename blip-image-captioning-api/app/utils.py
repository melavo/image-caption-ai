import io
from PIL import Image

def load_image_from_file(file_data):
    try:
        image = Image.open(io.BytesIO(file_data)).convert('RGB')
        return image
    except Exception as e:
        raise ValueError("Invalid image data") from e

def load_image_from_path_file(file_path):
    try:
        image = Image.open(file_path).convert('RGB')
        return image
    except Exception as e:
        raise ValueError("Invalid image data") from e