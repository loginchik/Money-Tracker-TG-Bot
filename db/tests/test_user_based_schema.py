import datetime as dt
import pytest
import pytest_asyncio

from .conftest import TestDBBase
from db.user_based_schema import ExpenseLimit, Expense, Income


@pytest.mark.asyncio(scope="class")
class TestUserBasedSchema(TestDBBase):

    def setup_class(self):
        super().setup_class()

