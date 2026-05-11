docker exec -it botbox_web env TESTING=1 DJANGO_SETTINGS_MODULE=BotBoxWeb.settings python -m pytest tests/ "$@"
