"""Tests for the pulsing experiment."""

import numpy as np
import pytest

from pyprobe.analysis.pulsing import Pulsing
from pyprobe.result import Result


@pytest.fixture
def Pulsing_fixture(procedure_fixture):
    """Pytest fixture for example pulsing experiment."""
    return Pulsing(input_data=procedure_fixture.experiment("Discharge Pulses"))


def test_pulse(Pulsing_fixture):
    """Test the pulse method."""
    pulse = Pulsing_fixture.pulse(0)
    assert (pulse.data["Step"] == 10).all()
    assert (pulse.data["Cycle"] == 4).all()


def test_V0(Pulsing_fixture):
    """Test the V0 attribute."""
    assert Pulsing_fixture.V0[0] == 4.1919
    assert len(Pulsing_fixture.V0) == 10


def test_V1(Pulsing_fixture):
    """Test the V1 attribute."""
    assert Pulsing_fixture.V1[0] == 4.1558
    assert len(Pulsing_fixture.V1) == 10


def test_I1(Pulsing_fixture):
    """Test the I1 attribute."""
    assert Pulsing_fixture.I1[0] == -0.0199936
    assert len(Pulsing_fixture.I1) == 10


def test_R0(Pulsing_fixture):
    """Test the R0 attribute."""
    assert np.isclose(Pulsing_fixture.R0[0], (4.1558 - 4.1919) / -0.0199936)
    assert len(Pulsing_fixture.R0) == 10


def test_Rt(Pulsing_fixture):
    """Test the Rt method."""
    assert np.isclose(Pulsing_fixture.Rt(10)[0], (4.1337 - 4.1919) / -0.0199936)
    assert len(Pulsing_fixture.Rt(10)) == 10


def test_pulse_summary(Pulsing_fixture):
    """Test the pulse_summary method."""
    assert isinstance(Pulsing_fixture.pulse_summary, Result)
