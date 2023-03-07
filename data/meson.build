desktop_file = i18n.merge_file(
  input: 'dev.tchx84.Portfolio.desktop.in',
  output: 'dev.tchx84.Portfolio.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

appstream_file = i18n.merge_file(
  input: 'dev.tchx84.Portfolio.metainfo.xml.in',
  output: 'dev.tchx84.Portfolio.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

install_data('dev.tchx84.Portfolio.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data('dev.tchx84.Portfolio-symbolic.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/symbolic/apps')
)

install_data('dev.tchx84.Portfolio.checkbox-symbolic.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/symbolic/apps')
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', '--nonet', appstream_file]
  )
endif

install_data('dev.tchx84.Portfolio.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

install_data('dev.tchx84.Portfolio.rules',
  install_dir: join_paths(get_option('datadir'), 'polkit-1/rules.d'),
  install_mode: 'rw-r--r--'
)

conf = configuration_data()
conf.set('prefix', get_option('prefix'))
conf.set('bindir', get_option('bindir'))

configure_file(
  input: 'dev.tchx84.Portfolio.service.in',
  output: get_option('service_filename'),
  configuration: conf,
  install_dir: join_paths(get_option('datadir'), 'dbus-1', 'services')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif
