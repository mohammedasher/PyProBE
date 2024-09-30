"""A module to load and process Biologic battery cycler data."""


from datetime import datetime
from typing import List

import polars as pl

from pyprobe.cyclers.basecycler import BaseCycler


class Biologic(BaseCycler):
    """A class to load and process Biologic battery cycler data."""

    input_data_path: str
    column_dict: dict[str, str] = {
        "Date": "Date",
        "time/*": "Time [*]",
        "Ns": "Step",
        "I/*": "Current [*]",
        "<I>/*": "Current [*]",
        "Ecell/*": "Voltage [*]",
        "Q charge/*": "Charge Capacity [*]",
        "Q discharge/*": "Discharge Capacity [*]",
        "Temperature/*": "Temperature [*]",
    }

    @staticmethod
    def read_file(filepath: str) -> pl.DataFrame | pl.LazyFrame:
        """Read a battery cycler file into a DataFrame.

        Args:
            filepath: The path to the file.

        Returns:
            pl.DataFrame | pl.LazyFrame: The DataFrame.
        """
        with open(filepath, "r", encoding="iso-8859-1") as file:
            file.readline()  # Skip the first line
            second_line = file.readline().strip()  # Read the second line
        _, value = second_line.split(":")
        n_header_lines = int(value.strip())

        with open(filepath, "r", encoding="iso-8859-1") as file:
            for i in range(n_header_lines):
                line = file.readline()
                if "Acquisition started on" in line:
                    start_time_line = line
                    break
        _, value = start_time_line.split(" : ")
        start_time = datetime.strptime(value.strip(), "%m/%d/%Y %H:%M:%S.%f")

        dataframe = pl.scan_csv(
            filepath, skip_rows=n_header_lines - 1, separator="\t", infer_schema=False
        )

        dataframe = dataframe.with_columns(
            (pl.col("time/s").cast(pl.Float64).cast(pl.Duration) + pl.lit(start_time))
            .cast(str)
            .alias("Date")
        )
        return dataframe

    @property
    def step(self) -> pl.Expr:
        """Identify the step number.

        Returns:
            pl.Expr: A polars expression for the step number.
        """
        return pl.col("Step") + 1


class BiologicMB(Biologic):
    """A class to load and process Biologic Modulo Bat  battery cycler data."""

    def get_imported_dataframe(
        self, dataframe_list: List[pl.DataFrame]
    ) -> pl.DataFrame | pl.LazyFrame:
        """Read a battery cycler file into a DataFrame.

        Args:
            filepath: The path to the file.

        Returns:
            pl.DataFrame | pl.LazyFrame: The imported DataFrame.
        """
        df_list = []
        for i, df in enumerate(dataframe_list):
            df = df.with_columns(pl.lit(i).alias("MB File"))
            df_list.append(df)
        complete_df = pl.concat(df_list, how="vertical")
        complete_df = self.apply_step_correction(complete_df)
        return complete_df

    @staticmethod
    def apply_step_correction(
        df: pl.DataFrame | pl.LazyFrame,
    ) -> pl.DataFrame | pl.LazyFrame:
        """Correct the step column.

        This method adds the maximum step number from the previous MB file to the step
        number of the following MB file so they monotonically increase.

        Args:
            df: The DataFrame to correct.

        Returns:
            pl.DataFrame: The corrected DataFrame.
        """
        # get the max step number for each MB file and add 1
        max_steps = df.group_by("MB File").agg(
            (pl.col("Ns").cast(pl.Int64).max() + 1).alias("Max_Step")
        )
        # sort the max steps by MB file
        max_steps = max_steps.sort("MB File")
        # get the cumulative sum of the max steps
        max_steps = max_steps.with_columns(pl.col("Max_Step").cum_sum())
        # add 1 to the MB file number to offset the join
        max_steps = max_steps.with_columns(pl.col("MB File") + 1)
        # join the max step number to the original dataframe and fill nulls with 0
        df_with_max_step = df.join(max_steps, on="MB File", how="left").fill_null(0)
        # add the max step number to the step number
        return df_with_max_step.with_columns(
            pl.col("Ns").cast(pl.Int64) + pl.col("Max_Step")
        )
