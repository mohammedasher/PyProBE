"""Tests for the degradation mode analysis module."""
import math

import numpy as np
import polars as pl
import pytest
from pydantic import ValidationError

import pyprobe.analysis.base.degradation_mode_analysis_functions as dma_functions
from pyprobe.analysis.degradation_mode_analysis import DMA
from pyprobe.result import Result


def graphite_LGM50_ocp_Chen2020(sto):
    """Chen2020 graphite ocp fit."""
    u_eq = (
        1.9793 * np.exp(-39.3631 * sto)
        + 0.2482
        - 0.0909 * np.tanh(29.8538 * (sto - 0.1234))
        - 0.04478 * np.tanh(14.9159 * (sto - 0.2769))
        - 0.0205 * np.tanh(30.4444 * (sto - 0.6103))
    )

    return u_eq


def nmc_LGM50_ocp_Chen2020(sto):
    """Chen2020 nmc ocp fit."""
    u_eq = (
        -0.8090 * sto
        + 4.4875
        - 0.0428 * np.tanh(18.5138 * (sto - 0.5542))
        - 17.7326 * np.tanh(15.7890 * (sto - 0.3117))
        + 17.5842 * np.tanh(15.9308 * (sto - 0.3120))
    )

    return u_eq


n_points = 1000
z = np.linspace(0, 1, 1000)


def test_fit_ocv():
    """Test the fit_ocv method."""
    capacity = np.linspace(0, 1, n_points)
    x_real = [0.8, 0.1, 0.1, 0.7]
    x_pe_real = np.linspace(x_real[0], x_real[1], n_points)
    x_ne_real = np.linspace(x_real[2], x_real[3], n_points)

    # test charge
    voltage = nmc_LGM50_ocp_Chen2020(x_pe_real) - graphite_LGM50_ocp_Chen2020(x_ne_real)

    result = Result(
        base_dataframe=pl.DataFrame(
            {"Voltage [V]": voltage, "Capacity [Ah]": capacity}
        ),
        info={},
    )
    dma = DMA(input_data=result)
    x_guess = [0.8, 0.4, 0.2, 0.6]
    params, fit = dma.fit_ocv(
        x_ne=z,
        x_pe=z,
        ocp_ne=graphite_LGM50_ocp_Chen2020(z),
        ocp_pe=nmc_LGM50_ocp_Chen2020(z),
        x_guess=x_guess,
    )
    assert isinstance(params, Result)
    assert params.data.columns == [
        "x_pe low SOC",
        "x_pe high SOC",
        "x_ne low SOC",
        "x_ne high SOC",
        "Cell Capacity [Ah]",
        "Cathode Capacity [Ah]",
        "Anode Capacity [Ah]",
        "Li Inventory [Ah]",
    ]

    assert isinstance(fit, Result)
    assert fit.data.columns == [
        "Capacity [Ah]",
        "SOC",
        "Input Voltage [V]",
        "Fitted Voltage [V]",
        "Input dSOCdV [1/V]",
        "Fitted dSOCdV [1/V]",
        "Input dVdSOC [V]",
        "Fitted dVdSOC [V]",
    ]

    param_values = list(params.data.row(0))
    np.testing.assert_allclose(
        np.array(param_values)[:4],
        np.array(x_real),
        rtol=1e-4,
    )

    # test discharge
    voltage = np.flip(voltage)
    capacity = -1 * capacity
    result = Result(
        base_dataframe=pl.DataFrame(
            {"Voltage [V]": voltage, "Capacity [Ah]": capacity}
        ),
        info={},
    )
    dma = DMA(input_data=result)
    params, _ = dma.fit_ocv(
        x_ne=z,
        x_pe=z,
        ocp_ne=graphite_LGM50_ocp_Chen2020(z),
        ocp_pe=nmc_LGM50_ocp_Chen2020(z),
        x_guess=x_guess,
    )

    param_values = list(params.data.row(0))
    np.testing.assert_allclose(
        np.array(param_values)[:4],
        np.array(x_real),
        rtol=1e-4,
    )

    result = Result(
        base_dataframe=pl.DataFrame({"Voltage [V]": voltage, "Time [s]": capacity}),
        info={},
    )
    dma = DMA(input_data=result)
    with pytest.raises(ValidationError):
        dma.fit_ocv(
            x_ne=z,
            x_pe=z,
            ocp_ne=graphite_LGM50_ocp_Chen2020(z),
            ocp_pe=nmc_LGM50_ocp_Chen2020(z),
            x_guess=x_guess,
        )


