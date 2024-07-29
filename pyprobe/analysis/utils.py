"""Module for utilities for analysis classes."""
from typing import Any, List

import numpy as np
from numpy.typing import NDArray

from pyprobe.result import Result
from pydantic import BaseModel, model_validator
from pyprobe.typing import PyProBEDataType


def assemble_array(input_data: List[Result], name: str) -> NDArray[Any]:
    """Assemble an array from a list of results.

    Args:
        input_data (List[Result]): A list of results.
        name (str): The name of the variable.

    Returns:
        NDArray: The assembled array.
    """
    return np.vstack([input.get_only(name) for input in input_data])

class BaseAnalysis(BaseModel):
    """A base class for analysis classes."""

    class Config:
        arbitrary_types_allowed = True

    input_data: PyProBEDataType
    required_columns: List[str]
    
    @model_validator(mode='after')
    def check_required_columns(self)->'BaseAnalysis':
        missing_columns = [col for col in self.required_columns if col not in self.input_data.column_list]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        return self

