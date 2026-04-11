# LT_scenario_gen

LT_scenario_gen is a toolkit for generating **safety-critical long-tail scenarios**, supporting both **image editing** and **text-to-image** workflows. It is designed for data augmentation and evaluation in autonomous driving and intelligent mobility systems.

## Features
- **Image editing workflow**: select and edit scenario categories from source images to generate long-tail samples.
- **Text-to-image workflow**: generate long-tail scenarios from natural-language prompts with category selection.

## Prerequisites
- Python 3.x
- A configured image generation/editing API

> **Note**: Configure `API_KEY` and `BASE_URL` in `utils/config.json`, and ensure compatibility with **nano banana pro**.

## Project Structure
```
LT_scenario_gen/
├── dataset_gen/           # main scripts and data generation logic
├── output_img/            # output directory for generated samples
├── prompt/                # prompt templates
├── utils/                 # configuration and utilities (includes config.json)
├── error_log.txt
└── README.md
```

## Usage

### 1) Generate long-tail scenarios by editing source images
Go to the `dataset_gen` folder:

1. Put your source images into `input_img/`.
2. Run `main(mism_step1())` in `M_img_S_mdf_step1.py`.
3. The `output_img/` directory will contain `opt.json` and `choose.json`, for example:

```json
{
  "best": "3.3, 2.1",
  "second": "1.3, 1.5, 3.4",
  "other": "1.1, 1.2, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.5",
  "input_image_path": "../input_img/t8.jpg"
}
```

```json
{
  "choose": "",
  "input_image_path": "../input_img/t8.jpg"
}
```

4. Fill in the category in `choose.json` under `"choose": ""` (manually or automatically via your own implementation). If the contents of `choose.json` and `opt.json` are not written correctly, you can execute `save_choose_to_json.py` and `save_opt_to_json.py` in the `utils` module to write the template content.
5. Run `main(mism_step2(1))` in `M_img_S_mdf_step2.py`.
6. Generated long-tail scenarios will appear in `output_img/`.

### 2) Generate long-tail scenarios from natural language
Go to the `dataset_gen` folder:

1. In `txt_2_pic.py`, enter the natural-language description and the category selection in the required location inside the `main` method.
2. Run the script.
3. Generated long-tail scenarios will appear in `output_img/`.

## Run Guide

The scripts in `LT_scenario_gen` use many relative paths, so the safest way is to run them from the `dataset_gen/` directory.

### Method A: Image editing workflow from existing driving images

This method is suitable when you already have front-view driving images and want to transform them into long-tail scenarios.

1. Prepare your input images:
   - Put all source images into `LT_scenario_gen/input_img/`.
   - Confirm `dataset_gen/file_path.json` points to:

```json
{
  "input_image_path": "../input_img",
  "output_image_path": "../output_img"
}
```

2. Configure the API:
   - Edit `LT_scenario_gen/utils/config.json`.
   - Fill in `OPENAI_API_KEY` and `BASE_URL`.

3. Enter the script directory and run step 1:

```powershell
cd LT_scenario_gen/dataset_gen
python M_img_S_mdf_step1.py
```

4. Check the generated category suggestion files:
   - The project expects files such as `opt.json` and `choose.json`.
   - You then manually fill the desired category into the `choose` field, for example `2.1`, `2.5`, `3.3`, or a finer category such as `3.3.1`.

Example:

```json
[
  {
    "choose": "3.3",
    "input_image_path": "../input_img/example.png"
  }
]
```

5. Run step 2 to generate the edited long-tail images:

```powershell
python M_img_S_mdf_step2.py
```

6. Check the results under `LT_scenario_gen/output_img/`.

### Method B: Direct text-to-image generation

This method is suitable when you want to generate a long-tail scene directly from a text description without providing an input image.

1. Open `LT_scenario_gen/dataset_gen/txt_2_pic.py`.
2. Edit the variables at the bottom of the file:

```python
desc = "Enter your natural language description"
opt = "Enter your OPT here"
```

Example:

```python
desc = "A dashcam view of a vehicle driving on an urban road at night, with light traffic ahead."
opt = "3.4"
```

3. Run the script from `dataset_gen/`:

```powershell
cd LT_scenario_gen/dataset_gen
python txt_2_pic.py
```

4. The generated image will be saved to `LT_scenario_gen/output_img/`.

### Method C: Batch processing multiple source images

If you place multiple images into `input_img/`, both `M_img_S_mdf_step1.py` and `M_img_S_mdf_step2.py` will iterate through all images in that folder. A typical batch workflow is:

```powershell
cd LT_scenario_gen/dataset_gen
python M_img_S_mdf_step1.py
python M_img_S_mdf_step2.py
```

This is the recommended method when you want to build a batch of edited long-tail samples for augmentation or evaluation.

## Notes Before Running

- Install dependencies first if needed, for example: `pip install requests`.
- Run the scripts from `LT_scenario_gen/dataset_gen/`; otherwise relative paths may fail.
- `txt_2_pic.py` supports auto naming by default. If you want a fixed output filename, change `MODE = "manual"` and set `MANUAL_FILENAME`.
- The runtime scripts now resolve configuration, prompt, input, and output paths from their own file locations. By default, generated metadata is written to `output_img/opt.json` and `output_img/choose.json`.

## Troubleshooting
- **No output generated**: confirm the output path is `output_img/` and verify that the scripts executed successfully.
- **API call failures**: verify `API_KEY` and `BASE_URL` in `utils/config.json`, and confirm **nano banana pro** support.

## Contributing
Issues and PRs are welcome, especially for adding automatic category selection or improving documentation.

## License
This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.