def test_fit_ocv_discharge():
    """Test the fit_ocv method for a discharge curve."""
    n_points = 1000
    capacity = np.linspace(1, 0, n_points)
    x_real = [0.8, 0.1, 0.1, 0.7]
    x_pe_real = np.linspace(x_real[1], x_real[0], n_points)
    x_ne_real = np.linspace(x_real[3], x_real[2], n_points)
    voltage = nmc_LGM50_ocp_Chen2020(x_pe_real) - graphite_LGM50_ocp_Chen2020(x_ne_real)

    z = np.linspace(0, 1, n_points)
    ocp_pe = nmc_LGM50_ocp_Chen2020(z)
    ocp_ne = graphite_LGM50_ocp_Chen2020(z)

    x_guess = [0.8, 0.4, 0.2, 0.6]
    result = Result(
        base_dataframe=pl.DataFrame(
            {"Voltage [V]": voltage, "Capacity [Ah]": capacity}
        ),
        info={},
    )
    dma = DMA(input_data=result)
    params, _ = dma.fit_ocv(
        x_ne=z, x_pe=z, ocp_ne=ocp_ne, ocp_pe=ocp_pe, x_guess=x_guess
    )

    param_values = list(params.data.row(0))
    np.testing.assert_allclose(
        np.array(param_values)[:4],
        np.array(x_real),
        rtol=1e-4,
    )


@pytest.fixture
def bol_ne_limits_fixture():
    """Return the anode stoichiometry limits."""
    return np.array([0.02, 0.99])


@pytest.fixture
def bol_pe_limits_fixture():
    """Return the cathode stoichiometry limits."""
    return np.array([0.05, 0.9])


@pytest.fixture
def eol_ne_limits_fixture():
    """Return the anode stoichiometry limits."""
    return np.array([0.3, 0.99])


@pytest.fixture
def eol_pe_limits_fixture():
    """Return the cathode stoichiometry limits."""
    return np.array([0.05, 0.9])


@pytest.fixture
def bol_capacity_fixture(bol_ne_limits_fixture, bol_pe_limits_fixture):
    """Return the cell and electrode capacities."""
    cell_capacity = 5
    pe_capacity, ne_capacity, li_inventory = dma_functions.calc_electrode_capacities(
        bol_pe_limits_fixture[0],
        bol_pe_limits_fixture[1],
        bol_ne_limits_fixture[0],
        bol_ne_limits_fixture[1],
        cell_capacity,
    )
    return [cell_capacity, pe_capacity, ne_capacity, li_inventory]


@pytest.fixture
def eol_capacity_fixture(eol_ne_limits_fixture, eol_pe_limits_fixture):
    """Return the cell and electrode capacities."""
    cell_capacity = 4.5
    pe_capacity, ne_capacity, li_inventory = dma_functions.calc_electrode_capacities(
        eol_pe_limits_fixture[0],
        eol_pe_limits_fixture[1],
        eol_ne_limits_fixture[0],
        eol_ne_limits_fixture[1],
        cell_capacity,
    )
    return [cell_capacity, pe_capacity, ne_capacity, li_inventory]


@pytest.fixture
def bol_result_fixture(bol_capacity_fixture):
    """Return a Result instance."""
    voltage = np.linspace(0, 1, n_points)
    capacity = np.linspace(0, 1, n_points)
    result = Result(
        base_dataframe=pl.DataFrame(
            {"Voltage [V]": voltage, "Capacity [Ah]": capacity}
        ),
        info={},
    )
    dma = DMA(input_data=result)
    dma.stoichiometry_limits = Result(
        base_dataframe=pl.LazyFrame(
            {
                "Cell Capacity [Ah]": bol_capacity_fixture[0],
                "Cathode Capacity [Ah]": bol_capacity_fixture[1],
                "Anode Capacity [Ah]": bol_capacity_fixture[2],
                "Li Inventory [Ah]": bol_capacity_fixture[3],
            }
        ),
        info={},
    )
    return dma


