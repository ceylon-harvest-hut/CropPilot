from app.infrastructure.agent.tool_trace import records_from_tool_round


def test_records_from_tool_round_maps_calls_and_results() -> None:
    records = records_from_tool_round(
        [
            {
                "name": "calculate_crop_density_and_spacing",
                "args": {"crop_name": "Cabbage", "land_area_hectares": 0.5},
            }
        ],
        ["Needs 2,500 plants."],
    )

    assert len(records) == 1
    assert records[0].name == "calculate_crop_density_and_spacing"
    assert records[0].arguments["crop_name"] == "Cabbage"
    assert records[0].result == "Needs 2,500 plants."
