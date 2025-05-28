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