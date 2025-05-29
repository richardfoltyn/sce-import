from enum import IntEnum

import pandas as pd

class WellBeingEnum(IntEnum):

    NA = -1
    MUCH_WORSE = 1
    SOMEWHAT_WORSE = 2
    SAME = 3
    SOMEWHAT_BETTER = 4
    MUCH_BETTER = 5

    def __str__(self) -> str:

        cls = type(self)
        mapping = {
            cls.NA: 'NA',
            cls.MUCH_WORSE: 'Much worse off',
            cls.SOMEWHAT_WORSE: 'Somewhat worse off',
            cls.SAME: 'About the same',
            cls.SOMEWHAT_BETTER: 'Somewhat better off',
            cls.MUCH_BETTER: 'Much better off'
        }

        return mapping[self]


class EmplStatusEnum(IntEnum):
    """
    Categorical response for Q10, employment status.
    """

    FULL_TIME = 1
    PART_TIME = 2
    NOT_WORKING = 3
    TEMP_LAYOFF = 4
    LEAVE = 5
    DISABLED = 6
    RETIRED = 7
    STUDENT = 8
    HOMEMAKER = 9
    OTHER = 10

    def __str__(self) -> str:
        cls = type(self)
        mapping = {
            cls.FULL_TIME: "Working full-time (for someone or self-employed)",
            cls.PART_TIME: "Working part-time (for someone or self-employed)",
            cls.NOT_WORKING: "Not working, but would like to work",
            cls.TEMP_LAYOFF: "Temporarily laid off",
            cls.LEAVE: "On sick or other leave",
            cls.DISABLED: "Permanently disabled or unable to work",
            cls.RETIRED: "Retiree or early retiree",
            cls.STUDENT: "Student, at school or in training",
            cls.HOMEMAKER: "Homemaker",
            cls.OTHER: "Other"
        }
        return mapping[self]


class EmplTypeEnum(IntEnum):
    """
    Categorical response for Q12new, working for someone else or self-employed.
    """

    FOR_SOMEONE_ELSE = 1
    SELF_EMPLOYED = 2

    def __str__(self) -> str:

        cls = type(self)
        mapping = {
            cls.FOR_SOMEONE_ELSE: "Work for someone else",
            cls.SELF_EMPLOYED: "Self-employed"
        }
        return mapping[self]


class EducationEnum(IntEnum):
    """
    Represents different levels of educational attainment.
    """
    LT_HS = 1
    HS = 2
    SOME_COLLEGE = 3
    ASSOCIATE_DEGREE = 4
    BACHELORS_DEGREE = 5
    MASTERS_DEGREE = 6
    DOCTORAL_DEGREE = 7
    PROFESSIONAL_DEGREE = 8
    OTHER = 9

    def __str__(self) -> str:
        """
        Returns the full string description of the education level.
        """
        
        cls = type(self)
        
        mapping = {
            cls.LT_HS: "Less than high school",
            cls.HS: "High school diploma (or equivalent)",
            cls.SOME_COLLEGE: "Some college but no degree (including academic, vocational, or occupational programs)",
            cls.ASSOCIATE_DEGREE: "Associate/Junior College degree (including academic, vocational, or occupational programs)",
            cls.BACHELORS_DEGREE: "Bachelor’s Degree (For example: BA, BS)",
            cls.MASTERS_DEGREE: "Master’s Degree (For example: MA, MBA, MS, MSW)",
            cls.DOCTORAL_DEGREE: "Doctoral Degree (For example: PhD)",
            cls.PROFESSIONAL_DEGREE: "Professional Degree (For example: MD, JD, DDS)",
            cls.OTHER: "Other"
        }
        return mapping[self]



class Educ4Enum(IntEnum):
    """
    Represents broader categories of educational attainment.
    """

    LT_HS = 1
    HS = 2
    SOME_COLLEGE = 3
    COLLEGE = 4 

    def __str__(self) -> str:
        """
        Returns the full string description of the coarse education level.
        """
        
        cls = type(self)
        
        # Dictionary mapping enum members to their full descriptions
        mapping = {
            cls.LT_HS: "Less than high school",
            cls.HS: "High school or equivalent",
            cls.SOME_COLLEGE: "Some college, including associate's degree",
            cls.COLLEGE: "Bachelor's degree or higher",
        }
        return mapping[self]


# Total pre-tax family income categories
INCOME_CATEGORIES = {
    1: "Less than $10,000",
    2: "$10,000 to $19,999",
    3: "$20,000 to $29,999",
    4: "$30,000 to $39,999",
    5: "$40,000 to $49,999",
    6: "$50,000 to $59,999",
    7: "$60,000 to $74,999",
    8: "$75,000 to $99,999",
    9: "$100,000 to $149,999",
    10: "$150,000 to $199,999",
    11: "$200,000 or more"
}
