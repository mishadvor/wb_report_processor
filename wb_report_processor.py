import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

# Заголовок приложения
st.title("📊 Обработка финансовых отчётов Wildberries")

# Выбор режима работы
mode = st.radio(
    "Выберите режим работы:", ["Один файл", "Два файла (Россия + СНГ)"], horizontal=True
)

if mode == "Один файл":
    # Загрузка одного файла
    uploaded_file = st.file_uploader(
        "Загрузите Excel-файл отчёта Wildberries", type=["xlsx", "xls"]
    )

    if uploaded_file is not None:
        try:
            # Чтение файла
            df = pd.read_excel(uploaded_file, dtype={"Баркод": str, "Размер": str})

            # Обработка данных
            with st.spinner("Обработка данных..."):
                sums1_per_category = (
                    df.groupby("Артикул поставщика")
                    .agg(
                        {
                            "Цена розничная": "sum",
                            "Вайлдберриз реализовал Товар (Пр)": "sum",
                            "К перечислению Продавцу за реализованный Товар": "sum",
                            "Услуги по доставке товара покупателю": "sum",
                        }
                    )
                    .astype(int)
                    .reset_index()
                )

                # Создание Excel файла
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    sums1_per_category.to_excel(
                        writer, sheet_name="Results", index=False
                    )

                output.seek(0)

                # Отображение результатов
                st.success("Обработка завершена!")
                st.download_button(
                    label="⬇️ Скачать отчёт",
                    data=output,
                    file_name="wildberries_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
            st.stop()
    else:
        st.warning("Пожалуйста, загрузите файл отчёта")

else:  # Режим "Два файла"
    # Загрузка двух файлов
    col1, col2 = st.columns(2)

    with col1:
        uploaded_file_russia = st.file_uploader(
            "Загрузите файл по России", type=["xlsx", "xls"]
        )

    with col2:
        uploaded_file_cis = st.file_uploader(
            "Загрузите файл по СНГ", type=["xlsx", "xls"]
        )

    if uploaded_file_russia is not None and uploaded_file_cis is not None:
        try:
            # Чтение файлов
            df_Russia = pd.read_excel(
                uploaded_file_russia, dtype={"Баркод": str, "Размер": str}
            )
            df_CIS = pd.read_excel(
                uploaded_file_cis, dtype={"Баркод": str, "Размер": str}
            )

            # Объединение данных
            df = pd.concat([df_Russia, df_CIS], ignore_index=True)

            # Обработка данных (примерная - уточните вашу логику обработки)
            with st.spinner("Обработка данных..."):

                # ============== ОБРАБОТКА ДАННЫХ ==== НАЧАЛО ========

                # Суммирование и агрегация данных
                sums1_per_category = (
                    df.groupby("Артикул поставщика")
                    .agg(
                        {
                            "Цена розничная": "sum",
                            "Вайлдберриз реализовал Товар (Пр)": "sum",
                            "К перечислению Продавцу за реализованный Товар": "sum",
                            "Услуги по доставке товара покупателю": "sum",
                        }
                    )
                    .astype(int)
                    .reset_index()
                )

                sums1_per_category["К Перечислению без Логистики"] = (
                    sums1_per_category["К перечислению Продавцу за реализованный Товар"]
                    - sums1_per_category["Услуги по доставке товара покупателю"]
                ).astype(
                    int
                )  # Преобразование в int сразу после вычисления

                sums1_per_category["Сумма СПП"] = (
                    sums1_per_category["Цена розничная"]
                    - sums1_per_category["Вайлдберриз реализовал Товар (Пр)"]
                ).astype(int)

                sums1_per_category["% Лог/рс"] = (
                    (
                        (
                            sums1_per_category["Услуги по доставке товара покупателю"]
                            / sums1_per_category[
                                "К перечислению Продавцу за реализованный Товар"
                            ]
                        )
                        * 100
                    )
                    .replace(np.inf, 100.0)
                    .round(1)
                )

                sums1_per_category["% Лог/Наша Цена"] = (
                    (
                        (
                            sums1_per_category["Услуги по доставке товара покупателю"]
                            / sums1_per_category["Цена розничная"]
                        )
                        * 100
                    )
                    .replace(np.inf, 100.0)
                    .round(1)
                )  # Заменяем inf на 100% (1.0 = 100%)

                # -11111111------------------------------

                # Фильтруем только возвраты, затем группируем по артикулу и суммируем
                returns_by_article = (
                    df[df["Тип документа"] == "Возврат"]
                    .groupby("Артикул поставщика")[
                        [
                            "Цена розничная",
                            "Вайлдберриз реализовал Товар (Пр)",
                            "К перечислению Продавцу за реализованный Товар",
                        ]
                    ]
                    .sum()
                    .fillna(0)
                    .reset_index()
                )
                # Переименовываем колонку
                returns_by_article = returns_by_article.rename(
                    columns={"Цена розничная": "Возвраты Наша цена"}
                )
                returns_by_article = returns_by_article.rename(
                    columns={
                        "Вайлдберриз реализовал Товар (Пр)": "Возвраты реализация ВБ"
                    }
                )
                returns_by_article = returns_by_article.rename(
                    columns={
                        "К перечислению Продавцу за реализованный Товар": "Возврты к перечислению"
                    }
                )

                # ---------------- Объежиняем 5 и 1 талицы --------------------------

                first_merged = sums1_per_category.merge(
                    returns_by_article, on="Артикул поставщика", how="left"
                ).fillna(
                    0
                )  # Заменяем все NaN после слияния

                # -------------------------------------------------------------------

                # Добавляем колонки Чистые продажм для трех сумм продаж

                first_merged["Чистые продажи Наши"] = (
                    first_merged["Цена розничная"] - first_merged["Возвраты Наша цена"]
                )
                first_merged["Чистая реализацич ВБ"] = (
                    first_merged["Вайлдберриз реализовал Товар (Пр)"]
                    - first_merged["Возвраты реализация ВБ"]
                )
                first_merged["Чистое Перечисление"] = (
                    first_merged["К перечислению Продавцу за реализованный Товар"]
                    - first_merged["Возврты к перечислению"]
                )
                first_merged["Чистое Перечисление без Логистики"] = (
                    first_merged["Чистое Перечисление"]
                    - first_merged["Услуги по доставке товара покупателю"]
                )

                ##########---------- Агрегация исходной таблица по Артикулам и суммы колонок ------------

                # Суммирование и агрегация данных (игнорируя нули в цене)
                cost_per_category = (
                    df.groupby("Артикул поставщика")
                    .agg(
                        {
                            "Цена розничная": lambda x: (
                                x[x != 0].mean() if any(x != 0) else 0
                            ),  # Среднее без учета нулей
                            "Вайлдберриз реализовал Товар (Пр)": lambda x: (
                                x[x != 0].mean() if any(x != 0) else 0
                            ),
                            "К перечислению Продавцу за реализованный Товар": lambda x: (
                                x[x != 0].mean() if any(x != 0) else 0
                            ),
                            "Услуги по доставке товара покупателю": lambda x: x.mean()
                            * 2,
                        }
                    )
                    .astype(int)
                    .reset_index()
                )

                cost_per_category["СПП Средняя"] = (
                    cost_per_category["Цена розничная"]
                    - cost_per_category["Вайлдберриз реализовал Товар (Пр)"]
                ).round(1)
                cost_per_category["К Перечислению без Логистики Средняя"] = (
                    cost_per_category["К перечислению Продавцу за реализованный Товар"]
                    - cost_per_category["Услуги по доставке товара покупателю"]
                ).round(1)

                cost_per_category["% Лог/Перечисление с Лог Средний"] = (
                    (
                        (
                            cost_per_category["Услуги по доставке товара покупателю"]
                            / cost_per_category[
                                "К перечислению Продавцу за реализованный Товар"
                            ]
                        )
                        * 100
                    )
                    .replace(np.inf, 100.0)
                    .round(1)
                )

                cost_per_category["% Лог/Наша цена Средний"] = (
                    (
                        (
                            cost_per_category["Услуги по доставке товара покупателю"]
                            / cost_per_category["Цена розничная"]
                        )
                        * 100
                    )
                    .replace(np.inf, 100.0)
                    .round(1)
                )  # Заменяем inf на 100% (1.0 = 100%)

                # ---------------- Объежиняем 6 и first_merged талицы --------------------------

                second_merged = first_merged.merge(
                    cost_per_category, on="Артикул поставщика", how="left"
                ).fillna(
                    0
                )  # Заменяем все NaN после слияния

                # -------------------------------------------------------------------

                second_merged = second_merged.rename(
                    columns={"Цена розничная_y": "Наша цена Средняя"}
                )
                second_merged = second_merged.rename(
                    columns={
                        "Вайлдберриз реализовал Товар (Пр)_y": "Реализация ВБ Средняя"
                    }
                )
                second_merged = second_merged.rename(
                    columns={
                        "К перечислению Продавцу за реализованный Товар_y": "К перечислению Среднее"
                    }
                )
                second_merged = second_merged.rename(
                    columns={
                        "Услуги по доставке товара покупателю_y": "Логистика Одной Юбки Средняя"
                    }
                )

                # ---------------- Объежиняем 5 + 1 + 6 + 8 Таблицы --------------------------

                # fird_merged = (second_merged.merge(cost_per_category, on='Артикул поставщика', how='left') .fillna(0))  # Заменяем все NaN после слияния

                # -------------------------------------------------------------------

                ##--  88888888----- Сортируем Колонку 'Виды логистики, штрафов и доплат' по типам и связываем с Артикулом продавца

                # 1. Сначала преобразуем списки в отдельные строки с помощью explode()
                df_exploded = df.explode("Виды логистики, штрафов и доплат")

                # 2. Заполним пропущенные значения (если есть)
                df_exploded["Виды логистики, штрафов и доплат"] = df_exploded[
                    "Виды логистики, штрафов и доплат"
                ].fillna("Не указано")

                # 3. Теперь можем группировать, считать и отсортировать по одному из сторлбцов.
                status_log = (
                    df_exploded.groupby("Артикул поставщика")[
                        "Виды логистики, штрафов и доплат"
                    ]
                    .value_counts()
                    .unstack(fill_value=0)
                    # .sort_values('', ascending=True)
                    .reset_index()
                )

                # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

                # Сначала заполним пропуски нулями во всех используемых колонках
                # for col in ['К клиенту при продаже', 'От клиента при возврате', 'От клиента при отмене']:
                #    status_log[col] = status_log[col].fillna(0)

                # Если нет какой либо колонки, особенно 'От клиента при возврате', создаем ее.
                for col in [
                    "К клиенту при продаже",
                    "От клиента при возврате",
                    "От клиента при отмене",
                ]:
                    status_log[col] = status_log.get(col, pd.Series(0)).fillna(0)

                # Расчёт %Выкупа с учетом нулевых значений в числителе и знаменателе

                numerator = status_log["К клиенту при продаже"]
                denominator = (
                    status_log["К клиенту при отмене"]
                    + status_log["К клиенту при продаже"]
                    + status_log["От клиента при возврате"]
                )

                status_log["%Выкупа"] = np.where(
                    (numerator == 0)
                    & (
                        denominator == 0
                    ),  # Новое условие: если и числитель, и знаменатель равны нулю
                    0,  # Результат: 0%
                    np.where(
                        numerator
                        == 0
                        & (
                            denominator > 0
                        ),  # Если числитель равен нулю и знаменатель положительный
                        -100,  # Результат: -100%
                        np.where(
                            denominator
                            == 0,  # Если знаменатель равен нулю, а он не может быть уже =0!
                            0,  # то переходим к обычному делению...
                            (numerator / denominator)
                            * 100,  # и тут как раз Нормальное деление
                        ).astype(int),
                    ),
                )

                # Вычисляем Себестоимость для каждого Артикула
                status_log["Себес Продаж (600р)"] = (
                    (status_log["К клиенту при продаже"]) * 600
                ).round(0)

                # Сортировка
                # status_log.sort_values(by='Чистые продажи', ascending=False, inplace=True)

                # ---------------- Объежиняем 5 + 1 + 6 + 8 Таблицы (отдельные колонки) --------------------------

                third_merged = second_merged.merge(
                    status_log[
                        [
                            "Артикул поставщика",
                            "К клиенту при продаже",
                            "%Выкупа",
                            "Себес Продаж (600р)",
                        ]
                    ],
                    on="Артикул поставщика",
                    how="left",
                ).fillna(
                    0
                )  # Заменяем все NaN после слияния

                # -------------------------------------------------------------------

                # Переименовываем столбцы ---------------------------------------
                third_merged = third_merged.rename(
                    columns={"К клиенту при продаже": "Кол-во Продаж"}
                )
                third_merged = third_merged.rename(
                    columns={"Цена розничная_x": "Сумма Продаж Наша Цена"}
                )
                third_merged = third_merged.rename(
                    columns={
                        "Вайлдберриз реализовал Товар (Пр)_x": "Сумма Продаж по цене ВБ"
                    }
                )
                third_merged = third_merged.rename(
                    columns={
                        "К перечислению Продавцу за реализованный Товар_x": "Сумма Продаж Перечислени С Лог"
                    }
                )
                third_merged = third_merged.rename(
                    columns={"Услуги по доставке товара покупателю_x": "Логистика"}
                )
                # third_merged = third_merged.rename(columns={'Услуги по доставке товара покупателю_x': 'Логистика'})

                # ---------  Колонка Маржа ---------------------------
                third_merged["Маржа"] = (
                    third_merged["Чистое Перечисление без Логистики"]
                    - third_merged["Себес Продаж (600р)"]
                ).round(1)

                # ---------- Колонка Налог --------------------------

                third_merged["Налоги"] = (
                    third_merged["Чистая реализацич ВБ"] * 0.07
                ).round(1)

                # --------- Колонка Прибыль ---------------------------------
                third_merged["Прибыль"] = (
                    third_merged["Маржа"] - third_merged["Налоги"]
                ).round(1)

                # ------------------------------------------------------------

                # Сортировка по колонке Сумма Продаж Наша Цена
                third_merged.sort_values(
                    by="Сумма Продаж Наша Цена", ascending=False, inplace=True
                )

                print(third_merged.head(10).to_string(index=False))

                ##Записываем в один файл на разные страницы. Если это одно число, не забываем делать DF/Siries
                # with pd.ExcelWriter('/content/Sums_FinRepWB_Sveta.xlsx') as writer:
                #  third_merged.to_excel(writer, sheet_name='Test', index=False)

                # ------- Вормируем общие суммы в таблицу по нужным колонкам ------------

                # print(totall_summary)

                ##### --------- Логистика/Штрафы/Все Удержания  -----###################

                # Группируем и считаем данные
                all_add_log = (
                    df.groupby("Обоснование для оплаты")
                    .agg(
                        {
                            "Услуги по доставке товара покупателю": "sum",
                            "Общая сумма штрафов": "sum",
                            "Хранение": "sum",
                            "Удержания": "sum",
                            "Платная приемка": "sum",
                        }
                    )
                    .reset_index()
                )

                # Создаем DataFrame с итоговыми суммами
                totall_summary = pd.DataFrame(
                    {
                        "Колонка": [
                            "Логистика",
                            "Сумма СПП",
                            "Сумма Чистых продаж без Возвратов и Логистики",
                            "Кол-во Продаж, Шт",
                            "Себестоимость продаж",
                            "Прибыль без налога",
                            "Штрафы",
                            "Хранение",
                            "Удержания",
                            "Платная приемка",
                            "Итого: прибыль минус доп. удержания",  # Добавляем итоговую строку
                        ],
                        "Общая сумма": [
                            third_merged["Логистика"].sum(),
                            third_merged["Сумма СПП"].sum(),
                            third_merged["Чистое Перечисление без Логистики"].sum(),
                            third_merged["Кол-во Продаж"].sum(),
                            third_merged["Себес Продаж (600р)"].sum(),
                            third_merged["Прибыль"].sum(),
                            all_add_log["Общая сумма штрафов"].sum(),
                            all_add_log["Хранение"].sum(),
                            all_add_log["Удержания"].sum(),
                            all_add_log["Платная приемка"].sum(),
                            # расчет итоговой прибыли:
                            third_merged["Прибыль"].sum()
                            - (
                                all_add_log["Общая сумма штрафов"].sum()
                                + all_add_log["Хранение"].sum()
                                + all_add_log["Удержания"].sum()
                                + all_add_log["Платная приемка"].sum()
                            ),
                        ],
                    }
                )

                ###############   Юбки летние  Soft    ###################################

                # Группировка ТОЛЬКО артикулов с "Софт"
                summary_soft = (
                    df[
                        df["Артикул поставщика"].str.contains(
                            "Софт", case=False, na=False
                        )
                    ]
                    .groupby("Артикул поставщика", as_index=False)
                    .agg(
                        {
                            "Цена розничная": [
                                ("Сумма продаж наша цена (Софт)", "sum"),
                                (
                                    "Средняя Наша цена (Софт)",
                                    lambda x: x[x != 0].mean(),
                                ),
                            ]
                        }
                    )
                    .round(0)
                    .astype(int, errors="ignore")
                )

                # Переименование столбцов
                summary_soft.columns = [
                    "Артикул поставщика",
                    "Сумма продаж (Софт)",
                    "Цена средняя (Софт)",
                ]

                # Сортировка
                summary_soft.sort_values(
                    by="Сумма продаж (Софт)", ascending=False, inplace=True
                )

                # ================ ОБРАБОТКА ДАННЫХ ==== КОНЕЦ ============================

                # Создание Excel файла
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    sums1_per_category.to_excel(
                        writer, sheet_name="Summary_Table_by_Art", index=False
                    )
                    totall_summary.to_excel(
                        writer, sheet_name="Totall_Summary", index=False
                    )
                    summary_soft.to_excel(
                        writer, sheet_name="Soft_Summary", index=False
                    )

                output.seek(0)

                # Отображение результатов
                st.success("Обработка завершена!")
                st.download_button(
                    label="⬇️ Скачать отчёт",
                    data=output,
                    file_name="wildberries_report_combined.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
            st.stop()
    else:
        st.warning("Пожалуйста, загрузите оба файла")





'''
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

# Заголовок приложения
st.title("📊 Обработка финансовых отчётов Wildberries")

# Загрузка файла через интерфейс
uploaded_file = st.file_uploader("Загрузите Excel-файл отчёта Wildberries", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Чтение исходного файла с указанием типов данных
        df = pd.read_excel(uploaded_file, dtype={'Баркод': str, 'Размер': str})

        # ===== ОБРАБОТКА ДАННЫХ =====
        # Суммирование и агрегация данных
        sums1_per_category = df.groupby('Артикул поставщика').agg({
            'Цена розничная': 'sum',
            'Вайлдберриз реализовал Товар (Пр)': 'sum',
            'К перечислению Продавцу за реализованный Товар': 'sum',
            'Услуги по доставке товара покупателю': 'sum'
        }).astype(int).reset_index()

        sums1_per_category['К Перечислению без Логистики'] = (
            sums1_per_category['К перечислению Продавцу за реализованный Товар'] - 
            sums1_per_category['Услуги по доставке товара покупателю']
        ).astype(int)

        sums1_per_category['Сумма СПП'] = (
            sums1_per_category['Цена розничная'] - 
            sums1_per_category['Вайлдберриз реализовал Товар (Пр)']
        ).astype(int)

        sums1_per_category['% Лог/рс'] = (
            (sums1_per_category['Услуги по доставке товара покупателю'] /
            sums1_per_category['К перечислению Продавцу за реализованный Товар']) * 100
        ).replace(np.inf, 100.0).round(1)

        sums1_per_category['% Лог/Наша Цена'] = (
            (sums1_per_category['Услуги по доставке товара покупателю'] /
            sums1_per_category['Цена розничная']) * 100
        ).replace(np.inf, 100.0).round(1)

        # Фильтруем только возвраты
        returns_by_article = (
            df[df['Тип документа'] == 'Возврат']
            .groupby('Артикул поставщика')
            [['Цена розничная', 'Вайлдберриз реализовал Товар (Пр)',
              'К перечислению Продавцу за реализованный Товар']]
            .sum()
            .fillna(0)
            .reset_index()
        )

        returns_by_article = returns_by_article.rename(columns={
            'Цена розничная': 'Возвраты Наша цена',
            'Вайлдберриз реализовал Товар (Пр)': 'Возвраты реализация ВБ',
            'К перечислению Продавцу за реализованный Товар': 'Возврты к перечислению'
        })

        # Объединяем таблицы
        first_merged = sums1_per_category.merge(
            returns_by_article,
            on='Артикул поставщика',
            how='left'
        ).fillna(0)

        # Добавляем колонки Чистые продажи
        first_merged['Чистые продажи Наши'] = first_merged['Цена розничная'] - first_merged['Возвраты Наша цена']
        first_merged['Чистая реализацич ВБ'] = first_merged['Вайлдберриз реализовал Товар (Пр)'] - first_merged['Возвраты реализация ВБ']
        first_merged['Чистое Перечисление'] = first_merged['К перечислению Продавцу за реализованный Товар'] - first_merged['Возврты к перечислению']
        first_merged['Чистое Перечисление без Логистики'] = first_merged['Чистое Перечисление'] - first_merged['Услуги по доставке товара покупателю']

        # Средние значения
        cost_per_category = df.groupby('Артикул поставщика').agg({
            'Цена розничная': lambda x: x[x != 0].mean() if any(x != 0) else 0,
            'Вайлдберриз реализовал Товар (Пр)': lambda x: x[x != 0].mean() if any(x != 0) else 0,
            'К перечислению Продавцу за реализованный Товар': lambda x: x[x != 0].mean() if any(x != 0) else 0,
            'Услуги по доставке товара покупателю': lambda x: x.mean() * 2
        }).astype(int).reset_index()

        cost_per_category['СПП Средняя'] = (
            cost_per_category['Цена розничная'] -
            cost_per_category['Вайлдберриз реализовал Товар (Пр)']
        ).round(1)

        cost_per_category['К Перечислению без Логистики Средняя'] = (
            cost_per_category['К перечислению Продавцу за реализованный Товар'] -
            cost_per_category['Услуги по доставке товара покупателю']
        ).round(1)

        cost_per_category['% Лог/Перечисление с Лог Средний'] = (
            (cost_per_category['Услуги по доставке товара покупателю'] /
             cost_per_category['К перечислению Продавцу за реализованный Товар']) * 100
        ).replace(np.inf, 100.0).round(1)

        cost_per_category['% Лог/Наша цена Средний'] = (
            (cost_per_category['Услуги по доставке товара покупателю'] /
             cost_per_category['Цена розничная']) * 100
        ).replace(np.inf, 100.0).round(1)

        # Объединяем таблицы
        second_merged = first_merged.merge(
            cost_per_category,
            on='Артикул поставщика',
            how='left'
        ).fillna(0)

        second_merged = second_merged.rename(columns={
            'Цена розничная_y': 'Наша цена Средняя',
            'Вайлдберриз реализовал Товар (Пр)_y': 'Реализация ВБ Средняя',
            'К перечислению Продавцу за реализованный Товар_y': 'К перечислению Среднее',
            'Услуги по доставке товара покупателю_y': 'Логистика Одной Юбки Средняя'
        })

        # Обработка логистики
        df_exploded = df.explode('Виды логистики, штрафов и доплат')
        df_exploded['Виды логистики, штрафов и доплат'] = df_exploded['Виды логистики, штрафов и доплат'].fillna('Не указано')

        status_log = (
            df_exploded.groupby('Артикул поставщика')
            ['Виды логистики, штрафов и доплат']
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )

        for col in ['К клиенту при продаже', 'От клиента при возврате', 'От клиента при отмене']:
            status_log[col] = status_log.get(col, pd.Series(0)).fillna(0)

        numerator = status_log['К клиенту при продаже']
        denominator = (
            status_log['К клиенту при отмене'] +
            status_log['К клиенту при продаже'] +
            status_log['От клиента при возврате']
        )

        status_log['%Выкупа'] = np.where(
            (numerator == 0) & (denominator == 0),
            0,
            np.where(
                numerator == 0 & (denominator > 0),
                -100,
                np.where(
                    denominator == 0,
                    0,
                    (numerator / denominator) * 100
                ).astype(int)
            )
        )

        status_log['Себес Продаж (600р)'] = (status_log['К клиенту при продаже'] * 600).round(0)

        # Финальное объединение
        third_merged = second_merged.merge(
            status_log[['Артикул поставщика', 'К клиенту при продаже', '%Выкупа', 'Себес Продаж (600р)']],
            on='Артикул поставщика',
            how='left'
        ).fillna(0)

        # Переименование столбцов
        third_merged = third_merged.rename(columns={
            'К клиенту при продаже': 'Кол-во Продаж',
            'Цена розничная_x': 'Сумма Продаж Наша Цена',
            'Вайлдберриз реализовал Товар (Пр)_x': 'Сумма Продаж по цене ВБ',
            'К перечислению Продавцу за реализованный Товар_x': 'Сумма Продаж Перечислени С Лог',
            'Услуги по доставке товара покупателю_x': 'Логистика'
        })

        # Расчеты
        third_merged['Маржа'] = (third_merged['Чистое Перечисление без Логистики'] - third_merged['Себес Продаж (600р)']).round(1)
        third_merged['Налоги'] = (third_merged['Чистая реализацич ВБ'] * 0.07).round(1)
        third_merged['Прибыль'] = (third_merged['Маржа'] - third_merged['Налоги']).round(1)
        third_merged.sort_values(by='Сумма Продаж Наша Цена', ascending=False, inplace=True)

        # Формирование итоговой таблицы
        all_add_log = df.groupby('Обоснование для оплаты').agg({
            'Услуги по доставке товара покупателю': 'sum',
            'Общая сумма штрафов': 'sum',
            'Хранение': 'sum',
            'Удержания': 'sum',
            'Платная приемка': 'sum'
        }).reset_index()

        totall_summary = pd.DataFrame({
            'Колонка': [
                'Логистика',
                'Сумма СПП',
                'Сумма Чистых продаж без Возвратов и Логистики',
                'Кол-во Продаж, Шт',
                'Себестоимость продаж',
                'Прибыль без налога',
                'Штрафы',
                'Хранение',
                'Удержания',
                'Платная приемка',
                'Итого: прибыль минус доп. удержания'
            ],
            'Общая сумма': [
                third_merged['Логистика'].sum(),
                third_merged['Сумма СПП'].sum(),
                third_merged['Чистое Перечисление без Логистики'].sum(),
                third_merged['Кол-во Продаж'].sum(),
                third_merged['Себес Продаж (600р)'].sum(),
                third_merged['Прибыль'].sum(),
                all_add_log['Общая сумма штрафов'].sum(),
                all_add_log['Хранение'].sum(),
                all_add_log['Удержания'].sum(),
                all_add_log['Платная приемка'].sum(),
                third_merged['Прибыль'].sum() - (
                    all_add_log['Общая сумма штрафов'].sum() +
                    all_add_log['Хранение'].sum() +
                    all_add_log['Удержания'].sum() +
                    all_add_log['Платная приемка'].sum()
                )
            ]
        })

        # Обработка "Софт" товаров
        summary_soft = (
            df[df['Артикул поставщика'].str.contains('Софт', case=False, na=False)]
            .groupby('Артикул поставщика', as_index=False)
            .agg({
                'Цена розничная': [
                    ('Сумма продаж наша цена (Софт)', 'sum'),
                    ('Средняя Наша цена (Софт)', lambda x: x[x != 0].mean())
                ]
            })
            .round(0)
            .astype(int, errors='ignore')
        )
        summary_soft.columns = ['Артикул поставщика', 'Сумма продаж (Софт)', 'Цена средняя (Софт)']
        summary_soft.sort_values(by='Сумма продаж (Софт)', ascending=False, inplace=True)

        # Создаем Excel-файл в памяти
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            third_merged.to_excel(writer, sheet_name='Summary_Table_by_Art', index=False)
            totall_summary.to_excel(writer, sheet_name='Totall_Summary', index=False)
            summary_soft.to_excel(writer, sheet_name='Soft_Summary', index=False)
        
        output.seek(0)

        # Показываем результат
        st.success("Обработка завершена!")
        st.download_button(
            label="⬇️ Скачать отчёт",
            data=output,
            file_name="wildberries_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Произошла ошибка: {str(e)}")
        st.stop()
else:
    st.warning("Пожалуйста, загрузите файл отчёта Wildberries")
'''
