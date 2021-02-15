conf = configuration_data()
conf.set('resource_dir', join_paths(meson.build_root(), 'src'))
conf.set('source_dir', meson.source_root())

test_window_file = configure_file(
  input: 'window.py.in',
  output: 'window.py',
  configuration: conf,
)

test_worker_file = configure_file(
  input: 'worker.py.in',
  output: 'worker.py',
  configuration: conf,
)

test_service_file = configure_file(
  input: 'service.py.in',
  output: 'service.py',
  configuration: conf,
)

src_dir = join_paths(meson.source_root(), 'src')
tests_dir = join_paths(meson.source_root(), 'tests')

pyflakes = find_program('pyflakes', required: false)
if pyflakes.found()
  test('pyflakes', pyflakes,
    args: [src_dir, test_window_file, test_worker_file])
endif

black = find_program('black', required: false)
if black.found()
  test('black', black,
    args: ['--check', src_dir, test_window_file, test_worker_file])
endif

tests = [
    test_window_file,
    test_worker_file,
]

if get_option('run_service_tests')
  tests += test_service_file
endif

pytest = find_program('pytest', required: false)
if pytest.found()
  test('pytest', pytest,
    args: tests)
endif
