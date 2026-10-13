set noexec on




---- v1.0.1, 2026-10-13
--- Adjust 'Cyber' government classification
-- This used to be 'Unknown and other' but has now been classified by govt
update pm
set
    pm.government_classification = 'Functional profession'
from civil_service.professions_mapping pm
where
    pm.profession_name = 'Cyber'
