import datetime as dt

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column
from sqlalchemy import Sequence
from sqlalchemy import ForeignKey
from sqlalchemy import SmallInteger, Integer
from sqlalchemy import Date, DateTime
from sqlalchemy import String
from sqlalchemy import select, exists, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


shared_meta = MetaData(schema='shared')
SharedBase = declarative_base(metadata=shared_meta)


class BotUser(SharedBase):
    """
    Bot user table.
    """
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    tg_id = Column(Integer, primary_key=True, nullable=False, comment='User TG ID')
    tg_username = Column(String(32), nullable=True, comment='User TG username')
    tg_first_name = Column(String(255), nullable=True, comment='User TG first name')
    registration_date = Column(Date, nullable=False, default=dt.date.today(), comment='User registration date')
    last_interaction = Column(DateTime, nullable=False, default=dt.datetime.now(), comment='User last interaction',
                              onupdate=dt.datetime.now())
    web_password = Column(String(12), nullable=True, comment='User web password')
    lang = Column(String(3), nullable=True, comment='User language', default='en')

    @classmethod
    async def create(cls, tg_id, tg_username, lang, async_session, tg_first_name=None):
        """
        Saves new user in DB if they do not exist yet.

        Args:
            tg_id (int): User TG id.
            tg_username (str): User TG username.
            lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): Session.
            tg_first_name (str): User TG first name.
            web_password (str): User web password.
        """
        # Check user doesn't exist yet
        exists_status = await cls.exists(user_id=tg_id, async_session=async_session)
        if exists_status:
            raise ValueError('User with such ID already exists')

        async with async_session() as session:
            user = cls.__new__(cls)
            user.__init__(tg_id=tg_id, tg_username=tg_username, tg_first_name=tg_first_name, lang=lang)
            session.add(user)
            await session.commit()

    @classmethod
    async def exists(cls, user_id, async_session):
        """
        Checks if user with such id exists in database.

        Args:
            user_id (int): User id value to check user.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            bool: True if user exists in database.
        """
        # Generate exists query
        query = select(exists(cls)).where(user_id == cls.tg_id)
        # Query data from db
        async with async_session() as session:
            data = await session.execute(query)

        return data.scalar() is not None

    @classmethod
    async def get_by_id(cls, user_id, async_session):
        """
        Gets user object by their telegram ID value.

        Args:
            user_id (int): User id.
            async_session (async_sessionmaker[AsyncSession]): async_sessionmaker to request AsyncSession.

        Returns:
            BotUser | None: User object, if exists, else None.
        """
        query = select(cls).where(user_id == cls.tg_id)
        async with async_session() as session:
            data = await session.execute(query)
        result = data.one_or_none()
        return result[0] if result else None

    @classmethod
    async def update(cls, tg_id, async_session, new_username=None, new_first_name=None,
                     new_web_password=None, new_lang=None):
        user_to_update = await cls.get_by_id(user_id=tg_id, async_session=async_session)
        if user_to_update:
            update_values = dict()
            if new_username: update_values['tg_username'] = new_username
            if new_first_name: update_values['tg_first_name'] = new_first_name
            if new_web_password: update_values['web_password'] = new_web_password
            if new_lang: update_values['lang'] = new_lang

            if len(update_values) > 0:
                statement = update(cls).where(tg_id == cls.tg_id).values(**update_values)
                async with async_session() as session:
                    await session.execute(statement)
                    await session.commit()
            else:
                raise ValueError('Provide at lease one new value')

        else:
            raise ValueError('User with such ID does not exist')

    @classmethod
    async def delete(cls, tg_id, async_session):
        user = await cls.get_by_id(user_id=tg_id, async_session=async_session)
        if user is not None:
            async with async_session() as session:
                await session.delete(user)
                await session.commit()
        else:
            raise ValueError('User with such ID does not exist')


