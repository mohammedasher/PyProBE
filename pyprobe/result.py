"""A module for the Result class."""
from typing import Dict, Tuple, Union

import numpy as np
import polars as pl
from numpy.typing import NDArray

from pyprobe.unitconverter import UnitConverter


class Result:
    """A result object for returning data and plotting.

    Attributes:
        _data (pl.LazyFrame | pl.DataFrame): The data as a polars DataFrame or
            LazyFrame.
        data (Optional[pl.DataFrame]): The data as a polars DataFrame.
        info (Dict[str, str | int | float]): A dictionary containing test info.
    """

    def __init__(
        self,
        _data: pl.LazyFrame | pl.DataFrame,
        info: Dict[str, str | int | float],
    ) -> None:
        """Initialize the Result object.

        Args:
            _data (pl.LazyFrame | pl.DataFrame): The filtered _data.
            info (Dict[str, str | int | float]): A dict containing test info.
        """
        self._data = _data
        self.info = info

    def __call__(
        self, *args: str
    ) -> Union[NDArray[np.float64], Tuple[NDArray[np.float64], ...]]:
        """Return columns of the data as numpy arrays.

        Args:
            *args (str): The column names to return.

        Returns:
            Union[NDArray[np.float64], Tuple[NDArray[np.float64], ...]]:
                The columns as numpy arrays.
        """
        arrays = []
        for col in args:
            self.check_units(col)
            if col not in self.data.columns:
                raise ValueError(f"Column '{col}' not in data.")
            arrays.append(self.data[col].to_numpy())
        return arrays[0] if len(arrays) == 1 else tuple(arrays)

    @property
    def data(self) -> pl.DataFrame:
        """Return the data as a polars DataFrame.

        Returns:
            pl.DataFrame: The data as a polars DataFrame.
        """
        if isinstance(self._data, pl.LazyFrame):
            self._data = self._data.collect()
        return self._data

    def print(self) -> None:
        """Print the data."""
        print(self.data)

    def check_units(self, column_name: str) -> None:
        """Check if a column exists and convert the units if it does not.

        Args:
            column_name (str): The column name to convert to.
        """
        if column_name not in self.data.columns:
            instruction = UnitConverter(column_name).from_default()
            self._data = self.data.with_columns(instruction)
