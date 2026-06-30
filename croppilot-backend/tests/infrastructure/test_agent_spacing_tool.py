from unittest.mock import MagicMock

from app.infrastructure.agent.tools.spacing import (
    build_spacing_langchain_tool,
    calculate_crop_density_and_spacing,
)


def _mock_driver(record) -> MagicMock:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    result = MagicMock()
    result.single.return_value = record
    session.run.return_value = result
    return driver


def test_calculate_crop_density_and_spacing_computes_plant_count() -> None:
    result = calculate_crop_density_and_spacing(
        _mock_driver({"row_dist": 60.0, "plant_dist": 30.0}),
        crop_name="cabbage",
        land_area_hectares=1.0,
    )

    assert "Cabbage" in result
    assert "60.0x30.0cm" in result
    assert "5,555" in result


def test_calculate_crop_density_and_spacing_crop_not_found() -> None:
    result = calculate_crop_density_and_spacing(
        _mock_driver(None),
        crop_name="Unknown",
        land_area_hectares=1.0,
    )

    assert "could not be found" in result


def test_calculate_crop_density_and_spacing_missing_spacing_metrics() -> None:
    result = calculate_crop_density_and_spacing(
        _mock_driver({"row_dist": None, "plant_dist": 30.0}),
        crop_name="Pepper",
        land_area_hectares=0.5,
    )

    assert "spacing metrics are missing" in result


def test_spacing_langchain_tool_invokes_core_logic() -> None:
    tool = build_spacing_langchain_tool(
        _mock_driver({"row_dist": 60.0, "plant_dist": 30.0})
    )

    result = tool.invoke(
        {"crop_name": "cabbage", "land_area_hectares": 1.0},
    )

    assert "Cabbage" in result
    assert tool.name == "calculate_crop_density_and_spacing"
