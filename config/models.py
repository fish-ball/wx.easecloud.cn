from django.db import models
from django.contrib.auth.models import User, Group, Permission


class Option(models.Model):
    """
    选项类，系统的全局选项
    """

    OPTION_FORMAT_CHOICES = (
        ('text', '文本'),
        ('number', '数字'),
        ('json', 'JSON 对象'),
        ('file', '文件对象'),
        ('choice_single', '单项选择'),
        ('choice_multiple', '多项选择'),
    )

    name = models.CharField(
        verbose_name='选项关键字',
        primary_key=True,
        max_length=100
    )

    title = models.CharField(
        verbose_name='选项标题',
        max_length=100,
        default='',
    )

    value = models.TextField(
        verbose_name='选项值',
        blank=True,
        default='',
    )

    format = models.CharField(
        verbose_name='选项格式',
        max_length=20,
        default='text',
        choices=OPTION_FORMAT_CHOICES,
    )

    meta_data = models.TextField(
        verbose_name='辅助数据',
        blank=True,
        default='',
    )

    def __str__(self):
        return '%s(%s)' % (self.name, self.value)

    class Meta:
        db_table = 'config_option'
        verbose_name = '选项'
        verbose_name_plural = '选项'

    @staticmethod
    def get(name, default=''):
        opt = Option.objects.filter(name=name).first()
        return opt.value if opt else default

    @staticmethod
    def get_list(name, delimiter=',', default=()):
        val = Option.get(name)
        return val.split(delimiter) if val else default

    @staticmethod
    def set(name, value):
        opt = Option.objects.filter(name=name).first()
        opt = opt or Option(name=name, value=value)
        opt.value = value
        opt.save()
        return opt.value

    @staticmethod
    def is_user_in_option_groups(user, option_name):
        """
        返回一个用户是否在选项指定的组中
        """
        return Group.objects.filter(
            user=user, user__is_active=True,
            name__in=(Option.get(option_name).split(','))
        ).exists()

    def user_list(self):
        """
        返回组列表选项对应的用户列表
        """
        return User.objects.filter(
            is_active=True,
            groups__name__in=(self.value.split(',')),
        ).distinct()

    @staticmethod
    def get_users_in_option_groups(option_name):
        """
        返回指定的选项组里面涉及的所有用户
        """
        option = Option.objects.filter(name=option_name).first()
        return option and option.user_list() or User.objects.none()

