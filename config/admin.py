from django.contrib import admin
import config.models


@admin.register(config.models.Option)
class OptionAdmin(admin.ModelAdmin):
    """
    选项管理
    """

    list_display = [
        'name', 'value', 'format',
    ]


