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
  "input_image_path": "../input_pic/t8.jpg"
}
```

```json
{
  "choose": "",
  "input_image_path": "../input_pic/t8.jpg"
}
```

4. Fill in the category in `choose.json` under `"choose": ""` (manually or automatically via your own implementation).
5. Run `main(mism_step2(1))` in `M_img_S_mdf_step2.py`.
6. Generated long-tail scenarios will appear in `output_img/`.

### 2) Generate long-tail scenarios from natural language
Go to the `dataset_gen` folder:

1. In `txt_2_pic.py`, enter the natural-language description and the category selection in the required location inside the `main` method.
2. Run the script.
3. Generated long-tail scenarios will appear in `output_img/`.

## Troubleshooting
- **No output generated**: confirm the output path is `output_img/` and verify that the scripts executed successfully.
- **API call failures**: verify `API_KEY` and `BASE_URL` in `utils/config.json`, and confirm **nano banana pro** support.

## Contributing
Issues and PRs are welcome, especially for adding automatic category selection or improving documentation.

## License
No license is declared here. Please contact the maintainers or check the repository root for licensing details.
