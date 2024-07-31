"""A module to load and process battery cycler data."""

import glob
import os
import re
import warnings
from abc import ABC, abstractmethod
from typing import Dict, List

import polars as pl

from pyprobe.unitconverter import UnitConverter


class BaseCycler(ABC):
    """A class to load and process battery cycler data.

    Args:
        input_data_path (str): The path to the input data.
        common_suffix (str): The part of the filename before an index number,
            when a single procedure is split into multiple files.
        column_name_pattern (str): The regular expression pattern to match the
            column names.
        column_dict (Dict[str, str]): A dictionary mapping the expected columns to
            the actual column names in the data.
    """

    def __init__(
        self,
        input_data_path: str,
        common_suffix: str,
        column_name_pattern: str,
        column_dict: Dict[str, str],
    ) -> None:
        """Create a cycler object."""
        self.input_data_path = input_data_path
        self.common_suffix = common_suffix
        self.column_name_pattern = column_name_pattern
        self.column_dict = column_dict
        self._dataframe_columns = self.imported_dataframe.columns

        self.required_columns = {
            "Date": self.date,
            "Time [s]": self.time,
            "Cycle": self.cycle,
            "Step": self.step,
            "Event": self.event,
            "Current [A]": self.current,
            "Voltage [V]": self.voltage,
            "Capacity [Ah]": self.capacity,
        }
        self.pyprobe_dataframe = self.imported_dataframe.select(
            list(self.required_columns.values())
        )

    @property
    def date(self) -> pl.Expr:
        """Identify and format the date column.

        Returns:
            pl.Expr: A polars expression for the date column.
        """
        if (
            self.imported_dataframe.dtypes[
                self.imported_dataframe.columns.index("Date")
            ]
            != pl.Datetime
        ):
            return pl.col("Date").str.to_datetime().alias("Date")
        else:
            return pl.col("Date")

    @property
    def time(self) -> pl.Expr:
        """Identify and format the time column.

        Returns:
            pl.Expr: A polars expression for the time column.
        """
        return pl.col(self.column_dict["Time"]).cast(pl.Float64).alias("Time [s]")

    @property
    def step(self) -> pl.Expr:
        """Identify and format the step column."""
        return pl.col(self.column_dict["Step"]).cast(pl.Int64).alias("Step")

    @property
    def current(self) -> pl.Expr:
        """Identify and format the current column.

        Returns:
            pl.Expr: A polars expression for the current column.
        """
        return (
            self.search_columns(
                self._dataframe_columns,
                self.column_dict["Current"],
                self.column_name_pattern,
            )
            .to_default()
            .cast(pl.Float64)
        )

    @property
    def voltage(self) -> pl.Expr:
        """Identify and format the voltage column.

        Returns:
            pl.Expr: A polars expression for the voltage column.
        """
        return (
            self.search_columns(
                self._dataframe_columns,
                self.column_dict["Voltage"],
                self.column_name_pattern,
            )
            .to_default()
            .cast(pl.Float64)
        )

    @property
    def charge_capacity(self) -> pl.Expr:
        """Identify and format the charge capacity column.

        Returns:
            pl.Expr: A polars expression for the charge capacity column.
        """
        return (
            self.search_columns(
                self._dataframe_columns,
                self.column_dict["Charge Capacity"],
                self.column_name_pattern,
            )
            .to_default(keep_name=True)
            .cast(pl.Float64)
        )

    @property
    def discharge_capacity(self) -> pl.Expr:
        """Identify and format the discharge capacity column.

        Returns:
            pl.Expr: A polars expression for the discharge capacity column.
        """
        return (
            self.search_columns(
                self._dataframe_columns,
                self.column_dict["Discharge Capacity"],
                self.column_name_pattern,
            )
            .to_default(keep_name=True)
            .cast(pl.Float64)
        )

    @property
    def capacity_from_ch_dch(self) -> pl.Expr:
        """Calculate the capacity from charge and discharge capacities.

        Returns:
            pl.Expr: A polars expression for the capacity column.
        """
        diff_charge_capacity = (
            self.charge_capacity.diff().clip(lower_bound=0).fill_null(strategy="zero")
        )

        diff_discharge_capacity = (
            self.discharge_capacity.diff()
            .clip(lower_bound=0)
            .fill_null(strategy="zero")
        )
        return (
            (diff_charge_capacity - diff_discharge_capacity).cum_sum()
            + self.charge_capacity.max()
        ).alias("Capacity [Ah]")

    @property
    def capacity(self) -> pl.Expr:
        """Identify and format the capacity column.

        Returns:
            pl.Expr: A polars expression for the capacity column.
        """
        if "Capacity" in self.column_dict:
            return (
                self.search_columns(
                    self._dataframe_columns,
                    self.column_dict["Capacity"],
                    self.column_name_pattern,
                )
                .to_default()
                .cast(pl.Float64)
            )
        else:
            return self.capacity_from_ch_dch

    @property
    def cycle(self) -> pl.Expr:
        """Identify the cycle number.

        Cycles are defined by repetition of steps. They are identified by a decrease
        in the step number.

        Returns:
            pl.Expr: A polars expression for the cycle number.
        """
        return (
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

    @property
    def event(self) -> pl.Expr:
        """Identify the event number.

        Events are defined by any change in the step number, increase or decrease.

        Returns:
            pl.Expr: A polars expression for the event number.
        """
        return (
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

    @staticmethod
    @abstractmethod
    def read_file(filepath: str) -> pl.DataFrame | pl.LazyFrame:
        """Read a battery cycler file into a DataFrame.

        Args:
            filepath (str): The path to the file.

        Returns:
            pl.DataFrame | pl.LazyFrame: The DataFrame.
        """
        pass

    @property
    def dataframe_list(self) -> list[pl.DataFrame | pl.LazyFrame]:
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
    def imported_dataframe(self) -> pl.DataFrame:
        """Return the dataframe containing the data from all imported files.

        Returns:
            pl.DataFrame | pl.LazyFrame: The DataFrame.
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

    @staticmethod
    def search_columns(
        columns: List[str],
        search_quantity: str,
        name_pattern: str,
    ) -> "UnitConverter":
        """Search for a quantity in the columns of the DataFrame.

        Args:
            columns: The columns to search.
            search_quantity: The quantity to search for.
            name_pattern: The pattern to match the column name.
            default_quantity: The default quantity name.
        """
        for column_name in columns:
            try:
                quantity, _ = UnitConverter.get_quantity_and_unit(
                    column_name, name_pattern
                )
            except ValueError:
                continue

            if quantity == search_quantity:
                return UnitConverter(
                    column_name=column_name,
                    name_pattern=name_pattern,
                )
        raise ValueError(f"Quantity {search_quantity} not found in columns.")
