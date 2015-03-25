import sys

def inject_app_defaults(app_name):
    __import__("%s.settings" % app_name)
    # Import our defaults, project defaults, and project settings
    _app_settings = sys.modules['%s.settings' % app_name]
    _def_settings = sys.modules['django.conf.global_settings']
    _settings = sys.modules['django.conf'].settings

    # Add the values from the application.settings module
    for _k in dir(_app_settings):
        if _k.isupper():
            # Add the value to the default settings module
            setattr(_def_settings, _k, getattr(_app_settings, _k))

            # Add the value to the settings, if not already present
            if not hasattr(_settings, _k):
                setattr(_settings, _k, getattr(_app_settings, _k))

inject_app_defaults(__name__)
