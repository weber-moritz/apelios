import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_broker_client():
	"""Shared broker client mock for input-layer tests."""
	mock = MagicMock()
	mock.connect = AsyncMock()
	mock.disconnect = AsyncMock()
	mock.subscribe = AsyncMock()
	mock.publish = AsyncMock()
	return mock