python = import('python')
python_bin = python.find_installation('python3')
python_dir = join_paths(get_option('prefix'), python_bin.get_install_dir())

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(python_dir, meson.project_name())
gnome = import('gnome')

dependency('libhandy-1', version : '>= 1.5')

gnome.compile_resources('portfolio',
  'portfolio.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'dev.tchx84.Portfolio.in',
  output: 'dev.tchx84.Portfolio',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

portfolio_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'popup.py',
  'worker.py',
  'places.py',
  'utils.py',
  'service.py',
  'place.py',
  'translation.py',
  'cache.py',
  'settings.py',
  'trash.py',
  'devices.py',
  'properties.py',
  'about.py',
  'passphrase.py',
  'placeholder.py',
]

install_data(portfolio_sources, install_dir: moduledir)
