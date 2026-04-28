# Civil Service Statistics Extraction

Scripts for extracting various IfG datasets built on [Civil Service Statistics (CSS)](https://www.gov.uk/government/collections/civil-service-statistics)
releases.

## Project structure

Below is a generalised view of the structure of the repository. `dataset` below is an umbrella for each of the CSS datasets, which are: `age`, `disability_status`, `ethnicity`, `faith`, `sex`, `sexual_orientation`, `grade`, `leaving_cause`, `location`, `pay` and `professions_functions`.

```
├── Scripts/
|   ├── dataset/
|   |   ├── python/
|   |   |   ├── extract_dataset_data.py
|   |   |   ├── compare_dataset_data.py
|   |   ├── sql/
|   |   |   ├── compare_dataset_organisations_data.sql
|   |   |   ├── select_dataset_organisations_data.sql
|   ├── utils.py
├── .pre-commit-config.yaml
└── README.md
```

## Scripts 

*Coming soon*
