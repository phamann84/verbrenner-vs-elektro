from tco_app.cli import _build_inputs, parse_args


def test_global_acquisition_mode_lease_applies_to_both_vehicles():
    args = parse_args([
        "--acquisition-mode",
        "lease",
        "--manual-fuel-price",
        "1.85",
        "--ev-lease-monthly-rate",
        "499",
        "--ice-lease-monthly-rate",
        "399",
    ])

    _, ev, ice, _ = _build_inputs(args)

    assert ev.acquisition_mode == "lease"
    assert ice.acquisition_mode == "lease"
