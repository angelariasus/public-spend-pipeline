from datetime import date

import pytest

from public_spend.config import DEFAULT_OECE_TABLES, Period, Settings


class TestPeriod:
    def test_parse_and_format(self):
        period = Period.parse("2024-01")
        assert period == Period(2024, 1)
        assert str(period) == "2024-01"
        assert period.first_day == date(2024, 1, 1)

    @pytest.mark.parametrize("value", ["2024-1", "2024/01", "24-01", "", "2024-13"])
    def test_parse_rejects_invalid_values(self, value):
        with pytest.raises(ValueError):
            Period.parse(value)

    def test_ordering(self):
        assert Period(2024, 12) < Period(2025, 1)


class TestSettings:
    def test_defaults(self):
        settings = Settings.from_env({"WAREHOUSE_DSN": "postgresql://u:p@h/db"})
        assert settings.oece_start_period == Period(2024, 1)
        assert settings.oece_end_period is None
        assert settings.oece_tables == DEFAULT_OECE_TABLES
        assert settings.oece_base_url == "https://contratacionesabiertas.oece.gob.pe/api/v1"

    def test_overrides(self):
        settings = Settings.from_env(
            {
                "WAREHOUSE_DSN": "postgresql://u:p@h/db",
                "OECE_START_PERIOD": "2025-03",
                "OECE_END_PERIOD": "2025-06",
                "OECE_TABLES": "records, COM_AWARDS",
                "OECE_BASE_URL": "https://example.org/api/v1/",
            }
        )
        assert settings.oece_start_period == Period(2025, 3)
        assert settings.oece_end_period == Period(2025, 6)
        assert settings.oece_tables == ("records", "com_awards")
        assert settings.oece_base_url == "https://example.org/api/v1"

    def test_requires_dsn(self):
        with pytest.raises(ValueError, match="WAREHOUSE_DSN"):
            Settings.from_env({})
