from django.db import migrations


OLD_SLUG = "el-del-arquero"
OLD_NAME = "El del Arquero"
NEW_NAME = "ATAJA PENALES"
OLD_TITLE = "EL DEL ARQUERO"
NEW_TITLE = "ATAJA PENALES"


def rename_arquero_game(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameConfig = apps.get_model("games", "GameConfig")

    Game.objects.filter(slug=OLD_SLUG).update(name=NEW_NAME)

    for game_config in GameConfig.objects.filter(game__slug=OLD_SLUG):
        config = dict(game_config.config or {})
        texts = dict(config.get("texts") or {})
        if texts.get("welcome_title") != OLD_TITLE:
            continue
        texts["welcome_title"] = NEW_TITLE
        config["texts"] = texts
        game_config.config = config
        game_config.save(update_fields=["config"])


def restore_arquero_game_name(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameConfig = apps.get_model("games", "GameConfig")

    Game.objects.filter(slug=OLD_SLUG).update(name=OLD_NAME)

    for game_config in GameConfig.objects.filter(game__slug=OLD_SLUG):
        config = dict(game_config.config or {})
        texts = dict(config.get("texts") or {})
        if texts.get("welcome_title") != NEW_TITLE:
            continue
        texts["welcome_title"] = OLD_TITLE
        config["texts"] = texts
        game_config.config = config
        game_config.save(update_fields=["config"])


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rename_arquero_game, restore_arquero_game_name),
    ]
