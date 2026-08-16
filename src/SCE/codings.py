"""Authoritative questionnaire recodes used by SCE transformations."""

from dataclasses import dataclass
from typing import Final

from SCE.enums import (
    Educ4Enum,
    EducationEnum,
    EmplStatusEnum,
    EmplTypeEnum,
    GenderEnum,
    PartnerEmplStatusEnum,
    ResidenceOwnershipEnum,
    SameEmployerEnum,
    YesNoEnum,
)


@dataclass(frozen=True, slots=True)
class BinaryRecode:
    """Classify source categories into true, false, and unclassifiable codes."""

    true_codes: frozenset[int]
    false_codes: frozenset[int]
    missing_codes: frozenset[int] = frozenset()

    @property
    def source_codes(self) -> frozenset[int]:
        """Return every explicitly classified source code."""
        return self.true_codes | self.false_codes | self.missing_codes


def _codes(*values: int) -> frozenset[int]:
    """Return enum values as an immutable set of integer source codes."""
    return frozenset(map(int, values))


YES_NO_RECODE: Final = BinaryRecode(
    true_codes=_codes(YesNoEnum.YES),
    false_codes=_codes(YesNoEnum.NO),
)

HOUSEHOLD_CHANGED_RECODE: Final = BinaryRecode(
    # D1 asks whether composition is the same, so an explicit No means changed.
    true_codes=_codes(YesNoEnum.NO),
    false_codes=_codes(YesNoEnum.YES),
)

SELF_EMPLOYED_RECODE: Final = BinaryRecode(
    true_codes=_codes(EmplTypeEnum.SELF_EMPLOYED),
    false_codes=_codes(EmplTypeEnum.FOR_SOMEONE_ELSE),
)

FEMALE_RECODE: Final = BinaryRecode(
    true_codes=_codes(GenderEnum.FEMALE),
    false_codes=_codes(GenderEnum.MALE),
)

HISPANIC_RECODE: Final = YES_NO_RECODE
COUPLE_RECODE: Final = YES_NO_RECODE

COLLEGE_RECODE: Final = BinaryRecode(
    true_codes=_codes(
        EducationEnum.BACHELORS_DEGREE,
        EducationEnum.MASTERS_DEGREE,
        EducationEnum.DOCTORAL_DEGREE,
        EducationEnum.PROFESSIONAL_DEGREE,
    ),
    false_codes=_codes(
        EducationEnum.LT_HS,
        EducationEnum.HS,
        EducationEnum.SOME_COLLEGE,
        EducationEnum.ASSOCIATE_DEGREE,
    ),
    # Other does not establish whether the respondent has a college degree.
    missing_codes=_codes(EducationEnum.OTHER),
)

EDUCATION_TO_EDUC4: Final[dict[int, int]] = {
    int(EducationEnum.LT_HS): int(Educ4Enum.LT_HS),
    int(EducationEnum.HS): int(Educ4Enum.HS),
    int(EducationEnum.SOME_COLLEGE): int(Educ4Enum.SOME_COLLEGE),
    int(EducationEnum.ASSOCIATE_DEGREE): int(Educ4Enum.SOME_COLLEGE),
    int(EducationEnum.BACHELORS_DEGREE): int(Educ4Enum.COLLEGE),
    int(EducationEnum.MASTERS_DEGREE): int(Educ4Enum.COLLEGE),
    int(EducationEnum.DOCTORAL_DEGREE): int(Educ4Enum.COLLEGE),
    int(EducationEnum.PROFESSIONAL_DEGREE): int(Educ4Enum.COLLEGE),
    # EducationEnum.OTHER is intentionally omitted and therefore maps to missing.
}

OWNER_RECODE: Final = BinaryRecode(
    true_codes=_codes(ResidenceOwnershipEnum.OWN),
    false_codes=_codes(ResidenceOwnershipEnum.RENT),
    # Other does not establish ownership and must not be treated as renting.
    missing_codes=_codes(ResidenceOwnershipEnum.OTHER),
)

SAME_EMPLOYER_RECODE: Final = BinaryRecode(
    true_codes=_codes(
        SameEmployerEnum.SAME_JOB,
        SameEmployerEnum.SAME_EMPLOYER_DIFFERENT_ROLE,
    ),
    false_codes=_codes(
        SameEmployerEnum.DIFFERENT_EMPLOYER,
        SameEmployerEnum.NOT_PREVIOUSLY_EMPLOYED,
    ),
    # Other does not establish whether the employer is the same.
    missing_codes=_codes(SameEmployerEnum.OTHER),
)

# `working` means literally working now. Temporary layoff and leave remain zero,
# even though questionnaire routing treats those statuses as attached to a job.
Q10_WORKING_COLUMNS: Final = tuple(
    f"Q10_{int(code)}"
    for code in (EmplStatusEnum.FULL_TIME, EmplStatusEnum.PART_TIME)
)
Q10_OTHER_COLUMNS: Final = (f"Q10_{int(EmplStatusEnum.OTHER)}",)

SPOUSE_WORKING_COLUMNS: Final = tuple(
    f"HH2_{int(code)}"
    for code in (
        PartnerEmplStatusEnum.FULL_TIME,
        PartnerEmplStatusEnum.PART_TIME,
        PartnerEmplStatusEnum.SELF_EMPLOYED,
    )
)
SPOUSE_OTHER_COLUMNS: Final = (
    f"HH2_{int(PartnerEmplStatusEnum.OTHER)}",
)