class ExpenseCategory(SharedBase):
    """
    Expense category table.
    """
    __tablename__ = 'expense_category'
    __table_args__ = {'extend_existing': True}

    id = Column(SmallInteger, Sequence('expense_category_id_seq', schema='shared'), primary_key=True, autoincrement=True,
                nullable=False, comment='Category ID')
    title_ru = Column(String(length=20), nullable=False, default='Без названия', comment='Category russian title')
    title_en = Column(String(length=25), nullable=False, default='No title', comment='Category english title')
    slug = Column(String(length=10), nullable=False, default='untitled', comment='Category slug')

    @classmethod
    async def get_all_categories(cls, async_session):
        """
        Generate dict of available title categories.

        Resulting dict structure is: { category id: { "ru": category title in russian, "en": category title in english } }

        Args:
            async_session (async_sessionmaker[AsyncSession]): Async sessionmaker object to request AsyncSession object.

        Returns:
            dict[str, dict[str, str]]: Dict of available title categories.
        """
        # Query data from db
        query = select(cls).where(1 != cls.id)
        async with async_session() as session:
            data = await session.execute(query)
        # Convert db data to dict
        categories_dict = dict()
        for category in data.scalars():
            categories_dict[category.id] = {
                'ru': category.title_ru,
                'en': category.title_en,
            }
        return categories_dict

    @classmethod
    async def get_category_by_id(cls, category_id, async_session):
        """
        Get category object by its id.

        Args:
            category_id (int): Target category's id.
            async_session (async_sessionmaker[AsyncSession]): Async sessionmaker object to request AsyncSession object.

        Returns:
            ExpenseCategory | None: Category object or None, if object with specified id does not exist.
        """
        # Query
        query = select(cls).where(category_id == cls.id)
        async with async_session() as session:
            data = await session.execute(query)
        # Decode
        category = data.one_or_none()
        return category[0] if category is not None else None

    @classmethod
    async def insert_or_update(cls, category_id, title_ru, title_en, slug, async_session):
        async with async_session() as session:
            data = await session.execute(select(cls).where(cls.id == category_id))
        result = data.one_or_none()

        if result is None:
            new_ = cls.__new__(cls)
            new_.__init__(id=category_id, title_ru=title_ru, title_en=title_en, slug=slug)
            async with async_session() as session:
                session.add(new_)
                await session.commit()
            return f'Added new category {category_id}'
        else:
            result = result[0]
            if result.title_ru != title_ru or result.title_en != title_en or result.slug != slug:
                async with async_session() as session:
                    session.execute(
                        update(cls).where(cls.id == category_id).values(title_ru=title_ru, title_en=title_en,
                                                                        slug=slug))
                    await session.commit()
                return f'Updated category {category_id}'


