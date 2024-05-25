"""Tests for the neware module."""
from datetime import datetime

import polars as pl
import polars.testing as pl_testing

from pyprobe.cyclers.neware import process_dataframe, read_file


def test_read_file():
    """Test the read_file method."""
    unprocessed_dataframe = read_file(
        "tests/sample_data_neware/sample_data_neware.xlsx"
    )
    assert isinstance(unprocessed_dataframe, pl.DataFrame)


def test_read_multiple_files():
    """Test the read_file method with multiple files."""
    unprocessed_dataframe = read_file(
        "tests/sample_data_neware/sample_data_neware*.xlsx"
    )
    assert isinstance(unprocessed_dataframe, pl.DataFrame)


def test_read_and_process_file(benchmark):
    """Test the full process of reading and processing a file."""

    def read_and_process():
        unprocessed_dataframe = read_file(
            "tests/sample_data_neware/sample_data_neware.xlsx"
        )
        processed_dataframe = process_dataframe(unprocessed_dataframe)
        return processed_dataframe

    processed_dataframe = benchmark(read_and_process)
    rows = processed_dataframe.shape[0]
    expected_columns = [
        "Date",
        "Time [s]",
        "Cycle",
        "Step",
        "Current [A]",
        "Voltage [V]",
        "Capacity [Ah]",
    ]
    assert isinstance(processed_dataframe, pl.DataFrame)
    all(col in processed_dataframe.columns for col in expected_columns)

    unprocessed_dataframe = read_file(
        "tests/sample_data_neware/sample_data_neware*.xlsx"
    )
    processed_dataframe = process_dataframe(unprocessed_dataframe)
    assert processed_dataframe.shape[0] == rows * 2
    all(col in processed_dataframe.columns for col in expected_columns)


def test_process_dataframe():
    """Test the neware method."""
    dataframe = pl.DataFrame(
        {
            "Date": [
                datetime(2022, 2, 2, 2, 2, 2),
                datetime(2022, 2, 2, 2, 2, 3),
                datetime(2022, 2, 2, 2, 2, 0),
                datetime(2022, 2, 2, 2, 2, 1),
            ],
            "Cycle Index": [1, 1, 1, 1],
            "Step Index": [3, 4, 1, 2],
            "Current(mA)": [3, 4, 1, 2],
            "Voltage(V)": [6, 7, 4, 5],
            "Chg. Cap.(Ah)": [
                0,
                0,
                0,
                20,
            ],
            "DChg. Cap.(Ah)": [10, 20, 0, 0],
        }
    )
    processed_dataframe = process_dataframe(dataframe)
    processed_dataframe = processed_dataframe.select(
        ["Time [s]", "Cycle", "Step", "Current [A]", "Voltage [V]", "Capacity [Ah]"]
    )
    expected_dataframe = pl.DataFrame(
        {
            "Time [s]": [0.0, 1.0, 2.0, 3.0],
            "Cycle": [1, 1, 1, 1],
            "Step": [1, 2, 3, 4],
            "Current [A]": [1e-3, 2e-3, 3e-3, 4e-3],
            "Voltage [V]": [4, 5, 6, 7],
            "Capacity [Ah]": [20, 40, 30, 20],
        }
    )
    pl_testing.assert_frame_equal(processed_dataframe, expected_dataframe)
