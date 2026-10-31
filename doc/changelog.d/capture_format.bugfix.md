``ray_*`` benchmarks pass ``file_format`` to ``memray.Tracker`` instead of
relying on the library default. The plugin default remains
``FileFormat.ALL_ALLOCATIONS``. Set ``ray_file_format = "aggregated"``
for ``AGGREGATED_ALLOCATIONS``.
