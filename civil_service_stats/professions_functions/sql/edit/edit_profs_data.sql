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


---- v1.0.2, 2026-10-19
--- Classify 'Inspector of education and training' as specialist profession
-- Government has never actually published a classification for this profession - we will need to disclose this if we use it in charts etc.
update pm
set
    pm.government_classification = 'Specialist profession'
from civil_service.professions_mapping pm
where
    pm.profession_name = 'Inspector of education and training'


---- v1.0.3, 2026-XX-XX
