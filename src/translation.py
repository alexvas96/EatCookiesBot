from pydantic import BaseModel


class Translation(BaseModel):
    change: str = '🛠 Изменить'
    cancel: str = '❌ Отмена'
    action_canceled: str = 'Действие отменено.'
    choose_from_keyboard: str = 'Пожалуйста, выберите действие, используя клавиатуру ниже.'
    invalid_input_format: str = 'Неверный формат ввода.'
    not_enough_votes_to_delivery: str = 'Мало голосов для доставки 🙄'
    subscription_cancelled: str = 'Подписка отменена.'
    go_to_site: str = 'Перейти на сайт'
    not_set: str = 'не установлено'

    current_mailing_params: str = 'Текущее время рассылки'
    mailing_change: str = 'Изменить время рассылки'
    mailing_cancel: str = 'Отписаться от рассылки'
    mailing_time_enter: str = 'Введите время в формате HH:MM.'
    mailing_time_changed: str = 'Время рассылки изменено'

    tz_current: str = 'Текущий часовой пояс'
    tz_changed: str = 'Часовой пояс изменен'
    tz_enter: str = 'Введите часовой пояс в формате ±HH:MM.'


default_translation = Translation()
