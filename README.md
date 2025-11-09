## 1. Клонировать репозиторий
## 2. Собрать и запустить проект:
   ### docker compose up --build
## 3. После сборки перейти по адресу
  ### http://localhost:8000


# Использование:

   
   При переходе по адресу http://localhost:8000 открывается главная страница, где будет поле для ввода города и показ погоды для этого города.

   
   <img width="538" height="172" alt="image" src="https://github.com/user-attachments/assets/7aac8eb4-00bd-437f-aac8-be37a5169967" />
   <img width="402" height="394" alt="image" src="https://github.com/user-attachments/assets/2f38cea2-17a7-422d-86e7-590315ed84a2" />

   Чтобы просмотреть история своих запросов, необходима нажать на ссылку "История", которая находится внизу страницы. После этого открывается страница с историей запросов, где вы можете посмотреть все запросы, отфильтровать их по городу или дате, а также экспортировать нужные данные в csv.

   
   <img width="877" height="415" alt="image" src="https://github.com/user-attachments/assets/2ea51cf3-dd9a-49a9-bc4c-d532bdee7b06" />


   Чтобы запустить тесты, необходимо в терминале ввести комманду
   ### docker compose run web pytest


