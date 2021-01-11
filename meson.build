project('portfolio',  
          version: '0.9.4',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')


subdir('data')
subdir('src')
subdir('po')
subdir('tests')

meson.add_install_script('build-aux/meson/postinstall.py')
