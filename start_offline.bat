@echo off
title Baxmal Meat Boutique - Oflayn Tizim (MeatFlow Pro)
color 0A
echo ======================================================
echo    BAXMAL MEAT BOUTIQUE - OFLAYN DASTURI ISHGA TUSHMOQDA
echo ======================================================
echo.
echo [1] Dastur ishga tushirilmoqda: http://127.0.0.1:8000
echo [2] Brauzer avtomatik ochiladi...
echo.
start http://127.0.0.1:8000
python manage.py runserver 0.0.0.0:8000
pause
