"""Seminar 6. Image Binary Classification with Keras. ML ops."""
import argparse
import os
import zipfile
import shutil
from urllib.request import urlretrieve

import tensorflow as tf
import keras
import boto3
import dotenv

DATA_URL = 'https://storage.yandexcloud.net/fa-bucket/cats_dogs_train.zip'
PATH_TO_DATA_ZIP = 'data/raw/cats_dogs_train.zip'
PATH_TO_DATA = 'data/raw/cats_dogs_train'
PATH_TO_MODEL = 'models/model_6'
BUCKET_NAME = 'neuralnets2023'
# todo fix your git user name and copy .env to project root
YOUR_GIT_USER = 'MrGummyl3ear'


def download_data():
    """Pipeline: download and extract data"""
    if not os.path.exists(PATH_TO_DATA_ZIP):
        print('Downloading data...')
        urlretrieve(DATA_URL, PATH_TO_DATA_ZIP)
    else:
        print('Data is already downloaded!')

    if not os.path.exists(PATH_TO_DATA):
        print('Extracting data...')
        with zipfile.ZipFile(PATH_TO_DATA_ZIP, 'r') as zip_ref:
            zip_ref.extractall(PATH_TO_DATA)
    else:
        print('Data is already extracted!')


def make_model(input_shape, num_classes):
    inputs = keras.Input(shape=input_shape)

    x = keras.layers.Rescaling(1.0 / 255)(inputs)
    x = keras.layers.Conv2D(128, 3, strides=2, padding="same")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)

    previous_block_activation = x  # Set aside residual

    for size in [256, 512, 728]:
        x = keras.layers.Activation("relu")(x)
        x = keras.layers.SeparableConv2D(size, 3, padding="same")(x)
        x = keras.layers.BatchNormalization()(x)

        x = keras.layers.Activation("relu")(x)
        x = keras.layers.SeparableConv2D(size, 3, padding="same")(x)
        x = keras.layers.BatchNormalization()(x)

        x = keras.layers.MaxPooling2D(3, strides=2, padding="same")(x)

        # Project residual
        residual = keras.layers.Conv2D(size, 1, strides=2, padding="same")(
            previous_block_activation
        )
        x = keras.layers.add([x, residual])  # Add back residual
        previous_block_activation = x  # Set aside next residual

    x = keras.layers.SeparableConv2D(1024, 3, padding="same")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)

    x = keras.layers.GlobalAveragePooling2D()(x)

    x = keras.layers.Dropout(0.5)(x)
    outputs = keras.layers.Dense(1, activation="sigmoid")(x)
    return keras.Model(inputs, outputs)


def train():
    """Pipeline: Build, train and save model to models/model_6"""
    # Todo: Copy some code from seminar5 and https://keras.io/examples/vision/image_classification_from_scratch/
    print('Training model')
    epochs = 5
    batch_size = 64
    image_size = (180, 180)

    train_ds, val_ds = keras.utils.image_dataset_from_directory(
        PATH_TO_DATA+"/PetImages",
        validation_split=0.2,
        subset="both",
        seed=1337,
        image_size=image_size,
        batch_size=batch_size,
    )

    model = make_model(image_size+(3,), 2)
    model.compile(optimizer=keras.optimizers.Adam(),
                  loss=keras.losses.BinaryCrossentropy(),
                  metrics=[keras.metrics.Precision(thresholds=0.5)])
    model.fit(train_ds, epochs=epochs, validation_data=val_ds)
    model.save(PATH_TO_MODEL)

def upload():
    """Pipeline: Upload model to S3 storage"""
    print('Upload model')
    zip_model_path = PATH_TO_MODEL+'.zip'
    shutil.make_archive(base_name=PATH_TO_MODEL,
                        format='zip',
                        root_dir=PATH_TO_MODEL)

    config = dotenv.dotenv_values('.env')

    ACCESS_KEY = config['ACCESS_KEY']
    SECRET_KEY = config['SECRET_KEY']

    client = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

    client.upload_file(zip_model_path, BUCKET_NAME, f'{YOUR_GIT_USER}/model_6.zip')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='src/seminar6.py',
        description='Typical DL lifecycle pipelines.')
    parser.add_argument('--download', action='store_true', help='Download images and extract to data/raw directory')
    parser.add_argument('--train', action='store_true', help='Build, train and save model to models/seminar6_model')
    parser.add_argument('--upload', action='store_true', help='Upload model to S3 storage')
    args = parser.parse_args()
    if args.download:
        download_data()
    if args.train:
        train()
    if args.upload:
        upload()