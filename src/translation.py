from pydantic import BaseModel


class Translation(BaseModel):
    change: str = '🛠 Изменить'
    cancel: str = '❌ Отмена'
    action_canceled: str = 'Действие отменено.'
    choose_from_keyboard: str = 'Пожалуйста, выберите действие, используя клавиатуру ниже.'
    invalid_input_format: str = 'Неверный формат ввода.'
    not_enough_votes_to_delivery: str = 'Мало голосов для доставки 🙄'

    tz_current: str = 'Текущий часовой пояс'
    tz_enter: str = 'Введите часовой пояс в формате ±HH:MM.'
