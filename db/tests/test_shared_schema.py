import datetime as dt
import pytest
import pytest_asyncio

from .conftest import TestDBBase
from db.shared_schema import BotUser, ExpenseCategory, ExpenseSubcategory, ExpenseLimitPeriod


@pytest.mark.asyncio(scope="class")
class TestSharedSchema(TestDBBase):

    def setup_class(self):
        super().setup_class()
        self.user_id = 1
        self.user_name = 'username'
        self.user_lang = 'ru'

    async def test_exists(self):
        exists_status = await BotUser.exists(user_id=2, async_session=self.maker)
        assert exists_status is False

    async def test_save_user(self):
        # Create new user
        new_user = await BotUser.create(tg_id=self.user_id, tg_username=self.user_name, lang=self.user_lang,
                                        async_session=self.maker)
        assert new_user is None

        # Check it exists
        exists_status = await BotUser.exists(user_id=self.user_id, async_session=self.maker)
        assert exists_status is True

        # Check it cannot be created again
        with pytest.raises(ValueError) as e:
            await BotUser.create(tg_id=self.user_id, tg_username=self.user_name, lang=self.user_lang,
                                 async_session=self.maker)
            assert str(e.value) == 'User with such ID already exists'

    async def test_get_by_id(self):
        user = await BotUser.get_by_id(self.user_id, async_session=self.maker)
        assert isinstance(user, BotUser)
        assert user.tg_id == self.user_id
        assert user.tg_username == self.user_name
        assert user.lang == self.user_lang
        assert isinstance(user.registration_date, dt.date)
        assert isinstance(user.last_interaction, dt.datetime)
        assert user.registration_date == user.last_interaction.date()

    async def test_update(self):
        with pytest.raises(ValueError) as e:
            await BotUser.update(tg_id=self.user_id, async_session=self.maker)
            assert str(e.value) == 'Provide at lease one new value'

        with pytest.raises(ValueError) as e:
            await BotUser.update(tg_id=1000, async_session=self.maker)
            assert str(e.value) == 'User with such ID does not exist'

        initial_user = await BotUser.get_by_id(self.user_id, async_session=self.maker)
        initial_interaction_date = initial_user.last_interaction

        new_username = 'userusername'
        await BotUser.update(tg_id=self.user_id, async_session=self.maker, new_username=new_username)
        self.user_name = new_username

        user = await BotUser.get_by_id(self.user_id, async_session=self.maker)
        assert user.tg_username == self.user_name
        assert user.lang == self.user_lang
        assert initial_interaction_date < user.last_interaction

    async def test_delete(self):
        await BotUser.delete(tg_id=self.user_id, async_session=self.maker)
        exists_status = await BotUser.exists(user_id=self.user_id, async_session=self.maker)
        assert exists_status is False

    async def test_expense_limit_period(self):
        period = ExpenseLimitPeriod(period=7)
        known_date = dt.date(2024, 4, 5)
        future_date = period.calculate_end_date(known_date)
        assert future_date == dt.date(2024, 4, 12)

    async def test_categories(self):
        category_id = 2
        subcategory_id = 2

        category = ExpenseCategory(id=category_id, title_en='category', title_ru='категория', slug='cat')
        subcategory = ExpenseSubcategory(id=subcategory_id, title_en='subcategory', title_ru='подкатегория', slug='subcat', category=category_id)

        async with self.maker() as session:
            session.add(category)
            session.add(subcategory)
            await session.commit()

        all_categories = await ExpenseCategory.get_all_categories(self.maker)
        assert isinstance(all_categories, dict)
        assert all_categories[category_id]['en'] == category.title_en
        assert all_categories[category_id]['ru'] == category.title_ru

        all_subcategories = await ExpenseSubcategory.get_by_category(category, self.maker)
        assert all_subcategories[subcategory_id]['en'] == subcategory.title_en
        assert all_subcategories[subcategory_id]['ru'] == subcategory.title_ru
        assert isinstance(all_subcategories, dict)

        cat = await ExpenseCategory.get_category_by_id(category_id, self.maker)
        assert cat.title_en == category.title_en
        assert cat.title_ru == category.title_ru
        assert cat.slug == category.slug

        subcat = await ExpenseSubcategory.get_by_id(subcategory_id, self.maker)
        assert subcat.title_en == subcategory.title_en
        assert subcat.title_ru == subcategory.title_ru
        assert subcat.slug == subcategory.slug
        assert subcat.category == subcategory.category == category.id
