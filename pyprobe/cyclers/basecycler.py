"""A module to load and process battery cycler data."""

import glob
import os
import re
import warnings
from typing import Dict, List

import polars as pl

from pyprobe.unitconverter import UnitConverter


class BaseCycler:
    """A class to load and process battery cycler data."""

    required_columns = [
        "Date",
        "Time [s]",
        "Cycle",
        "Step",
        "Event",
        "Current [A]",
        "Voltage [V]",
        "Capacity [Ah]",
    ]

    def __init__(
        self,
        input_data_path: str,
        common_suffix: str,
        column_name_pattern: str,
        column_dict: Dict[str, str],
    ) -> None:
        """Create a cycler object.

        Args:
            input_data_path (str): The path to the input data.
            common_suffix (str): The part of the filename before an index number,
                when a single procedure is split into multiple files.
            column_name_pattern (str): The regular expression pattern to match the
                column names.
            column_dict (Dict[str, str]): A dictionary mapping the expected columns to
                the actual column names in the data.
        """
        self.input_data_path = input_data_path
        self.common_suffix = common_suffix
        self.column_name_pattern = column_name_pattern
        self.column_dict = column_dict
        self._dataframe = self.raw_dataframe
        self._dataframe_columns = self._dataframe.columns

        self.imported_dataframe = pl.concat(
            [
                self.date,
                self.time,
                self.step,
                self.cycle,
                self.event,
                self.current,
                self.voltage,
                self.capacity_from_ch_dch,
            ],
            how="horizontal",
        )

    @property
    def date(self) -> pl.DataFrame:
        """Identify and format the date column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the date.
        """
        if self._dataframe.dtypes[self._dataframe.columns.index("Date")] != pl.Datetime:
            date = pl.col("Date").str.to_datetime().alias("Date")
        else:
            date = pl.col("Date")
        return self._dataframe.select(date)

    @property
    def time(self) -> pl.DataFrame:
        """Identify and format the time column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the time in [s].
        """
        time = pl.col(self.column_dict["Time"]).alias("Time [s]")
        return self._dataframe.select(time)

    @property
    def step(self) -> pl.DataFrame:
        """Identify and format the step column."""
        step = pl.col(self.column_dict["Step"]).alias("Step")
        return self._dataframe.select(step)

    @property
    def current(self) -> pl.DataFrame:
        """Identify and format the current column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the current in [A].
        """
        current = UnitConverter.search_columns(
            self._dataframe_columns,
            self.column_dict["Current"],
            self.column_name_pattern,
            "Current",
        ).to_default()
        return self._dataframe.select(current)

    @property
    def voltage(self) -> pl.DataFrame:
        """Identify and format the voltage column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the voltage in [V].
        """
        voltage = UnitConverter.search_columns(
            self._dataframe_columns,
            self.column_dict["Voltage"],
            self.column_name_pattern,
            "Voltage",
        ).to_default()
        return self._dataframe.select(voltage)

    @property
    def charge_capacity(self) -> pl.DataFrame:
        """Identify and format the charge capacity column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the charge capacity in
                [Ah].
        """
        charge_capacity = UnitConverter.search_columns(
            self._dataframe_columns,
            self.column_dict["Charge Capacity"],
            self.column_name_pattern,
            "Capacity",
        ).to_default(keep_name=True)
        return self._dataframe.select(charge_capacity)

    @property
    def discharge_capacity(self) -> pl.DataFrame:
        """Identify and format the discharge capacity column.

        Returns:
            pl.DataFrame: A single column DataFrame containing the discharge capacity in
                [Ah].
        """
        discharge_capacity = UnitConverter.search_columns(
            self._dataframe_columns,
            self.column_dict["Discharge Capacity"],
            self.column_name_pattern,
            "Capacity",
        ).to_default(keep_name=True)
        return self._dataframe.select(discharge_capacity)

    @property
    def capacity_from_ch_dch(self) -> pl.DataFrame:
        """Calculate the capacity from charge and discharge capacities.

        Returns:
            pl.DataFrame: A DataFrame containing the calculated capacity column in [Ah].
        """
        charge_and_discharge_capacity = pl.concat(
            [self.charge_capacity, self.discharge_capacity], how="horizontal"
        )
        diff_charge_capacity = (
            pl.col(f"{self.column_dict['Charge Capacity']} [Ah]")
            .diff()
            .clip(lower_bound=0)
            .fill_null(strategy="zero")
        )
        diff_discharge_capacity = (
            pl.col(f"{self.column_dict['Discharge Capacity']} [Ah]")
            .diff()
            .clip(lower_bound=0)
            .fill_null(strategy="zero")
        )
        capacity = (
            (diff_charge_capacity - diff_discharge_capacity).cum_sum()
            + pl.col(f"{self.column_dict['Charge Capacity']} [Ah]").max()
        ).alias("Capacity [Ah]")
        return charge_and_discharge_capacity.select(capacity)

    @property
    def cycle(self) -> pl.DataFrame:
        """Identify the cycle number.

        Cycles are defined by repetition of steps. They are identified by a decrease
        in the step number.

        Returns:
            pl.DataFrame: A single column DataFrame containing the cycle number.
        """
        cycle = (
            (
                pl.col(self.column_dict["Step"])
                - pl.col(self.column_dict["Step"]).shift()
                < 0
            )
            .fill_null(strategy="zero")
            .cum_sum()
            .alias("Cycle")
            .cast(pl.Int64)
        )
        return self._dataframe.select(cycle)

    @property
    def event(self) -> pl.DataFrame:
        """Identify the event number.

        Events are defined by any change in the step number, increase or decrease.

        Returns:
            pl.DataFrame: A single column DataFrame containing the event number.
        """
        event = (
            (
                pl.col(self.column_dict["Step"])
                - pl.col(self.column_dict["Step"]).shift()
                != 0
            )
            .fill_null(strategy="zero")
            .cum_sum()
            .alias("Event")
            .cast(pl.Int64)
        )
        return self._dataframe.select(event)

    @staticmethod
    def read_file(filepath: str) -> pl.DataFrame:
        """Read a battery cycler file into a DataFrame.

        Args:
            filepath (str): The path to the file.

        Returns:
            pl.DataFrame: The DataFrame.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def dataframe_list(self) -> list[pl.DataFrame]:
        """Return a list of all the imported dataframes.

        Returns:
            List[DataFrame]: A list of DataFrames.
        """
        files = glob.glob(self.input_data_path)
        files = self.sort_files(files)
        list = [self.read_file(file) for file in files]
        all_columns = set([col for df in list for col in df.columns])
        indices_to_remove = []
        for i in range(len(list)):
            if len(list[i].columns) < len(all_columns):
                indices_to_remove.append(i)
                warnings.warn(
                    f"File {os.path.basename(files[i])} has missing columns, "
                    "it has not been read."
                )
                continue
        return [df for i, df in enumerate(list) if i not in indices_to_remove]

    @property
    def raw_dataframe(self) -> pl.DataFrame:
        """Read a battery cycler file into a DataFrame.

        Args:
            filepath (str): The path to the file.
        """
        return pl.concat(self.dataframe_list, how="vertical", rechunk=True)

    def sort_files(self, file_list: List[str]) -> List[str]:
        """Sort a list of files by the integer in the filename.

        Args:
            file_list: The list of files.

        Returns:
            list: The sorted list of files.
        """
        # common first part of file names
        self.common_prefix = os.path.commonprefix(file_list)
        return sorted(file_list, key=self.sort_key)

    def sort_key(self, filepath: str) -> int:
        """Sort key for the files.

        Args:
            filepath (str): The path to the file.

        Returns:
            int: The integer in the filename.
        """
        # replace common prefix
        stripped_filepath = filepath.replace(self.common_prefix, "")

        # find the index of the common suffix
        suffix_index = stripped_filepath.find(self.common_suffix)

        # if the suffix is found, strip it and everything after it
        if suffix_index != -1:
            stripped_filepath = stripped_filepath[:suffix_index]
        # extract the first number in the filename
        match = re.search(r"\d+", stripped_filepath)
        return int(match.group()) if match else 0