@pytest.fixture
def eol_result_fixture(eol_capacity_fixture):
    """Return a Result instance."""
    voltage = np.linspace(0, 1, n_points)
    capacity = np.linspace(0, 1, n_points)
    result = Result(
        base_dataframe=pl.DataFrame(
            {"Voltage [V]": voltage, "Capacity [Ah]": capacity}
        ),
        info={},
    )
    dma = DMA(input_data=result)
    dma.stoichiometry_limits = Result(
        base_dataframe=pl.LazyFrame(
            {
                "Cell Capacity [Ah]": eol_capacity_fixture[0],
                "Cathode Capacity [Ah]": eol_capacity_fixture[1],
                "Anode Capacity [Ah]": eol_capacity_fixture[2],
                "Li Inventory [Ah]": eol_capacity_fixture[3],
            }
        ),
        info={},
    )
    return dma


def test_calculate_dma_parameters(
    bol_capacity_fixture, eol_capacity_fixture, bol_result_fixture, eol_result_fixture
):
    """Test the calculate_dma_parameters method."""
    expected_SOH = eol_capacity_fixture[0] / bol_capacity_fixture[0]
    expected_LAM_pe = 1 - eol_capacity_fixture[1] / bol_capacity_fixture[1]
    expected_LAM_ne = 1 - eol_capacity_fixture[2] / bol_capacity_fixture[2]
    expected_LLI = (
        bol_capacity_fixture[3] - eol_capacity_fixture[3]
    ) / bol_capacity_fixture[3]

    result = eol_result_fixture.quantify_degradation_modes(
        bol_result_fixture.stoichiometry_limits
    )
    assert result.data["SOH"].to_numpy()[1] == expected_SOH
    assert result.data["LAM_pe"].to_numpy()[1] == expected_LAM_pe
    assert result.data["LAM_ne"].to_numpy()[1] == expected_LAM_ne
    assert result.data["LLI"].to_numpy()[1] == expected_LLI
    assert result.data.columns == ["SOH", "LAM_pe", "LAM_ne", "LLI"]

    # test with missing or incorrect input data
    result = Result(
        base_dataframe=pl.DataFrame(
            {
                "Voltage [V]": np.linspace(0, 1, 10),
                "Capacity [Ah]": np.linspace(0, 1, 10),
            }
        ),
        info={},
    )


def test_average_ocvs(BreakinCycles_fixture):
    """Test the average_ocvs method."""
    break_in = BreakinCycles_fixture.cycle(0)
    break_in.set_SOC()
    dma = DMA.average_ocvs(input_data=break_in, charge_filter="constant_current(1)")
    assert math.isclose(dma.input_data.get_only("Voltage [V]")[0], 3.14476284763849)
    assert math.isclose(dma.input_data.get_only("Voltage [V]")[-1], 4.170649780122139)
    np.testing.assert_allclose(
        dma.input_data.get_only("SOC"), break_in.constant_current(1).get_only("SOC")
    )
    # test invalid input
    with pytest.raises(ValueError):
        DMA.average_ocvs(input_data=break_in.charge(0))


def test_calc_full_cell_ocv_composite():
    """Test the composite_full_cell_ocv method."""
    # Sample data
    n_points = 10
    params = [0.05, 0.01, 0.95, 0.9, 0.85]

    # Create data arrays
    z = np.linspace(0, 1, n_points)
    x_c1, ocp_c1 = z, np.linspace(1.5, 0.05, n_points)
    x_c2, ocp_c2 = z, np.linspace(2.3, 0.15, n_points)
    x_pe, ocp_pe = z, np.linspace(4, 2, n_points)
    cell_SOC = np.linspace(0, 1, n_points)

    # Run the function
    soc, y_pred = dma_functions.calc_full_cell_OCV_composite(
        SOC=cell_SOC,
        z_pe_lo=params[0],
        z_pe_hi=params[2],
        z_ne_lo=params[1],
        z_ne_hi=params[3],
        x_pe=x_pe,
        ocp_pe=ocp_pe,
        x_c1=x_c1,
        ocp_c1=ocp_c1,
        x_c2=x_c2,
        ocp_c2=ocp_c2,
        comp1_frac=params[4],
    )

    # Expected outcomes
    expected_soc = np.linspace(0, 1, n_points)
    expected_y_pred = np.array(
        [
            2.4,
            2.28091008,
            2.23166123,
            2.18241239,
            2.13316354,
            2.0839147,
            2.03466585,
            1.98541701,
            1.93616816,
            1.88691932,
        ]
    )

    # Assertions
    np.testing.assert_array_almost_equal(soc, expected_soc, decimal=8)
    np.testing.assert_array_almost_equal(y_pred, expected_y_pred, decimal=8)
