conf = configuration_data()
conf.set('resource_dir', join_paths(meson.build_root(), 'src'))
conf.set('source_dir', meson.source_root())

test_file = configure_file(
  input: 'window.py.in',
  output: 'window.py',
  configuration: conf,
)

src_dir = join_paths(meson.source_root(), 'src')
tests_dir = join_paths(meson.source_root(), 'tests')

pyflakes = find_program('pyflakes', required: false)
if pyflakes.found()
  test('pyflakes', pyflakes,
    args: [src_dir, test_file])
endif

black = find_program('black', required: false)
if black.found()
  test('black', black,
    args: [src_dir, test_file])
endif

tests = [
    test_file,
]

pytest = find_program('pytest', required: false)
if pytest.found()
  test('pytest', pytest,
    args: tests)
endif
