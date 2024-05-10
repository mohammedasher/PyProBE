"""A module for the Experiment class."""

from typing import Dict

import polars as pl

from pybatdata.filter import Filter


class Experiment(Filter):
    """An experiment in a battery procedure."""

    def __init__(
        self, _data: pl.LazyFrame | pl.DataFrame, info: Dict[str, str | int | float]
    ):
        """Create an experiment.

        Args:
            _data (polars.LazyFrame): The _data of data being filtered.
            info (Dict[str, str | int | float]): A dict containing test info.
        """
        super().__init__(_data, info)
