import torch
import shutil
import pickle
import requests
from argparse import Namespace

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from models.End_OptimizerExpansionNet import End_OptimizerExpansionNet
from utils.image_utils import preprocess_image
from utils.language_utils import tokens2description

model_dim = 512
n_enc= 3
n_dec = 3
max_length = 16
max_seq_len =74

beam_size = 5
load_path = '' #path to file .pth

drop_args = Namespace(enc=0.0,
                          dec=0.0,
                          enc_input=0.0,
                          dec_input=0.0,
                          other=0.0)
model_args = Namespace(model_dim=model_dim,
                           N_enc=n_enc,
                           N_dec=n_dec,
                           dropout=0.0,
                           drop_args=drop_args)

with open('./demo_material/demo_coco_tokens.pickle', 'rb') as f:
        coco_tokens = pickle.load(f)
        sos_idx = coco_tokens['word2idx_dict'][coco_tokens['sos_str']]
        eos_idx = coco_tokens['word2idx_dict'][coco_tokens['eos_str']]

img_size = 384

model = End_OptimizerExpansionNet(swin_img_size=img_size, swin_patch_size=4, swin_in_chans=3,
                                swin_embed_dim=192, swin_depths=[2, 2, 18, 2], swin_num_heads=[6, 12, 24, 48],
                                swin_window_size=12, swin_mlp_ratio=4., swin_qkv_bias=True, swin_qk_scale=None,
                                swin_drop_rate=0.0, swin_attn_drop_rate=0.0, swin_drop_path_rate=0.0,
                                swin_norm_layer=torch.nn.LayerNorm, swin_ape=False, swin_patch_norm=True,
                                swin_use_checkpoint=False,
                                final_swin_dim=1536,
                                d_model=model_dim, N_enc=n_enc,
                                N_dec=n_dec, num_heads=8, ff=2048,
                                num_exp_enc_list=[32, 64, 128, 256, 512],
                                num_exp_dec=16,
                                output_word2idx=coco_tokens['word2idx_dict'],
                                output_idx2word=coco_tokens['idx2word_list'],
                                max_seq_len=max_seq_len, drop_args=model_args.drop_args,
                                rank='cpu')
   
#checkpoint = torch.load(load_path, map_location=torch.device('cuda:0'))
checkpoint = torch.load(load_path)
model.load_state_dict(checkpoint['model_state_dict'])


def predict_step(image_paths):
    
    input_images = []
    for path in image_paths:
        input_images.append(preprocess_image(path, img_size))
    
    preds = []
  
    for i in range(len(input_images)):
        path = image_paths[i]
        image = input_images[i]
        beam_search_kwargs = {'beam_size': beam_size,
                              'beam_max_seq_len': max_seq_len,
                              'sample_or_max': 'max',
                              'how_many_outputs': 1,
                              'sos_idx': sos_idx,
                              'eos_idx': eos_idx}
        with torch.no_grad():
            pred, _ = model(enc_x=image,
                            enc_x_num_pads=[0],
                            mode='beam_search', **beam_search_kwargs)
        pred = tokens2description(pred[0][0], coco_tokens['idx2word_list'], sos_idx, eos_idx)
        preds.append(pred)
    
    preds = [pred.strip() for pred in preds]
        #print(path + ' \n\tDescription: ' + pred + '\n')
    return preds

app = FastAPI(title="Image Captioning API", description="An API for generating caption for image.")

class ImageCaption(BaseModel):
    caption: str

class ItemCaption(BaseModel):
    imageUrl: str
    imageName: str

@app.post("/predict", response_model=ImageCaption)
def predict(file: UploadFile = File(...)):
    file_location = f"images/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    result = predict_step([file_location])
    return JSONResponse(content={"caption": result[0]})

@app.post("/predicts", response_model=ImageCaption)
def predicts(files: list[UploadFile]):
    imagePaths = [];
    for file in files:
        file_location = f"images/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        imagePaths.append(file_location)
    result = predict_step(imagePaths)
    return JSONResponse(content={"caption": result})

@app.post("/captioned")
def captioned(item: ItemCaption):
    r = requests.get(item.imageUrl) 
    file_location = "images/" +item.imageName
    with open(file_location, 'wb') as f:
        f.write(r.content)
    result = predict_step([file_location])
    return JSONResponse(content={"caption": result})

# Redirect the user to the documentation
@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")