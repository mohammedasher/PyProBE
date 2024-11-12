"""Tests for the pulsing experiment."""

import numpy as np
import pytest

import pyprobe.analysis.pulsing as pulsing
from pyprobe.analysis.pulsing import Pulsing
from pyprobe.result import Result


@pytest.fixture
def Pulsing_fixture(procedure_fixture):
    """Pytest fixture for example pulsing experiment."""
    procedure_fixture.set_SOC(
        reference_charge=procedure_fixture.experiment("Break-in Cycles").charge(-1)
    )
    return Pulsing(input_data=procedure_fixture.experiment("Discharge Pulses"))


def test_pulse(Pulsing_fixture):
    """Test the pulse method."""
    pulse = Pulsing_fixture.pulse(0)
    assert pulse.data["Time [s]"][0] == 483572.397
    assert (pulse.data["Step"] == 10).all()

    pulse = Pulsing_fixture.pulse(6)
    assert pulse.data["Time [s]"][0] == 531149.401
    assert (pulse.data["Step"] == 10).all()


def test_pulse_summary(Pulsing_fixture):
    """Test the pulse_summary method."""
    pulse_summary = Pulsing_fixture.pulse_summary([10])
    assert isinstance(Pulsing_fixture.pulse_summary(), Result)
    assert isinstance(pulse_summary, Result)
    assert pulse_summary.get("OCV [V]")[0] == 4.1919
    assert np.isclose(pulse_summary.get("R0 [Ohms]")[0], (4.1558 - 4.1919) / -0.0199936)
    assert np.isclose(
        pulse_summary.get("R_10s [Ohms]")[0], (4.1337 - 4.1919) / -0.0199936
    )


def test_get_ocv_curve(procedure_fixture):
    """Test the get_ocv_curve method."""
    procedure_fixture.set_SOC(
        reference_charge=procedure_fixture.experiment("Break-in Cycles").charge(-1)
    )
    input_data = procedure_fixture.experiment("Discharge Pulses")
    result = pulsing.get_ocv_curve(input_data)
    expected_ocv_points = [
        4.1919,
        4.0949,
        3.9934,
        3.8987,
        3.8022,
        3.7114,
        3.665,
        3.6334,
        3.5866,
        3.5164,
        3.4513,
    ]
    assert isinstance(result, Result)
    assert result.column_list == input_data.column_list
    assert np.allclose(result.get("Voltage [V]"), expected_ocv_points)