class ExpenseSubcategory(SharedBase):
    """
    Expense subcategory table.
    """
    __tablename__ = 'expense_subcategory'
    __table_args__ = {'extend_existing': True}

    id = Column(SmallInteger, Sequence('expense_subcategory_id_seq', schema='shared'), primary_key=True, autoincrement=True,
                nullable=False)
    title_ru = Column(String(length=50), nullable=False, default='Без названия', comment='Category russian title')
    title_en = Column(String(length=50), nullable=False, default='No title', comment='Category english title')
    slug = Column(String(length=25), nullable=False, default='untitled', comment='Category slug')
    category = Column(SmallInteger, ForeignKey(column=ExpenseCategory.id, name='expense_subcategory_category_fk',
                                               onupdate='CASCADE', ondelete='CASCADE'),
                      default=1, nullable=False, comment='Parent category ID')

    @classmethod
    async def get_by_category(cls, category: ExpenseCategory | int, async_session):
        """
        Get subcategories dict for specified category.

        Category can be specified both by ExpenseCategory object or category int value.
        Resulting dict structure is: { subcategory id: { "ru": subcategory title in russian, "en": subcategory title in english } }

        Args:
            category (ExpenseCategory | int): Target category object to get id from or category id int value.
            async_session (async_sessionmaker[AsyncSession]): Async sessionmaker object to request AsyncSession object.

        Returns:
            dict[str, dict[str, str]]: Dict of subcategories.
        """
        # Generate query
        if isinstance(category, ExpenseCategory):
            query = select(cls).where(1 != cls.id).where(category.id == cls.category)
        elif isinstance(category, int):
            query = select(cls).where(1 != cls.id).where(category == cls.category)
        else:
            raise TypeError('category must be ExpenseCategory or int')

        # Query data
        async with async_session() as session:
            data = await session.execute(query)

        # Convert data to dict
        subcategories_dict = dict()
        for subcategory in data.scalars():
            subcategories_dict[subcategory.id] = {
                'ru': subcategory.title_ru,
                'en': subcategory.title_en,
            }

        return subcategories_dict

    @classmethod
    async def get_by_id(cls, subcategory_id, async_session):
        """
        Get subcategory object by its id.

        Args:
            subcategory_id (int): Target subcategory's id.
            async_session (async_sessionmaker[AsyncSession]): Async sessionmaker object to request AsyncSession object.

        Returns:
            ExpenseSubcategory | None: Subcategory object or None, if object with specified id does not exist.
        """
        query = select(cls).where(subcategory_id == cls.id)
        async with (async_session() as session):
            data = await session.execute(query)
        subcategory = data.one_or_none()
        return subcategory[0] if subcategory is not None else None

    @classmethod
    async def insert_or_update(cls, subcategory_id, title_ru, title_en, slug, category_id, async_session):
        async with async_session() as session:
            data = await session.execute(select(cls).where(subcategory_id == cls.id))
        result = data.one_or_none()

        if result is None:
            new_ = cls.__new__(cls)
            new_.__init__(id=subcategory_id, title_ru=title_ru, title_en=title_en, slug=slug, category=category_id)
            async with async_session() as session:
                session.add(new_)
                await session.commit()
            return f'Added new subcategory {subcategory_id} for category {category_id}'
        else:
            result = result[0]
            if result.title_ru != title_ru or result.title_en != title_en or result.slug != slug or result.category != category_id:
                async with async_session() as session:
                    session.execute(
                        update(cls).where(subcategory_id == cls.id).values(title_ru=title_ru, title_en=title_en, slug=slug, category=category_id))
                    await session.commit()
                return f'Updated subcategory {subcategory_id}'


class ExpenseLimitPeriod(SharedBase):
    """
    Expense limit period table.
    """
    __tablename__ = 'expense_limit_periods'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, Sequence(name='expense_limit_periods_id_seq', schema='shared'), primary_key=True, nullable=False)
    period = Column(SmallInteger, nullable=False, comment='Period in days')

    def calculate_end_date(self, start_date):
        """
        Calculate end date for specified period.

        Args:
            start_date (datetime.date): Start date of period.

        Returns:
            datetime.date: End date of period.
        """
        return start_date + dt.timedelta(days=self.period)

    @classmethod
    async def get_by_id(cls, period_id, async_session):
        async with async_session() as session:
            data = await session.execute(select(cls).where(cls.id == period_id))
        result = data.one_or_none()
        return result[0] if result is not None else None

    @classmethod
    async def insert_or_update(cls, period_id, period_value, async_session):
        async with async_session() as session:
            data = await session.execute(select(cls).where(period_id == cls.id))
        result = data.one_or_none()

        if result is None:
            new_ = cls.__new__(cls)
            new_.__init__(id=period_id, period=period_value)
            async with async_session() as session:
                session.add(new_)
                await session.commit()
            return f'Added new limit period {period_id}'
        else:
            result = result[0]
            if result.period != period_value:
                async with async_session() as session:
                    session.execute(
                        update(cls).where(period_id == cls.id).values(period=period_value))
                    await session.commit()
                return f'Updated limit period {period_id}'


def setup_shared_schema(setup_engine, drop_first=False):
    """
    Requests engine to reflect current database structure in shared schema.
    Creates all tables that are not present.

    Args:
        setup_engine (sqlalchemy.engine.Engine): SQLAlchemy engine to connect to database.
        drop_first (bool): Drop all tables in schema if exists before reflecting.
    """
    if drop_first:
        with setup_engine.connect() as conn:
            with conn.begin():
                for table in SharedBase.metadata.tables.values():
                    conn.execute(text(f'''DROP TABLE IF EXISTS {table.schema}.{table.name} CASCADE;'''))
    SharedBase.metadata.create_all(bind=setup_engine, checkfirst=True)
