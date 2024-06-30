import os
import datetime as dt
from random import randint
from loguru import logger

import pandas as pd
import numpy as np

from plotly.subplots import make_subplots
from plotly import graph_objects as go
from PIL import Image, ImageOps

from configs import BASE_DIR
from bot.routers.common_router import MessageTexts as MT


class GraphCreator:
    def __init__(self, data, user_lang):
        self.data = data
        self.user_lang = user_lang

        self.MAIN_COLOR = '#4a08ff'
        self.MAIN_COLOR_RGB = (75, 10, 255)
        self.COMPLEMENT_RGB = (151, 149, 255)
        self.LIGHT_COLOR = '#cbcaff'
        self.FONT_SIZE = 12

        self.temp_folder = os.path.join(BASE_DIR, 'temp')
        os.makedirs(self.temp_folder, exist_ok=True)

    def create_expense_cards(self, user_id, min_date, max_bars=5, user_nickname=None):
        """
        Creates expense report graphs: line plot, bar chart and map.

        Args:
            user_id (int): User's id for filenames.
            min_date (dt.date): Axes min date.
            max_bars (int): Axes max bars.
            user_nickname (str): User's nickname.

        Returns:
            tuple[str]: Paths to graph files.
        """
        graph_paths = []

        # Create line bar
        line = self.__line_plot(user_nickname=user_nickname, min_date=min_date, type_='expense')
        line_fp = self.__img_filename(user_id)
        line.write_image(line_fp, width=1000, height=500, format='png', scale=3)
        self.__add_border(line_fp)
        logger.info(f'Created {line_fp}')
        graph_paths.append(line_fp)

        # Categories bar chart
        categories_data = self.data.groupby('category')['amount'].sum().sort_values(ascending=False)
        categories_bar = self.__bar_chart(data=categories_data, max_bars=max_bars)
        # Subcategories bar chart
        subcategories_data = self.data.groupby('subcategory')['amount'].sum().sort_values(ascending=False)
        subcategories_bar = self.__bar_chart(data=subcategories_data, max_bars=max_bars)

        # Create bars graph
        titles = ['Наиболее затратные категории' if self.user_lang == 'ru' else 'Most expensive categories',
                  'Наиболее затратные подкатегории' if self.user_lang == 'ru' else 'Most expensive subcategories']
        bars = make_subplots(rows=1, cols=2, horizontal_spacing=0.15, subplot_titles=titles)
        bars.add_trace(categories_bar, row=1, col=1)
        bars.update_xaxes(visible=False)
        bars.update_yaxes(visible=True)
        bars.add_trace(subcategories_bar, row=1, col=2)
        bars.update_layout(title=self.__title(user_nickname, type_='expense'), **self.__figure_layout_static_kwargs())

        bars_fp = self.__img_filename(user_id)
        bars.write_image(bars_fp, width=1000, height=500, format='png', scale=3)
        self.__add_border(bars_fp)
        logger.info(f'Created {bars_fp}')
        graph_paths.append(bars_fp)

        # Create map
        data_2 = self.data.to_crs(4326)
        data_2 = data_2[~data_2.location.isna()]
        location_x_min = (data_2.location.x >= (data_2.location.x.median() - data_2.location.x.quantile(0.99)))
        location_x_max = (data_2.location.x <= (data_2.location.x.median() + data_2.location.x.quantile(0.99)))
        location_y_min = (data_2.location.y >= (data_2.location.y.median() - data_2.location.y.quantile(0.99)))
        location_y_max = (data_2.location.y <= (data_2.location.y.median() + data_2.location.y.quantile(0.99)))
        data_2 = data_2[location_x_min & location_x_max & location_y_min & location_y_max]
        if data_2.shape[0] > 0:
            map_graph = self.__map_plot(data=data_2)
            map_graph_fp = self.__img_filename(user_id)
            map_graph.write_image(map_graph_fp, width=500, height=600, format='png', scale=3)
            self.__add_border(map_graph_fp)
            logger.info(f'Created {map_graph_fp}')
            graph_paths.append(map_graph_fp)

        return graph_paths

    def create_income_cards(self, user_id, min_date, user_nickname=None):
        """
        Creates incomes report graph.

        Args:
            user_id (int): User's id for filenames.
            min_date (dt.date): Axes min date.
            user_nickname (str): User's nickname.

        Returns:
            str: Path to file.
        """
        line = self.__line_plot(user_nickname=user_nickname, min_date=min_date, type_='income')
        line_fp = self.__img_filename(user_id)
        line.write_image(line_fp, width=1000, height=500, format='png', scale=3)
        self.__add_border(line_fp)
        logger.info(f'Created {line_fp}')

        return line_fp

    def __title(self, user_nickname, type_='expense'):
        """
        Creates main graph title.

        Args:
            user_nickname (str): Nickname of the user.

        Returns:
            str: Title.
        """
        # Generate daterange
        try:
            min_date = MT.format_date(self.data.event_time.min().date())
            max_date = MT.format_date(self.data.event_time.max().date())
        except AttributeError:
            min_date = MT.format_date(self.data.event_date.min())
            max_date = MT.format_date(self.data.event_date.max())
        title_daterange = '-'.join([min_date, max_date])

        # Create language-specific title
        if self.user_lang == 'ru':
            if type_ == 'expense':
                title = f'Отчёт о расходах в период {title_daterange}'
            else:
                title = f'Отчёт о доходах в период {title_daterange}'
        else:
            if type_ == 'expense':
                title = f'Expenses report for the period of {title_daterange}'
            else:
                title = f'Incomes report for the period of {title_daterange}'

        # Add nickname
        if user_nickname is not None:
            title += f' (@{user_nickname})'

        return title

    def __img_filename(self, user_id):
        """
        Generates unique filename to save temp image for sending it to user.

        Args:
            user_id (int): User id.

        Returns:
            str: Filepath.
        """
        dt_stamp = dt.datetime.now().strftime('%y%m%d%H%M%S')
        ext = '.png'

        fn = f'{dt_stamp}_{user_id}'

        while os.path.exists(os.path.join(self.temp_folder, fn + ext)):
            fn += str(randint(1, 10))

        fp = os.path.join(self.temp_folder, fn + ext)
        return fp

    def __line_plot(self, min_date, user_nickname, type_):
        """
        Creates line plot.

        Args:
            min_date (dt.date): Axes min date
            user_nickname (str): User's nickname.
            type_ (str): Type of line plot: income / expense.

        Returns:
            go.Figure: Line plot.
        """
        date_list = pd.date_range(start=min_date, end=dt.date.today()).date

        figure = go.Figure()
        max_y = 0

        group_column = 'category' if type_ == 'expense' else 'passive_status'
        sort_column = 'event_time' if type_ == 'expense' else 'event_date'

        if type_ == 'income':
            self.data[group_column] = self.data[group_column].map({
                True: 'Пассивный' if self.user_lang == 'ru' else 'Passive',
                False: 'Активный' if self.user_lang == 'ru' else 'Active',
            })

        self.data = self.data.sort_values(by=[sort_column], ascending=True)

        categories_list = self.data[group_column].unique()
        gradient = self.__gradient(len(categories_list))
        categories_total_amount = self.data.groupby(group_column)['amount'].sum().sort_values(ascending=False)
        categories_colors = dict(zip(categories_total_amount.index, gradient))
        del categories_total_amount

        for category in categories_list:
            data_slice = self.data[self.data[group_column] == category]
            current_max = data_slice['amount'].max()
            current_color = categories_colors[category]
            max_y = max(max_y, current_max)

            line = go.Scatter(x=data_slice[sort_column], y=data_slice['amount'],
                              **self.__line_plot_static_kwargs(marker_color=current_color))
            figure.add_trace(line)
            annotation_data = dict(x=line.x[-1], y=line.y[-1], text=category)
            figure.add_annotation(**annotation_data, font=dict(color=current_color))

        figure.update_xaxes(**self.__line_plot_xaxis_kwargs(date_list))
        figure.update_yaxes(**self.__line_plot_yaxis_kwargs(max_y))
        figure.update_layout(title=self.__title(user_nickname=user_nickname, type_=type_),
                             **self.__figure_layout_static_kwargs())

        return figure

    def __line_plot_static_kwargs(self, marker_color=None):
        return dict(
            line=dict(color=self.LIGHT_COLOR, width=1, dash='dot'),
            mode='lines+markers',
            marker=dict(color=self.MAIN_COLOR if marker_color is None else marker_color),
        )

    def __line_plot_xaxis_kwargs(self, date_list):
        general_kwargs = dict(
            showgrid=True,
            gridwidth=0.5,
            linewidth=1,
            gridcolor=self.LIGHT_COLOR,
            tickformat='%d.%m.%Y'
        )

        general_kwargs['title'] = MT('Дата', 'Date').get(self.user_lang)
        if len(date_list) / 3 < 2:
            general_kwargs['tickvals'] = date_list
            general_kwargs['ticktext'] = date_list
        else:
            general_kwargs['tickvals'] = date_list[::3]
            general_kwargs['ticktext'] = date_list[::3]

        return general_kwargs

    def __line_plot_yaxis_kwargs(self, max_y):
        y_step = np.floor(max_y / 15)
        yticks = np.arange(0, max_y + y_step, y_step)

        general_kwargs = dict(
            showgrid=True,
            gridwidth=0.5,
            linewidth=1,
            gridcolor=self.LIGHT_COLOR,
            tickformat='{:.2f}',
            title_font=dict(size=self.FONT_SIZE, color=self.MAIN_COLOR),
            tickfont=dict(color=self.MAIN_COLOR),
            tickvals=yticks,
            ticktext=yticks
        )
        general_kwargs['title'] = MT('Сумма покупки', 'Expense amount').get(self.user_lang)

        return general_kwargs

    def __bar_chart(self, data, max_bars=5):
        other_name = MT('Иное', 'Other').get(self.user_lang)

        # Cut bars
        if data.shape[0] > max_bars:
            other = data.iloc[max_bars:].sum()
            categorical_data = data.iloc[:max_bars]
            categorical_data[other_name] = other

        # Sort bars
        data = data.sort_values(ascending=True)

        # Create bar
        bar = go.Bar(x=data.values, y=data.index, text=data.values, **self.__bar_chart_static_kwargs())
        return bar

    def __bar_chart_static_kwargs(self):
        return dict(
            orientation='h',
            textangle=0,
            textposition='auto',
            marker=dict(color=self.MAIN_COLOR)
        )

    def __map_plot(self, data):
        figure = make_subplots(rows=1, cols=1, specs=[[{'type': 'mapbox'}]])

        figure.add_trace(go.Scattermapbox(
            lat=data.location.y,
            lon=data.location.x,
            mode='markers',
            marker=dict(size=np.log2(data.amount), opacity=1, color=self.MAIN_COLOR, sizemin=2),
        ), row=1, col=1)

        map_center = {
            "lat": data['location'].y.mean(),
            "lon": data['location'].x.mean()
        }

        max_bound = max(abs(data.location.x.max() - data.location.x.min()),
                        abs(data.location.y.max() - data.location.y.min())) * 111
        if max_bound != 0:
            zoom = 12 - np.log(max_bound)
        else:
            zoom = 10

        title = 'Наиболее популярные места совершения покупок' \
            if self.user_lang == 'ru' else 'Most popular expense locations'

        figure.update_layout(
            width=500, height=600,
            title=title,
            title_font=dict(size=self.FONT_SIZE, color=self.LIGHT_COLOR),
            mapbox_style="carto-positron",
            mapbox_zoom=zoom,
            mapbox_center=map_center,
            margin={"r": 0, "t": self.FONT_SIZE * 2.5, "l": 0, "b": 0},
            paper_bgcolor=self.MAIN_COLOR,
        )

        return figure

    def __figure_layout_static_kwargs(self):
        return dict(
            title_font=dict(size=self.FONT_SIZE * 1.618, color=self.MAIN_COLOR),
            font=dict(family='Arial', size=self.FONT_SIZE, color=self.MAIN_COLOR),
            plot_bgcolor='white',
            paper_bgcolor='white',
            width=1000, height=1000,
            showlegend=False,
            margin={'t': 100, 'b': 10, 'l': 150, 'r': 50},
        )

    def __add_border(self, img_path, border_width=None):
        """
        Adds border around the image.

        Args:
            img_path (str): Path to image.
            border_width (int): Width of border in px. Defaults to image width / 100.
        """
        img = Image.open(img_path)
        if border_width is None:
            border_width = int(img.width / 100)

        # Добавьте ободку к изображению
        bordered_image = ImageOps.expand(img, border=border_width, fill=self.MAIN_COLOR_RGB)
        bordered_image.save(img_path)

    def __gradient(self, steps):
        """
        Generates gradient between self.MAIN_COLOR_RGB and self.COMPLEMENT_RGB

        Args:
            steps (int): number of steps

        Returns:
            np.ndarray: Gradient values.
        """
        color1 = np.array(self.MAIN_COLOR_RGB)
        color2 = np.array(self.COMPLEMENT_RGB)

        steps_array = np.linspace(0, 1, steps)

        gradient = np.outer(steps_array, color2 - color1) + color1
        gradient_rbg = []
        for gr in gradient:
            gr_int = list(map(int, gr))
            gr_rgb = f'rgb({",".join(map(str, gr_int))})'
            gradient_rbg.append(gr_rgb)
        return gradient_rbg


