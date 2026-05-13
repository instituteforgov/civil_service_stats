# Civil Service Statistics Extraction

Scripts for extracting various IfG datasets built on [Civil Service Statistics (CSS)](https://www.gov.uk/government/collections/civil-service-statistics)
releases.

## Project structure

Below is a generalised view of the structure of the repository. `dataset` below is an umbrella for each of the CSS datasets, which are: `age`, `disability_status`, `ethnicity`, `faith`, `sex`, `sexual_orientation`, `grade`, `leaving_cause`, `location`, `pay` and `professions_functions`.

```
├── civil_service_stats/
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

| File | Description |
| ---- | ----------- |
| `extract_dataset_data.py` | Reads data from existing CS Stats Excel sheet and loads to database |
| `compare_dataset_data.py` | Checks that augmented SQL output matches data from source Excel |
| `compare_dataset_organisation_data.sql` | Replicates the organisation collation done in the Excel working file - basis for comparison with source in `compare_dataset_data.py` |
| `select_dataset_organisations_data.sql` | Augments organisations data and re-inserts into Excel file. Same as `compare_dataset_organisation_data.sql` but with following small changes: <li><strong>IfG core department</strong>: Added</li><li><strong>Latest organisation</strong>: Latest actual organisation always reported, rather than latest determinate organisation</li><li><strong>Latest departmental group</strong>: Latest actual (IfG) departmental group always reported, rather than latest determinate organisation</li></ul>  

