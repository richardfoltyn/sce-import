"""Regression fixtures for household-composition propagation."""

import numpy as np
import pandas as pd

from SCE.importer import propagate_household_composition


def test_household_composition_is_propagated_within_user() -> None:
    """Verify complete composition states remain respondent-specific."""
    index = pd.MultiIndex.from_tuples(
        [
            (101, 1),
            (101, 2),
            (202, 1),
            (202, 2),
            (303, 1),
            (303, 2),
            (303, 3),
            (404, 1),
        ],
        names=["userid", "wid"],
    )
    initial = pd.DataFrame(
        {
            "Q45new_1": [1.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 1.0],
            "Q45new_2": [0.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 1.0],
        },
        index=index,
    )
    updates = pd.DataFrame(
        {
            "Q45new_1": [
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                0.0,
                9.0,
                2.0,
            ],
            "Q45new_2": [
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                2.0,
                np.nan,
                3.0,
            ],
        },
        index=index,
    )
    expected = pd.DataFrame(
        {
            "Q45new_1": [1.0, 1.0, np.nan, np.nan, np.nan, 0.0, 0.0, 2.0],
            "Q45new_2": [0.0, 0.0, np.nan, np.nan, np.nan, 2.0, 2.0, 3.0],
        },
        index=index,
    )

    # User 303's complete repeat response seeds the state without consulting D1;
    # its later partial response must not overwrite any component.
    result = propagate_household_composition(initial, updates)

    pd.testing.assert_frame_equal(result, expected)
