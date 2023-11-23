INSERT INTO public.place_types (id,"name") OVERRIDING SYSTEM VALUE VALUES
	 (1,'Рестораны, кафе'),
	 (2,'Фастфуд'),
	 (3,'Другое');

SELECT setval('place_types_id_seq', 3);

INSERT INTO public.places (id,"name",url,place_type_id,choice_message,is_delivery) OVERRIDING SYSTEM VALUE VALUES
	 (1,'Смола','https://yandex.ru/maps/org/smola/49061841656',1,NULL,true),
	 (2,'Madame Vy','https://madamevy.ru',1,NULL,true),
	 (3,'UROK','https://eda.yandex.ru/spb/r/urok',1,NULL,true),
	 (4,'Яндекс.Лавка','https://lavka.yandex.ru/2',2,NULL,true),
	 (5,'Столовая «Уральский мост»','https://xn--80aqdcejojlflb4j.xn--p1ai',1,NULL,true),
	 (6,'Не заказываю',NULL,3,'Мало голосов для доставки 🙄',false);

SELECT setval('places_id_seq', 6);
