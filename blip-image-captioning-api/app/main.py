from fastapi import FastAPI, File, UploadFile, HTTPException
import requests
import logging.config
from model import load_model, generate_caption
from utils import load_image_from_file, load_image_from_path_file
from config import settings
from pydantic import BaseModel

app = FastAPI()

# Load the BLIP model once when the app starts
model, processor = load_model(settings.blip_model_name)

# Configure logging
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class ImageCaption(BaseModel):
    caption: str

class ItemCaption(BaseModel):
    imageUrl: str
    imageName: str

# Example root path handler
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Image Captioning API!"}

@app.post("/predict")
async def caption(file: UploadFile = File(...), text: str = None):
    try:
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Invalid image format")

        loaded_image = load_image_from_file(await file.read())
        caption = generate_caption(model, processor, loaded_image, text)
        return {"caption": caption}
    except Exception as e:
        logger.exception("Error in /caption endpoint")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await file.close()

@app.post("/captioned")
async def captioned(item: ItemCaption):
    r = requests.get(item.imageUrl) 
    file_location = "Images/" +item.imageName
    with open(file_location, 'wb') as f:
        f.write(r.content)
    loaded_image = load_image_from_path_file(file_location)
    caption = generate_caption(model, processor, loaded_image, None)
    return {"caption": caption}


