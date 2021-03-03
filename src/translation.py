import locale

try:
    from locale import gettext as _
except ImportError:
    from gettext import gettext as _


def translation_init(localedir):
    try:
        locale.bindtextdomain("portfolio", localedir)
        locale.textdomain("portfolio")
    except AttributeError:
        import gettext

        gettext.bindtextdomain("portfolio", localedir)
        gettext.textdomain("portfolio")


def gettext(*args, **kwargs):
    return _(*args, **kwargs)
