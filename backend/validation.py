from fastapi import HTTPException
from models import DataType, HealthRecordCreate

# Valid ranges for each data type: (min, max, expected_unit)
DATA_RANGES: dict[DataType, tuple[float, float, str | None]] = {
    DataType.steps: (0, 200_000, "count"),
    DataType.distance: (0, 500_000, "meters"),
    DataType.calories: (0, 50_000, "kcal"),
    DataType.exercise: (0, 1440, "minutes"),
    DataType.heart_rate: (20, 300, "bpm"),
    DataType.blood_pressure_systolic: (50, 300, "mmHg"),
    DataType.blood_pressure_diastolic: (20, 200, "mmHg"),
    DataType.body_temperature: (30, 45, "celsius"),
    DataType.weight: (1, 700, "kg"),
    DataType.sleep: (0, 1440, "minutes"),
    DataType.nutrition: (0, 100_000, "kcal"),
}


def validate_records(records: list[HealthRecordCreate]) -> None:
    errors = []
    for i, record in enumerate(records):
        range_info = DATA_RANGES.get(record.data_type)
        if range_info is None:
            continue
        min_val, max_val, _ = range_info
        if not (min_val <= record.value <= max_val):
            errors.append(
                f"Record {i}: {record.data_type.value} value {record.value} "
                f"out of range [{min_val}, {max_val}]"
            )
    if errors:
        raise HTTPException(status_code=422, detail=errors)
