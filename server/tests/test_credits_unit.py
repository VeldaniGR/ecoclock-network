"""Tests unitarios para los schemas Pydantic de créditos."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import CreditOut, CreditsSummary


def test_creditout_minimal():
	"""CreditOut se construye con los 4 campos obligatorios."""
	c = CreditOut(
		id=1,
		amount=1.0,
		task_id=42,
		granted_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc),
	)
	assert c.id == 1
	assert c.amount == 1.0
	assert c.task_id == 42


def test_creditout_rejects_negative_amount():
	"""CreditOut.amount no puede ser negativo (Field ge=0)."""
	with pytest.raises(ValidationError):
		CreditOut(
			id=1,
			amount=-0.01,
			task_id=42,
			granted_at=datetime.now(timezone.utc),
		)


def test_creditssummary_empty_recent():
	"""CreditsSummary admite recent como lista vacía por defecto."""
	s = CreditsSummary(user_id=1, username="velo", total=0.0)
	assert s.recent == []
	assert s.total == 0.0


def test_creditssummary_with_recent_credits():
	"""CreditsSummary serializa recent como lista de CreditOut."""
	s = CreditsSummary(
		user_id=1,
		username="velo",
		total=2.0,
		recent=[
			CreditOut(
				id=1,
				amount=1.0,
				task_id=10,
				granted_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc),
			),
			CreditOut(
				id=2,
				amount=1.0,
				task_id=11,
				granted_at=datetime(2026, 8, 3, 9, 5, tzinfo=timezone.utc),
			),
		],
	)
	assert len(s.recent) == 2
	assert s.recent[0].task_id == 10
