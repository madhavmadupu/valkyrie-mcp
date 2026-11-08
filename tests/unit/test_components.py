"""The COTS database must be sourced, physically plausible and consistent with validation data."""

import pytest
from validation_cases import UIUC_APC_PEAK_ETA

from valkyrie.components import (
    BATTERIES,
    MOTORS,
    PROPELLERS,
    find_battery,
    find_motor,
    find_propeller,
)


@pytest.mark.parametrize("part", MOTORS + BATTERIES + PROPELLERS, ids=lambda p: p.model)
def test_every_part_cites_a_source(part):
    assert part.source.startswith("https://")


@pytest.mark.parametrize("battery", BATTERIES, ids=lambda b: b.model)
def test_pack_specific_energy_is_physical(battery):
    assert 120 <= battery.specific_energy_whkg <= 280  # LiPo packs ~140-190, Li-ion cells ~200-260


def test_lipo_packs_support_the_150_whkg_default():
    lipo = [b.specific_energy_whkg for b in BATTERIES if b.chemistry == "LiPo"]
    assert min(lipo) <= 150 <= max(lipo)


@pytest.mark.parametrize("prop", [p for p in PROPELLERS if p.peak_efficiency is not None], ids=lambda p: p.model)
def test_propeller_efficiency_is_the_uiuc_measured_peak(prop):
    runs = [eta for run, eta in UIUC_APC_PEAK_ETA.items() if run.startswith(prop.model.removesuffix("E") + " ")]
    assert prop.peak_efficiency == pytest.approx(max(runs))


def test_motor_power_to_weight_is_physical():
    for m in MOTORS:
        assert 3_000 <= m.max_power_w / m.mass_kg <= 15_000  # W/kg for hobby/UAV outrunners


def test_finders_filter():
    assert all(m.max_power_w >= 700 for m in find_motor(700))
    assert all(b.energy_wh >= 200 for b in find_battery(200))
    assert [p.model for p in find_propeller(14, tolerance=0.5)] == ["14x10E"]
