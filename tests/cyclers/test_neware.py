"""Tests for the neware module."""
from datetime import datetime

import polars as pl
import polars.testing as pl_testing
import pytest

from pyprobe.cyclers.neware import Neware


@pytest.fixture
def neware_cycler():
    """Create a Neware cycler object."""
    return Neware("tests/sample_data/neware/sample_data_neware.xlsx")


def test_read_file(neware_cycler):
    """Test the read_file method."""
    unprocessed_dataframe = neware_cycler.read_file(
        "tests/sample_data/neware/sample_data_neware.xlsx"
    )
    assert isinstance(unprocessed_dataframe, pl.DataFrame)


def test_sort_files(neware_cycler):
    """Test the sort_files method."""
    file_list = [
        "test_2_experiment_3_file_5_1.xlsx",
        "test_2_experiment_3_file_5_3.xlsx",
        "test_2_experiment_3_file_5.xlsx",
        "test_2_experiment_3_file_5_2.xlsx",
    ]
    sorted_files = neware_cycler.sort_files(file_list)
    assert sorted_files == [
        "test_2_experiment_3_file_5.xlsx",
        "test_2_experiment_3_file_5_1.xlsx",
        "test_2_experiment_3_file_5_2.xlsx",
        "test_2_experiment_3_file_5_3.xlsx",
    ]


def test_read_multiple_files(neware_cycler):
    """Test the read_file method with multiple files."""
    unprocessed_dataframe = neware_cycler.imported_dataframe
    assert isinstance(unprocessed_dataframe, pl.DataFrame)


def test_read_and_process(benchmark, neware_cycler):
    """Test the full process of reading and processing a file."""

    def read_and_process():
        return neware_cycler.pyprobe_dataframe

    pyprobe_dataframe = benchmark(read_and_process)
    rows = pyprobe_dataframe.shape[0]
    expected_columns = [
        "Date",
        "Time [s]",
        "Step",
        "Cycle",
        "Event",
        "Current [A]",
        "Voltage [V]",
        "Capacity [Ah]",
    ]
    assert isinstance(pyprobe_dataframe, pl.DataFrame)
    assert set(pyprobe_dataframe.columns) == set(expected_columns)

    neware_cycler = Neware("tests/sample_data/neware/sample_data_neware*.xlsx")
    pyprobe_dataframe = neware_cycler.pyprobe_dataframe
    assert pyprobe_dataframe.shape[0] == rows * 2
    assert set(pyprobe_dataframe.columns) == set(expected_columns)


def test_process_dataframe(monkeypatch):
    """Test the neware method."""

    def mock_dataframe(self):
        return pl.DataFrame(
            {
                "Date": [
                    datetime(2022, 2, 2, 2, 2, 0),
                    datetime(2022, 2, 2, 2, 2, 1),
                    datetime(2022, 2, 2, 2, 2, 2),
                    datetime(2022, 2, 2, 2, 2, 3),
                    datetime(2022, 2, 2, 2, 2, 4),
                    datetime(2022, 2, 2, 2, 2, 5),
                ],
                "Step Index": [1, 2, 1, 2, 4, 5],
                "Current(mA)": [1, 2, 3, 4, 0, 0],
                "Voltage(V)": [4, 5, 6, 7, 8, 9],
                "Chg. Cap.(Ah)": [
                    0,
                    20,
                    0,
                    0,
                    0,
                    0,
                ],
                "DChg. Cap.(Ah)": [0, 0, 10, 20, 20, 20],
            }
        )

    monkeypatch.setattr(
        "pyprobe.cyclers.neware.Neware.imported_dataframe", property(mock_dataframe)
    )
    neware_cycler = Neware("tests/sample_data/neware/sample_data_neware.xlsx")
    pyprobe_dataframe = neware_cycler.pyprobe_dataframe
    pyprobe_dataframe = pyprobe_dataframe.select(
        [
            "Time [s]",
            "Step",
            "Current [A]",
            "Voltage [V]",
            "Capacity [Ah]",
        ]
    )
    expected_dataframe = pl.DataFrame(
        {
            "Time [s]": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "Step": [1, 2, 1, 2, 4, 5],
            "Current [A]": [1e-3, 2e-3, 3e-3, 4e-3, 0, 0],
            "Voltage [V]": [4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
            "Capacity [Ah]": [20.0, 40.0, 30.0, 20.0, 20.0, 20.0],
        }
    )
    pl_testing.assert_frame_equal(pyprobe_dataframe, expected_dataframe)
