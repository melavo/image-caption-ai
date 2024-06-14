# image-caption-ai
## End_OptimizerExpansionNet: Optimizing Economical Image Captioning ExpansionNet v2 Optimization
The improvement for [ExpansionNet v2](https://arxiv.org/abs/2208.06551) in MSCOCO image captioning task with the three improvement:

1) Utilizing Swin-TransformerV2-Base as the core extractor of image visual features.
2) Memory-Augmented Attention integrated into the traditional Multi-Head Attention
3) With the introduction of the new Multiplicative Residual Embedding layer and adjustments to the Static and Dynamic Expansion structure, the number of encoder and decoder layers has been reduced.

## Training Scripts:

#### Requirements:

* python >= 3.7
* numpy
* Java 1.8.0
* pytorch 1.9.0
* h5py

The training progress is done on the two model: Optimizer-ExpansionNet and the baseline - ExpansionNet v2, you need to choose the model to train in the `train.py` and `test.py` files. For Optimizer-ExpansionNet, `N_enc` and `N_dec` are `2`, that for ExpansionNet v2 is `3`.  

#### Dataset preparation:

MSCOCO 2014 dataset: [here](https://cocodataset.org/#home)

The respective captions of [Jia Cheng Hu](https://github.com/jchenghu): [drive](https://drive.google.com/drive/folders/1bBMH4-Fw1LcQZmSzkMCqpEl0piIP88Y3?usp=sharing)

Swin-Transformer backbone: [github](https://github.com/microsoft/Swin-Transformer/blob/main/MODELHUB.md)

#### 1. Cross Entropy Training: Features generation:

First we generate the features for the first training step:
```
python data_generator.py \
    --save_model_path ./path_to_backbone/swinv2_base_patch4_window12to24_192to384_22kto1k_ft.pth \
    --output_path ./path_to_features_file/features.hdf5 \
    --images_path ./path_to_dataset_folder/ \
    --captions_path ./path_to_dataset_folder/
```
The ouput file "features.hdf5"'s size is pretty big (67.7GB), be careful of your hardware capacity.

#### 2. Cross-Entropy Training: Partial Training:

In this step the model is trained using the Cross Entropy loss and the features generated
in the previous step:
```
python train.py --N_enc 2 --N_dec 2  \
    --model_dim 512 --seed 775533 --optim_type radam --sched_type custom_warmup_anneal  \
    --warmup 10000 --lr 2e-4 --anneal_coeff 0.8 --anneal_every_epoch 2 --enc_drop 0.3 \
    --dec_drop 0.3 --enc_input_drop 0.3 --dec_input_drop 0.3 --drop_other 0.3  \
    --batch_size 48 --num_accum 1 --num_gpus 1 --ddp_sync_port 11317 --eval_beam_sizes [3]  \
    --save_path ./save_checkpoint_path/ --save_every_minutes 60 --how_many_checkpoints 1  \
    --is_end_to_end False --features_path ./path_to_features_file/features.hdf5 --partial_load False \
    --print_every_iter 11807 --eval_every_iter 999999 \
    --reinforce False --num_epochs 8
```
#### 3. Cross-Entropy Training: End to End Training:

The following command will train the entire network in the end to end mode. However, one argument need to be changed according to the previous result, the checkpoint name file with the prefix `checkpoint_ ... _xe.pth`, which may be overwritten if be kept the same name, we will refer it as `phase2_checkpoint` below and in
the later step:
```
python train.py --N_enc 2 --N_dec 2  \
    --model_dim 512 --optim_type radam --seed 775533   --sched_type custom_warmup_anneal  \
    --warmup 1 --lr 3e-5 --anneal_coeff 0.55 --anneal_every_epoch 1 --enc_drop 0.3 \
    --dec_drop 0.3 --enc_input_drop 0.3 --dec_input_drop 0.3 --drop_other 0.3  \
    --batch_size 8 --num_accum 3 --num_gpus 1 --ddp_sync_port 11317 --eval_beam_sizes [3]  \
    --save_path ./save_checkpoint_path/ --save_every_minutes 60 --how_many_checkpoints 1  \
    --is_end_to_end True --images_path ./path_to_dataset_folder/ --partial_load True \
    --backbone_save_path ./path_to_backbone/swinv2_base_patch4_window12to24_192to384_22kto1k_ft.pth \
    --body_save_path ./save_checkpoint_path/phase2_checkpoint \
    --print_every_iter 15000 --eval_every_iter 999999 \
    --reinforce False --num_epochs 2
```
#### 4. CIDEr optimization: Features generation:

This step generates the features for the reinforcement step:
```
python data_generator.py \
    --save_model_path ./save_checkpoint_path/phase3_checkpoint \
    --output_path ./path_to_features_file/features.hdf5 \
    --images_path ./path_to_dataset_folder/ \
    --captions_path ./path_to_dataset_folder/
```

#### 5. CIDEr optimization: Partial Training:

The following command performs the partial training using the self-critical learning:
```
python train.py --N_enc 2 --N_dec 2  \
    --model_dim 512 --optim_type radam --seed 775533  --sched_type custom_warmup_anneal  \
    --warmup 1 --lr 1e-4 --anneal_coeff 0.8 --anneal_every_epoch 1 --enc_drop 0.1 \
    --dec_drop 0.1 --enc_input_drop 0.1 --dec_input_drop 0.1 --drop_other 0.1  \
    --batch_size 8 --num_accum 2 --num_gpus 1 --ddp_sync_port 11317 --eval_beam_sizes [5]  \
    --save_path ./save_checkpoint_path/ --save_every_minutes 60 --how_many_checkpoints 1  \
    --is_end_to_end False --partial_load True \
    --features_path ./path_to_features_file/features.hdf5 \
    --body_save_path ./save_checkpoint_path/phase3_checkpoint.pth \
    --print_every_iter 4000 --eval_every_iter 99999 \
    --reinforce True --num_epochs 9
```

#### 6. CIDEr optimization: End to End Training:

This final step retrains the model in an end-to-end manner, but it is optional as it only marginally enhances performance:
```
python train.py --N_enc 2 --N_dec 2  \
    --model_dim 512 --optim_type radam --seed 775533 --sched_type custom_warmup_anneal  \
    --warmup 1 --anneal_coeff 1.0 --lr 2e-6 --enc_drop 0.1 \
    --dec_drop 0.1 --enc_input_drop 0.1 --dec_input_drop 0.1 --drop_other 0.1  \
    --batch_size 4 --num_accum 2 --num_gpus 1 --ddp_sync_port 11317 --eval_beam_sizes [5]  \
    --save_path ./save_checkpoint_path/ --save_every_minutes 60 --how_many_checkpoints 1  \
    --is_end_to_end True --images_path ./path_to_dataset_folder/ --partial_load True \
    --backbone_save_path ./save_checkpoint_path/phase3_checkpoint \
    --body_save_path ./save_checkpoint_path/phase5_checkpoint \
    --print_every_iter 15000 --eval_every_iter 999999 \
    --reinforce True --num_epochs 1
```

## Evaluation:

```
python test.py --N_enc 2 --N_dec 2 --model_dim 512 \
    --num_gpus 1 --eval_beam_sizes [5] --is_end_to_end True \
    --save_model_path ./save_checkpoint_path/phase6_checkpoint
```
## Demo:

To test the model on generic images, you can run the script:
``` 
python demo.py \
     	--load_path path_to_checkpoint/___.pth \
     	--image_paths your_image_path/image_1 your_image_path/image_2 ...
```


## API End_OptimizerExpansionNet:

To run api model

``` 
uvicorn api:app --reload --host 127.0.0.1 --workers 4 --port 5000 --uds /tmp/uvicorndemo.sock
```

## API BLIP

cd to folder blip-image-captioning-api
pip install -r requirements.txt
uvicorn main:app --reload
or
uvicorn main:app --reload --host 127.0.0.1 --workers 4 --port 5001 --uds /tmp/uvicornblip.sock

## App Android Demo Image Caption
Changed https://demo.com:8443 to link api image caption