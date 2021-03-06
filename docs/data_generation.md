### Генерация пар вида (номер опции, количество голосов)

1. Генерация количества опций $n \in [1, 10]$.
2. Введем множество $I$ номеров опций, $|I| = n$. Пусть $I = [0, n)$.
3. Генерация количества групп опций с одинаковым числом голосов $d \in [0, n]$.
4. Генерация множества $S$ номеров опций, которые не будут учитываться при
определении победителя,
$S = \left\lbrace x\,\vert\, x \in I \right\rbrace$, $|S| \leq n$.
5. Для каждого номера опции $i \in I$ генерируем число $d_i \in [0, d]$.
$d_i = 0$ означает, что количество голосов за опцию $i$ уникально в текущем опросе.
6. Составляем словарь $G$ из пар вида $(k, \left\lbrace i \in I\,\vert\,d_i = k \right\rbrace)$. Здесь $k \in K = \left\lbrace x\,\vert\, \exists i \in I: x = d_i \right\rbrace$.
7. Для каждого $k \in K \backslash \left\lbrace 0 \right\rbrace$ генерируем число голосов $v_k$.
8. Для каждого элемента из $G[0]$ генерируем оставшиеся элементы $v_{d+1},...,v_n$.
9. Таким образом, получаем список уникальных значений $[v_1, ..., v_d, v_{d+1}, ..., v_n]$.